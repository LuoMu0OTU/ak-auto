"""Domain 层：执行状态机与执行结果（Phase 1 任务 2）。

对应 AGENTS.md 第 2.6/2.7 条：
- 状态：Pending / Preparing / Running / Stopping / Succeeded / Failed / Cancelled
  （Paused 暂不启用：底层 MaaFw 不支持安全检查点）。
- 所有运行必须有终态；事件携带 run_id / task_id / 时间戳 / 状态 / 诊断。
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class ExecutionState(str, Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    RUNNING = "running"
    STOPPING = "stopping"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in _TERMINAL


_TERMINAL = frozenset({ExecutionState.SUCCEEDED, ExecutionState.FAILED, ExecutionState.CANCELLED})

# 合法转移表（终态无出边）
_ALLOWED: dict[ExecutionState, frozenset[ExecutionState]] = {
    ExecutionState.PENDING: frozenset({ExecutionState.PREPARING, ExecutionState.CANCELLED}),
    ExecutionState.PREPARING: frozenset({ExecutionState.RUNNING, ExecutionState.FAILED, ExecutionState.CANCELLED}),
    ExecutionState.RUNNING: frozenset(
        {ExecutionState.STOPPING, ExecutionState.SUCCEEDED, ExecutionState.FAILED, ExecutionState.CANCELLED}
    ),
    ExecutionState.STOPPING: frozenset({ExecutionState.SUCCEEDED, ExecutionState.FAILED, ExecutionState.CANCELLED}),
    ExecutionState.SUCCEEDED: frozenset(),
    ExecutionState.FAILED: frozenset(),
    ExecutionState.CANCELLED: frozenset(),
}


class IllegalTransition(RuntimeError):
    """非法状态转移。"""


class StateMachine:
    """最小执行状态机：只允许合法转移，终态不可再转。"""

    def __init__(self, initial: ExecutionState = ExecutionState.PENDING) -> None:
        self.state = initial

    def transition(self, to: ExecutionState) -> None:
        if to not in _ALLOWED.get(self.state, frozenset()):
            raise IllegalTransition(f"非法状态转移：{self.state.value} -> {to.value}")
        self.state = to

    @property
    def terminal(self) -> bool:
        return self.state.terminal


def new_run_id() -> str:
    return f"run-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"


@dataclass
class ExecutionResult:
    """一次任务运行的最终结果（含 TaskResult 的兼容字段）。"""

    run_id: str
    task_id: str
    state: ExecutionState
    duration_ms: int = 0
    nodes: list[str] = field(default_factory=list)
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0

    # ---- TaskResult 兼容层（report.py 等旧调用方零改动）----
    @property
    def entry(self) -> str:
        return self.task_id

    @property
    def ok(self) -> bool:
        return self.state is ExecutionState.SUCCEEDED

    @property
    def status(self) -> str:
        return self.state.value

    @property
    def summary(self) -> str:
        n = len(self.nodes)
        mark = "OK" if self.ok else "FAIL"
        status = self.error or self.status  # 如 missing-node 这类合成错误优先展示
        return f"{self.task_id}: {mark} ({status}, {self.duration_ms}ms, {n} nodes)"

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "state": self.state.value,
            "ok": self.ok,
            "duration_ms": self.duration_ms,
            "nodes": self.nodes,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }
