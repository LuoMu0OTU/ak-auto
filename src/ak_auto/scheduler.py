"""任务编排：运行单个任务、顺序执行、失败重试。

Phase 1 任务 2 起：结果统一为 domain.ExecutionResult（带 run_id / 状态机 / 错误码）；
`TaskResult` 保留为别名，旧调用方（report 等）零改动。
任务 3 起：可通过 bus 参数接收 TaskStarted/TaskProgress/TaskCompleted/TaskFailed 事件。
任务 4 起：`_run_entry` 支持协作式取消（cancel_event + MaaFw post_stop）。
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from maa.tasker import Tasker

from .domain import (
    EventBus,
    EventType,
    ExecutionResult,
    ExecutionState,
    StateMachine,
    TaskEvent,
    new_run_id,
)

# 兼容别名：旧代码 `from .scheduler import TaskResult` 仍可用
TaskResult = ExecutionResult


def _detail_status_name(detail) -> str:
    st = detail.status
    if st.succeeded:
        return "succeeded"
    if st.failed:
        return "failed"
    if st.running:
        return "running"
    if st.pending:
        return "pending"
    return "unknown"


def _run_entry(
    tasker: Tasker,
    entry: str,
    run_id: str,
    cancel_event: Optional[threading.Event] = None,
    bus: Optional[EventBus] = None,
    poll_interval: float = 0.05,
) -> tuple[ExecutionResult, bool]:
    """统一单任务执行：无 cancel_event 时与旧的阻塞 wait 等价；
    有则轮询 job.done，收到取消请求后调用 MaaFw post_stop 并置 CANCELLED。

    返回 (结果, 是否被取消)。
    """
    t0 = time.perf_counter()
    machine = StateMachine(ExecutionState.PENDING)
    machine.transition(ExecutionState.PREPARING)
    machine.transition(ExecutionState.RUNNING)

    if bus:
        bus.publish(
            TaskEvent(type=EventType.TASK_STARTED, run_id=run_id, task_id=entry,
                      state=ExecutionState.RUNNING)
        )

    job = tasker.post_task(entry)
    cancelled = False
    if cancel_event is None:
        job.wait()
    else:
        while not job.done:
            if cancel_event.is_set():
                machine.transition(ExecutionState.STOPPING)
                try:
                    tasker.post_stop().wait()
                except Exception:  # noqa: BLE001 —— 停止失败不阻塞取消路径
                    pass
                machine.transition(ExecutionState.CANCELLED)
                cancelled = True
                break
            time.sleep(poll_interval)

    detail = job.get()
    dt = int((time.perf_counter() - t0) * 1000)
    finished_at = time.time()

    if cancelled:
        state, error = ExecutionState.CANCELLED, "cancelled"
    elif detail is None:
        state, error = ExecutionState.FAILED, "no-detail"
    elif detail.status.succeeded:
        state, error = ExecutionState.SUCCEEDED, ""
    else:
        state, error = ExecutionState.FAILED, _detail_status_name(detail)

    if not machine.terminal:
        machine.transition(state)

    nodes: list[str] = []
    try:
        for n in detail.nodes if detail else []:
            if n.name:
                nodes.append(n.name)
    except Exception:  # noqa: BLE001
        pass

    if bus:
        etype = (
            EventType.TASK_CANCELLED
            if cancelled
            else EventType.TASK_COMPLETED
            if state is ExecutionState.SUCCEEDED
            else EventType.TASK_FAILED
        )
        bus.publish(
            TaskEvent(
                type=etype,
                run_id=run_id,
                task_id=entry,
                state=state,
                message=error,
                diagnostic={"nodes": nodes, "duration_ms": dt},
            )
        )

    result = ExecutionResult(
        run_id=run_id,
        task_id=entry,
        state=state,
        duration_ms=dt,
        nodes=nodes,
        error=error,
        started_at=t0,
        finished_at=finished_at,
    )
    return result, cancelled


def run_task(tasker: Tasker, entry: str, bus: Optional[EventBus] = None) -> ExecutionResult:
    """运行单个任务（入口节点）并等待结束，返回结构化结果。"""
    result, _ = _run_entry(tasker, entry, new_run_id(), cancel_event=None, bus=bus)
    return result


def _cancelled_result(entry: str) -> ExecutionResult:
    return ExecutionResult(
        run_id=new_run_id(),
        task_id=entry,
        state=ExecutionState.CANCELLED,
        error="cancelled",
    )


def _recover_capture(tasker: Tasker) -> None:
    """截图自愈前置：每个任务执行前还原窗口 + 恢复截图（失败静默继续）。"""
    try:
        from . import device

        device.recover_capture(tasker.controller)
    except Exception:  # noqa: BLE001 —— 恢复失败不阻断任务
        pass


def run_sequence(
    tasker: Tasker,
    entries: list[str],
    retry_per_task: int = 2,
    available: Optional[set[str]] = None,
    on_progress=None,
    bus: Optional[EventBus] = None,
    cancel_event: Optional[threading.Event] = None,
) -> list[ExecutionResult]:
    """按顺序运行多个任务；单任务失败重试，仍失败则跳过并继续。

    有 cancel_event 时：每个任务开始前检查取消；已取消则剩余任务全部记为 CANCELLED。
    """
    results: list[ExecutionResult] = []
    avail = available if available is not None else set(tasker.resource.node_list)
    for i, entry in enumerate(entries):
        if cancel_event is not None and cancel_event.is_set():
            for rest in entries[i:]:
                results.append(_cancelled_result(rest))
            break

        if entry not in avail:
            results.append(
                ExecutionResult(
                    run_id=new_run_id(),
                    task_id=entry,
                    state=ExecutionState.FAILED,
                    error="missing-node",
                )
            )
            if on_progress:
                on_progress(f"[skip] 任务节点不存在：{entry}")
            continue

        result: Optional[ExecutionResult] = None
        cancelled = False
        _recover_capture(tasker)  # 截图自愈前置：战斗可能把截图链路打挂
        for attempt in range(1 + retry_per_task):
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break
            if on_progress:
                on_progress(f"[run] {entry} (第 {attempt + 1} 次)")
            if bus:
                bus.publish(
                    TaskEvent(
                        type=EventType.TASK_PROGRESS,
                        run_id="",
                        task_id=entry,
                        message=f"第 {attempt + 1} 次尝试",
                    )
                )
            result, cancelled = _run_entry(tasker, entry, new_run_id(), cancel_event, bus)
            if result.ok or cancelled:
                break
        if cancelled and (result is None or result.state is not ExecutionState.CANCELLED):
            result = _cancelled_result(entry)
        if result is not None:
            results.append(result)
        if on_progress and result is not None:
            on_progress(result.summary)
    return results
