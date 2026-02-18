# HealthPorta MCP Integrations

Public integration pack for connecting AI clients to the HealthPorta MCP server.

- MCP endpoint: `https://mcp.healthporta.com/mcp`
- OAuth: required
- Integration name: `HealthPorta MCP`

## Supported Clients

| Client | Artifact | Status |
|---|---|---|
| Gemini | `gemini-extension.json` | Supported |
| Claude | `providers/claude/plugin/.mcp.json` | Supported |
| Cursor | `providers/cursor/plugin/mcp.json` | Supported |
| OpenClaw | `examples/openclaw/mcp.json` | Supported |
| Codex/CLI | `examples/codex/mcp.json` | Supported |
| ChatGPT-compatible | `examples/chatgpt/mcp.json` | Supported |
| Generic MCP clients | `examples/generic/mcp.json` | Supported |

## Quick Start

### Gemini
1. Import `gemini-extension.json`.
2. Authenticate with OAuth when prompted.
3. Verify with `healthporta_healthcheck` and `healthporta_auth_status`.

### Claude
1. Use `providers/claude/plugin/.mcp.json` as MCP config.
2. Authenticate with OAuth.
3. Verify with `healthporta_healthcheck`.

### Cursor
1. Use `providers/cursor/plugin/mcp.json` as MCP config.
2. Authenticate with OAuth.
3. Verify with `healthporta_healthcheck`.

### Codex/CLI
1. Add server URL from `examples/codex/mcp.json`.
2. Run client auth command.
3. Verify with `healthporta_healthcheck`.

### OpenClaw
1. Use `examples/openclaw/mcp.json` as MCP config.
2. Authenticate with OAuth.
3. Verify with `healthporta_healthcheck`.

## Public OAuth/Discovery Endpoints

- Authorization: `https://mcp.healthporta.com/mcp/oauth/authorize`
- Token: `https://mcp.healthporta.com/mcp/oauth/token`
- Dynamic registration: `https://mcp.healthporta.com/mcp/oauth/register`
- Well-known metadata:
  - `https://mcp.healthporta.com/.well-known/oauth-authorization-server`
  - `https://mcp.healthporta.com/.well-known/oauth-protected-resource/mcp`

## Public Usage Guidance

- Prefer operation-driven calls (`call_operation`) over raw path calls.
- For pharmacy geo search, combine `name_like` with chain filtering:
  - canonical: `network`, `network_aliases`
  - aliases accepted by this MCP layer in pharmacy context: `chain`, `chain_aliases`

## Troubleshooting

- `Failed to discover OAuth configuration`:
  - Check that `.well-known` endpoints are reachable.
- `Invalid Host header`:
  - Client is reaching MCP with a host value not accepted by server policy.
  - Use canonical URL `https://mcp.healthporta.com/mcp`.
- `Token exchange failed`:
  - Retry OAuth sign-in.
  - If persistent, collect error payload and open an issue.
- Upstream `502/503/504`:
  - Usually temporary upstream outage.
  - Retry later.

## Security Notes

- Do not include secrets in prompts or repo files.
- Use OAuth sessions only.
- Restrict API key scope in HealthPorta where applicable.

## VS Code and Copilot

- VS Code workspace support is included under `.vscode/`:
  - `settings.json`
  - `extensions.json`
  - `tasks.json`
- GitHub Copilot repository instructions are in:
  - `.github/copilot-instructions.md`

## Repository Policy

This is a public repository.

- Allowed: public integration docs, client configs, public skills.
- Forbidden: internal architecture docs, internal ops runbooks, `AGENTS.md`, `DEVOPS*.md`, private endpoint maps.

CI enforces this policy.

## Maintenance

This integration is maintained by **EndurantDevs LLC** (nick@endurantdev.com).
