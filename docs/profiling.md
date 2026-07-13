# Profiling AutoCode Search

This guide explains how to profile the integration locally during development.
Profiling is **not** integrated into Home Assistant or the release pipeline.

## cProfile

Use the standard library profiler to measure function-level cost in tests or
benchmarks.

```sh
python3 -m cProfile -o autocode.prof -m pytest tests/providers/test_smartir_provider.py -q
python3 -m pstats autocode.prof
```

Inside `pstats`:

```text
sort cumtime
stats 20
```

To profile the development benchmark:

```sh
python3 -m cProfile -o benchmark.prof tools/benchmark.py --files 10 --commands-per-file 50
python3 -m pstats benchmark.prof
```

### Tips

- Profile one module or test file at a time for clearer output.
- Compare profiles before and after an optimization on the same machine.
- Ignore the first run when filesystem caches are cold; run twice and compare
  the second profile.

## py-spy

[py-spy](https://github.com/benfred/py-spy) samples a running Python process
without modifying code. It is useful when reproducing a slowdown inside Docker.

Install:

```sh
pip install py-spy
```

Record a flame graph while Home Assistant is running in Docker:

```sh
cd docker
docker compose up -d
docker compose top
py-spy record -o autocode-flame.svg --pid <home-assistant-pid> --duration 30
```

While the sample runs, trigger an AutoCode Search session from the UI or
Developer Tools.

### Tips

- Use `--native` if you need C-extension visibility.
- Keep the sample window short (15–30 seconds) and focused on one action.
- Do not ship flame graphs with private paths or tokens.

## Related tools

- `tools/benchmark.py` — repeatable provider and memory timings.
- `tools/coverage.sh` — pytest coverage with HTML output.
- `tools/release_check.py` — release validation before tagging.
