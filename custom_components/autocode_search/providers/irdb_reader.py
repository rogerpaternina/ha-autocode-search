"""IRDB file discovery, reading, and IRCode conversion."""

from __future__ import annotations

import csv
import json
import logging
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models.ir_code import IRCode

_LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".csv", ".json")


@dataclass(frozen=True, slots=True)
class IRDBFileReference:
    """Describe one IRDB file discovered on disk."""

    path: Path
    manufacturer: str | None
    device_type: str | None
    model: str | None


def discover_irdb_files(database_path: Path) -> list[IRDBFileReference]:
    """Discover every supported IRDB file below the database root."""
    if not database_path.is_dir():
        return []

    _LOGGER.debug("Scanning IRDB files")
    references: list[IRDBFileReference] = []
    for file_path in sorted(database_path.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        references.append(_build_file_reference(database_path, file_path))

    return references


def read_irdb_file(reference: IRDBFileReference) -> list[IRCode]:
    """Read one IRDB file and convert its contents to IRCode objects."""
    if reference.path.suffix.lower() == ".csv":
        return _read_csv_file(reference)
    if reference.path.suffix.lower() == ".json":
        return _read_json_file(reference)
    return []


def read_irdb_database(database_path: Path) -> list[IRCode]:
    """Discover and read every supported IRDB file."""
    references = discover_irdb_files(database_path)
    codes: list[IRCode] = []
    loaded_files = 0

    for reference in references:
        file_codes = read_irdb_file(reference)
        if not file_codes:
            continue
        loaded_files += 1
        codes.extend(file_codes)

    _LOGGER.debug("Loaded %d files", loaded_files)
    _LOGGER.debug("Loaded %d IR codes", len(codes))
    return codes


def _build_file_reference(database_path: Path, file_path: Path) -> IRDBFileReference:
    """Build metadata for a discovered IRDB file from its relative path."""
    relative_parts = file_path.relative_to(database_path).parts
    manufacturer = relative_parts[0] if len(relative_parts) >= 3 else None
    device_type = relative_parts[1] if len(relative_parts) >= 3 else None
    model = file_path.stem if file_path.stem else None
    return IRDBFileReference(
        path=file_path,
        manufacturer=manufacturer,
        device_type=device_type,
        model=model,
    )


def _read_csv_file(reference: IRDBFileReference) -> list[IRCode]:
    """Convert one IRDB CSV file into IRCode objects."""
    try:
        with reference.path.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                _LOGGER.warning(
                    "Invalid IRDB CSV file %s: missing header", reference.path
                )
                return []

            return [
                code
                for row in reader
                if (code := _csv_row_to_ir_code(row, reference)) is not None
            ]
    except (OSError, UnicodeDecodeError, csv.Error) as err:
        _LOGGER.warning("Unable to load IRDB file %s: %s", reference.path, err)
        return []


def _csv_row_to_ir_code(
    row: Mapping[str, str | None], reference: IRDBFileReference
) -> IRCode | None:
    """Convert one IRDB CSV row into an IRCode."""
    function_name = _row_value(row, "functionname", "function_name", "function")
    protocol = _row_value(row, "protocol")
    device = _row_value(row, "device")
    subdevice = _row_value(row, "subdevice")
    function = _row_value(row, "function")

    if not function_name or not protocol or not device or not subdevice or not function:
        return None

    supported_models = (reference.model,) if reference.model else None
    return IRCode(
        name=function_name,
        payload=_build_protocol_payload(protocol, device, subdevice, function),
        protocol=protocol,
        manufacturer=reference.manufacturer,
        model=reference.model,
        device_type=reference.device_type,
        supported_models=supported_models,
    )


def _read_json_file(reference: IRDBFileReference) -> list[IRCode]:
    """Convert one IRDB JSON file into IRCode objects."""
    try:
        with reference.path.open(encoding="utf-8") as file:
            raw_data: Any = json.load(file)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as err:
        _LOGGER.warning("Unable to load IRDB file %s: %s", reference.path, err)
        return []

    if not isinstance(raw_data, dict):
        _LOGGER.warning("Invalid IRDB file %s: expected an object", reference.path)
        return []

    return _json_object_to_ir_codes(raw_data, reference)


def _json_object_to_ir_codes(
    data: dict[str, Any], reference: IRDBFileReference
) -> list[IRCode]:
    """Convert a JSON object into one or more IRCode instances."""
    commands = data.get("commands")
    if isinstance(commands, dict):
        manufacturer = (
            _optional_string(data.get("manufacturer")) or reference.manufacturer
        )
        device_type = _optional_string(data.get("device_type")) or reference.device_type
        supported_models = _supported_models(data.get("supportedModels"))
        model = supported_models[0] if supported_models else reference.model
        protocol = _optional_string(data.get("protocol"))

        return [
            IRCode(
                name=name,
                payload=payload,
                protocol=protocol,
                manufacturer=manufacturer,
                model=model,
                device_type=device_type,
                supported_models=supported_models,
            )
            for name, payload in _iter_json_commands(commands)
            if isinstance(payload, str) and payload
        ]

    if all(key in data for key in ("name", "payload")):
        return [
            IRCode(
                name=str(data["name"]),
                payload=str(data["payload"]),
                protocol=_optional_string(data.get("protocol")),
                manufacturer=_optional_string(data.get("manufacturer"))
                or reference.manufacturer,
                model=_optional_string(data.get("model")) or reference.model,
                device_type=_optional_string(data.get("device_type"))
                or reference.device_type,
                supported_models=_supported_models(data.get("supportedModels")),
            )
        ]

    _LOGGER.warning("Unsupported IRDB JSON structure in %s", reference.path)
    return []


def _iter_json_commands(
    commands: Mapping[str, Any], prefix: tuple[str, ...] = ()
) -> Iterator[tuple[str, str]]:
    """Flatten nested JSON command objects into named payloads."""
    for command, value in commands.items():
        path = (*prefix, command)
        if isinstance(value, str):
            yield _command_name(path), value
        elif isinstance(value, dict):
            yield from _iter_json_commands(value, path)


def _command_name(parts: tuple[str, ...]) -> str:
    first, *rest = parts
    return first + "".join(part[:1].upper() + part[1:] for part in rest)


def _build_protocol_payload(
    protocol: str, device: str, subdevice: str, function: str
) -> str:
    """Build a provider-neutral payload from IRDB protocol fields."""
    return f"{protocol}:{device},{subdevice},{function}"


def _row_value(row: Mapping[str, str | None], *keys: str) -> str | None:
    """Return the first populated CSV column for the requested keys."""
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _supported_models(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None

    models = tuple(model for model in value if isinstance(model, str) and model)
    return models or None
