## Public Repository Checklist

- [ ] Ordinary changes target `dev`. A release PR targets `main` with one commit whose parent is current `main`, whose tree exactly matches the current validated `dev` commit, and whose `Accepted-Dev: <full SHA>` trailer identifies that DEV commit.
- [ ] Release validation is identified by the exact commit and successful GitHub Actions checks; a branch name or PR description is not release evidence.
- [ ] This PR contains only public integration content.
- [ ] No internal architecture, internal runbooks, or private operational details were added.
- [ ] No `AGENTS.md`, `DEVOPS*.md`, or similar internal guidance files were added.
- [ ] No secrets or secret-like values are present.
- [ ] MCP endpoint references remain `https://mcp.healthporta.com/mcp`.
