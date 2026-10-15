"""事件总线与调度器事件测试（Phase 1 任务 3；FakeTasker 是任务 7 的种子）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.domain import EventBus, EventType, ExecutionState, TaskEvent  # noqa: E402
from ak_auto.scheduler import run_task, run_sequence  # noqa: E402


# ---- 假 Tasker（不依赖真实 MaaFw/游戏）----
class _FakeNode:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeStatus:
    def __init__(self, ok: bool) -> None:
        self.succeeded = ok
        self.failed = not ok
        self.running = False
        self.pending = False


class _FakeDetail:
    def __init__(self, ok: bool, nodes: list[str]) -> None:
        self.status = _FakeStatus(ok)
        self.nodes = [_FakeNode(n) for n in nodes]


class _FakeJob:
    def __init__(self, ok: bool, nodes: list[str]) -> None:
        self._detail = _FakeDetail(ok, nodes)

    def wait(self) -> None:
        return None

    def get(self):
        return self._detail


class _FakeResource:
    node_list = ["Fake", "Fake@Done", "Recruit"]


class FakeTasker:
    resource = _FakeResource()

    def __init__(self, ok: bool = True, nodes: list[str] | None = None) -> None:
        self.ok = ok
        self.nodes = nodes or ["Fake@Done"]
        self.posted: list[str] = []

    def post_task(self, entry: str) -> _FakeJob:
        self.posted.append(entry)
        return _FakeJob(self.ok, self.nodes)


# ---- 事件总线单元测试 ----
def test_subscribe_specific_type() -> None:
    bus = EventBus()
    got: list[TaskEvent] = []
    bus.subscribe(EventType.TASK_FAILED, got.append)
    bus.publish(TaskEvent(type=EventType.TASK_STARTED, run_id="r", task_id="X"))
    bus.publish(TaskEvent(type=EventType.TASK_FAILED, run_id="r", task_id="X", message="boom"))
    assert [e.type for e in got] == [EventType.TASK_FAILED]


def test_subscribe_all_and_payload() -> None:
    bus = EventBus()
    got: list[TaskEvent] = []
    bus.subscribe_all(got.append)
    bus.publish(TaskEvent(type=EventType.TASK_STARTED, run_id="r1", task_id="Recruit",
                          state=ExecutionState.RUNNING, diagnostic={"a": 1}))
    assert len(got) == 1
    e = got[0]
    assert e.run_id == "r1" and e.task_id == "Recruit" and e.timestamp > 0
    assert e.diagnostic == {"a": 1}


def test_handler_exception_isolated() -> None:
    bus = EventBus()
    good: list[TaskEvent] = []

    def bad(_: TaskEvent) -> None:
        raise RuntimeError("订阅者崩了")

    bus.subscribe_all(bad)
    bus.subscribe_all(good.append)
    bus.publish(TaskEvent(type=EventType.TASK_STARTED, run_id="r", task_id="X"))
    assert len(good) == 1  # 一个订阅者抛异常不影响其他


# ---- 调度器事件集成（FakeTasker）----
def test_run_task_emits_started_and_completed() -> None:
    bus = EventBus()
    got: list[TaskEvent] = []
    bus.subscribe_all(got.append)
    result = run_task(FakeTasker(ok=True), "Fake", bus=bus)
    assert result.ok and result.entry == "Fake"
    assert [e.type for e in got] == [EventType.TASK_STARTED, EventType.TASK_COMPLETED]
    assert got[0].run_id == got[1].run_id == result.run_id


def test_run_task_emits_failed() -> None:
    bus = EventBus()
    got: list[TaskEvent] = []
    bus.subscribe(EventType.TASK_FAILED, got.append)
    result = run_task(FakeTasker(ok=False), "Fake", bus=bus)
    assert not result.ok and result.error == "failed"
    assert [e.type for e in got] == [EventType.TASK_FAILED]
    assert got[0].message == "failed"


def test_run_sequence_emits_progress_and_results() -> None:
    bus = EventBus()
    got: list[TaskEvent] = []
    bus.subscribe_all(got.append)
    results = run_sequence(FakeTasker(ok=True), ["Fake", "Recruit"], retry_per_task=0, bus=bus)
    assert [r.entry for r in results] == ["Fake", "Recruit"]
    assert [e.type for e in got].count(EventType.TASK_PROGRESS) == 2  # 每任务 1 次尝试
    assert [e.type for e in got].count(EventType.TASK_COMPLETED) == 2


def test_run_sequence_missing_node() -> None:
    results = run_sequence(FakeTasker(ok=True), ["不存在任务"], retry_per_task=0)
    assert len(results) == 1 and not results[0].ok and results[0].error == "missing-node"
