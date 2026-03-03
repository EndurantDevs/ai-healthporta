---
description: Public OAuth and connectivity troubleshooting for HealthPorta MCP
alwaysApply: false
---

## Codex transport mismatch

If Codex reports `No such file or directory (os error 2)` during MCP startup or lists `Auth: Unsupported`:

1. Inspect current MCP config:
   - `codex mcp get healthporta`
2. If output shows `transport: stdio`, recreate as URL transport:
   - `codex mcp remove healthporta`
   - `codex mcp add healthporta --url https://mcp.healthporta.com/mcp`
   - `codex mcp login healthporta`
3. Confirm fixed state:
   - `codex mcp get healthporta` includes `transport: streamable_http`
   - `codex mcp list` shows `Auth: OAuth` for `healthporta`

## OAuth discovery issues

If a client reports OAuth discovery failure:

1. Verify:
   - `https://mcp.healthporta.com/.well-known/oauth-authorization-server`
   - `https://mcp.healthporta.com/.well-known/oauth-protected-resource/mcp`
2. Ensure MCP server URL is exactly `https://mcp.healthporta.com/mcp`.

## Token exchange issues

If token exchange fails:

1. Re-run OAuth sign-in from client.
2. Capture error payload and status code.
3. If status is `5xx`, retry after a short delay.

## Host/origin errors

If client reports `Invalid Host header`:

1. Confirm client is configured with canonical MCP URL.
2. Remove non-canonical host aliases from client config.

## Upstream gateway errors

For `502`, `503`, `504`:

- Treat as upstream availability issue.
- Retry later and keep user informed.
