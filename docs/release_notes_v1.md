# Release Notes — AutoCode Search v1.0.0

AutoCode Search v1.0.0 is the first stable public release of the Home Assistant
integration for automatic infrared code discovery.

## Highlights

- **Multi-source search** — SmartIR, IRDB, and LIRC combined through the
  Composite Provider with deduplication and smart ranking.
- **Learning** — Success Memory remembers working codes and prioritizes them in
  future searches with persistent JSON storage.
- **Full Home Assistant UX** — Config Flow, 16 diagnostic sensors, 2 binary
  sensors, 2 buttons, and 11 services.
- **Lovelace dashboard** — Importable dashboard with conditional controls,
  helpers, scripts, and automation examples.
- **Production hardening** — Audited logging, exception handling, developer
  benchmarks, release validation tools, and GitHub templates.

## Architecture

```text
Home Assistant (UI, Services, Entities)
        │
        ▼
   Coordinator
        │
        ▼
   SearchEngine ──► SearchSession / SearchFilter
        │
        ▼
 Composite Provider ──► SmartIR | IRDB | LIRC
        │
        ▼
 Success Memory ──► Storage Backend
        │
        ▼
 Remote Adapter ──► remote.send_command
```

See [architecture.md](architecture.md) for detailed diagrams.

## Requirements

| Component | Minimum |
|-----------|---------|
| Home Assistant | 2026.1.0 |
| Python | 3.13 |
| HACS | 1.30.0 (recommended) |
| Remote entity | One configured `remote.*` |

Full matrix: [compatibility.md](compatibility.md).

## Installation

### HACS

1. Add `rogerpaternina/ha-autocode-search` as a custom integration repository.
2. Install **Autocode Search** from HACS.
3. Restart Home Assistant.
4. Add the integration under **Settings → Devices & services**.

### Dashboard (optional)

1. Copy helpers from `examples/entities.yaml`.
2. Copy scripts from `examples/scripts.yaml`.
3. Import `examples/lovelace-dashboard.yaml` as a new dashboard.

See [README](../README.md) for step-by-step instructions.

## Services

| Service | Purpose |
|---------|---------|
| `start_search` | Begin a new IR code search |
| `next_code` / `previous_code` | Navigate codes |
| `pause` / `resume` / `cancel` | Control active search |
| `finish_search` | End search and await confirmation |
| `confirm_success` / `reject_result` | User feedback on last code |
| `mark_success` | Manually record a working code |
| `clear_success_memory` | Reset learned codes |

## Known limitations

- Only one config entry is supported (`single_config_entry`).
- No YAML configuration; all setup is via Config Flow.
- The `running` binary sensor is off when paused; use progress and elapsed time
  sensors to infer paused state.
- Dashboard screenshots are pending (see [roadmap.md](roadmap.md)).
- Provider paths (SmartIR, IRDB, LIRC) must exist on the filesystem; missing
  databases log a warning and contribute zero codes.
- Release candidates use the `1.0.0-rc1` version tag until the stable release
  is published.

## Upgrading from pre-1.0

1. Update via HACS or replace `custom_components/autocode_search`.
2. Restart Home Assistant.
3. Success memory data is preserved automatically in `.storage`.
4. Review `CHANGELOG.md` for breaking changes between 0.2.x and 1.0.0.

## Security

Report vulnerabilities per [SECURITY.md](../SECURITY.md). Do not open public
issues for security reports.

## Links

- [README](../README.md)
- [Contributing](../CONTRIBUTING.md)
- [Release checklist](release_checklist.md)
- [Roadmap](roadmap.md)
