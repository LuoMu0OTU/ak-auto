"""信用购买优先级策略测试（Phase 5）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.tasks.mall import pick_item  # noqa: E402


def test_priority_order() -> None:
    items = ["招聘许可", "寻访凭证", "家具零件", "龙门币"]
    assert pick_item(items, ["招聘许可", "寻访凭证"], [], []) == "招聘许可"


def test_skip_bought_then_next() -> None:
    items = ["招聘许可", "寻访凭证"]
    assert pick_item(items, ["招聘许可", "寻访凭证"], [], ["招聘许可"]) == "寻访凭证"


def test_blacklist_skipped() -> None:
    items = ["家具零件", "招聘许可"]
    assert pick_item(items, ["家具零件", "招聘许可"], ["家具零件"], []) == "招聘许可"


def test_ocr_fragment_matches() -> None:
    # OCR 常见截断：把「招聘许可」识别成「招聘许」
    assert pick_item(["招聘许"], ["招聘许可"], [], []) == "招聘许可"


def test_none_when_all_bought_or_missing() -> None:
    assert pick_item(["寻访凭证"], ["招聘许可", "寻访凭证"], [], ["招聘许可", "寻访凭证"]) is None
    assert pick_item(["龙门币"], ["招聘许可"], [], []) is None
