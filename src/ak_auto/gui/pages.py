"""设置页与运行记录页（Phase 2 第 3 轮）。"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..application import ConfigurationService
from ..config import PROJECT_ROOT, AppConfig


class SettingsPage(QWidget):
    """关键设置项编辑：经 ConfigurationService 原子保存；默认关闭付费资源（风险提示）。"""

    def __init__(self, cfg: AppConfig, svc: ConfigurationService, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.svc = svc

        title = QLabel("设置")
        title.setObjectName("title")

        self.game_path = QLineEdit(cfg.startup.game_path)
        self.game_path.setPlaceholderText(r"例如 E:\Arknights\Arknights.exe")
        self.stage = QLineEdit(cfg.fight.stage)
        self.times = QSpinBox()
        self.times.setRange(0, 999)
        self.times.setValue(cfg.fight.times)
        self.times.setToolTip("0 = 直到理智耗尽")
        self.medicine = QSpinBox()
        self.medicine.setRange(0, 999)
        self.medicine.setValue(cfg.fight.medicine)
        self.stone = QSpinBox()
        self.stone.setRange(0, 999)
        self.stone.setValue(cfg.fight.stone)
        self.retry = QSpinBox()
        self.retry.setRange(0, 10)
        self.retry.setValue(cfg.runtime.retry_per_task)

        form = QFormLayout()
        form.addRow("游戏路径", self.game_path)
        form.addRow("刷图关卡", self.stage)
        form.addRow("刷图次数（0=直到理智耗尽）", self.times)
        form.addRow("用药数量", self.medicine)
        form.addRow("碎源石数量", self.stone)
        form.addRow("任务失败重试次数", self.retry)
        form.setLabelAlignment(form.labelAlignment())

        risk = QLabel("⚠ 用药 / 碎源石消耗付费资源：请确认后再设置（默认关闭）。")
        risk.setObjectName("muted")

        self.status = QLabel("")
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._save)
        self.reset_btn = QPushButton("恢复默认")
        self.reset_btn.clicked.connect(self._reset)

        row = QHBoxLayout()
        row.addWidget(self.save_btn)
        row.addWidget(self.reset_btn)
        row.addStretch(1)

        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addLayout(form)
        lay.addWidget(risk)
        lay.addLayout(row)
        lay.addWidget(self.status)
        lay.addStretch(1)

    def _save(self) -> None:
        self.cfg.startup.game_path = self.game_path.text().strip()
        self.cfg.fight.stage = self.stage.text().strip().upper() or "CE-6"
        self.cfg.fight.times = self.times.value()
        self.cfg.fight.medicine = self.medicine.value()
        self.cfg.fight.stone = self.stone.value()
        self.cfg.runtime.retry_per_task = self.retry.value()
        self.svc.save(self.cfg)
        self.status.setText("已保存 ✓（下次运行生效）")

    def _reset(self) -> None:
        d = AppConfig()
        self.game_path.setText(d.startup.game_path)
        self.stage.setText(d.fight.stage)
        self.times.setValue(d.fight.times)
        self.medicine.setValue(d.fight.medicine)
        self.stone.setValue(d.fight.stone)
        self.retry.setValue(d.runtime.retry_per_task)
        self.status.setText("已恢复默认（点「保存」生效）")


class RunLogPage(QWidget):
    """历史运行记录：读 logs/run-*.json（新→旧）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        title = QLabel("运行记录")
        title.setObjectName("title")

        self.list = QListWidget()
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.list.currentItemChanged.connect(self._show_current)

        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(self.list, 2)
        lay.addWidget(self.detail, 3)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        self.detail.clear()
        files = sorted(
            (PROJECT_ROOT / "logs").glob("run-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:30]
        if not files:
            self.detail.setPlainText("还没有运行记录。跑一次 daily 或 GUI 任务后会出现在这里。")
            return
        for f in files:
            self.list.addItem(f.name)
        self.list.setCurrentRow(0)

    def _show_current(self, item) -> None:
        if item is None:
            return
        path = PROJECT_ROOT / "logs" / item.text()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.detail.setPlainText("记录文件无法读取。")
            return
        lines = [f"运行报告（{data.get('started_at', '?')}）", "-" * 56]
        for t in data.get("tasks", []):
            mark = "OK " if t.get("ok") else "FAIL"
            lines.append(f"{mark}  {t.get('entry')}  ({t.get('status')}, {t.get('duration_ms')}ms, "
                         f"{len(t.get('nodes', []))} nodes)" + (f"  [{t.get('error')}]" if t.get("error") else ""))
        lines += ["-" * 56, f"共 {len(data.get('tasks', []))} 项，总耗时 {data.get('total_ms', 0) / 1000:.1f}s"]
        self.detail.setPlainText("\n".join(lines))
