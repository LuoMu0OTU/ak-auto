"""Infrastructure 层：GameWindowAdapter（Phase 1 任务 6）。

游戏窗口与输入控制器的生命周期管理：
- acquire：确保窗口（含自动启动）并连接控制器；**同一时间只允许一个控制器**（AGENTS.md 第 2.4 条），已连接则复用；
- release：释放引用并还原被 MaaFw 伪最小化的窗口（第 5.4 条清理要求）。
"""
from __future__ import annotations

import threading

from .. import device
from ..config import AppConfig


class WindowNotFound(RuntimeError):
    """游戏窗口不存在（自动启动也失败）。"""


class GameWindowAdapter:
    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self._lock = threading.Lock()
        self._controller = None
        self._hwnd = None

    @property
    def acquired(self) -> bool:
        with self._lock:
            return self._controller is not None

    def acquire(self, on_log=None):
        """确保游戏窗口并连接控制器；已连接则复用（单控制者互斥）。"""
        with self._lock:
            if self._controller is not None:
                return self._hwnd, self._controller
            win = device.ensure_game_window(self.cfg, on_log=on_log)
            if not win:
                raise WindowNotFound(
                    "未找到游戏窗口，自动启动也没成功。请确认 config 的 startup.game_path，或手动打开游戏。"
                )
            ctrl = device.connect_controller(
                win["hwnd"],
                device.parse_screencap(self.cfg.device.screencap[0]),
                device.parse_input(self.cfg.device.mouse_input[0]),
                device.parse_input(self.cfg.device.keyboard_input),
            )
            self._hwnd, self._controller = win["hwnd"], ctrl
            return self._hwnd, ctrl

    def release(self, restore: bool = True) -> None:
        """释放控制器引用，并（默认）还原游戏窗口。"""
        with self._lock:
            hwnd = self._hwnd
            self._hwnd, self._controller = None, None
        if hwnd and restore:
            device.restore_window(hwnd)
