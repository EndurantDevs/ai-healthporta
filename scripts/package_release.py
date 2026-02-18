#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


ARTIFACTS = [
    "gemini-extension.json",
    "server.json",
    ".claude-plugin/marketplace.json",
    ".cursor-plugin/marketplace.json",
    "providers/claude/plugin",
    "providers/cursor/plugin",
    "examples/codex/mcp.json",
    "examples/chatgpt/mcp.json",
    "examples/generic/mcp.json",
    "examples/openclaw/mcp.json",
    "skills/healthporta-workflow/SKILL.md",
    "skills/mcp-auth-troubleshooting/SKILL.md",
]


def main() -> int:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    for rel in ARTIFACTS:
        src = ROOT / rel
        if not src.exists():
            raise FileNotFoundError(f"missing release artifact: {rel}")

    shutil.copy2(ROOT / "gemini-extension.json", DIST / "gemini-extension.json")
    shutil.copy2(ROOT / "server.json", DIST / "server.json")
    shutil.make_archive(str(DIST / "healthporta-claude-plugin"), "zip", ROOT / "providers/claude/plugin")
    shutil.make_archive(str(DIST / "healthporta-cursor-plugin"), "zip", ROOT / "providers/cursor/plugin")
    shutil.make_archive(str(DIST / "healthporta-public-skills"), "zip", ROOT / "skills")
    shutil.copy2(ROOT / "examples/codex/mcp.json", DIST / "codex-mcp.json")
    shutil.copy2(ROOT / "examples/chatgpt/mcp.json", DIST / "chatgpt-mcp.json")
    shutil.copy2(ROOT / "examples/generic/mcp.json", DIST / "generic-mcp.json")
    shutil.copy2(ROOT / "examples/openclaw/mcp.json", DIST / "openclaw-mcp.json")

    print("release artifacts prepared in dist/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
