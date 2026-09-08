from __future__ import annotations

import copy
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import URLError


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("policy", ROOT / "scripts/check_release_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
MAIN, DEV, RELEASE = "1" * 40, "2" * 40, "3" * 40
TREE = "4" * 40


def commit(sha, tree=TREE, parents=(), accepted=DEV):
    return {"sha": sha, "commit": {"tree": {"sha": tree},
                                   "message": f"Release\n\nAccepted-Dev: {accepted}"},
            "parents": [{"sha": parent} for parent in parents]}


class ReleasePolicyTests(unittest.TestCase):
    def proposal(self, target="main"):
        current = {"number": 7, "state": "open", "base": {"ref": target, "sha": MAIN,
                   "repo": {"full_name": policy.REPOSITORY}},
                   "head": {"ref": "temporary-candidate", "sha": RELEASE,
                            "repo": {"full_name": policy.REPOSITORY}}}
        event = {"number": 7, "pull_request": copy.deepcopy(current)}
        return current, event

    def test_initial_development_pr_needs_no_prior_development_validation(self):
        current, event = self.proposal("dev")
        with patch.object(policy, "api", return_value=current), \
                patch.object(policy, "accepted_validation") as validation:
            self.assertEqual(policy.pull_request(event)["target"], "dev")
        validation.assert_not_called()

    def test_main_release_is_one_parent_one_commit_and_exact_development_tree(self):
        for failure in (None, "base", "count", "parent", "tree", "trailer", "fork", "permanent", "moved"):
            with self.subTest(failure=failure):
                current, event = self.proposal()
                revisions = {"main": commit(MAIN), "dev": commit(DEV),
                             RELEASE: commit(RELEASE, parents=[MAIN])}
                commits = [{"sha": RELEASE}]
                if failure == "base": current["base"]["sha"] = "a" * 40
                if failure == "count": commits.append({"sha": DEV})
                if failure == "parent": revisions[RELEASE]["parents"].append({"sha": DEV})
                if failure == "tree": revisions[RELEASE]["commit"]["tree"]["sha"] = "b" * 40
                if failure == "trailer": revisions[RELEASE]["commit"]["message"] = f"Accepted-Dev: {MAIN}"
                if failure == "fork": current["head"]["repo"]["full_name"] = "other/ai-healthporta"
                if failure == "permanent": current["head"]["ref"] = "dev"
                if failure == "moved": current["head"]["sha"] = DEV
                with patch.object(policy, "api", return_value=current), \
                        patch.object(policy, "pages", return_value=commits), \
                        patch.object(policy, "commit", side_effect=lambda ref: revisions[ref]), \
                        patch.object(policy, "accepted_validation", return_value=[]) as validate:
                    if failure:
                        with self.assertRaises(ValueError): policy.pull_request(event)
                    else:
                        result = policy.pull_request(event)
                        self.assertEqual(result["dev_sha"], DEV)
                        self.assertEqual(result["tree_sha"], TREE)
                        validate.assert_called_once_with(DEV, "dev")

    def test_accepted_dev_is_one_full_sha_trailer_in_the_footer(self):
        for message in ("Release", "Accepted-Dev: short", f"Accepted-Dev: {DEV}\n\nBody",
                        f"Accepted-Dev: {DEV}\nAccepted-Dev: {MAIN}",
                        f"Accepted-Dev: {DEV}\nAccepted-Dev: invalid"):
            release = commit(RELEASE)
            release["commit"]["message"] = message
            with self.subTest(message=message), self.assertRaises(ValueError):
                policy.accepted_dev(release)
        self.assertEqual(policy.accepted_dev(commit(RELEASE)), DEV)

    def test_trusted_reporting_checks_main_and_posts_failure_for_rejected_or_stale_pr(self):
        environment = {"GITHUB_RUN_ID": "99", "GITHUB_EVENT_NAME": "pull_request_target",
                       "GITHUB_REF": "refs/heads/main", "GITHUB_SHA": MAIN}
        pr, event = self.proposal()
        for failure in (None, "rejected", "network", "event", "ref", "checkout", "main_moved", "retargeted"):
            with self.subTest(failure=failure):
                env, posted = dict(environment), []
                if failure == "event": env["GITHUB_EVENT_NAME"] = "pull_request"
                if failure == "ref": env["GITHUB_REF"] = "refs/heads/dev"
                error = {"rejected": ValueError("wrong tree"), "network": URLError("offline")}.get(failure)
                heads = [commit(MAIN), commit(DEV if failure == "main_moved" else MAIN)]
                current = copy.deepcopy(pr)
                if failure == "retargeted": current["base"]["ref"] = "dev"
                with patch.dict(os.environ, env), \
                        patch.object(policy.subprocess, "check_output", return_value=DEV if failure == "checkout" else MAIN), \
                        patch.object(policy, "commit", side_effect=heads), \
                        patch.object(policy, "api", side_effect=lambda path, data=None: posted.append((path, data)) if data else current), \
                        patch.object(policy, "pull_request", side_effect=error, return_value={"target": "main"}) as check:
                    if failure:
                        with self.assertRaises((ValueError, URLError)): policy.report_pull_request(event)
                    else:
                        self.assertEqual(policy.report_pull_request(event), {"target": "main"})
                self.assertEqual([data["state"] for _, data in posted],
                                 ["pending", "failure" if failure else "success"])
                self.assertTrue(all(path == f"statuses/{RELEASE}" for path, _ in posted))
                self.assertTrue(all(data["context"] == "release-policy/main" for _, data in posted))
                if failure in {"event", "ref", "checkout"}: check.assert_not_called()

    def test_development_status_cannot_satisfy_the_main_release_gate(self):
        pr, event = self.proposal("dev")
        posted = []
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "99", "GITHUB_EVENT_NAME": "pull_request_target",
                                     "GITHUB_REF": "refs/heads/main", "GITHUB_SHA": MAIN}), \
                patch.object(policy.subprocess, "check_output", return_value=MAIN), \
                patch.object(policy, "commit", return_value=commit(MAIN)), \
                patch.object(policy, "api", side_effect=lambda path, data=None: posted.append(data) if data else pr), \
                patch.object(policy, "pull_request", return_value={"target": "dev"}):
            policy.report_pull_request(event)
        self.assertEqual([data["context"] for data in posted], ["release-policy/dev"] * 2)

    def test_publication_recovers_the_merged_pr_and_exact_accepted_dev_mapping(self):
        parent, advanced = "5" * 40, "6" * 40
        failures = (None, "advanced_dev", "missing_pr", "unmerged", "wrong_merge", "duplicate_pr",
                    "fork", "permanent", "count", "head", "candidate_parent", "main_parent",
                    "main_tree", "dev_tree", "main_trailer", "missing_trailer", "ancestry",
                    "wrong_merge_base", "dev_moved", "failed_dev_ci")
        for failure in failures:
            with self.subTest(failure=failure):
                pr, _ = self.proposal()
                pr.update({"merged": True, "state": "closed", "merge_commit_sha": MAIN})
                revisions = {MAIN: commit(MAIN, parents=[parent]),
                             RELEASE: commit(RELEASE, parents=[parent]), DEV: commit(DEV),
                             "dev": commit(advanced if failure == "advanced_dev" else DEV)}
                associated = [] if failure == "missing_pr" else [pr]
                commits = [{"sha": RELEASE}]
                ancestry = {"status": "ahead" if failure == "advanced_dev" else "identical",
                            "merge_base_commit": {"sha": DEV}}
                if failure == "unmerged": pr["merged"] = False
                if failure == "wrong_merge": pr["merge_commit_sha"] = DEV
                if failure == "duplicate_pr": associated.append(copy.deepcopy(pr))
                if failure == "fork": pr["head"]["repo"]["full_name"] = "other/repo"
                if failure == "permanent": pr["head"]["ref"] = "dev"
                if failure == "count": commits.append({"sha": DEV})
                if failure == "head": commits[0]["sha"] = DEV
                if failure == "candidate_parent": revisions[RELEASE]["parents"] = [{"sha": DEV}]
                if failure == "main_parent": revisions[MAIN]["parents"].append({"sha": DEV})
                if failure == "main_tree": revisions[MAIN]["commit"]["tree"]["sha"] = "a" * 40
                if failure == "dev_tree": revisions[DEV]["commit"]["tree"]["sha"] = "a" * 40
                if failure == "main_trailer": revisions[MAIN]["commit"]["message"] = f"Accepted-Dev: {MAIN}"
                if failure == "missing_trailer": revisions[RELEASE]["commit"]["message"] = "release"
                if failure == "ancestry": ancestry["status"] = "diverged"
                if failure == "wrong_merge_base": ancestry["merge_base_commit"]["sha"] = MAIN
                dev_reads = 0

                def get_commit(ref):
                    nonlocal dev_reads
                    if ref == "dev":
                        dev_reads += 1
                        if failure == "dev_moved" and dev_reads > 1: return commit(advanced)
                    return revisions[ref]

                with patch.object(policy, "pages", side_effect=lambda path: associated if path.endswith("/pulls") else commits), \
                        patch.object(policy, "api", side_effect=lambda path: ancestry if path.startswith("compare/") else pr), \
                        patch.object(policy, "commit", side_effect=get_commit), \
                        patch.object(policy, "accepted_validation", return_value=[{"run_id": 10}],
                                     side_effect=ValueError("failed DEV push") if failure == "failed_dev_ci" else None) as validation:
                    if failure not in {None, "advanced_dev"}:
                        with self.assertRaises(ValueError): policy.merged_release(revisions[MAIN])
                    else:
                        result = policy.merged_release(revisions[MAIN])
                        self.assertEqual((result["pr_number"], result["head_sha"], result["dev_sha"]),
                                         (7, RELEASE, DEV))
                        validation.assert_called_once_with(DEV, "dev")

    def validation_fixture(self):
        runs, checks = {}, []
        for number, (workflow, names) in enumerate(policy.CHECKS.items(), 1):
            runs[workflow] = [{"id": number, "head_sha": DEV, "head_branch": "dev",
                              "event": "push", "path": f".github/workflows/{workflow}",
                              "head_repository": {"full_name": policy.REPOSITORY},
                              "status": "completed", "conclusion": "success",
                              "check_suite_id": number, "run_attempt": 1}]
            for name in sorted(names):
                checks.append({"id": len(checks) + 10, "name": name, "head_sha": DEV,
                               "app": {"id": policy.GITHUB_ACTIONS_APP},
                               "check_suite": {"id": number},
                               "status": "completed", "conclusion": "success"})
        return runs, checks

    def test_success_requires_exact_push_workflows_and_authenticated_check_suites(self):
        for failure in (None, "sha", "branch", "event", "workflow", "repository", "app",
                        "suite", "missing", "failed_check", "failed_latest_run", "failed_latest_check"):
            with self.subTest(failure=failure):
                runs, checks = self.validation_fixture()
                run = runs["validate.yml"][0]
                fields = {"sha": ("head_sha", MAIN), "branch": ("head_branch", "main"),
                          "event": ("event", "pull_request"), "workflow": ("path", "other.yml")}
                if failure in fields: run[fields[failure][0]] = fields[failure][1]
                if failure == "repository": run["head_repository"]["full_name"] = "other/repo"
                if failure == "app": checks[0]["app"]["id"] = 999
                if failure == "suite": checks[0]["check_suite"]["id"] = 999
                if failure == "missing": checks.pop(0)
                if failure == "failed_check": checks[0]["conclusion"] = "failure"
                if failure == "failed_latest_run":
                    runs["validate.yml"].append({**run, "id": 999, "conclusion": "failure"})
                if failure == "failed_latest_check":
                    checks.append({**checks[0], "id": 999, "conclusion": "failure"})

                def pages(path, key):
                    return checks if key == "check_runs" else runs[path.split("/")[2]]

                with patch.object(policy, "pages", side_effect=pages):
                    if failure:
                        with self.assertRaises(ValueError): policy.accepted_validation(DEV, "dev")
                    else:
                        self.assertEqual(len(policy.accepted_validation(DEV, "dev")), 2)

    def test_publication_requires_current_main_and_main_push_acceptance(self):
        for event, ref, checkout, allowed in [
            ("push", "refs/tags/v1.0", MAIN, True),
            ("workflow_dispatch", "refs/heads/main", MAIN, True),
            ("workflow_dispatch", "refs/heads/dev", DEV, False),
            ("push", "refs/tags/v1.0", DEV, False),
            ("push", "refs/heads/main", MAIN, False),
        ]:
            with self.subTest(event=event, ref=ref, checkout=checkout), \
                    patch.object(policy, "commit", return_value=commit(MAIN)), \
                    patch.object(policy, "merged_release", return_value={"dev_sha": DEV}), \
                    patch.object(policy, "accepted_validation", return_value=[]) as validate:
                if allowed:
                    self.assertEqual(policy.publication(event, ref, checkout)["main_sha"], MAIN)
                    validate.assert_called_once_with(MAIN, "main")
                else:
                    with self.assertRaises(ValueError): policy.publication(event, ref, checkout)
        with patch.object(policy, "commit", side_effect=[commit(MAIN), commit(MAIN), commit(DEV)]), \
                patch.object(policy, "merged_release", return_value={"dev_sha": DEV}), \
                patch.object(policy, "accepted_validation", return_value=[]):
            with self.assertRaisesRegex(ValueError, "moved"):
                policy.publication("push", "refs/tags/v1.0", MAIN)
        with patch.object(policy, "commit", return_value=commit(MAIN)), \
                patch.object(policy, "merged_release", side_effect=ValueError("no merged PR")), \
                patch.object(policy, "accepted_validation") as validation:
            with self.assertRaisesRegex(ValueError, "no merged PR"):
                policy.publication("push", "refs/tags/v1.0", MAIN)
            validation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
