"""GUI 启动入口（Phase 2）。"""
from __future__ import annotations

import sys


def run_gui() -> int:
    """启动图形界面并进入事件循环；返回 Qt 退出码。"""
    from PySide6.QtWidgets import QApplication

    from ..application import ConfigurationService
    from .main_window import MainWindow
    from .theme import apply_theme

    svc = ConfigurationService()
    cfg = svc.load()

    app = QApplication(sys.argv)
    app.setApplicationName("ak-auto")
    app.setOrganizationName("ak-auto")
    apply_theme(app)

    win = MainWindow(cfg)
    if svc.warning:
        win._log(f"[warn] {svc.warning}")  # noqa: SLF001 —— 启动期提示
    win.show()
    return app.exec()
