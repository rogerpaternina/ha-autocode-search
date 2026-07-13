"""LIRC file discovery, parsing, and IRCode conversion."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from ..models.ir_code import IRCode

_LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".conf", ".lircd.conf")
_REMOTE_NAME_PATTERN = re.compile(r"^KEY_(?P<name>.+)$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class LIRCFileReference:
    """Describe one LIRC file discovered on disk."""

    path: Path
    manufacturer: str | None
    device_type: str | None
    model: str | None


@dataclass(frozen=True, slots=True)
class LIRCRemoteDefinition:
    """Describe one remote block parsed from a LIRC configuration file."""

    name: str | None
    protocol: str | None
    commands: tuple[tuple[str, str], ...]


def discover_lirc_files(database_path: Path) -> list[LIRCFileReference]:
    """Discover every supported LIRC file below the database root."""
    if not database_path.is_dir():
        return []

    _LOGGER.debug("Scanning LIRC files")
    references: list[LIRCFileReference] = []
    for file_path in sorted(database_path.rglob("*")):
        if not file_path.is_file():
            continue
        if not _is_supported_lirc_file(file_path):
            continue
        references.append(_build_file_reference(database_path, file_path))

    return references


def read_lirc_file(reference: LIRCFileReference) -> list[IRCode]:
    """Read one LIRC file and convert its contents to IRCode objects."""
    try:
        content = reference.path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        _LOGGER.warning("Unable to load LIRC file %s: %s", reference.path, err)
        return []

    remotes = parse_lirc_config(content)
    codes: list[IRCode] = []
    for remote in remotes:
        codes.extend(_remote_to_ir_codes(remote, reference))
    return codes


def read_lirc_database(database_path: Path) -> list[IRCode]:
    """Discover and read every supported LIRC file."""
    references = discover_lirc_files(database_path)
    codes: list[IRCode] = []
    loaded_files = 0

    for reference in references:
        file_codes = read_lirc_file(reference)
        if not file_codes:
            continue
        loaded_files += 1
        codes.extend(file_codes)

    _LOGGER.debug("Loaded %d files", loaded_files)
    _LOGGER.debug("Loaded %d IR codes", len(codes))
    return codes


def parse_lirc_config(content: str) -> list[LIRCRemoteDefinition]:
    """Parse one or more remote definitions from a LIRC configuration file."""
    lines = content.splitlines()
    remotes: list[LIRCRemoteDefinition] = []
    index = 0

    while index < len(lines):
        stripped = lines[index].strip()
        if stripped == "begin remote":
            remote, index = _parse_remote_block(lines, index)
            if remote.commands:
                remotes.append(remote)
            continue
        index += 1

    return remotes


def _parse_remote_block(
    lines: list[str], start_index: int
) -> tuple[LIRCRemoteDefinition, int]:
    """Parse a ``begin remote`` block and return the next line index."""
    remote_name: str | None = None
    protocol: str | None = None
    commands: list[tuple[str, str]] = []
    index = start_index + 1

    while index < len(lines):
        stripped = lines[index].strip()
        if stripped == "end remote":
            return (
                LIRCRemoteDefinition(
                    name=remote_name,
                    protocol=protocol,
                    commands=tuple(commands),
                ),
                index + 1,
            )
        if stripped == "begin codes":
            block_commands, index = _parse_codes_block(lines, index + 1)
            commands.extend(block_commands)
            continue

        key, value = _split_key_value(stripped)
        if key == "name" and value:
            remote_name = value
        elif key == "protocol" and value:
            protocol = value
        index += 1

    return (
        LIRCRemoteDefinition(
            name=remote_name,
            protocol=protocol,
            commands=tuple(commands),
        ),
        index,
    )


def _parse_codes_block(
    lines: list[str], start_index: int
) -> tuple[list[tuple[str, str]], int]:
    """Parse a ``begin codes`` block."""
    commands: list[tuple[str, str]] = []
    index = start_index

    while index < len(lines):
        stripped = lines[index].strip()
        if stripped == "end codes":
            return commands, index + 1
        if not stripped or stripped.startswith("#"):
            index += 1
            continue

        parts = stripped.split()
        if len(parts) >= 2:
            command_name = parts[0]
            payload = " ".join(parts[1:])
            if command_name and payload:
                commands.append((command_name, payload))
        index += 1

    return commands, index


def _remote_to_ir_codes(
    remote: LIRCRemoteDefinition, reference: LIRCFileReference
) -> list[IRCode]:
    """Convert one parsed remote into IRCode objects."""
    manufacturer = reference.manufacturer
    device_type = reference.device_type
    model = reference.model or remote.name
    protocol = remote.protocol or _infer_protocol(reference.path, remote.name)
    supported_models = (model,) if model else None

    return [
        IRCode(
            name=_normalize_command_name(command_name),
            payload=payload,
            protocol=protocol,
            manufacturer=manufacturer,
            model=model,
            device_type=device_type,
            supported_models=supported_models,
        )
        for command_name, payload in remote.commands
    ]


def _build_file_reference(database_path: Path, file_path: Path) -> LIRCFileReference:
    """Build metadata for a discovered LIRC file from its relative path."""
    relative_parts = file_path.relative_to(database_path).parts
    manufacturer = relative_parts[0] if len(relative_parts) >= 3 else None
    device_type = relative_parts[1] if len(relative_parts) >= 3 else None
    model = _file_stem(file_path)
    return LIRCFileReference(
        path=file_path,
        manufacturer=manufacturer,
        device_type=device_type,
        model=model,
    )


def _is_supported_lirc_file(file_path: Path) -> bool:
    lowered_name = file_path.name.lower()
    return any(lowered_name.endswith(extension) for extension in SUPPORTED_EXTENSIONS)


def _file_stem(file_path: Path) -> str | None:
    name = file_path.name
    if name.lower().endswith(".lircd.conf"):
        stem = name[: -len(".lircd.conf")]
    elif name.lower().endswith(".conf"):
        stem = name[: -len(".conf")]
    else:
        stem = file_path.stem
    return stem or None


def _split_key_value(line: str) -> tuple[str | None, str | None]:
    parts = line.split(maxsplit=1)
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0].lower(), None
    return parts[0].lower(), parts[1].strip()


def _normalize_command_name(command_name: str) -> str:
    match = _REMOTE_NAME_PATTERN.match(command_name)
    if match is not None:
        return match.group("name").replace("_", " ").strip().lower()
    return command_name.replace("_", " ").strip().lower()


def _infer_protocol(file_path: Path, remote_name: str | None) -> str | None:
    candidates = (
        remote_name or "",
        _file_stem(file_path) or "",
        file_path.name,
    )
    for candidate in candidates:
        lowered = candidate.lower()
        for protocol in ("rc5", "rc6", "nec", "sony", "panasonic", "raw"):
            if protocol in lowered:
                return protocol.upper()
    return "LIRC"
