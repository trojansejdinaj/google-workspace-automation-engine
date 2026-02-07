from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from gw_engine.logger import JsonlLogger
from gw_engine.run_context import RunContext


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    OK = "OK"
    FAILED = "FAILED"


@dataclass(frozen=True)
class StepResult:
    ok: bool
    outputs: dict[str, Any] | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        if not self.ok and not self.error:
            raise ValueError("error is required when ok is False")


@dataclass(frozen=True)
class Step:
    name: str
    fn: Callable[[RunContext, RunState, JsonlLogger], StepResult]

    def run(self, ctx: RunContext, state: RunState, log: JsonlLogger) -> StepResult:
        return self.fn(ctx, state, log)


@dataclass(frozen=True)
class Workflow:
    name: str
    steps: list[Step]


@dataclass
class RunState:
    data: dict[str, Any] = field(default_factory=dict)
    step_outputs: dict[str, Any] = field(default_factory=dict)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "data": self.data,
            "step_outputs": self.step_outputs,
        }

    def persist(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        payload = self.to_jsonable()
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")
        tmp_path.replace(path)
