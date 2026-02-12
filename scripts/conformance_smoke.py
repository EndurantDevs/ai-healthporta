#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = "https://mcp.healthporta.com"

ENDPOINTS = [
    f"{BASE}/.well-known/oauth-authorization-server",
    f"{BASE}/.well-known/oauth-protected-resource/mcp",
]


def fetch_json(url: str) -> tuple[int, dict | None, str]:
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = None
            return resp.status, payload, body
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, None, body
    except URLError as exc:
        return 0, None, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="HealthPorta MCP conformance smoke checks")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if endpoint status codes differ from strict expectations.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    warnings: list[str] = []

    for endpoint in ENDPOINTS:
        status, payload, body = fetch_json(endpoint)
        if args.strict:
            acceptable = {200}
        else:
            acceptable = {200, 403}

        if status not in acceptable:
            failures.append(f"{endpoint} returned status {status}: {body[:200]}")
            continue
        if status == 403:
            warnings.append(f"{endpoint} returned 403 (likely WAF/bot protection in CI context)")
            continue
        if not isinstance(payload, dict):
            failures.append(f"{endpoint} did not return JSON object")

    status, _payload, body = fetch_json(f"{BASE}/mcp")
    if args.strict:
        acceptable_mcp = {401, 405}
    else:
        acceptable_mcp = {401, 403, 405}

    if status not in acceptable_mcp:
        failures.append(f"{BASE}/mcp expected 401/405 without auth, got {status}: {body[:200]}")
    elif status == 403 and not args.strict:
        warnings.append(f"{BASE}/mcp returned 403 without auth (likely WAF/bot protection in CI context)")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1

    for warning in warnings:
        print(f"WARN: {warning}")

    print("conformance smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
