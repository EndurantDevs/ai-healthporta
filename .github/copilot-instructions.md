# HealthPorta MCP Repo Instructions for Copilot

This repository is public and contains only client-facing integration artifacts.

## Scope

- Build and maintain public MCP integration files for AI clients.
- Keep all configs aligned to the canonical MCP endpoint:
  - `https://mcp.healthporta.com/mcp`

## Safety rules

- Do not add secrets, tokens, credentials, or host-specific private values.
- Do not add private operations notes or infrastructure details.
- Do not add files like `AGENTS.md` or `DEVOPS*.md`.

## Editing rules

- Keep JSON artifacts valid and minimal.
- If an MCP endpoint changes, update all config files and validation scripts together.
- Preserve public language in docs and skills.
- Prefer concise, actionable troubleshooting text.

## Validation

Before finalizing changes, run:

- `python3 scripts/content_guard.py`
- `python3 scripts/validate_artifacts.py`
- `python3 scripts/conformance_smoke.py`
