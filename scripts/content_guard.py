#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATH_PATTERNS = [
    re.compile(r"(^|/)AGENTS\.md$", re.IGNORECASE),
    re.compile(r"(^|/)DEVOPS[^/]*\.md$", re.IGNORECASE),
    re.compile(r"(^|/)internal[^/]*\.md$", re.IGNORECASE),
]

FORBIDDEN_TEXT_PATTERNS = [
    re.compile(r"\binternal[_ -]?api\b", re.IGNORECASE),
    re.compile(r"\bprivate\s+runbook\b", re.IGNORECASE),
    re.compile(r"\bjenkins\b", re.IGNORECASE),
    re.compile(r"\bredis://[^\s]+", re.IGNORECASE),
]

TEXT_EXTENSIONS = {".md", ".txt", ".json", ".yml", ".yaml"}


def is_ignored(path: Path) -> bool:
    parts = set(path.parts)
    return ".git" in parts or "__pycache__" in parts


def main() -> int:
    errors: list[str] = []
    files = [p for p in ROOT.rglob("*") if p.is_file() and not is_ignored(p)]

    for file_path in files:
        rel = file_path.relative_to(ROOT).as_posix()
        for pattern in FORBIDDEN_PATH_PATTERNS:
            if pattern.search(rel):
                errors.append(f"forbidden file path: {rel}")

        if file_path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        for pattern in FORBIDDEN_TEXT_PATTERNS:
            if pattern.search(content):
                errors.append(f"forbidden content pattern '{pattern.pattern}' in {rel}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("content guard passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
