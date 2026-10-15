"""Domain 层：任务事件与最小事件总线（Phase 1 任务 3）。

对应 AGENTS.md 第 2.7 条：事件携带 run_id、task_id、时间戳、状态与必要诊断数据；
事件类型：TaskStarted / TaskProgress / TaskCompleted / TaskFailed / TaskCancelled / ConnectionChanged。

实现原则（第 2.10 条）：自研轻量同步订阅，不引入大型事件库；
订阅者异常不影响其他订阅者与任务执行。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .state import ExecutionState


class EventType(str, Enum):
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    CONNECTION_CHANGED = "connection_changed"


@dataclass
class TaskEvent:
    type: EventType
    run_id: str
    task_id: str
    timestamp: float = field(default_factory=time.time)
    state: Optional[ExecutionState] = None
    message: str = ""
    diagnostic: dict = field(default_factory=dict)


Handler = Callable[[TaskEvent], None]


class EventBus:
    """最小同步事件总线。

    用法：
        bus = EventBus()
        bus.subscribe(EventType.TASK_FAILED, lambda e: print(e))
        bus.publish(TaskEvent(...))
    """

    def __init__(self) -> None:
        self._subs: dict[EventType, list[Handler]] = {}
        self._all: list[Handler] = []

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        self._subs.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        """订阅全部事件类型。"""
        self._all.append(handler)

    def publish(self, event: TaskEvent) -> None:
        for handler in list(self._all) + list(self._subs.get(event.type, [])):
            try:
                handler(event)
            except Exception:  # noqa: BLE001 —— 订阅者异常不得影响任务执行
                continue

    def listener_count(self, event_type: Optional[EventType] = None) -> int:
        if event_type is None:
            return len(self._all) + sum(len(v) for v in self._subs.values())
        return len(self._subs.get(event_type, [])) + len(self._all)
