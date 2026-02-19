from __future__ import annotations

import json
from pathlib import Path

from gw_engine.artifacts import register_artifact
from gw_engine.run_context import RunContext


def test_register_artifact_appends_to_index(tmp_path: Path) -> None:
    ctx = RunContext.create(tmp_path / "runs")

    a = ctx.artifacts_dir / "a.txt"
    b = ctx.artifacts_dir / "b.txt"
    a.write_text("a\n", encoding="utf-8")
    b.write_text("b\n", encoding="utf-8")

    register_artifact(ctx, name="a", path=a, type="txt", metadata={"n": 1})
    register_artifact(ctx, name="b", path=b, type="txt", metadata={"n": 1})

    payload = json.loads(ctx.artifacts_index_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert [x["name"] for x in payload] == ["a", "b"]
    assert all(x["path"].startswith("artifacts/") for x in payload)
