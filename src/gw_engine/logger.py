from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _iso_utc(ts: float | None = None) -> str:
    # RFC3339-ish without external deps; good enough for baseline.
    # time.time() is seconds since epoch.
    t = time.gmtime(ts if ts is not None else time.time())
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", t)


@dataclass
class JsonlLogger:
    path: Path
    component: str

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, level: str, event: str, **fields: Any) -> None:
        record: dict[str, Any] = {
            "ts": _iso_utc(),
            "level": level.upper(),
            "component": self.component,
            "event": event,
            **fields,
        }
        # One JSON object per line (JSONL)
        line = json.dumps(record, ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def info(self, event: str, **fields: Any) -> None:
        self.log("INFO", event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self.log("ERROR", event, **fields)

    def debug(self, event: str, **fields: Any) -> None:
        self.log("DEBUG", event, **fields)
