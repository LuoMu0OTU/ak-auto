"""Domain 层：任务定义、状态、事件、策略等核心模型（Phase 1 逐步建立）。"""

from .events import EventBus, EventType, TaskEvent
from .state import (
    ExecutionResult,
    ExecutionState,
    IllegalTransition,
    StateMachine,
    new_run_id,
)
from .taskdef import ParamSpec, TASK_CATALOG, TaskDefinition, all_tasks, resolve_task

__all__ = [
    "ParamSpec",
    "TASK_CATALOG",
    "TaskDefinition",
    "all_tasks",
    "resolve_task",
    "ExecutionResult",
    "ExecutionState",
    "IllegalTransition",
    "StateMachine",
    "new_run_id",
    "EventBus",
    "EventType",
    "TaskEvent",
]
