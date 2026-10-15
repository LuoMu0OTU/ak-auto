"""Application 层：诊断服务（CLI doctor 与 GUI 诊断页共用，AGENTS.md 共享核心）。"""
from __future__ import annotations

import os
import sys

from ..config import AppConfig
from ..infrastructure import AssetManager


def run_checks(cfg: AppConfig) -> list[tuple[str, bool, str]]:
    """环境 / 资源 / 游戏路径 / 窗口 检查。返回 (名称, 是否通过, 说明)。"""
    checks: list[tuple[str, bool, str]] = []

    py = sys.version_info
    ok = (py.major, py.minor) == (3, 12)
    checks.append(("Python 3.12", ok, f"{py.major}.{py.minor}.{py.micro}" + ("" if ok else "（必须 3.12）")))

    try:
        import maa  # noqa: F401
        checks.append(("MaaFw 可导入", True, "ok"))
    except Exception as e:  # noqa: BLE001
        checks.append(("MaaFw 可导入", False, str(e)))

    am = AssetManager().status()
    checks.append(("识别资源（MANIFEST）", bool(am["manifest"]), "存在" if am["manifest"] else "缺失，请先 fetch-assets"))
    checks.append(("OCR 模型", bool(am["ocr"]), "就绪" if am["ocr"] else "缺失，请先 fetch-assets"))
    checks.append(("模板图", bool(am["images"]), "就绪" if am["images"] else "缺失，请先 fetch-assets"))

    game = cfg.startup.game_path
    checks.append(("游戏路径存在", os.path.isfile(game), game))

    try:
        from .. import device

        device.init_maa()
        win = device.find_game_window(cfg)
        checks.append(
            ("游戏窗口", win is not None,
             f"hwnd={win['hwnd']} title={win['window_name']!r}" if win else "未找到（游戏是否已启动？）")
        )
    except Exception as e:  # noqa: BLE001
        checks.append(("游戏窗口", False, str(e)))

    return checks


def window_list() -> list[dict]:
    """当前所有窗口（probe --list 与 GUI 诊断共用）。"""
    from .. import device

    device.init_maa()
    return device.list_windows()
