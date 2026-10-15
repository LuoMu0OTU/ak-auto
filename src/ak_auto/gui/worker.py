"""QThread 桥接：GUI 在非 UI 线程跑任务（AGENTS.md 第 2.3 条）。

UI 线程只发 start/stop；事件与结果经 Qt 信号跨线程安全回传。
"""
from __future__ import annotations

import threading
import time

from PySide6.QtCore import QThread, Signal

from ..application import ExecutionController
from ..domain import EventBus
from ..infrastructure import GameWindowAdapter, MaaFrameworkAdapter


class TaskWorker(QThread):
    """后台线程执行任务序列（经 Application 层，不直接碰识别/点击）。"""

    log = Signal(str)       # 日志 / 事件文本
    done = Signal(object)   # list[ExecutionResult]
    failed = Signal(str)    # 装配失败信息

    def __init__(self, cfg, entries, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.entries = list(entries)
        self._stop = threading.Event()

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
            self.done.emit(controller.wait(timeout=0))
        except Exception as exc:  # noqa: BLE001 —— 错误也回传 UI，不留静默失败
            self.failed.emit(str(exc))
        finally:
            win_adapter.release(restore=True)

    def _on_event(self, e) -> None:
        self.log.emit(f"{e.type.value} {e.task_id} {e.message}".strip())

    def stop(self) -> None:
        """请求安全停止（协作式取消）。"""
        self._stop.set()
