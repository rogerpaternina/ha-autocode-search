#!/usr/bin/env python3
"""Validate release readiness for AutoCode Search."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components" / "autocode_search" / "manifest.json"
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"
README = ROOT / "README.md"
ARCHITECTURE = ROOT / "docs" / "architecture.md"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
RELEASE_CHECKLIST = ROOT / "docs" / "release_checklist.md"
RELEASE_NOTES = ROOT / "docs" / "release_notes_v1.md"
COMPATIBILITY = ROOT / "docs" / "compatibility.md"
HACS_JSON = ROOT / "hacs.json"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Represent the outcome of a single release validation step."""

    name: str
    ok: bool
    detail: str = ""


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_files() -> list[CheckResult]:
    """Verify that required release documentation exists."""
    required = {
        "README.md": README,
        "CHANGELOG.md": CHANGELOG,
        "docs/architecture.md": ARCHITECTURE,
        "CONTRIBUTING.md": CONTRIBUTING,
        "docs/release_checklist.md": RELEASE_CHECKLIST,
        "docs/release_notes_v1.md": RELEASE_NOTES,
        "docs/compatibility.md": COMPATIBILITY,
        "SECURITY.md": ROOT / "SECURITY.md",
        ".github/PULL_REQUEST_TEMPLATE.md": (
            ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
        ),
    }
    results: list[CheckResult] = []
    for label, path in required.items():
        results.append(
            CheckResult(
                name=f"file:{label}",
                ok=path.is_file(),
                detail="missing" if not path.is_file() else "present",
            )
        )
    return results


def check_versions() -> list[CheckResult]:
    """Ensure manifest and pyproject versions match."""
    manifest = json.loads(_read_text(MANIFEST))
    manifest_version = manifest["version"]
    pyproject_match = re.search(
        r'^version = "([^"]+)"', _read_text(PYPROJECT), re.MULTILINE
    )
    pyproject_version = pyproject_match.group(1) if pyproject_match else ""
    same = manifest_version == pyproject_version
    return [
        CheckResult(
            name="version:manifest",
            ok=bool(manifest_version),
            detail=manifest_version,
        ),
        CheckResult(
            name="version:pyproject",
            ok=bool(pyproject_version),
            detail=pyproject_version,
        ),
        CheckResult(
            name="version:sync",
            ok=same,
            detail=(
                "versions match"
                if same
                else f"manifest={manifest_version} pyproject={pyproject_version}"
            ),
        ),
    ]


def check_changelog(version: str) -> CheckResult:
    """Verify the changelog mentions the target version."""
    content = _read_text(CHANGELOG)
    mentioned = f"## [{version}]" in content or "## [Unreleased]" in content
    return CheckResult(
        name="changelog:version",
        ok=mentioned,
        detail=f"looking for [{version}] or [Unreleased]",
    )


def check_manifest() -> list[CheckResult]:
    """Validate required manifest and HACS metadata fields."""
    manifest = json.loads(_read_text(MANIFEST))
    hacs = json.loads(_read_text(HACS_JSON))
    required_manifest = (
        "domain",
        "name",
        "version",
        "documentation",
        "issue_tracker",
        "codeowners",
    )
    results = [
        CheckResult(
            name=f"manifest:{field}",
            ok=field in manifest and bool(manifest[field]),
            detail=str(manifest.get(field, "missing")),
        )
        for field in required_manifest
    ]
    results.append(
        CheckResult(
            name="manifest:requirements_empty",
            ok=manifest.get("requirements") == [],
            detail=str(manifest.get("requirements")),
        )
    )
    results.append(
        CheckResult(
            name="hacs:homeassistant",
            ok=bool(hacs.get("homeassistant")),
            detail=str(hacs.get("homeassistant", "missing")),
        )
    )
    return results


def run_command(name: str, command: list[str]) -> CheckResult:
    """Execute a quality command and capture its success state."""
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    ok = completed.returncode == 0
    detail = completed.stdout.strip() or completed.stderr.strip()
    if len(detail) > 200:
        detail = detail[:200] + "..."
    return CheckResult(name=name, ok=ok, detail=detail or "ok")


def run_quality_checks(*, include_tools: bool) -> list[CheckResult]:
    """Run static analysis and tests."""
    commands = [
        ("ruff", ["python3", "-m", "ruff", "check", "."]),
        ("black", ["python3", "-m", "black", "--check", "."]),
        ("mypy", ["python3", "-m", "mypy", "custom_components/autocode_search"]),
        ("pytest", ["python3", "-m", "pytest", "-q"]),
    ]
    if include_tools:
        commands.extend(
            [
                (
                    "benchmark",
                    [
                        "python3",
                        "tools/benchmark.py",
                        "--files",
                        "1",
                        "--commands-per-file",
                        "2",
                    ],
                ),
                (
                    "release-check-self",
                    ["python3", "tools/release_check.py", "--skip-quality"],
                ),
            ]
        )
    return [run_command(name, command) for name, command in commands]


def collect_results(*, version: str, include_tools: bool) -> list[CheckResult]:
    """Run every release validation step."""
    results: list[CheckResult] = []
    results.extend(check_required_files())
    results.extend(check_versions())
    results.append(check_changelog(version))
    results.extend(check_manifest())
    if not include_tools:
        return results
    results.extend(run_quality_checks(include_tools=True))
    return results


def print_results(results: list[CheckResult]) -> int:
    """Print validation results and return a process exit code."""
    failed = [result for result in results if not result.ok]
    width = max(len(result.name) for result in results)
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        detail = f" ({result.detail})" if result.detail else ""
        print(f"{status:<4} {result.name:<{width}}{detail}")
    print()
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


def main() -> int:
    """Validate release readiness from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        default=json.loads(_read_text(MANIFEST))["version"],
        help="Expected release version",
    )
    parser.add_argument(
        "--skip-quality",
        action="store_true",
        help="Only validate metadata and documentation files",
    )
    args = parser.parse_args()
    results = collect_results(version=args.version, include_tools=not args.skip_quality)
    return print_results(results)


if __name__ == "__main__":
    raise SystemExit(main())
