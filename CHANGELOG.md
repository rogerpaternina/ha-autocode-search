# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0-rc1] - 2026-07-13

### Added

- **Sprint 22** — Hardening, optimization, and release candidate preparation.
- Development benchmarks (`tools/benchmark.py`) for providers, ranking, and memory.
- Coverage script (`tools/coverage.sh`) and profiling guide (`docs/profiling.md`).
- Release validation tool (`tools/release_check.py`).
- GitHub issue and pull request templates, `CODEOWNERS`, and `SECURITY.md`.
- Compatibility matrix (`docs/compatibility.md`) and v1 release notes.
- Product roadmap (`docs/roadmap.md`) replacing inline TODO comments.

### Changed

- Service exception handling now catches specific errors instead of bare `Exception`.
- Removed redundant debug logging from service handlers.
- `InMemoryCodeProvider` typing improved without `type: ignore` comments.
- `ProviderFactory` docstrings translated to English.
- Version bumped to `1.0.0-rc1` across manifest and pyproject.

### Removed

- Stale `TODO` comments from integration code (tracked in roadmap).


### Added

- **Sprint 20** — Confirmación de resultados y botones de entidad.
- Servicios `confirm_success` y `reject_result`.
- Botones `Confirm success` y `Reject result`.
- Sensor binario `Waiting confirmation`.
- Flujo de confirmación integrado con Success Memory.

## [0.1.9] - 2026-06-15

### Added

- **Sprint 19** — Sensores de aprendizaje y ranking de proveedores.
- Sensores `Success records`, `Last success`, `Last provider`, `Last tested command`.
- Sensores `Provider order` y `Provider ranking reason`.
- ProviderRanking con ordenamiento contextual.

## [0.1.8] - 2026-06-01

### Added

- **Sprint 18** — Almacenamiento persistente de éxitos.
- StorageBackend con persistencia JSON.
- SuccessRepository como capa de abstracción.
- Integración de SuccessMemory con almacenamiento en disco.
- Servicio `clear_success_memory`.

## [0.1.7] - 2026-05-15

### Added

- **Sprint 17** — Success Memory y servicio mark_success.
- SuccessMemory con búsqueda por contexto.
- Servicio `mark_success` para registro manual de éxitos.
- Priorización de códigos exitosos en búsquedas futuras.

## [0.1.6] - 2026-05-01

### Added

- **Sprint 16** — Composite Provider y deduplicación.
- CompositeCodeProvider que unifica SmartIR, IRDB y LIRC.
- Eliminación de duplicados entre proveedores.
- Sensores `Providers used` y `Duplicates removed`.

## [0.1.5] - 2026-04-15

### Added

- **Sprint 15** — Proveedor LIRC.
- LIRCProvider con lectura de archivos de configuración LIRC.
- Soporte para rutas de sistema LIRC.

## [0.1.4] - 2026-04-01

### Added

- **Sprint 14** — Proveedor IRDB.
- IRDBProvider con lectura de la base de datos IRDB.
- Filtrado por fabricante, modelo y tipo de dispositivo.

## [0.1.3] - 2026-03-15

### Added

- **Sprint 13** — Proveedor SmartIR.
- SmartIRProvider con códigos de la comunidad SmartIR.
- Filtrado y normalización de códigos SmartIR.

## [0.1.2] - 2026-03-01

### Added

- **Sprint 12** — SearchFilter y filtrado de proveedores.
- Modelo SearchFilter con fabricante, modelo, tipo y comando.
- Filtrado aplicado en todos los proveedores.
- Sensor `Filter summary`.

## [0.1.1] - 2026-02-15

### Added

- **Sprint 11** — Sensores de diagnóstico y sensores binarios.
- Sensores de progreso, códigos probados, tiempo transcurrido y metadatos.
- Sensor binario `Running`.
- Coordinator con actualización periódica del estado.

## [0.1.0] - 2026-02-01

### Added

- **Sprint 10** — Servicios de búsqueda y motor central.
- SearchEngine con ciclo start/next/previous/pause/resume/cancel/finish.
- SearchSession con gestión de estado.
- Servicios `start_search`, `next_code`, `previous_code`, `pause`, `resume`, `cancel`, `finish_search`.
- HomeAssistantRemoteAdapter con estrategias Broadlink y genérica.

## [0.0.5] - 2026-01-15

### Added

- **Sprint 9** — Config Flow completo.
- Selección de remote, tipo de dispositivo, marca y proveedor.
- Options flow para reconfiguración.
- Traducciones en inglés y español.

## [0.0.4] - 2026-01-01

### Added

- **Sprint 8** — Coordinator y estructura de plataformas.
- AutocodeSearchCoordinator como puente de estado.
- Registro de plataformas sensor, binary_sensor y button.

## [0.0.3] - 2025-12-15

### Added

- **Sprint 7** — Adaptador remoto de Home Assistant.
- HomeAssistantRemoteAdapter con detección de integración.
- BroadlinkRawStrategy y GenericStrategy.

## [0.0.2] - 2025-12-01

### Added

- **Sprint 6** — Modelos de dominio.
- IRCode, SearchSession y SearchFilter como modelos base.
- Estructura de directorios del proyecto.

## [0.0.1] - 2025-11-15

### Added

- **Sprint 5** — Esqueleto de integración HACS.
- Manifest, const, config flow básico.
- CI con pytest, ruff, black, mypy y hassfest.
- Entorno Docker de desarrollo.

[Unreleased]: https://github.com/rogerpaternina/ha-autocode-search/compare/v1.0.0-rc1...HEAD
[1.0.0-rc1]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.2.0...v1.0.0-rc1
[0.2.0]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.1.9...v0.2.0
[0.1.9]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.0.5...v0.1.0
[0.0.5]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/rogerpaternina/ha-autocode-search/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/rogerpaternina/ha-autocode-search/releases/tag/v0.0.1
