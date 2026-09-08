from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("policy", ROOT / "scripts/check_release_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
MAIN, DEV, RELEASE = "1" * 40, "2" * 40, "3" * 40
TREE = "4" * 40


def commit(sha, tree=TREE, parents=()):
    return {"sha": sha, "commit": {"tree": {"sha": tree}},
            "parents": [{"sha": parent} for parent in parents]}


class ReleasePolicyTests(unittest.TestCase):
    def proposal(self, target="main"):
        current = {"state": "open", "base": {"ref": target, "sha": MAIN,
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
        for failure in (None, "base", "count", "parent", "tree", "fork", "permanent", "moved"):
            with self.subTest(failure=failure):
                current, event = self.proposal()
                revisions = {"main": commit(MAIN), "dev": commit(DEV),
                             RELEASE: commit(RELEASE, parents=[MAIN])}
                commits = [{"sha": RELEASE}]
                if failure == "base": current["base"]["sha"] = "a" * 40
                if failure == "count": commits.append({"sha": DEV})
                if failure == "parent": revisions[RELEASE]["parents"].append({"sha": DEV})
                if failure == "tree": revisions[RELEASE]["commit"]["tree"]["sha"] = "b" * 40
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
                    patch.object(policy, "accepted_validation", return_value=[]) as validate:
                if allowed:
                    self.assertEqual(policy.publication(event, ref, checkout)["main_sha"], MAIN)
                    validate.assert_called_once_with(MAIN, "main")
                else:
                    with self.assertRaises(ValueError): policy.publication(event, ref, checkout)
        with patch.object(policy, "commit", side_effect=[commit(MAIN), commit(MAIN), commit(DEV)]), \
                patch.object(policy, "accepted_validation", return_value=[]):
            with self.assertRaisesRegex(ValueError, "moved"):
                policy.publication("push", "refs/tags/v1.0", MAIN)


if __name__ == "__main__":
    unittest.main()
