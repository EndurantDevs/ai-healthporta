# Contributing

This public repository contains HealthPorta integration bundles, client
configuration, examples and public skills. Keep examples synthetic and exclude
credentials, account data and deployment details.

## Development pull requests

Start from the current `dev` branch and open ordinary pull requests against
`dev`, even though the public default branch is `main`:

```bash
git fetch origin
git switch -c fix/short-description origin/dev
```

Describe the changed behavior and the checks you ran. Run focused local checks
for the affected files; for documentation, use
`python3 scripts/content_guard.py`. Packaging and validation commands are in
[the validation workflow](.github/workflows/validate.yml). GitHub CI is the
full-validation gate; do not run a local pre-push suite or hook. Authorized
pushes use `git push --no-verify`.

Wait for the required checks on the current PR head, address valid review
feedback, refresh the target branch and use **Rebase and merge**. Never
force-push `dev` or `main`. After merging, verify the checks on the resulting
`dev` commit; a passing PR run does not replace those checks.

This repository publishes integration bundles rather than deploying a server.
DEV acceptance covers the changed bundles and client behavior. The conformance
smoke script checks public endpoints and can accept a WAF response in its
default mode; passing that check alone does not prove an authenticated client
flow. Maintainers coordinate any service testing in DEV and keep sensitive
evidence outside the public PR.

## Stable releases

A release into `main` is a separate action requested by a human after `dev` is
stable and accepted. Merging a development PR does not request a release.
Maintainers follow the [release procedure](README.md#contribution-and-release-flow)
to prepare the accepted DEV tree, pass release CI and use **Rebase and merge**.
Publish bundles only through the existing validated main/tag workflow.
