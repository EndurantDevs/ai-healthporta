from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
PUSH_MAIN_ARC_RUNNER = (
    "${{ github.event_name == 'push' && github.ref == 'refs/heads/main' && "
    "vars.AI_HEALTHPORTA_CI_RUNNER || 'ubuntu-latest' }}"
)
TRUSTED_MAIN_ARC_RUNNER = (
    "${{ (github.event_name == 'push' || github.event_name == 'workflow_dispatch') "
    "&& github.ref == 'refs/heads/main' && vars.AI_HEALTHPORTA_CI_RUNNER || "
    "'ubuntu-latest' }}"
)
PINNED_ACTION = re.compile(r"^[^./\s][^@\s]*@[0-9a-f]{40}$")
STEP = re.compile(r"(?ms)^      - (?P<body>.*?)(?=^      - |\Z)")
RELEASE_ACTION = "softprops/action-gh-release@3d0d9888cb7fd7b750713d6e236d1fcb99157228"


class CiRunnerRoutingTests(unittest.TestCase):
    def test_only_trusted_main_validation_uses_the_optional_arc_route(self) -> None:
        content_guard = (WORKFLOWS / "content-guard.yml").read_text()
        validate = (WORKFLOWS / "validate.yml").read_text()

        self.assertEqual(content_guard.count(f"runs-on: {PUSH_MAIN_ARC_RUNNER}"), 1)
        self.assertNotIn("workflow_dispatch:", content_guard)
        self.assertEqual(validate.count(f"runs-on: {TRUSTED_MAIN_ARC_RUNNER}"), 2)
        self.assertIn("workflow_dispatch:", validate)
        for name in ("conformance-nightly.yml", "release-artifacts.yml"):
            workflow = (WORKFLOWS / name).read_text()
            self.assertNotIn("AI_HEALTHPORTA_CI_RUNNER", workflow)
            self.assertIn("runs-on: ubuntu-latest", workflow)

    def test_actions_are_immutable_and_checkouts_drop_credentials(self) -> None:
        for path in sorted(WORKFLOWS.glob("*.yml")):
            workflow = path.read_text()
            if path.name == "artifact-cleanup.yml":
                self.assertNotIn("uses:", workflow)
                self.assertNotIn("actions/checkout@", workflow)
                continue
            actions = re.findall(r"uses:\s+([^\s#]+)", workflow)
            self.assertTrue(actions, path.name)
            self.assertTrue(all(PINNED_ACTION.fullmatch(action) for action in actions), path.name)
            checkouts = [
                block
                for block in STEP.findall(workflow)
                if "uses: actions/checkout@" in block
            ]
            self.assertTrue(checkouts, path.name)
            self.assertTrue(
                all("persist-credentials: false" in block for block in checkouts),
                path.name,
            )

    def test_distribution_is_built_before_validation(self) -> None:
        workflow = (WORKFLOWS / "validate.yml").read_text()
        self.assertLess(
            workflow.index("python3 scripts/package_release.py"),
            workflow.index("python3 scripts/validate_artifacts.py"),
        )

        release = (WORKFLOWS / "release-artifacts.yml").read_text()
        self.assertIn("    permissions:\n      contents: write", release)
        self.assertIn(f"uses: {RELEASE_ACTION}", release)

    def test_artifacts_expire_and_cleanup_runs_only_after_consumers(self) -> None:
        release = (WORKFLOWS / "release-artifacts.yml").read_text()
        self.assertIn("retention-days: 1", release)

        cleanup = (WORKFLOWS / "artifact-cleanup.yml").read_text()
        self.assertIn("workflows: [release-artifacts]", cleanup)
        self.assertIn("types: [completed]", cleanup)
        self.assertIn("workflow_run.conclusion == 'success'", cleanup)
        self.assertIn("group: actions-artifact-cleanup\n", cleanup)
        self.assertNotIn("github.event.workflow_run.id || github.run_id", cleanup)
        self.assertIn(
            "/actions/runs/${RUN_ID}/artifacts?per_page=100",
            cleanup,
        )
        self.assertEqual(cleanup.count('artifact_ids="$(mktemp)"'), 2)
        self.assertEqual(cleanup.count('trap \'rm -f "$artifact_ids"\' EXIT'), 2)
        self.assertEqual(cleanup.count('done < "$artifact_ids"'), 2)

        stale = cleanup.split("  delete-stale-artifacts:", maxsplit=1)[1]
        self.assertIn("1 day ago", stale)
        self.assertIn(".expired == false and .created_at < $cutoff", stale)
        self.assertNotIn("/actions/runs/", stale)


if __name__ == "__main__":
    unittest.main()
