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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def api(path: str) -> dict | list:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
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
    require(current["head"]["repo"]["full_name"] == REPOSITORY
            and current["head"]["ref"] not in {"main", "dev"},
            "main releases must use a temporary same-repository branch")
    main, dev = commit("main"), commit("dev")
    commits = pages(f"pulls/{int(event['number'])}/commits")
    require(current["base"]["sha"] == main["sha"] and len(commits) == 1
            and commits[0]["sha"] == current["head"]["sha"],
            "main release must contain exactly one commit against current main")
    release = commit(current["head"]["sha"])
    require([parent["sha"] for parent in release["parents"]] == [main["sha"]],
            "release commit must have current main as its only parent")
    require(release["commit"]["tree"]["sha"] == dev["commit"]["tree"]["sha"],
            "release tree must exactly match current dev")
    evidence = accepted_validation(dev["sha"], "dev")
    require(commit("main")["sha"] == main["sha"] and commit("dev")["sha"] == dev["sha"],
            "release branches moved during validation")
    return {"target": "main", "head_sha": release["sha"], "dev_sha": dev["sha"],
            "tree_sha": dev["commit"]["tree"]["sha"], "validation": evidence}


def publication(event_name: str, ref: str, checkout_sha: str) -> dict:
    require((event_name == "workflow_dispatch" and ref == "refs/heads/main")
            or (event_name == "push" and ref.startswith("refs/tags/v")),
            "public artifacts require a version tag or a dispatch from main")
    main = commit("main")
    require(checkout_sha == main["sha"] == commit(ref)["sha"],
            "release checkout and requested ref must resolve to current main")
    evidence = accepted_validation(main["sha"], "main")
    require(commit("main")["sha"] == main["sha"] and commit(ref)["sha"] == main["sha"],
            "release ref moved during validation")
    return {"main_sha": main["sha"], "tree_sha": main["commit"]["tree"]["sha"],
            "validation": evidence}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["pull-request", "publication"])
    args = parser.parse_args()
    require(os.environ["GITHUB_REPOSITORY"] == REPOSITORY, "unexpected repository")
    if args.mode == "pull-request":
        require(os.environ["GITHUB_EVENT_NAME"] == "pull_request", "unexpected PR event")
        result = pull_request(json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text()))
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
