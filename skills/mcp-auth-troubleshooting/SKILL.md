---
description: Public OAuth and connectivity troubleshooting for HealthPorta MCP
alwaysApply: false
---

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
