"""GUI 冒烟测试（Phase 2：offscreen 平台，不弹窗、不连游戏）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.config import AppConfig  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_constructs(qapp) -> None:
    from ak_auto.gui.main_window import NAV_ITEMS, MainWindow

    win = MainWindow(AppConfig())
    assert win.windowTitle() == "ak-auto — 明日方舟本地自动化助手"
    assert win.nav.count() == len(NAV_ITEMS) == 4
    assert win.pages.count() == 4
    assert win.home.start_btn.isEnabled() is True
    assert win.home.stop_btn.isEnabled() is False  # 未运行时停止按钮禁用
    win.close()


def test_theme_applies(qapp) -> None:
    from ak_auto.gui.theme import TOKENS, apply_theme

    apply_theme(qapp)
    assert qapp.styleSheet()
    assert TOKENS["primary"] and TOKENS["bg"]


def test_task_page_lists_catalog(qapp) -> None:
    from ak_auto.gui.main_window import TaskPage

    page = TaskPage()
    assert len(page.checks) == 10  # 任务目录全量


def test_worker_is_qthread() -> None:
    from PySide6.QtCore import QThread

    from ak_auto.gui.worker import TaskWorker

    assert issubclass(TaskWorker, QThread)
