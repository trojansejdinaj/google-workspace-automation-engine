from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gw_engine.contracts import Workflow

WorkflowFactory = Callable[[dict[str, Any]], Workflow]

_REGISTRY: dict[str, WorkflowFactory] = {}


def register(name: str, factory: WorkflowFactory) -> None:
    _REGISTRY[name] = factory


def get(name: str) -> WorkflowFactory | None:
    return _REGISTRY.get(name)


def _register_builtin_workflows() -> None:
    # Side-effect imports to populate _REGISTRY via register().
    # Kept inside a function to satisfy ruff E402.
    from gw_engine.workflows import sheets_cleanup_reporting  # noqa: F401


_register_builtin_workflows()
