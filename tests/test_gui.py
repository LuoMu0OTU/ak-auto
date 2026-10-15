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
    app.processEvents()


@pytest.fixture(scope="module", autouse=True)
def _qt_cleanup(qapp):
    """模块结束时清理残留控件，避免 Qt/MaaFw C++ teardown 冲突。"""
    yield
    for w in qapp.topLevelWidgets():
        w.deleteLater()
    qapp.processEvents()


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


def test_sequence_interleaves_return_home() -> None:
    from ak_auto.gui.main_window import _sequence

    assert _sequence(["StartUp", "Infrast"]) == ["StartUp", "ReturnToHome", "Infrast"]
    assert _sequence(["Infrast"]) == ["ReturnToHome", "Infrast"]


def test_task_page_preset_and_selection(qapp) -> None:
    from ak_auto.gui.main_window import PRESETS, TaskPage

    page = TaskPage()
    page.apply_preset(PRESETS["快速收菜"])
    assert page.selected_entries() == ["ReturnToHome", "Infrast"]


def test_worker_is_qthread() -> None:
    from PySide6.QtCore import QThread

    from ak_auto.gui.worker import TaskWorker

    assert issubclass(TaskWorker, QThread)


def test_settings_page_save(tmp_path, qapp) -> None:
    from ak_auto.application import ConfigurationService
    from ak_auto.gui.pages import SettingsPage

    svc = ConfigurationService(tmp_path / "c.json")
    cfg = svc.load()
    page = SettingsPage(cfg, svc)
    page.game_path.setText(r"C:\Games\Arknights.exe")
    page._save()

    loaded = svc.load()
    assert loaded.startup.game_path == r"C:\Games\Arknights.exe"
    assert (tmp_path / "c.json").exists()


def test_runlog_page_reads_reports(tmp_path, qapp, monkeypatch) -> None:
    import json

    from ak_auto.gui import pages as pages_mod

    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "run-x.json").write_text(
        json.dumps(
            {
                "started_at": "2026-10-13T00:00:00",
                "all_ok": True,
                "total_ms": 1000,
                "tasks": [{"entry": "StartUp", "ok": True, "status": "succeeded",
                           "duration_ms": 1000, "nodes": ["StartUp"], "run_id": "r", "error": ""}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pages_mod, "PROJECT_ROOT", tmp_path)
    page = pages_mod.RunLogPage()
    assert page.list.count() == 1
    assert "StartUp" in page.detail.toPlainText()


def test_wizard_constructs(qapp, tmp_path) -> None:
    from ak_auto.application import ConfigurationService
    from ak_auto.gui.wizard import FirstRunWizard

    svc = ConfigurationService(tmp_path / "c.json")
    wiz = FirstRunWizard(svc.load(), svc)
    assert len(wiz.pageIds()) == 5
    assert wiz.windowTitle() == "ak-auto 首次启动向导"
    wiz.close()


def test_home_run_state_updates(qapp) -> None:
    from ak_auto.gui.main_window import HomePage

    page = HomePage(AppConfig())
    page.begin_run(5)
    assert not page.progress.isHidden() and "准备中" in page.run_state.text()

    page.set_task_state("Infrast", "running")
    assert "Infrast — running" in page.run_state.text()

    page.set_progress(2, 5)
    assert page.progress.value() == 2

    page.finish_run("3/5 成功")
    assert "已结束" in page.run_state.text()
    assert page.progress.isHidden()


def test_worker_has_state_signals() -> None:
    from ak_auto.gui.worker import TaskWorker

    for name in ("task_state", "seq_progress", "log", "done", "failed"):
        assert hasattr(TaskWorker, name), f"缺信号 {name}"
