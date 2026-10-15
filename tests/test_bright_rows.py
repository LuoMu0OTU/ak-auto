"""bright_rows（连战次数白色数字检测）测试：合成图 + 录制截图回归（Phase 1 任务 7）。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto import device  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "selector_rows.png"


def _dark(width: int = 1280, height: int = 720) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def test_bright_rows_detects_white_bands() -> None:
    img = _dark()
    for y in (300, 420):  # 两个白色条带
        img[y - 8: y + 8, 990:1030, :] = 255
    rows = device.bright_rows(img, x0=990, x1=1030, y0=0, y1=720, threshold=200)
    found = [y for y, _peak in rows]
    # 算法以 4px 步进 + 16px 窗口扫描，命中位置在条带 ±16px 内即可
    assert any(290 <= y <= 312 for y in found), f"未检测到 300 处白色条带：{found}"
    assert any(410 <= y <= 432 for y in found), f"未检测到 420 处白色条带：{found}"


def test_bright_rows_ignores_dark() -> None:
    img = _dark()
    img[300 - 8: 300 + 8, 990:1030, :] = 107  # 灰色（不可选）
    rows = device.bright_rows(img, x0=990, x1=1030, y0=0, y1=720, threshold=200)
    assert rows == []


def test_bright_rows_on_recorded_selector() -> None:
    """录制截图回归：真机录下的次数列表应能检出至少 2 个白色数字。"""
    if not FIXTURE.exists():
        pytest.skip("缺录制夹具（tests/fixtures/selector_rows.png）")
    img = np.array(__import__("PIL.Image").Image.open(FIXTURE).convert("RGB"))
    rows = device.bright_rows(img, x0=35, x1=75, y0=0, y1=480, threshold=200)
    assert len(rows) >= 2, f"录制截图上应能检出白色数字，实际 {rows}"
