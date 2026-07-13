# Contributing to AutoCode Search

Thank you for your interest in contributing! This guide covers the development workflow, project structure, and quality requirements.

## Getting started

### Prerequisites

- Python 3.13+
- Git
- Docker (optional, for running Home Assistant locally)

### Clone and install

```sh
git clone https://github.com/rogerpaternina/ha-autocode-search.git
cd ha-autocode-search
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Run tests

```sh
pytest -v
```

All 172+ tests must pass before submitting a pull request.

## Quality checks

The project enforces four quality tools in CI. Run them locally before committing:

### Ruff (linter)

```sh
ruff check .
```

### Black (formatter)

```sh
black --check .
```

To auto-format:

```sh
black .
```

### Mypy (type checker)

```sh
mypy custom_components/autocode_search
```

### Hassfest (integration validation)

Hassfest runs automatically in CI via GitHub Actions. It validates the manifest, services.yaml, translations, and integration structure.

## Docker development environment

An optional Docker setup runs Home Assistant with the local integration mounted:

```sh
cd docker
docker compose up -d
```

Open `http://localhost:8123` and complete the initial setup. The integration is available at `/config/custom_components/autocode_search`.

See [docker/README.md](docker/README.md) for logs, restart, and timezone configuration.

## Project structure

```text
ha-autocode-search/
├── custom_components/
│   └── autocode_search/       # Integration source code
│       ├── __init__.py        # Setup / unload entry points
│       ├── config_flow.py     # UI configuration wizard
│       ├── coordinator.py     # State bridge to HA entities
│       ├── services.py        # Service handlers
│       ├── sensor.py          # Diagnostic sensors
│       ├── binary_sensor.py   # Running / confirmation sensors
│       ├── button.py          # Confirm / reject buttons
│       ├── adapters/          # Remote transmission strategies
│       ├── engine/            # SearchEngine core
│       ├── memory/            # SuccessMemory learning
│       ├── models/            # Domain models (IRCode, SearchFilter, …)
│       ├── providers/         # SmartIR, IRDB, LIRC, Composite
│       └── storage/           # Persistent success storage
├── tests/                     # Pytest test suite
├── examples/                  # Lovelace, automations, scripts, helpers
├── docs/                      # Architecture and release docs
├── docker/                    # Development Docker environment
├── .github/workflows/         # CI pipelines
├── hacs.json                  # HACS metadata
├── pyproject.toml             # Tool configuration
└── requirements-dev.txt       # Development dependencies
```

## Architecture constraints

The core architecture is considered stable. The following components should not be modified without a dedicated sprint and architectural review:

- `SearchEngine` and `SearchSession`
- All providers (`SmartIR`, `IRDB`, `LIRC`, `Composite`, `InMemory`)
- `SuccessMemory` and `StorageBackend`
- `ProviderRanking`

Changes to these areas require corresponding test updates and should be discussed in an issue first.

## Adding tests

- Place unit tests in `tests/` mirroring the source structure.
- Use the stubs in `tests/ha_stubs.py` for Home Assistant dependencies.
- Provider tests go in `tests/providers/`.
- Storage tests go in `tests/storage/`.
- Memory tests go in `tests/memory/`.

Run a specific test file:

```sh
pytest tests/test_services.py -v
```

## Development tools

### Coverage

```sh
./tools/coverage.sh
```

Generates `htmlcov/index.html` with line coverage for the integration.

### Benchmarks

```sh
python3 tools/benchmark.py --files 5 --commands-per-file 20
```

Measures SmartIR, IRDB, LIRC, Composite, ranking, and Success Memory load times.

### Profiling

See [docs/profiling.md](docs/profiling.md) for cProfile and py-spy instructions.

### Release validation

Before tagging a release:

```sh
python3 tools/release_check.py
```

Use `--skip-quality` to validate documentation and version metadata only.

## Pull request guidelines

1. Create a feature branch from `main` or `develop`.
2. Write or update tests for your changes.
3. Run `ruff check .`, `black --check .`, `mypy custom_components/autocode_search`, and `pytest`.
4. Update `CHANGELOG.md` under `[Unreleased]` if the change is user-facing.
5. Submit the pull request with a clear description of what changed and why.

## Code style

- Line length: 88 characters (Black and Ruff default).
- Target Python version: 3.13.
- Use type hints throughout the integration code.
- Follow existing naming conventions and module organization.
- Keep comments focused on non-obvious business logic.

## Reporting issues

Use the [GitHub issue tracker](https://github.com/rogerpaternina/ha-autocode-search/issues) to report bugs or request features. Include:

- Home Assistant version.
- Integration version.
- Steps to reproduce.
- Relevant logs (enable debug logging for `custom_components.autocode_search`).

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
