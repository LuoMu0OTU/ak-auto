"""run_sequence 重试逻辑测试（Phase 3 配置生效链路：retry_per_task → 重试次数）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.scheduler import run_sequence  # noqa: E402
from fakes import FakeJob, FakeTasker  # noqa: E402


class FlakyTasker(FakeTasker):
    """第一次失败、第二次成功的任务器。"""

    def __init__(self) -> None:
        super().__init__(ok=True)
        self.fail_first = True

    def post_task(self, entry: str) -> FakeJob:
        self.posted.append(entry)
        if self.fail_first:
            self.fail_first = False
            return FakeJob(ok=False)
        return FakeJob(ok=True)


def test_retry_per_task_recovers() -> None:
    t = FlakyTasker()
    results = run_sequence(t, ["Fake"], retry_per_task=2)
    assert len(results) == 1 and results[0].ok
    assert len(t.posted) == 2  # 失败一次后重试成功


def test_retry_per_task_exhausted() -> None:
    t = FakeTasker(ok=False)
    results = run_sequence(t, ["Fake"], retry_per_task=1)
    assert results[0].state.value == "failed"
    assert len(t.posted) == 2  # 首次 + 1 次重试


def test_retry_zero_is_single_attempt() -> None:
    t = FakeTasker(ok=False)
    results = run_sequence(t, ["Fake"], retry_per_task=0)
    assert len(t.posted) == 1 and not results[0].ok
