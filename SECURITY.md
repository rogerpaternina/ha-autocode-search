# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x | Yes |
| 1.0.0-rc1 | Yes (release candidate) |
| 0.2.x and older | No |

Security fixes are released on the latest stable minor version. Upgrade to the
most recent patch release when available.

## Reporting a vulnerability

**Do not** open a public GitHub issue for security vulnerabilities.

Instead, report them privately:

1. Email the maintainer listed in [`manifest.json`](../custom_components/autocode_search/manifest.json) codeowners.
2. Or use [GitHub private vulnerability reporting](https://github.com/rogerpaternina/ha-autocode-search/security/advisories/new) if enabled.

Include:

- Affected version
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

You should receive an acknowledgment within 7 days. We will coordinate a fix
and disclosure timeline before publishing details.

## Scope

In scope:

- Code in `custom_components/autocode_search/`
- Release and validation scripts in `tools/`
- GitHub Actions workflows that build or test the integration

Out of scope:

- Third-party Home Assistant core vulnerabilities
- Misconfigured `remote` entities or Broadlink devices on the user's network
- Malicious IR code files placed in SmartIR/IRDB/LIRC directories by the user

## Best practices for users

- Keep Home Assistant and this integration updated.
- Only install the integration from the official repository or HACS.
- Restrict filesystem access to IR code databases under your config directory.
- Do not expose Home Assistant directly to the public internet without proper
  authentication and TLS.
