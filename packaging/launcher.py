"""打包版入口：双击启动 GUI（隐藏控制台），带参数走 CLI。

- PyInstaller 以 console=True 构建（窗口版引导器在本机于 Python 之前静默崩溃，
  见 ADR-0003「打包形态」备注）；GUI 启动时隐藏控制台并把输出重定向到日志。
- CLI 各子命令在带参数调用时走 ak_auto.__main__（静默日常/doctor/lint 等）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _data_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _redirect_to_log() -> None:
    """GUI 路径：stdout/stderr 重定向到 logs/console.log，避免打印崩溃且可查诊断。"""
    try:
        logdir = _data_dir() / "logs"
        logdir.mkdir(parents=True, exist_ok=True)
        log = open(logdir / "console.log", "a", encoding="utf-8", errors="replace")  # noqa: SIM115
        sys.stdout = log
        sys.stderr = log
    except Exception:
        sys.stdout = open(os.devnull, "w")  # noqa: SIM115
        sys.stderr = sys.stdout


def _hide_console() -> None:
    """隐藏打包版自带的控制台窗口（双击启动 GUI 时）。"""
    if not getattr(sys, "frozen", False) or sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass


def main() -> int:
    # 带参数 → CLI（静默日常/doctor/lint 等），保留控制台输出；双击无参 → GUI
    if len(sys.argv) > 1:
        from ak_auto.__main__ import main as cli_main

        return cli_main()
    _hide_console()
    _redirect_to_log()
    from ak_auto.gui.app import run_gui

    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
