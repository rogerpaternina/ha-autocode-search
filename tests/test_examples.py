"""Validate example YAML files reference existing entities and services."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
SERVICES_YAML = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "autocode_search"
    / "services.yaml"
)
TRANSLATIONS_EN = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "autocode_search"
    / "translations"
    / "en.json"
)

INTEGRATION_ENTITY_IDS = {
    "sensor.autocode_search_progress",
    "sensor.autocode_search_codes_tested",
    "sensor.autocode_search_total_codes",
    "sensor.autocode_search_current_command",
    "sensor.autocode_search_current_manufacturer",
    "sensor.autocode_search_current_model",
    "sensor.autocode_search_elapsed_time",
    "sensor.autocode_search_filter_summary",
    "sensor.autocode_search_providers_used",
    "sensor.autocode_search_duplicates_removed",
    "sensor.autocode_search_provider_order",
    "sensor.autocode_search_provider_ranking_reason",
    "sensor.autocode_search_success_records",
    "sensor.autocode_search_last_success",
    "sensor.autocode_search_last_provider",
    "sensor.autocode_search_last_tested_command",
    "binary_sensor.autocode_search_running",
    "binary_sensor.autocode_search_waiting_confirmation",
    "button.autocode_search_confirm_success",
    "button.autocode_search_reject_result",
}

EXAMPLE_HELPER_ENTITIES = {
    "input_select.autocode_manufacturer",
    "input_select.autocode_device_type",
    "input_select.autocode_provider",
    "input_text.autocode_model",
    "input_text.autocode_command",
}

EXAMPLE_SCRIPTS = {
    "script.search_start",
    "script.search_power",
    "script.search_volume_up",
    "script.search_mute",
    "script.search_input",
}

INTEGRATION_SERVICES = {
    "autocode_search.start_search",
    "autocode_search.next_code",
    "autocode_search.previous_code",
    "autocode_search.finish_search",
    "autocode_search.pause",
    "autocode_search.resume",
    "autocode_search.cancel",
    "autocode_search.mark_success",
    "autocode_search.clear_success_memory",
    "autocode_search.confirm_success",
    "autocode_search.reject_result",
}

EXAMPLE_PLACEHOLDER_ENTITIES = {
    "binary_sensor.living_room_confirm_button",
    "remote.living_room",
}

ENTITY_PATTERN = re.compile(
    r"(?:entity|entity_id):\s+"
    r"((?:sensor|binary_sensor|button|input_select|input_text|script)\.[a-z0-9_]+)"
)

SERVICE_PATTERN = re.compile(
    r"(?:service|action):\s+(autocode_search\.\w+|script\.\w+)"
)


def _load_services_from_yaml() -> set[str]:
    """Load service names declared in services.yaml."""
    content = SERVICES_YAML.read_text(encoding="utf-8")
    services: set[str] = set()
    for line in content.splitlines():
        if line and not line.startswith(" ") and line.endswith(":"):
            services.add(f"autocode_search.{line[:-1]}")
    return services


def _collect_yaml_files() -> list[Path]:
    """Return all example YAML files."""
    return sorted(EXAMPLES_DIR.glob("*.yaml"))


@pytest.fixture
def example_contents() -> dict[str, str]:
    """Load all example YAML file contents."""
    return {
        path.name: path.read_text(encoding="utf-8") for path in _collect_yaml_files()
    }


@pytest.mark.parametrize("yaml_file", _collect_yaml_files(), ids=lambda p: p.name)
def test_example_yaml_is_non_empty_and_well_formed(yaml_file: Path) -> None:
    """Each example YAML file must be non-empty with expected structure."""
    content = yaml_file.read_text(encoding="utf-8")
    assert content.strip(), f"{yaml_file.name} is empty"

    if yaml_file.name == "lovelace-dashboard.yaml":
        assert "title:" in content
        assert "views:" in content
    elif yaml_file.name == "entities.yaml":
        assert "input_select:" in content
        assert "input_text:" in content
    elif yaml_file.name == "automations.yaml":
        assert "- id:" in content
        assert "action:" in content
    elif yaml_file.name == "scripts.yaml":
        assert "search_power:" in content
        assert "action: autocode_search.start_search" in content


def test_all_example_files_exist() -> None:
    """All required example files must be present."""
    required = {
        "lovelace-dashboard.yaml",
        "entities.yaml",
        "automations.yaml",
        "scripts.yaml",
    }
    found = {path.name for path in _collect_yaml_files()}
    assert required == found


def test_services_yaml_matches_integration_services() -> None:
    """services.yaml must declare every integration service."""
    declared = _load_services_from_yaml()
    assert declared == INTEGRATION_SERVICES


def test_example_integration_entities_are_known(
    example_contents: dict[str, str],
) -> None:
    """Example files must only reference known integration entities."""
    for filename, content in example_contents.items():
        for match in ENTITY_PATTERN.finditer(content):
            entity_id = match.group(1)
            if entity_id.startswith("script."):
                assert (
                    entity_id in EXAMPLE_SCRIPTS
                ), f"{filename} references unknown script {entity_id}"
            elif entity_id.startswith(("input_select.", "input_text.")):
                assert (
                    entity_id in EXAMPLE_HELPER_ENTITIES
                ), f"{filename} references unknown helper {entity_id}"
            elif entity_id in EXAMPLE_PLACEHOLDER_ENTITIES:
                continue
            else:
                assert (
                    entity_id in INTEGRATION_ENTITY_IDS
                ), f"{filename} references unknown integration entity {entity_id}"


def test_example_services_are_known(example_contents: dict[str, str]) -> None:
    """Example files must only call known services."""
    known_services = INTEGRATION_SERVICES | EXAMPLE_SCRIPTS
    for filename, content in example_contents.items():
        for match in SERVICE_PATTERN.finditer(content):
            service = match.group(1)
            assert (
                service in known_services
            ), f"{filename} calls unknown service {service}"


def test_translation_keys_cover_all_sensors() -> None:
    """English translations must include every sensor entity key."""
    translations = json.loads(TRANSLATIONS_EN.read_text(encoding="utf-8"))
    sensor_keys = {key for key in translations.get("entity", {}).get("sensor", {})}
    expected_keys = {
        "progress",
        "codes_tested",
        "total_codes",
        "current_command",
        "current_manufacturer",
        "current_model",
        "elapsed_time",
        "filter_summary",
        "providers_used",
        "duplicates_removed",
        "provider_order",
        "provider_ranking_reason",
        "success_records",
        "last_success",
        "last_provider",
        "last_tested_command",
    }
    assert expected_keys.issubset(sensor_keys)
