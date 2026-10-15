"""GUI 子包（Phase 2）：PySide6 桌面界面。

入口：`python -m ak_auto gui`，或 `from ak_auto.gui.app import run_gui`。
GUI 只经 Application 层调用（AGENTS.md 第 2.1/2.2 条），不直接操作识别/点击。
"""

from .app import run_gui

__all__ = ["run_gui"]
