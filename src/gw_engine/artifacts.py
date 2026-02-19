from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gw_engine.run_context import RunContext, iso_utc_from_ms, now_ms


@dataclass(frozen=True)
class ArtifactRecord:
    name: str
    type: str
    path: str  # path relative to run_dir (posix)
    created_at: str  # ISO UTC
    metadata: dict[str, Any]


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(path)


def load_artifact_index(ctx: RunContext) -> list[dict[str, Any]]:
    if not ctx.artifacts_index_path.exists():
        return []
    with ctx.artifacts_index_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("artifact index must be a JSON list")
    return data


def register_artifact(
    ctx: RunContext,
    *,
    name: str,
    path: Path,
    type: str,
    metadata: dict[str, Any] | None = None,
) -> ArtifactRecord:
    rel = path.relative_to(ctx.run_dir).as_posix()
    rec = ArtifactRecord(
        name=name,
        type=type,
        path=rel,
        created_at=iso_utc_from_ms(now_ms()),
        metadata=metadata or {},
    )

    index = load_artifact_index(ctx)
    index.append(
        {
            "name": rec.name,
            "type": rec.type,
            "path": rec.path,
            "created_at": rec.created_at,
            "metadata": rec.metadata,
        }
    )
    _atomic_write_json(ctx.artifacts_index_path, index)
    return rec
