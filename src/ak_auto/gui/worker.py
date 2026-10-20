"""QThread 桥接：GUI 在非 UI 线程跑任务（AGENTS.md 第 2.3 条）。

UI 线程只发 start/stop；事件与结果经 Qt 信号跨线程安全回传。
"""
from __future__ import annotations

import threading
import time

from PySide6.QtCore import QThread, Signal

from ..application import ExecutionController
from ..domain import EventBus, EventType, ExecutionState
from ..infrastructure import GameWindowAdapter, MaaFrameworkAdapter


class TaskWorker(QThread):
    """后台线程执行任务序列（经 Application 层，不直接碰识别/点击）。"""

    log = Signal(str)            # 日志 / 事件文本
    done = Signal(object)        # list[ExecutionResult]
    failed = Signal(str)         # 装配失败信息
    task_state = Signal(str, str)  # (task_id, 状态值)：当前任务与状态机状态
    seq_progress = Signal(int, int)  # (已结束任务数, 序列总数)

    def __init__(self, cfg, entries, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.entries = list(entries)
        self._stop = threading.Event()
        self._finished_count = 0

    def run(self) -> None:  # noqa: D102 —— QThread 入口
        from .. import device

        device.init_maa()
        win_adapter = GameWindowAdapter(self.cfg)
        try:
            _hwnd, ctrl = win_adapter.acquire(on_log=self.log.emit)
            tasker = MaaFrameworkAdapter(self.cfg).build_tasker(ctrl)
            bus = EventBus()
            bus.subscribe_all(self._on_event)
            controller = ExecutionController(tasker, bus=bus)
            controller.start(self.entries, retry_per_task=0, on_progress=self.log.emit)
            while controller.running:
                if self._stop.is_set():
                    self.log.emit("[gui] 收到停止请求，正在安全停止 ...")
                    controller.cancel()
                time.sleep(0.1)
            results = controller.wait(timeout=0)
            try:
                from ..report import make_report

                make_report(results).save()
            except Exception:  # noqa: BLE001 —— 报告失败不影响运行结果
                pass
            self.done.emit(results)
        except Exception as exc:  # noqa: BLE001 —— 错误也回传 UI，不留静默失败
            self.failed.emit(str(exc))
        finally:
            win_adapter.release(restore=True)

    def _on_event(self, e) -> None:
        if e.type is EventType.TASK_STARTED:
            self.task_state.emit(e.task_id, ExecutionState.RUNNING.value)
        elif e.type in (EventType.TASK_COMPLETED, EventType.TASK_FAILED, EventType.TASK_CANCELLED):
            self.task_state.emit(e.task_id, e.state.value)
            self._finished_count += 1
            self.seq_progress.emit(self._finished_count, len(self.entries))
        self.log.emit(f"{e.type.value} {e.task_id} {e.message}".strip())

    def stop(self) -> None:
        """请求安全停止（协作式取消）。"""
        self._stop.set()


class UpdateWorker(QThread):
    """后台查询 GitHub Releases 最新版本（Phase 7 自动更新检查）。

    只检查+回传结果，不下载/安装；失败回传 None（UI 静默忽略）。
    """

    result = Signal(object)  # UpdateInfo | None

    def __init__(self, current: str, repo: str, parent=None) -> None:
        super().__init__(parent)
        self.current = current
        self.repo = repo

    def run(self) -> None:  # noqa: D102 —— QThread 入口
        from ..application.updates import check_latest

        info = check_latest(self.current, repo=self.repo)
        self.result.emit(info)
