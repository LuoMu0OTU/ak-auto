"""设置页 / 高级设置页 / 运行记录页（Phase 2/4）。"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
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


class _FnThread(QThread):
    """把任意函数放到后台线程跑，结果经信号回 UI。"""

    done = Signal(object)

    def __init__(self, fn, parent=None) -> None:
        super().__init__(parent)
        self.fn = fn

    def run(self) -> None:  # noqa: D102
        self.done.emit(self.fn())


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
        self.wizard_btn = QPushButton("重新运行首次向导")
        self.wizard_btn.clicked.connect(self._wizard)

        row = QHBoxLayout()
        row.addWidget(self.save_btn)
        row.addWidget(self.reset_btn)
        row.addStretch(1)

        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addLayout(form)
        lay.addWidget(risk)
        lay.addLayout(row)
        lay.addWidget(self.wizard_btn)
        lay.addWidget(self.status)
        lay.addStretch(1)

    def _wizard(self) -> None:
        from .wizard import FirstRunWizard

        FirstRunWizard(self.cfg, self.svc).exec()

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
    """历史运行记录：读 logs/run-*.json（新→旧）+ 顶部聚合统计。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        title = QLabel("运行记录")
        title.setObjectName("title")

        self.stats_label = QLabel("")
        self.stats_label.setObjectName("muted")

        self.list = QListWidget()
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.list.currentItemChanged.connect(self._show_current)

        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(self.stats_label)
        lay.addWidget(self.list, 2)
        lay.addWidget(self.detail, 3)
        self.refresh()

    def refresh(self) -> None:
        from ..application.stats import run_stats

        st = run_stats()
        if st["runs"]:
            parts = [
                f"最近 {st['runs']} 次运行",
                f"成功率 {int(st['all_ok_rate'] * 100)}%",
                f"累计耗时 {st['total_ms'] / 1000:.0f}s",
            ]
            if st["tasks"]:
                worst = max(st["tasks"].items(), key=lambda kv: kv[1]["runs"] - kv[1]["ok"])
                parts.append(f"最常失败：{worst[0]}（{worst[1]['ok']}/{worst[1]['runs']} 成功）")
            self.stats_label.setText(" · ".join(parts))
        else:
            self.stats_label.setText("还没有运行记录")

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


