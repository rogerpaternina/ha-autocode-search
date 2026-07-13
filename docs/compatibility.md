# Compatibility

Officially supported versions for AutoCode Search **v1.0.0-rc1**.

## Home Assistant

| Version | Support |
|---------|---------|
| 2026.1.0 and newer | Supported |
| 2025.x and older | Not tested |

The minimum version is declared in [`hacs.json`](../hacs.json) as
`homeassistant`.

## Python

| Version | Support |
|---------|---------|
| 3.13 | Supported (matches Home Assistant 2026.1 core) |
| 3.12 and older | Not supported for development tooling |

Development dependencies in [`pyproject.toml`](../pyproject.toml) target
Python 3.13.

## HACS

| Requirement | Value |
|-------------|-------|
| HACS | 1.30.0 or newer recommended |
| Repository type | Integration |
| Custom repository | Required until published in default catalog |

Install HACS following the [official HACS documentation](https://hacs.xyz/docs/setup/download),
then add this repository as a custom integration.

## Hardware and integrations

AutoCode Search requires a working `remote.*` entity. Tested setups include:

- Broadlink (`remote.send_command` with learned commands and `b64:` payloads)
- ESPHome remote entities
- Any integration that exposes the standard `remote` platform

SmartIR, IRDB, and LIRC providers read local filesystem paths under the Home
Assistant configuration directory. See [README](../README.md#providers) for
details.

## Version policy

- **Stable releases** (`1.0.0`, `1.1.0`, …) receive bug fixes on the latest
  minor line.
- **Release candidates** (`1.0.0-rc1`) are feature-complete previews; upgrade
  to the stable tag when published.
- **Pre-1.0 versions** are no longer supported after `1.0.0` is released.

Report compatibility issues on the
[issue tracker](https://github.com/rogerpaternina/ha-autocode-search/issues).
