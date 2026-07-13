# Release Checklist

Use this checklist before publishing a new version of AutoCode Search to HACS.

## Pre-release

- [ ] All tests pass locally (`pytest -v`)
- [ ] Ruff passes (`ruff check .`)
- [ ] Black passes (`black --check .`)
- [ ] Mypy passes (`mypy custom_components/autocode_search`)
- [ ] Hassfest CI workflow passes on the release branch
- [ ] No open critical bugs in the issue tracker

## Version bump

- [ ] Update `version` in `custom_components/autocode_search/manifest.json`
- [ ] Update `version` in `pyproject.toml`
- [ ] Move `[Unreleased]` entries to a new version section in `CHANGELOG.md`
- [ ] Add release date to the new `CHANGELOG.md` section
- [ ] Update comparison links at the bottom of `CHANGELOG.md`

## Documentation

- [ ] `README.md` reflects current features and installation steps
- [ ] `docs/architecture.md` is up to date with all components
- [ ] `CONTRIBUTING.md` instructions are accurate
- [ ] Example YAML files in `examples/` reference valid entities and services
- [ ] Service examples in README match `services.yaml`

## Screenshots

- [ ] Dashboard status panel capture (`docs/images/dashboard-status.png`)
- [ ] Dashboard confirmation capture (`docs/images/dashboard-confirmation.png`)
- [ ] Dashboard statistics capture (`docs/images/dashboard-stats.png`)
- [ ] Screenshots referenced in README are present and current

## HACS validation

- [ ] `hacs.json` has correct `name`, `render_readme`, and `homeassistant` version
- [ ] `manifest.json` has valid `domain`, `documentation`, `issue_tracker`, and `codeowners`
- [ ] Integration installs cleanly via HACS custom repository
- [ ] Config Flow completes without errors
- [ ] All entities appear under the Autocode Search device
- [ ] All services are callable from Developer Tools
- [ ] Lovelace dashboard imports without errors

## Release

- [ ] Create a git tag matching the version (e.g. `v0.3.0`)
- [ ] Push the tag to GitHub
- [ ] Create a GitHub Release with the changelog content
- [ ] Verify HACS picks up the new release
- [ ] Test a fresh install from HACS on a clean Home Assistant instance

## Post-release

- [ ] Monitor issue tracker for installation or regression reports
- [ ] Open `[Unreleased]` section in `CHANGELOG.md` for the next cycle
