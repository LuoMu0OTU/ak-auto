"""Application 层：执行控制器（Phase 1 任务 4）。

后台线程运行任务序列 + 协作式取消：
- 主线程调用 cancel() 置取消标志；
- 工作线程轮询到取消后调用 MaaFw post_stop 停止当前任务；
- 剩余任务记 CANCELLED；每次运行必有终态（SUCCEEDED / FAILED / CANCELLED）。

线程模型（AGENTS.md 第 2.3 条）：执行在非 UI 线程，状态读取加锁；事件经 EventBus 同步分发。
"""
from __future__ import annotations

import threading
from typing import Optional

from ..domain import EventBus, ExecutionResult, ExecutionState
from ..scheduler import run_sequence


class ExecutionController:
    """非阻塞任务执行 + 协作式取消。"""

    def __init__(
        self,
        tasker,
        bus: Optional[EventBus] = None,
        poll_interval: float = 0.05,
    ) -> None:
        self.tasker = tasker
        self.bus = bus
        self.poll = poll_interval
        self._cancel = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._state = ExecutionState.PENDING
        self._results: list[ExecutionResult] = []

    @property
    def state(self) -> ExecutionState:
        with self._lock:
            return self._state

    @property
    def results(self) -> list[ExecutionResult]:
        with self._lock:
            return list(self._results)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(
        self,
        entries: list[str],
        retry_per_task: int = 2,
        on_progress=None,
    ) -> None:
        """后台启动任务序列（非阻塞）。"""
        if self.running:
            raise RuntimeError("已有任务在运行，不能重复 start")
        self._cancel.clear()
        with self._lock:
            self._state = ExecutionState.PREPARING
            self._results = []
        self._thread = threading.Thread(
            target=self._worker,
            args=(list(entries), retry_per_task, on_progress),
            name="ak-auto-execution",
            daemon=True,
        )
        self._thread.start()

    def _worker(self, entries: list[str], retry: int, on_progress) -> None:
        with self._lock:
            self._state = ExecutionState.RUNNING
        results: list[ExecutionResult] = []
        try:
            results = run_sequence(
                self.tasker,
                entries,
                retry,
                on_progress=on_progress,
                bus=self.bus,
                cancel_event=self._cancel,
            )
        except Exception as exc:  # noqa: BLE001 —— 异常也必须有终态
            results.append(
                ExecutionResult(
                    run_id="",
                    task_id="<controller>",
                    state=ExecutionState.FAILED,
                    error=f"controller-error: {exc}",
                )
            )
        finally:
            with self._lock:
                self._results = results
                if any(r.state is ExecutionState.CANCELLED for r in results):
                    self._state = ExecutionState.CANCELLED
                elif results and all(r.ok for r in results):
                    self._state = ExecutionState.SUCCEEDED
                else:
                    self._state = ExecutionState.FAILED

    def cancel(self) -> None:
        """请求协作式取消（对未开始/已结束的运行无影响）。"""
        self._cancel.set()

    def wait(self, timeout: Optional[float] = None) -> list[ExecutionResult]:
        """等待运行结束（可带超时；超时返回当前已产出的结果）。"""
        if self._thread:
            self._thread.join(timeout)
        return self.results
