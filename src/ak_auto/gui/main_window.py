"""主窗口与页面框架（Phase 2 第 1 轮：深色主题原型）。

结构：左侧导航（首页/任务中心/运行记录/设置）+ QStackedWidget 页面。
首页的「运行 StartUp」按钮经 TaskWorker 走真实 Application 层执行。
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..domain import all_tasks
from .worker import TaskWorker

NAV_ITEMS = ["首页", "任务中心", "运行记录", "设置"]


class HomePage(QWidget):
    run_requested = Signal(list)
    stop_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("事件与日志会显示在这里 ...")

        title = QLabel("首页")
        title.setObjectName("title")
        hint = QLabel("连接状态 / 当前任务 / 进度 / 今日任务 / 最近结果（占位，后续轮次接入）")
        hint.setObjectName("muted")

        self.start_btn = QPushButton("运行 StartUp")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(lambda: self.run_requested.emit(["StartUp"]))
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_requested.emit)

        row = QHBoxLayout()
        row.addWidget(self.start_btn)
        row.addWidget(self.stop_btn)
        row.addStretch(1)

        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(hint)
        lay.addLayout(row)
        lay.addWidget(self.log_view, 1)

    def append_log(self, text: str) -> None:
        self.log_view.appendPlainText(text)

    def set_running(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)


class TaskPage(QWidget):
    """任务中心：列出任务目录（勾选/预设待后续轮次）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        title = QLabel("任务中心")
        title.setObjectName("title")
        hint = QLabel("仅展示真实可用的任务（勾选与预设下一轮接入）")
        hint.setObjectName("muted")

        self.checks: list[QCheckBox] = []
        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(hint)
        for t in all_tasks():
            cb = QCheckBox(f"{t.name}（{t.id} · {t.category} · 风险 {t.risk_level}）")
            cb.setChecked(t.id in ("StartUp", "AwardVisit", "Infrast", "Mall", "Recruit", "Award"))
            self.checks.append(cb)
            lay.addWidget(cb)
        lay.addStretch(1)


class RunLogPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        title = QLabel("运行记录")
        title.setObjectName("title")
        hint = QLabel("历史运行记录（后续轮次接入 logs/ 读取）")
        hint.setObjectName("muted")
        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(hint)
        lay.addStretch(1)


class SettingsPage(QWidget):
    def __init__(self, cfg, parent=None) -> None:
        super().__init__(parent)
        title = QLabel("设置")
        title.setObjectName("title")
        info = QLabel(
            f"配置文件：config/config.json（schema_version={cfg.schema_version}）\n"
            f"游戏路径：{cfg.startup.game_path}\n\n"
            "设置编辑界面后续轮次接入（ConfigurationService 已就绪）。"
        )
        info.setObjectName("muted")
        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(info)
        lay.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self, cfg) -> None:
        super().__init__()
        self.cfg = cfg
        self.worker: TaskWorker | None = None
        self.setWindowTitle("ak-auto — 明日方舟本地自动化助手")
        self.resize(1024, 680)

        self.nav = QListWidget()
        self.nav.addItems(NAV_ITEMS)
        self.nav.setFixedWidth(168)

        self.home = HomePage()
        self.pages = QStackedWidget()
        self.pages.addWidget(self.home)
        self.pages.addWidget(TaskPage())
        self.pages.addWidget(RunLogPage())
        self.pages.addWidget(SettingsPage(cfg))

        self.home.run_requested.connect(self._start)
        self.home.stop_requested.connect(self._stop)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)

        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.addWidget(self.nav)
        lay.addWidget(self.pages, 1)
        self.setCentralWidget(central)

        self.statusBar().showMessage("就绪")

    # ---- 任务执行（经 TaskWorker / Application 层）----
    def _start(self, entries: list[str]) -> None:
        if self.worker is not None and self.worker.isRunning():
            self._log("[gui] 已有任务在运行，先停止再开始。")
            return
        self.worker = TaskWorker(self.cfg, entries, parent=self)
        self.worker.log.connect(self._log)
        self.worker.done.connect(self._on_done)
        self.worker.failed.connect(lambda msg: self._log(f"[gui] 失败：{msg}"))
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
        self.home.set_running(True)
        self.statusBar().showMessage("运行中 ...")

    def _stop(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()

    def _on_done(self, results) -> None:
        for r in results:
            self._log(r.summary)

    def _on_finished(self) -> None:
        self.home.set_running(False)
        self.statusBar().showMessage("就绪")

    def _log(self, text: str) -> None:
        self.home.append_log(text)

    def closeEvent(self, event) -> None:  # noqa: N802 —— Qt 命名
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
        super().closeEvent(event)
