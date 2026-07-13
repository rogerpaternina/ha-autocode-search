#!/usr/bin/env python3
"""Development benchmark for AutoCode Search provider and memory performance."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from custom_components.autocode_search.memory import SuccessMemory  # noqa: E402
from custom_components.autocode_search.models.ir_code import IRCode  # noqa: E402
from custom_components.autocode_search.models.search_filter import (  # noqa: E402
    SearchFilter,
)
from custom_components.autocode_search.providers.composite import (  # noqa: E402
    CompositeCodeProvider,
)
from custom_components.autocode_search.providers.factory import (  # noqa: E402
    ProviderFactory,
)
from custom_components.autocode_search.providers.irdb import IRDBProvider  # noqa: E402
from custom_components.autocode_search.providers.lirc import LIRCProvider  # noqa: E402
from custom_components.autocode_search.providers.memory import (  # noqa: E402
    InMemoryCodeProvider,
)
from custom_components.autocode_search.providers.ranking import (  # noqa: E402
    ProviderRanking,
)
from custom_components.autocode_search.providers.smartir import (  # noqa: E402
    SmartIRProvider,
)


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Store the label and elapsed time for one benchmark step."""

    label: str
    seconds: float


class FakeConfig:
    """Resolve configuration paths below a temporary benchmark root."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def path(self, *parts: str) -> str:
        """Return a path relative to the fake configuration directory."""
        return str(self._root.joinpath(*parts))


class FakeHomeAssistant:
    """Expose the configuration API used by filesystem providers."""

    def __init__(self, root: Path) -> None:
        self.config = FakeConfig(root)


def _elapsed(start: float) -> float:
    return time.perf_counter() - start


def _write_smartir_dataset(root: Path, files: int, commands_per_file: int) -> None:
    category = root / "custom_components" / "smartir" / "codes" / "tv"
    category.mkdir(parents=True, exist_ok=True)
    for index in range(files):
        commands = {
            f"COMMAND_{command_index}": f"PAYLOAD_{index}_{command_index}"
            for command_index in range(commands_per_file)
        }
        payload = {
            "manufacturer": "LG",
            "supportedModels": [f"MODEL_{index}"],
            "supportedController": "Broadlink",
            "commands": commands,
        }
        (category / f"device_{index}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )


def _write_irdb_dataset(root: Path, files: int, commands_per_file: int) -> None:
    database = root / "irdb" / "codes" / "LG" / "TV"
    database.mkdir(parents=True, exist_ok=True)
    for index in range(files):
        rows = [
            (
                f"COMMAND_{command_index}",
                "NEC",
                "7",
                "7",
                str(command_index),
            )
            for command_index in range(commands_per_file)
        ]
        csv_file = database / f"MODEL_{index}.csv"
        csv_file.write_text(
            "functionname,protocol,device,subdevice,function\n"
            + "\n".join(
                f"{function_name},{protocol},{device},{subdevice},{function}"
                for function_name, protocol, device, subdevice, function in rows
            ),
            encoding="utf-8",
        )


def _write_lirc_dataset(root: Path, files: int, commands_per_file: int) -> None:
    database = root / "lirc" / "remotes" / "LG" / "TV"
    database.mkdir(parents=True, exist_ok=True)
    for index in range(files):
        lines = [
            "begin remote",
            f"  name  MODEL_{index}",
            "  protocol NEC",
            "  begin codes",
        ]
        lines.extend(
            f"    COMMAND_{command_index}  0x{index:04d}{command_index:04d}"
            for command_index in range(commands_per_file)
        )
        lines.extend(["  end codes", "end remote"])
        (database / f"device_{index}.conf").write_text(
            "\n".join(lines), encoding="utf-8"
        )


async def _benchmark_provider_load(
    label: str,
    provider: SmartIRProvider | IRDBProvider | LIRCProvider | InMemoryCodeProvider,
    search_filter: SearchFilter | None = None,
) -> BenchmarkResult:
    start = time.perf_counter()
    await provider.load(search_filter)
    return BenchmarkResult(label=label, seconds=_elapsed(start))


async def _benchmark_composite(hass: FakeHomeAssistant) -> BenchmarkResult:
    provider = CompositeCodeProvider(
        [
            SmartIRProvider(hass),
            IRDBProvider(hass),
            LIRCProvider(hass),
        ]
    )
    start = time.perf_counter()
    await provider.load(None)
    return BenchmarkResult(label="CompositeProvider.load", seconds=_elapsed(start))


def _benchmark_ranking(
    providers: list[SmartIRProvider | IRDBProvider | LIRCProvider],
) -> BenchmarkResult:
    ranking = ProviderRanking()
    search_filter = SearchFilter(
        manufacturer="LG",
        model="MODEL_0",
        device_type="tv",
        command="COMMAND_0",
    )
    start = time.perf_counter()
    for _ in range(1000):
        ranking.rank(search_filter, providers)
    return BenchmarkResult(label="ProviderRanking.rank x1000", seconds=_elapsed(start))


def _benchmark_success_memory(records: int) -> BenchmarkResult:
    memory = SuccessMemory()
    search_filter = SearchFilter(
        manufacturer="LG",
        model="MODEL_0",
        device_type="tv",
        command="COMMAND_0",
    )
    start = time.perf_counter()
    for index in range(records):
        memory.remember(
            search_filter,
            IRCode(
                name=f"COMMAND_{index}",
                payload=f"PAYLOAD_{index}",
                manufacturer="LG",
                model="MODEL_0",
                device_type="tv",
            ),
            "smartir",
        )
        memory.find(search_filter)
    return BenchmarkResult(
        label=f"SuccessMemory remember+match x{records}",
        seconds=_elapsed(start),
    )


async def run_benchmarks(
    *, files: int, commands_per_file: int
) -> list[BenchmarkResult]:
    """Execute all benchmark scenarios and return their timings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        _write_smartir_dataset(root, files, commands_per_file)
        _write_irdb_dataset(root, files, commands_per_file)
        _write_lirc_dataset(root, files, commands_per_file)
        hass = FakeHomeAssistant(root)
        search_filter = SearchFilter(
            manufacturer="LG",
            model="MODEL_0",
            device_type="tv",
            command="COMMAND_0",
        )
        providers = [
            SmartIRProvider(hass),
            IRDBProvider(hass),
            LIRCProvider(hass),
        ]

        results = [
            await _benchmark_provider_load(
                "SmartIRProvider.load",
                SmartIRProvider(hass),
                search_filter,
            ),
            await _benchmark_provider_load(
                "IRDBProvider.load",
                IRDBProvider(hass),
                search_filter,
            ),
            await _benchmark_provider_load(
                "LIRCProvider.load",
                LIRCProvider(hass),
                search_filter,
            ),
            await _benchmark_composite(hass),
            _benchmark_ranking(providers),
            _benchmark_success_memory(records=250),
        ]

        memory_codes = [
            IRCode(name=f"COMMAND_{index}", payload=f"PAYLOAD_{index}")
            for index in range(files * commands_per_file)
        ]
        results.append(
            await _benchmark_provider_load(
                "InMemoryCodeProvider.load",
                InMemoryCodeProvider(memory_codes),
                search_filter,
            )
        )
        factory_start = time.perf_counter()
        ProviderFactory.create("composite", hass)
        results.append(
            BenchmarkResult(
                label="ProviderFactory.create(composite)",
                seconds=_elapsed(factory_start),
            )
        )
        return results


def _print_results(results: list[BenchmarkResult]) -> None:
    width = max(len(result.label) for result in results)
    print(f"{'Benchmark':<{width}}  Seconds")
    print(f"{'-' * width}  -------")
    for result in results:
        print(f"{result.label:<{width}}  {result.seconds:.4f}")


def main() -> int:
    """Run provider and memory benchmarks from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--files", type=int, default=5, help="Dataset files per provider"
    )
    parser.add_argument(
        "--commands-per-file",
        type=int,
        default=20,
        help="Commands generated in each dataset file",
    )
    args = parser.parse_args()
    results = asyncio.run(
        run_benchmarks(files=args.files, commands_per_file=args.commands_per_file)
    )
    _print_results(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
