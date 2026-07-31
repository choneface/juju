from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Response:
    body: Any
    raw: bytes

    @property
    def json(self) -> Any:
        return self.body

    @property
    def text(self) -> str:
        return self.raw.decode("utf-8", errors="replace")

    def expect(self, expected: Mapping[str, Any] | Callable[[Any], bool] | Any) -> "Response":
        if callable(expected):
            if not expected(self.body):
                raise AssertionError(f"response did not satisfy predicate: {self.body!r}")
            return self

        if isinstance(expected, Mapping) and isinstance(self.body, Mapping):
            missing = {}
            for key, value in expected.items():
                if self.body.get(key) != value:
                    missing[key] = {"expected": value, "actual": self.body.get(key)}
            if missing:
                raise AssertionError(f"response fields did not match: {missing!r}")
            return self

        if self.body != expected:
            raise AssertionError(f"expected {expected!r}, got {self.body!r}")
        return self
