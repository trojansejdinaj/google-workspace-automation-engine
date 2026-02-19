from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


def new_run_id() -> str:
    # short + sortable-ish enough for now
    # (later you can switch to ULID without breaking the interface)
    return uuid4().hex


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_dir: Path
    logs_path: Path

    # T5: artifacts index contract
    artifacts_dir: Path
    artifacts_index_path: Path

    @staticmethod
    def create(runs_dir: Path) -> RunContext:
        run_id = new_run_id()
        run_dir = runs_dir / run_id
        logs_path = run_dir / "logs.jsonl"

        artifacts_dir = run_dir / "artifacts"
        artifacts_index_path = artifacts_dir / "index.json"

        run_dir.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        return RunContext(
            run_id=run_id,
            run_dir=run_dir,
            logs_path=logs_path,
            artifacts_dir=artifacts_dir,
            artifacts_index_path=artifacts_index_path,
        )


def now_ms() -> int:
    return int(time.time() * 1000)


def duration_ms(start_ms: int, end_ms: int) -> int:
    return max(0, end_ms - start_ms)


def iso_utc_from_ms(ms: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms / 1000))
