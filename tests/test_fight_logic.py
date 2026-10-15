"""Fight 连战决策纯函数测试（Phase 5）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.config import AppConfig  # noqa: E402
from ak_auto.tasks.fight import decide_loops  # noqa: E402


def test_max_affordable() -> None:
    n, reason = decide_loops(120, 36, AppConfig())  # times=0 → 最大可连战
    assert (n, reason) == (3, "")


def test_times_cap() -> None:
    cfg = AppConfig()
    cfg.fight.times = 2
    assert decide_loops(120, 36, cfg)[0] == 2


def test_times_one() -> None:
    cfg = AppConfig()
    cfg.fight.times = 1
    assert decide_loops(240, 36, cfg)[0] == 1


def test_min_sanity_blocks() -> None:
    cfg = AppConfig()
    cfg.fight.min_sanity = 100
    n, reason = decide_loops(60, 36, cfg)
    assert n is None and reason == "sanity-below-min"


def test_insufficient_sanity() -> None:
    n, reason = decide_loops(20, 36, AppConfig())
    assert n is None and reason == "sanity-insufficient"


def test_unknown_cost() -> None:
    n, reason = decide_loops(120, None, AppConfig())
    assert n is None and reason == "cost-unknown"
