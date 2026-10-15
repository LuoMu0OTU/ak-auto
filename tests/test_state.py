"""执行状态机与 ExecutionResult 测试（Phase 1 任务 2）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.domain import (  # noqa: E402
    ExecutionResult,
    ExecutionState,
    IllegalTransition,
    StateMachine,
    new_run_id,
)


def test_happy_path_transitions() -> None:
    m = StateMachine()
    assert m.state is ExecutionState.PENDING
    m.transition(ExecutionState.PREPARING)
    m.transition(ExecutionState.RUNNING)
    m.transition(ExecutionState.SUCCEEDED)
    assert m.terminal


def test_cancelled_from_any_nonterminal() -> None:
    for start, path in [
        (ExecutionState.PENDING, [ExecutionState.CANCELLED]),
        (ExecutionState.PREPARING, [ExecutionState.CANCELLED]),
        (ExecutionState.RUNNING, [ExecutionState.CANCELLED]),
    ]:
        m = StateMachine(start)
        for s in path:
            m.transition(s)
        assert m.terminal and m.state is ExecutionState.CANCELLED


def test_stopping_then_terminal() -> None:
    m = StateMachine(ExecutionState.RUNNING)
    m.transition(ExecutionState.STOPPING)
    m.transition(ExecutionState.SUCCEEDED)
    assert m.terminal
    m2 = StateMachine(ExecutionState.RUNNING)
    m2.transition(ExecutionState.STOPPING)
    m2.transition(ExecutionState.CANCELLED)
    assert m2.terminal


def test_illegal_transitions_raise() -> None:
    with pytest.raises(IllegalTransition):
        StateMachine().transition(ExecutionState.SUCCEEDED)  # PENDING 不能直接成功
    with pytest.raises(IllegalTransition):
        StateMachine(ExecutionState.SUCCEEDED).transition(ExecutionState.RUNNING)  # 终态无出边
    with pytest.raises(IllegalTransition):
        StateMachine(ExecutionState.RUNNING).transition(ExecutionState.PENDING)  # 不能回退


def test_result_compat_fields() -> None:
    r = ExecutionResult(
        run_id="run-x",
        task_id="Recruit",
        state=ExecutionState.SUCCEEDED,
        duration_ms=123,
        nodes=["Recruit", "Recruit@Done"],
    )
    assert r.entry == "Recruit"  # TaskResult 兼容
    assert r.ok is True
    assert r.status == "succeeded"
    assert "OK" in r.summary and "123ms" in r.summary


def test_result_failed_and_error() -> None:
    r = ExecutionResult(run_id="r", task_id="X", state=ExecutionState.FAILED, error="missing-node")
    assert r.ok is False
    assert "missing-node" in r.summary  # 合成错误优先展示


def test_to_dict_and_new_run_id() -> None:
    r = ExecutionResult(run_id="run-a", task_id="Fight", state=ExecutionState.FAILED, error="sanity-short")
    d = r.to_dict()
    assert d["run_id"] == "run-a" and d["state"] == "failed" and d["error"] == "sanity-short"
    assert new_run_id().startswith("run-")


def test_taskresult_alias() -> None:
    from ak_auto.scheduler import TaskResult

    assert TaskResult is ExecutionResult  # 旧 import 兼容
