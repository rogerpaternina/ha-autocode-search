# Roadmap

Items tracked from code audits and planned future work. This document replaces
inline `TODO` / `FIXME` comments in the codebase.

## v1.1 — Search results

- **Persist completed search results** — Expose or persist the outcome when
  `SearchEngine.finish()` completes so users can review historical searches
  without relying solely on success memory.
  _Origin: Sprint 22 audit of `engine/search_engine.py`._

## v1.1 — Diagnostics

- **Redact provider configuration in diagnostics** — When provider-specific
  configuration is added to the config entry, redact sensitive paths or tokens
  from `async_get_config_entry_diagnostics`.
  _Origin: Sprint 22 audit of `diagnostics.py`._

## v1.0 — Release assets

- **Dashboard screenshots** — Capture and add to `docs/images/`:
  - `dashboard-status.png` — Status and progress panel.
  - `dashboard-confirmation.png` — Confirmation controls.
  - `dashboard-stats.png` — Learning statistics panel.

## Future considerations

- Expose `search_status` (including paused) as a dedicated sensor entity.
- Options flow integration for `input_select.autocode_provider` helper.
- Additional IR code sources beyond SmartIR, IRDB, and LIRC.
