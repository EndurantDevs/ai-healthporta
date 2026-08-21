from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
ARC_RUNNER = (
    "${{ github.event_name == 'push' && github.ref == 'refs/heads/main' && "
    "vars.AI_HEALTHPORTA_CI_RUNNER || 'ubuntu-latest' }}"
)
PINNED_ACTION = re.compile(r"^[^./\s][^@\s]*@[0-9a-f]{40}$")


class CiRunnerRoutingTests(unittest.TestCase):
    def test_only_push_main_validation_uses_the_optional_arc_route(self) -> None:
        content_guard = (WORKFLOWS / "content-guard.yml").read_text()
        validate = (WORKFLOWS / "validate.yml").read_text()

        self.assertEqual(content_guard.count(f"runs-on: {ARC_RUNNER}"), 1)
        self.assertEqual(validate.count(f"runs-on: {ARC_RUNNER}"), 2)
        for name in ("conformance-nightly.yml", "release-artifacts.yml"):
            workflow = (WORKFLOWS / name).read_text()
            self.assertNotIn("AI_HEALTHPORTA_CI_RUNNER", workflow)
            self.assertIn("runs-on: ubuntu-latest", workflow)

    def test_actions_are_immutable_and_checkouts_drop_credentials(self) -> None:
        for path in sorted(WORKFLOWS.glob("*.yml")):
            workflow = path.read_text()
            actions = re.findall(r"uses:\s+([^\s#]+)", workflow)
            self.assertTrue(all(PINNED_ACTION.fullmatch(action) for action in actions), path.name)
            self.assertGreaterEqual(
                workflow.count("persist-credentials: false"),
                workflow.count("uses: actions/checkout@"),
                path.name,
            )

    def test_distribution_is_built_before_validation(self) -> None:
        workflow = (WORKFLOWS / "validate.yml").read_text()
        self.assertLess(
            workflow.index("python3 scripts/package_release.py"),
            workflow.index("python3 scripts/validate_artifacts.py"),
        )


if __name__ == "__main__":
    unittest.main()
