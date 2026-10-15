"""主窗口与页面框架（Phase 2）。

结构：左侧导航（首页/任务中心/运行记录/设置）+ QStackedWidget 页面。
任务中心：勾选任务目录 → 生成执行序列（ReturnToHome 间隔）→ 经 TaskWorker 走真实 Application 层执行。
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

PRESETS: dict[str, list[str]] = {
    "每日常规": ["StartUp", "AwardVisit", "Infrast", "Mall", "Recruit", "Fight", "Award", "AwardMail", "AwardSignIn"],
    "快速收菜": ["Infrast"],
    "公招与信用": ["AwardVisit", "Mall", "Recruit"],
}


def _sequence(chosen: list[str]) -> list[str]:
    """把勾选的任务变成执行序列：非 StartUp 任务前插 ReturnToHome（与 CLI daily 一致）。"""
    entries: list[str] = []
    for t in chosen:
        if t != "StartUp":
            entries.append("ReturnToHome")
        entries.append(t)
    return entries


class HomePage(QWidget):
    run_requested = Signal(list)
    stop_requested = Signal()

    def __init__(self, cfg, parent=None) -> None:
        super().__init__(parent)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("事件与日志会显示在这里 ...")

        title = QLabel("首页")
        title.setObjectName("title")
        self.status_label = QLabel(self._status_text(cfg))
        self.status_label.setObjectName("muted")

        self.start_btn = QPushButton("运行 StartUp（快速启动）")
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
        lay.addWidget(self.status_label)
        lay.addLayout(row)
        lay.addWidget(self.log_view, 1)

    @staticmethod
    def _status_text(cfg) -> str:
        from .. import device
        from ..infrastructure import AssetManager

        am = AssetManager().status()
        parts = [f"识别资源：{'就绪' if am['ready'] else '未就绪（先 fetch-assets）'}"]
        try:
            device.init_maa()
            win = device.find_game_window(cfg)
            parts.append(f"游戏窗口：{'已运行' if win else '未运行'}")
        except Exception:  # noqa: BLE001
            parts.append("游戏窗口：未知")
        return " · ".join(parts)

    def append_log(self, text: str) -> None:
        self.log_view.appendPlainText(text)

    def set_running(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)


class TaskPage(QWidget):
    run_requested = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        title = QLabel("任务中心")
        title.setObjectName("title")
        hint = QLabel("勾选要执行的任务（仅展示真实可用任务），点「开始执行」。")
        hint.setObjectName("muted")

        self.checks: dict[str, QCheckBox] = {}
        for t in all_tasks():
            cb = QCheckBox(f"{t.name}（{t.id} · {t.category} · 风险 {t.risk_level}）")
            cb.setChecked(t.id in PRESETS["每日常规"])
            self.checks[t.id] = cb

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("推荐预设："))
        for name, ids in PRESETS.items():
            btn = QPushButton(name)
            btn.clicked.connect(lambda _=False, i=ids: self.apply_preset(i))
            preset_row.addWidget(btn)
        preset_row.addStretch(1)

        self.run_btn = QPushButton("开始执行")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self._emit_run)

        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(hint)
        lay.addLayout(preset_row)
        for cb in self.checks.values():
            lay.addWidget(cb)
        lay.addWidget(self.run_btn)
        lay.addStretch(1)

    def apply_preset(self, ids: list[str]) -> None:
        for tid, cb in self.checks.items():
            cb.setChecked(tid in ids)

    def selected_entries(self) -> list[str]:
        chosen = [t.id for t in all_tasks() if self.checks[t.id].isChecked()]
        return _sequence(chosen)

    def _emit_run(self) -> None:
        entries = self.selected_entries()
        if entries:
            self.run_requested.emit(entries)


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

        self.home = HomePage(cfg)
        self.task_page = TaskPage()
        self.pages = QStackedWidget()
        self.pages.addWidget(self.home)
        self.pages.addWidget(self.task_page)
        self.pages.addWidget(RunLogPage())
        self.pages.addWidget(SettingsPage(cfg))

        self.home.run_requested.connect(self._start)
        self.home.stop_requested.connect(self._stop)
        self.task_page.run_requested.connect(self._start_and_show_log)
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

    def _start_and_show_log(self, entries: list[str]) -> None:
        self._start(entries)
        self.nav.setCurrentRow(0)  # 切回首页看日志

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
