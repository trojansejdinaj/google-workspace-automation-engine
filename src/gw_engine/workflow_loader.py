from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, cast

from gw_engine.contracts import Workflow


class WorkflowLoadError(RuntimeError):
    pass


def load_workflow_from_repo_root(
    repo_root: Path, workflow_name: str, cfg: dict[str, Any]
) -> Workflow:
    wf_py = repo_root / "workflows" / workflow_name / "workflow.py"
    if not wf_py.exists():
        raise WorkflowLoadError(f"Missing workflow entrypoint: {wf_py}")

    spec = importlib.util.spec_from_file_location(f"gw_workflow_{workflow_name}", wf_py)
    if spec is None or spec.loader is None:
        raise WorkflowLoadError(f"Could not load spec for: {wf_py}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    get_workflow = getattr(mod, "get_workflow", None)
    if not callable(get_workflow):
        raise WorkflowLoadError(f"{wf_py} must define: get_workflow(cfg) -> Workflow")

    wf = get_workflow(cfg)
    return cast(Workflow, wf)
