#!/usr/bin/env python3
"""Verify pull-request routing and source-bound public artifact releases."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request


REPOSITORY = "EndurantDevs/ai-healthporta"
CHECKS = {
    "validate.yml": {"validate-artifacts", "conformance-smoke"},
    "content-guard.yml": {"content-guard"},
}
GITHUB_ACTIONS_APP = 15368
POLICY_STATUS = "release-policy"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def api(path: str, data: dict | None = None) -> dict | list:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        data=json.dumps(data).encode() if data is not None else None,
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def pages(path: str, key: str | None = None) -> list:
    values = []
    separator = "&" if "?" in path else "?"
    for page in range(1, 21):
        payload = api(f"{path}{separator}per_page=100&page={page}")
        batch = payload[key] if key else payload
        values.extend(batch)
        if len(batch) < 100:
            return values
    raise ValueError("GitHub evidence exceeds the bounded pagination limit")


def commit(ref: str) -> dict:
    return api("commits/" + urllib.parse.quote(ref, safe=""))


def accepted_validation(sha: str, branch: str) -> list[dict]:
    check_runs = pages(f"commits/{sha}/check-runs?filter=all", "check_runs")
    evidence = []
    for workflow, names in CHECKS.items():
        query = urllib.parse.urlencode({"branch": branch, "event": "push", "head_sha": sha})
        runs = pages(f"actions/workflows/{workflow}/runs?{query}", "workflow_runs")
        matches = [run for run in runs if run["head_sha"] == sha
                   and run["head_branch"] == branch and run["event"] == "push"
                   and run["path"] == f".github/workflows/{workflow}"
                   and run["head_repository"]["full_name"] == REPOSITORY]
        require(bool(matches), f"no exact {branch} push validation for {workflow}")
        run = max(matches, key=lambda item: item["id"])
        require(run["status"] == "completed" and run["conclusion"] == "success",
                f"latest exact {branch} {workflow} validation is not successful")
        ids = {}
        for name in sorted(names):
            matching_checks = [check for check in check_runs if check["name"] == name
                               and check["head_sha"] == sha
                               and check["app"]["id"] == GITHUB_ACTIONS_APP
                               and check["check_suite"]["id"] == run["check_suite_id"]]
            require(bool(matching_checks), f"missing authenticated {name} check")
            check = max(matching_checks, key=lambda item: item["id"])
            require(check["status"] == "completed" and check["conclusion"] == "success",
                    f"latest authenticated {name} check is not successful")
            ids[name] = check["id"]
        evidence.append({"workflow": workflow, "run_id": run["id"],
                         "run_attempt": run["run_attempt"], "check_run_ids": ids})
    return evidence


def accepted_dev(release: dict) -> str:
    footer = release["commit"]["message"].strip().split("\n\n")[-1].splitlines()
    trailers = [line for line in footer if line.startswith("Accepted-Dev:")]
    require(len(trailers) == 1 and bool(re.fullmatch(r"Accepted-Dev: [0-9a-f]{40}", trailers[0])),
            "release commit requires one Accepted-Dev: <40-character SHA> trailer")
    return trailers[0].split(": ", 1)[1]


def release_commit(pr: dict) -> dict:
    require(pr["head"]["repo"]["full_name"] == REPOSITORY
            and pr["head"]["ref"] not in {"main", "dev"},
            "main releases must use a temporary same-repository branch")
    commits = pages(f"pulls/{int(pr['number'])}/commits")
    require(len(commits) == 1 and commits[0]["sha"] == pr["head"]["sha"],
            "main release pull request must contain exactly one commit")
    release = commit(pr["head"]["sha"])
    require(len(release["parents"]) == 1, "release commit must have only one parent")
    return release


def pull_request(event: dict) -> dict:
    current = api(f"pulls/{int(event['number'])}")
    require(current["state"] == "open" and current["base"]["repo"]["full_name"] == REPOSITORY,
            "pull request is not open against this repository")
    require(current["head"]["sha"] == event["pull_request"]["head"]["sha"]
            and current["base"]["ref"] == event["pull_request"]["base"]["ref"],
            "pull request changed after this validation event")
    if current["base"]["ref"] == "dev":
        return {"target": "dev", "head_sha": current["head"]["sha"]}
    require(current["base"]["ref"] == "main", "ordinary pull requests must target dev")
    main, dev = commit("main"), commit("dev")
    release = release_commit(current)
    require(current["base"]["sha"] == main["sha"], "release base must be current main")
    require([parent["sha"] for parent in release["parents"]] == [main["sha"]],
            "release commit must have current main as its only parent")
    require(accepted_dev(release) == dev["sha"]
            and release["commit"]["tree"]["sha"] == dev["commit"]["tree"]["sha"],
            "release trailer and tree must exactly match current dev")
    evidence = accepted_validation(dev["sha"], "dev")
    require(commit("main")["sha"] == main["sha"] and commit("dev")["sha"] == dev["sha"],
            "release branches moved during validation")
    return {"target": "main", "head_sha": release["sha"], "dev_sha": dev["sha"],
            "tree_sha": dev["commit"]["tree"]["sha"], "validation": evidence}


def report_pull_request(event: dict) -> dict:
    """Post the protected-main policy result to the exact PR head, never PR code."""
    sha = event["pull_request"]["head"]["sha"]
    require(bool(re.fullmatch(r"[0-9a-f]{40}", sha)), "invalid PR head SHA")
    base = event["pull_request"]["base"]["ref"]
    context = POLICY_STATUS + "/" + (base if base in {"main", "dev"} else "invalid")
    target = f"https://github.com/{REPOSITORY}/actions/runs/{int(os.environ['GITHUB_RUN_ID'])}"

    def status(state: str) -> None:
        api(f"statuses/{sha}", {"state": state, "context": context,
                               "target_url": target,
                               "description": "Protected-main release policy: " + state})

    status("pending")
    try:
        require(os.environ["GITHUB_EVENT_NAME"] == "pull_request_target"
                and os.environ["GITHUB_REF"] == "refs/heads/main",
                "policy reporting requires the protected main PR target workflow")
        checkout = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        require(checkout == os.environ["GITHUB_SHA"] == commit("main")["sha"],
                "policy checkout must be the current main event commit")
        result = pull_request(event)
        require(commit("main")["sha"] == checkout, "policy main moved during validation")
        current = api(f"pulls/{int(event['number'])}")
        require(current["state"] == "open" and current["head"]["sha"] == sha
                and current["base"]["ref"] == base, "PR changed during policy reporting")
    except Exception:
        status("failure")
        raise
    status("success")
    return result


def merged_release(main: dict) -> dict:
    prs = []
    for associated in pages(f"commits/{main['sha']}/pulls"):
        if associated["base"]["ref"] != "main":
            continue
        pr = api(f"pulls/{int(associated['number'])}")
        if (pr["merged"] and pr["state"] == "closed"
                and pr["base"]["ref"] == "main"
                and pr["base"]["repo"]["full_name"] == REPOSITORY
                and pr["merge_commit_sha"] == main["sha"]):
            prs.append(pr)
    require(len(prs) == 1, "current main requires one authenticated merged release PR")
    pr = prs[0]
    release = release_commit(pr)
    dev_sha = accepted_dev(release)
    dev, current_dev = commit(dev_sha), commit("dev")
    require(len(main["parents"]) == 1
            and [parent["sha"] for parent in main["parents"]]
            == [parent["sha"] for parent in release["parents"]]
            and main["commit"]["tree"]["sha"] == release["commit"]["tree"]["sha"]
            == dev["commit"]["tree"]["sha"] and accepted_dev(main) == dev_sha,
            "merged main must preserve the release parent, DEV trailer and exact DEV tree")
    ancestry = api(f"compare/{dev_sha}...{current_dev['sha']}")
    require(ancestry["status"] in {"ahead", "identical"}
            and ancestry["merge_base_commit"]["sha"] == dev_sha,
            "accepted DEV commit must remain in dev history")
    evidence = accepted_validation(dev_sha, "dev")
    require(commit("dev")["sha"] == current_dev["sha"], "dev moved during validation")
    return {"pr_number": pr["number"], "head_sha": release["sha"],
            "dev_sha": dev_sha, "tree_sha": dev["commit"]["tree"]["sha"],
            "validation": evidence}


def publication(event_name: str, ref: str, checkout_sha: str) -> dict:
    require((event_name == "workflow_dispatch" and ref == "refs/heads/main")
            or (event_name == "push" and ref.startswith("refs/tags/v")),
            "public artifacts require a version tag or a dispatch from main")
    main = commit("main")
    require(checkout_sha == main["sha"] == commit(ref)["sha"],
            "release checkout and requested ref must resolve to current main")
    mapping = merged_release(main)
    evidence = accepted_validation(main["sha"], "main")
    require(commit("main")["sha"] == main["sha"] and commit(ref)["sha"] == main["sha"],
            "release ref moved during validation")
    return {"main_sha": main["sha"], "tree_sha": main["commit"]["tree"]["sha"],
            "release": mapping, "validation": evidence}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["pull-request", "report-pull-request", "publication"])
    args = parser.parse_args()
    require(os.environ["GITHUB_REPOSITORY"] == REPOSITORY, "unexpected repository")
    if args.mode in {"pull-request", "report-pull-request"}:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        if args.mode == "report-pull-request":
            result = report_pull_request(event)
        else:
            require(os.environ["GITHUB_EVENT_NAME"] == "pull_request", "unexpected PR event")
            result = pull_request(event)
    else:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        require(bool(re.fullmatch(r"[0-9a-f]{40}", sha)), "invalid checkout commit")
        result = publication(os.environ["GITHUB_EVENT_NAME"], os.environ["GITHUB_REF"], sha)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (KeyError, TypeError, ValueError) as error:
        raise SystemExit(f"Release policy rejected: {error}") from None
