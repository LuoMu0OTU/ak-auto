"""公招标签选择策略测试（Phase 5：tag_priority 消费）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.data.recruitment import best_selection, best_tag_combination  # noqa: E402


def test_tag_priority_hit_selects_priority_tag() -> None:
    tags = ["高级资深干员", "近卫", "费用回复", "快速复活", "输出"]
    combo = best_selection(tags, ["高级资深干员", "资深干员"])
    assert combo == ["高级资深干员"]  # 高资单独选，不被保底组合干扰


def test_tag_priority_order_matters() -> None:
    tags = ["资深干员", "高级资深干员", "输出"]
    combo = best_selection(tags, ["高级资深干员", "资深干员"])
    assert combo == ["高级资深干员"]  # 按优先级顺序取更高者


def test_tag_priority_miss_falls_back_to_guarantee() -> None:
    tags = ["近卫", "输出", "费用回复"]
    with_prio = best_selection(tags, ["高级资深干员"])
    without = best_selection(tags)
    assert with_prio == without  # 未命中优先标签时行为不变


def test_guarantee_combo_still_works() -> None:
    # 经典保底组合：快速复活+输出 → 4★（砾/红 等）
    combo, ops = best_tag_combination(["快速复活", "输出"], 4)
    assert combo and ops and all(o["rarity"] >= 4 for o in ops)


def test_empty_priority_is_noop() -> None:
    tags = ["近卫", "输出"]
    assert best_selection(tags, []) == best_selection(tags)
    assert best_selection(tags, None) == best_selection(tags)
