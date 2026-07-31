import asyncio
import subprocess
import sys
import unittest
from pathlib import Path

from be_the_cowboy.runner import run_tests


class RunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_runs_tests_concurrently(self):
        started = asyncio.Event()
        finished = []

        async def first():
            started.set()
            await asyncio.sleep(0.05)
            finished.append("first")

        async def second():
            await started.wait()
            finished.append("second")

        results = await run_tests([first, second])

        self.assertTrue(all(result.passed for result in results))
        self.assertEqual(finished, ["second", "first"])


class CliTests(unittest.TestCase):
    def test_cli_runs_registered_tests(self):
        root = Path(__file__).resolve().parents[1]
        fixture = root / "tests" / "fixtures" / "be_the_cowboy_sample_test.py"

        completed = subprocess.run(
            [sys.executable, "-m", "be_the_cowboy.cli", "test", str(fixture)],
            cwd=root,
            env={"PYTHONPATH": str(root / "src")},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("be-the-cowboy: 2 passed, 0 failed", completed.stdout)
