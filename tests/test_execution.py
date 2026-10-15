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

from fakes import BlockingTasker  # noqa: E402


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
