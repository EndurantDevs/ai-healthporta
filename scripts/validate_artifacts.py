#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://mcp.healthporta.com/mcp"

JSON_FILES = [
    "gemini-extension.json",
    "server.json",
    ".claude-plugin/marketplace.json",
    ".cursor-plugin/marketplace.json",
    "providers/claude/plugin/.claude-plugin/plugin.json",
    "providers/claude/plugin/.mcp.json",
    "providers/cursor/plugin/.cursor-plugin/plugin.json",
    "providers/cursor/plugin/mcp.json",
    "examples/codex/mcp.json",
    "examples/chatgpt/mcp.json",
    "examples/generic/mcp.json",
    "examples/openclaw/mcp.json",
]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def assert_endpoint(value: str, source: str, errors: list[str]) -> None:
    if value != ENDPOINT:
        errors.append(f"{source}: expected endpoint {ENDPOINT}, got {value}")


def main() -> int:
    errors: list[str] = []

    for rel in JSON_FILES:
        path = ROOT / rel
        if not path.exists():
            errors.append(f"missing required file: {rel}")
            continue
        try:
            load_json(path)
        except Exception as exc:
            errors.append(f"invalid json in {rel}: {exc}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    gemini = load_json(ROOT / "gemini-extension.json")
    assert_endpoint(gemini["mcpServers"]["healthporta"]["httpUrl"], "gemini-extension.json", errors)

    server_json = load_json(ROOT / "server.json")
    assert_endpoint(server_json["remotes"][0]["url"], "server.json", errors)

    claude_mcp = load_json(ROOT / "providers/claude/plugin/.mcp.json")
    assert_endpoint(claude_mcp["mcpServers"]["healthporta"]["url"], "providers/claude/plugin/.mcp.json", errors)

    cursor_mcp = load_json(ROOT / "providers/cursor/plugin/mcp.json")
    assert_endpoint(cursor_mcp["mcpServers"]["healthporta"]["url"], "providers/cursor/plugin/mcp.json", errors)

    codex_mcp = load_json(ROOT / "examples/codex/mcp.json")
    assert_endpoint(codex_mcp["mcpServers"]["healthporta"]["url"], "examples/codex/mcp.json", errors)

    chatgpt_mcp = load_json(ROOT / "examples/chatgpt/mcp.json")
    assert_endpoint(chatgpt_mcp["mcpServers"]["healthporta"]["url"], "examples/chatgpt/mcp.json", errors)

    generic_mcp = load_json(ROOT / "examples/generic/mcp.json")
    assert_endpoint(generic_mcp["mcpServers"]["healthporta"]["url"], "examples/generic/mcp.json", errors)

    openclaw_mcp = load_json(ROOT / "examples/openclaw/mcp.json")
    assert_endpoint(openclaw_mcp["mcpServers"]["healthporta"]["url"], "examples/openclaw/mcp.json", errors)

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("artifact validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
