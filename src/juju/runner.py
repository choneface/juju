from __future__ import annotations

import asyncio
import importlib.util
import inspect
import sys
import time
import traceback
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

Hook = Callable[[], Union[Any, Awaitable[Any]]]
TestFn = Callable[[], Union[Any, Awaitable[Any]]]


@dataclass
class Registry:
    setups: list[Hook] = field(default_factory=list)
    teardowns: list[Hook] = field(default_factory=list)
    tests: list[TestFn] = field(default_factory=list)


registry = Registry()


def setup(fn: Hook) -> Hook:
    registry.setups.append(fn)
    return fn


def teardown(fn: Hook) -> Hook:
    registry.teardowns.append(fn)
    return fn


def test(fn: TestFn) -> TestFn:
    registry.tests.append(fn)
    return fn


@dataclass(frozen=True)
class TestResult:
    name: str
    passed: bool
    duration: float
    error: str | None = None


async def run_files(paths: list[str | Path], jobs: int | None = None) -> int:
    registry.setups.clear()
    registry.teardowns.clear()
    registry.tests.clear()

    for path in paths:
        load_file(Path(path))

    if not registry.tests:
        print("juju: no tests registered", file=sys.stderr)
        return 1

    try:
        for fn in registry.setups:
            await call(fn)

        results = await run_tests(registry.tests, jobs=jobs)
    finally:
        for fn in reversed(registry.teardowns):
            await call(fn)

    failed = [result for result in results if not result.passed]
    for result in results:
        status = "ok" if result.passed else "fail"
        print(f"{status} {result.name} ({result.duration:.3f}s)")
        if result.error:
            print(indent(result.error.rstrip(), "  "))

    passed = len(results) - len(failed)
    print(f"\njuju: {passed} passed, {len(failed)} failed")
    return 1 if failed else 0


async def run_tests(tests: list[TestFn], jobs: int | None = None) -> list[TestResult]:
    if jobs is None or jobs < 1:
        jobs = len(tests)

    semaphore = asyncio.Semaphore(jobs)

    async def run_one(fn: TestFn) -> TestResult:
        async with semaphore:
            started = time.perf_counter()
            try:
                await call(fn)
                return TestResult(name=fn.__name__, passed=True, duration=time.perf_counter() - started)
            except Exception:
                return TestResult(
                    name=fn.__name__,
                    passed=False,
                    duration=time.perf_counter() - started,
                    error=traceback.format_exc(),
                )

    return await asyncio.gather(*(run_one(fn) for fn in tests))


async def call(fn: Callable[..., Any]) -> Any:
    result = fn()
    if inspect.isawaitable(result):
        return await result
    return result


def load_file(path: Path) -> None:
    path = path.resolve()
    module_name = f"juju_user_test_{abs(hash(path))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"could not load test file: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)


def indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())
