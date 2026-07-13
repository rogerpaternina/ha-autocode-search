"""Tests for release tooling, documentation consistency, and GitHub templates."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "custom_components" / "autocode_search" / "manifest.json"
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"
TOOLS_DIR = ROOT / "tools"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_manifest_required_fields() -> None:
    """Manifest must expose the fields required for HACS publication."""
    manifest = json.loads(_read_text(MANIFEST))
    assert manifest["domain"] == "autocode_search"
    assert manifest["name"] == "Autocode Search"
    assert manifest["config_flow"] is True
    assert manifest["requirements"] == []
    assert manifest["single_config_entry"] is True
    for key in ("documentation", "issue_tracker", "codeowners", "version"):
        assert manifest.get(key), f"manifest missing {key}"


def test_manifest_version_matches_pyproject() -> None:
    """Integration version must stay in sync across manifest and pyproject."""
    manifest_version = json.loads(_read_text(MANIFEST))["version"]
    pyproject_match = re.search(
        r'^version = "([^"]+)"', _read_text(PYPROJECT), re.MULTILINE
    )
    assert pyproject_match is not None
    assert manifest_version == pyproject_match.group(1)


def test_changelog_mentions_current_version() -> None:
    """Changelog must document the current manifest version."""
    version = json.loads(_read_text(MANIFEST))["version"]
    changelog = _read_text(CHANGELOG)
    assert f"## [{version}]" in changelog or "## [Unreleased]" in changelog


def test_documentation_files_exist() -> None:
    """Release documentation referenced by tooling must exist."""
    required = [
        ROOT / "README.md",
        ROOT / "CHANGELOG.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        ROOT / "docs" / "architecture.md",
        ROOT / "docs" / "compatibility.md",
        ROOT / "docs" / "profiling.md",
        ROOT / "docs" / "release_notes_v1.md",
        ROOT / "docs" / "release_checklist.md",
        ROOT / "docs" / "roadmap.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    assert not missing, f"Missing docs: {missing}"


def test_github_templates_exist() -> None:
    """GitHub issue and pull request templates must be present."""
    templates = [
        ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "documentation.yml",
        ROOT / ".github" / "CODEOWNERS",
    ]
    missing = [str(path.relative_to(ROOT)) for path in templates if not path.is_file()]
    assert not missing, f"Missing templates: {missing}"


def test_github_issue_templates_define_title_prefix() -> None:
    """Issue templates should include a title prefix for triage."""
    for name in ("bug_report.yml", "feature_request.yml", "documentation.yml"):
        content = _read_text(ROOT / ".github" / "ISSUE_TEMPLATE" / name)
        assert "title:" in content
        assert "[" in content


def test_hacs_json_matches_manifest() -> None:
    """HACS metadata must reference a supported Home Assistant version."""
    hacs = json.loads(_read_text(ROOT / "hacs.json"))
    assert hacs["name"] == json.loads(_read_text(MANIFEST))["name"]
    assert re.match(r"^\d{4}\.\d+\.\d+$", hacs["homeassistant"])


def test_release_check_metadata_only_passes() -> None:
    """Release check metadata validation must pass in the repository."""
    completed = subprocess.run(
        [sys.executable, "tools/release_check.py", "--skip-quality"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_release_check_collect_results() -> None:
    """Release check helpers must report all required file checks."""
    sys.path.insert(0, str(ROOT))
    from tools.release_check import check_required_files, check_versions

    file_results = check_required_files()
    version_results = check_versions()
    assert all(result.ok for result in file_results)
    assert all(result.ok for result in version_results)


def test_benchmark_runs_with_minimal_dataset() -> None:
    """Benchmark script must execute and print timings."""
    completed = subprocess.run(
        [
            sys.executable,
            "tools/benchmark.py",
            "--files",
            "1",
            "--commands-per-file",
            "2",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "SmartIRProvider.load" in completed.stdout
    assert "SuccessMemory" in completed.stdout


@pytest.mark.parametrize(
    "script_name",
    ["benchmark.py", "release_check.py", "coverage.sh"],
)
def test_tool_files_exist_and_are_non_empty(script_name: str) -> None:
    """Development tools must be present in tools/."""
    path = TOOLS_DIR / script_name
    assert path.is_file()
    assert path.read_text(encoding="utf-8").strip()


def test_readme_links_to_compatibility_and_release_notes() -> None:
    """README must reference compatibility and release documentation."""
    readme = _read_text(ROOT / "README.md")
    assert "docs/compatibility.md" in readme
    assert "docs/release_notes_v1.md" in readme


def test_security_policy_declares_supported_versions() -> None:
    """SECURITY.md must document supported versions."""
    security = _read_text(ROOT / "SECURITY.md")
    assert "Supported versions" in security
    assert "1.0" in security