class AdvancedPage(QWidget):
    """高级设置（Phase 4）：任务排序 + 刷图/公招高级参数 + 运行参数。

    范围验证（SpinBox 边界）、推荐值、恢复默认、风险与「计划中」标注；
    全部经 ConfigurationService 原子保存，不绕过安全策略。
    """

    def __init__(self, cfg: AppConfig, svc: ConfigurationService, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.svc = svc

        title = QLabel("高级设置")
        title.setObjectName("title")
        hint = QLabel("这些参数影响实际执行；不确定的项保持默认即可。带「计划中」标注的参数已提供配置，"
                      "将在后续版本生效。")
        hint.setObjectName("muted")

        # ---- 任务排序 ----
        order_label = QLabel("任务顺序（每日常规按此顺序执行）")
        self.order_list = QListWidget()
        for t in cfg.runtime.task_order:
            self.order_list.addItem(t)
        up_btn = QPushButton("上移")
        up_btn.clicked.connect(lambda: self._move(-1))
        down_btn = QPushButton("下移")
        down_btn.clicked.connect(lambda: self._move(1))
        order_btns = QVBoxLayout()
        order_btns.addWidget(up_btn)
        order_btns.addWidget(down_btn)
        order_btns.addStretch(1)
        order_row = QHBoxLayout()
        order_row.addWidget(self.order_list, 1)
        order_row.addLayout(order_btns)

        # ---- 刷图高级 ----
        self.min_sanity = QSpinBox()
        self.min_sanity.setRange(0, 999)
        self.min_sanity.setValue(cfg.fight.min_sanity)
        self.min_sanity.setToolTip("理智低于该值时停止刷图；0 = 不限")
        self.series = QCheckBox("连续作战")
        self.series.setChecked(cfg.fight.series)

        fight_form = QFormLayout()
        fight_form.addRow("理智下限（0=不限）", self.min_sanity)
        fight_form.addRow("", self.series)
        fight_form.addRow(QLabel("「理智下限」计划中：战斗任务将在后续版本消费该配置。"), QLabel(""))

        # ---- 公招高级 ----
        self.tag_priority = QLineEdit(", ".join(cfg.recruit.tag_priority))
        self.tag_priority.setPlaceholderText("如：资深干员, 高级资深干员")
        self.max_times = QSpinBox()
        self.max_times.setRange(0, 10)
        self.max_times.setValue(cfg.recruit.max_times)
        self.time_hours = QSpinBox()
        self.time_hours.setRange(1, 9)
        self.time_hours.setValue(cfg.recruit.time_hours)
        self.ensure_4star = QCheckBox("保底四星（3 次无四星标签时改选保底组合）")
        self.ensure_4star.setChecked(cfg.recruit.ensure_4star)
        self.expedite = QCheckBox("使用加急许可（消耗资源）")
        self.expedite.setChecked(cfg.recruit.expedite)

        recruit_form = QFormLayout()
        recruit_form.addRow("标签优先级", self.tag_priority)
        recruit_form.addRow("每日次数", self.max_times)
        recruit_form.addRow("招募时长（小时）", self.time_hours)
        recruit_form.addRow("", self.ensure_4star)
        recruit_form.addRow("", self.expedite)
        recruit_form.addRow(QLabel("「标签优先级」计划中：公招任务将在后续版本消费该配置。"), QLabel(""))

        # ---- 运行参数 ----
        self.retry = QSpinBox()
        self.retry.setRange(0, 10)
        self.retry.setValue(cfg.runtime.retry_per_task)
        self.shot_on_error = QCheckBox("任务失败时保存截图（logs/debug）")
        self.shot_on_error.setChecked(cfg.runtime.screenshot_on_error)

        runtime_form = QFormLayout()
        runtime_form.addRow("失败重试次数", self.retry)
        runtime_form.addRow("", self.shot_on_error)

        # ---- 保存 ----
        self.status = QLabel("")
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._save)
        self.default_btn = QPushButton("恢复默认")
        self.default_btn.clicked.connect(self._reset)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.default_btn)
        btn_row.addStretch(1)

        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(hint)
        lay.addWidget(order_label)
        lay.addLayout(order_row)
        lay.addWidget(QLabel("刷图高级"))
        lay.addLayout(fight_form)
        lay.addWidget(QLabel("公招高级"))
        lay.addLayout(recruit_form)
        lay.addWidget(QLabel("运行参数"))
        lay.addLayout(runtime_form)
        lay.addLayout(btn_row)
        lay.addWidget(self.status)
        lay.addStretch(1)

    def _move(self, delta: int) -> None:
        row = self.order_list.currentRow()
        target = row + delta
        if row < 0 or not (0 <= target < self.order_list.count()):
            return
        item = self.order_list.takeItem(row)
        self.order_list.insertItem(target, item)
        self.order_list.setCurrentRow(target)

    def _order(self) -> list[str]:
        return [self.order_list.item(i).text() for i in range(self.order_list.count())]

    def _save(self) -> None:
        self.cfg.runtime.task_order = self._order()
        self.cfg.fight.min_sanity = self.min_sanity.value()
        self.cfg.fight.series = self.series.isChecked()
        self.cfg.recruit.tag_priority = [x.strip() for x in self.tag_priority.text().split(",") if x.strip()]
        self.cfg.recruit.max_times = self.max_times.value()
        self.cfg.recruit.time_hours = self.time_hours.value()
        self.cfg.recruit.ensure_4star = self.ensure_4star.isChecked()
        self.cfg.recruit.expedite = self.expedite.isChecked()
        self.cfg.runtime.retry_per_task = self.retry.value()
        self.cfg.runtime.screenshot_on_error = self.shot_on_error.isChecked()
        self.svc.save(self.cfg)
        self.status.setText("已保存 ✓（任务中心与下次运行生效）")

    def _reset(self) -> None:
        d = AppConfig()
        self.order_list.clear()
        for t in d.runtime.task_order:
            self.order_list.addItem(t)
        self.min_sanity.setValue(d.fight.min_sanity)
        self.series.setChecked(d.fight.series)
        self.tag_priority.setText(", ".join(d.recruit.tag_priority))
        self.max_times.setValue(d.recruit.max_times)
        self.time_hours.setValue(d.recruit.time_hours)
        self.ensure_4star.setChecked(d.recruit.ensure_4star)
        self.expedite.setChecked(d.recruit.expedite)
        self.retry.setValue(d.runtime.retry_per_task)
        self.shot_on_error.setChecked(d.runtime.screenshot_on_error)
        self.status.setText("已恢复默认（点「保存」生效）")


class DiagnosticsPage(QWidget):
    """诊断页（Phase 4）：doctor 自检 / 窗口探测（后台线程，不阻塞 UI）。"""

    def __init__(self, cfg: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        title = QLabel("诊断")
        title.setObjectName("title")
        hint = QLabel("环境自检与窗口探测；只读检查，不执行任何游戏操作。")
        hint.setObjectName("muted")

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("点击上方按钮开始。")

        self.check_btn = QPushButton("运行自检（doctor）")
        self.check_btn.clicked.connect(self._run_checks)
        self.win_btn = QPushButton("窗口列表（probe）")
        self.win_btn.clicked.connect(self._run_windows)

        row = QHBoxLayout()
        row.addWidget(self.check_btn)
        row.addWidget(self.win_btn)
        row.addStretch(1)

        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(hint)
        lay.addLayout(row)
        lay.addWidget(self.output, 1)

    def _run_checks(self) -> None:
        from ..application.diagnostics import run_checks

        self.output.setPlainText("自检中 ...")
        self.check_btn.setEnabled(False)

        def render(checks) -> None:
            self.check_btn.setEnabled(True)
            lines = [f"[{'OK ' if ok else 'FAIL'}] {name}  {msg}" for name, ok, msg in checks]
            lines += ["", "结论：" + ("全部通过" if all(ok for _, ok, _ in checks) else "存在未通过项")]
            self.output.setPlainText("\n".join(lines))

        self._thread = _FnThread(lambda: run_checks(self.cfg))
        self._thread.done.connect(render)
        self._thread.start()

    def _run_windows(self) -> None:
        from ..application.diagnostics import window_list

        self.output.setPlainText("探测中 ...")
        self.win_btn.setEnabled(False)

        def render(wins) -> None:
            self.win_btn.setEnabled(True)
            lines = [f"共 {len(wins)} 个窗口（匹配 device.window_match 的会被识别为游戏）", ""]
            for w in wins:
                lines.append(f"hwnd={w['hwnd']}\tclass={w['class_name']!r}\ttitle={w['window_name']!r}")
            self.output.setPlainText("\n".join(lines))

        self._thread = _FnThread(lambda: window_list())
        self._thread.done.connect(render)
        self._thread.start()
