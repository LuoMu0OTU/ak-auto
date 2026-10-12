"""任务编排：运行单个任务、顺序执行、失败重试。"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from maa.tasker import Tasker


@dataclass
class TaskResult:
    entry: str
    ok: bool
    status: str
    duration_ms: int
    nodes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        n = len(self.nodes)
        return f"{self.entry}: {'OK' if self.ok else 'FAIL'} ({self.status}, {self.duration_ms}ms, {n} nodes)"


def _status_name(detail) -> str:
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


def run_task(tasker: Tasker, entry: str) -> TaskResult:
    """运行单个任务（入口节点）并等待结束，返回结构化结果。"""
    t0 = time.perf_counter()
    job = tasker.post_task(entry)
    job.wait()
    detail = job.get()
    dt = int((time.perf_counter() - t0) * 1000)

    if detail is None:
        return TaskResult(entry, False, "no-detail", dt)

    nodes: list[str] = []
    try:
        for n in detail.nodes:
            if n.name:
                nodes.append(n.name)
    except Exception:  # noqa: BLE001
        pass

    return TaskResult(entry, detail.status.succeeded, _status_name(detail), dt, nodes)


def run_sequence(
    tasker: Tasker,
    entries: list[str],
    retry_per_task: int = 2,
    available: Optional[set[str]] = None,
    on_progress=None,
) -> list[TaskResult]:
    """按顺序运行多个任务；单任务失败重试，仍失败则跳过并继续。"""
    results: list[TaskResult] = []
    avail = available if available is not None else set(tasker.resource.node_list)
    for entry in entries:
        if entry not in avail:
            results.append(TaskResult(entry, False, "missing-node", 0, []))
            if on_progress:
                on_progress(f"[skip] 任务节点不存在：{entry}")
            continue

        result: Optional[TaskResult] = None
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
