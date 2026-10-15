"""任务编排：运行单个任务、顺序执行、失败重试。

Phase 1 任务 2 起：结果统一为 domain.ExecutionResult（带 run_id / 状态机 / 错误码）；
`TaskResult` 保留为别名，旧调用方（report 等）零改动。
"""
from __future__ import annotations

import time
from typing import Optional

from maa.tasker import Tasker

from .domain import ExecutionResult, ExecutionState, StateMachine, new_run_id

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


def run_task(tasker: Tasker, entry: str) -> ExecutionResult:
    """运行单个任务（入口节点）并等待结束，返回结构化结果。

    生命周期经状态机跟踪：PENDING → PREPARING → RUNNING → 终态
    （当前为阻塞执行，中间态不可观测；观测与取消见任务 3/4）。
    """
    run_id = new_run_id()
    t0 = time.perf_counter()
    machine = StateMachine(ExecutionState.PENDING)
    machine.transition(ExecutionState.PREPARING)
    machine.transition(ExecutionState.RUNNING)

    job = tasker.post_task(entry)
    job.wait()
    detail = job.get()
    dt = int((time.perf_counter() - t0) * 1000)
    finished_at = time.time()

    if detail is None:
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

    return ExecutionResult(
        run_id=run_id,
        task_id=entry,
        state=state,
        duration_ms=dt,
        nodes=nodes,
        error=error,
        started_at=t0,
        finished_at=finished_at,
    )


def run_sequence(
    tasker: Tasker,
    entries: list[str],
    retry_per_task: int = 2,
    available: Optional[set[str]] = None,
    on_progress=None,
) -> list[ExecutionResult]:
    """按顺序运行多个任务；单任务失败重试，仍失败则跳过并继续。"""
    results: list[ExecutionResult] = []
    avail = available if available is not None else set(tasker.resource.node_list)
    for entry in entries:
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
        for attempt in range(1 + retry_per_task):
            if on_progress:
                on_progress(f"[run] {entry} (第 {attempt + 1} 次)")
            result = run_task(tasker, entry)
            if result.ok:
                break
        if result is not None:
            results.append(result)
        if on_progress and result is not None:
            on_progress(result.summary)
    return results
