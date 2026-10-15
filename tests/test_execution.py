"""执行控制器与协作式取消测试（Phase 1 任务 4）。"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.application import ExecutionController  # noqa: E402
from ak_auto.domain import EventBus, EventType, ExecutionState  # noqa: E402
from ak_auto.scheduler import run_sequence  # noqa: E402


class _Node:
    def __init__(self, name: str) -> None:
        self.name = name


class _Status:
    def __init__(self, ok: bool) -> None:
        self.succeeded = ok
        self.failed = not ok
        self.running = False
        self.pending = False


class _Detail:
    def __init__(self, ok: bool, nodes: list[str]) -> None:
        self.status = _Status(ok)
        self.nodes = [_Node(n) for n in nodes]


class _InstantJob:
    def wait(self) -> None:
        return None

    def get(self):
        return None


class BlockingJob:
    """任务一直挂到 release 被置位（模拟运行中的 MaaFw 任务）。"""

    def __init__(self, release: threading.Event, ok: bool = True, nodes: list[str] | None = None) -> None:
        self._release = release
        self._ok = ok
        self._nodes = nodes or ["Fake@Done"]

    @property
    def done(self) -> bool:
        return self._release.is_set()

    def wait(self) -> None:
        self._release.wait()

    def get(self):
        return _Detail(self._ok, self._nodes)


class BlockingTasker:
    """可控假 Tasker：post_stop 模拟 MaaFw 停止并释放当前任务。"""

    class resource:  # noqa: D106 —— run_sequence 需要 node_list
        node_list = ["Fake", "Fake@Done", "Recruit", "Fight"]

    def __init__(self) -> None:
        self.release = threading.Event()
        self.stop_called = threading.Event()
        self.posted: list[str] = []

    def post_task(self, entry: str) -> BlockingJob:
        self.posted.append(entry)
        return BlockingJob(self.release)

    def post_stop(self) -> _InstantJob:
        self.stop_called.set()
        self.release.set()  # 模拟 MaaFw：stop 之后 job 结束
        return _InstantJob()


class RaisingTasker(BlockingTasker):
    def post_task(self, entry: str):
        raise RuntimeError("boom")


def _wait_state(controller: ExecutionController, timeout: float = 5.0) -> ExecutionState:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not controller.running:
            return controller.state
        time.sleep(0.01)
    raise TimeoutError("控制器超时未结束")


def test_normal_completion() -> None:
    t = BlockingTasker()
    c = ExecutionController(t)
    c.start(["Fake"], retry_per_task=0)
    time.sleep(0.1)  # 让工作线程挂到任务上
    t.release.set()
    results = c.wait(timeout=5)
    assert c.state is ExecutionState.SUCCEEDED
    assert len(results) == 1 and results[0].ok


def test_cancel_stops_running_task() -> None:
    t = BlockingTasker()
    c = ExecutionController(t)
    c.start(["Fake"], retry_per_task=0)
    time.sleep(0.1)
    c.cancel()
    results = c.wait(timeout=5)
    assert c.state is ExecutionState.CANCELLED
    assert results[0].state is ExecutionState.CANCELLED
    assert t.stop_called.is_set()  # post_stop 确实被调用


def test_cancel_emits_event() -> None:
    bus = EventBus()
    got: list = []
    bus.subscribe(EventType.TASK_CANCELLED, got.append)
    t = BlockingTasker()
    c = ExecutionController(t, bus=bus)
    c.start(["Fake"], retry_per_task=0)
    time.sleep(0.1)
    c.cancel()
    c.wait(timeout=5)
    assert got and got[0].task_id == "Fake"


def test_sequence_remaining_cancelled() -> None:
    ev = threading.Event()
    ev.set()  # 提前取消
    results = run_sequence(BlockingTasker(), ["Fake", "Recruit"], retry_per_task=0, cancel_event=ev)
    assert len(results) == 2
    assert all(r.state is ExecutionState.CANCELLED for r in results)
    assert results[0].error == "cancelled"


def test_double_start_raises() -> None:
    t = BlockingTasker()
    c = ExecutionController(t)
    c.start(["Fake"], retry_per_task=0)
    with pytest.raises(RuntimeError):
        c.start(["Recruit"])
    t.release.set()
    c.wait(timeout=5)


def test_worker_exception_has_terminal_state() -> None:
    c = ExecutionController(RaisingTasker())
    c.start(["Fake"], retry_per_task=0)
    results = c.wait(timeout=5)
    assert c.state is ExecutionState.FAILED  # 异常也必须落到终态
    assert results and "controller-error" in results[0].error
