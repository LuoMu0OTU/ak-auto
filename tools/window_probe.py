#!/usr/bin/env python3
"""探测明日方舟窗口与截图/输入方式。

用法：
    python tools/window_probe.py --list
    python tools/window_probe.py [--config config/config.json] [--out debug/shots] [--click 640,360]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto import device  # noqa: E402
from ak_auto.config import AppConfig, PROJECT_ROOT  # noqa: E402


def _utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main() -> int:
    _utf8()
    ap = argparse.ArgumentParser(description="探测明日方舟窗口与截图/输入方式")
    ap.add_argument("--config", default=None, help="config.json 路径")
    ap.add_argument("--list", action="store_true", help="仅列出所有窗口")
    ap.add_argument("--click", default=None, help="点击测试：x,y（如 --click 640,360）")
    ap.add_argument("--out", default=str(PROJECT_ROOT / "debug" / "shots"), help="截图保存目录")
    args = ap.parse_args()

    device.init_maa()
    cfg = AppConfig.load(args.config)

    if args.list:
        for w in device.list_windows():
            print(f"hwnd={w['hwnd']}\tclass={w['class_name']!r}\ttitle={w['window_name']!r}")
        return 0

    win = device.find_game_window(cfg)
    if not win:
        print("未找到匹配窗口，当前桌面窗口列表：")
        for w in device.list_windows():
            print(f"  hwnd={w['hwnd']}\tclass={w['class_name']!r}\ttitle={w['window_name']!r}")
        print("\n请在 config/config.json 的 device.window_match 里填 class_name 或 title_contains。")
        return 1

    print(f"命中窗口: hwnd={win['hwnd']} class={win['class_name']!r} title={win['window_name']!r}")

    result = device.probe_best(cfg, win, save_dir=args.out)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))

    if args.click:
        try:
            x, y = (int(v) for v in args.click.split(","))
        except ValueError:
            print("--click 格式应为 x,y，例如 --click 640,360")
            return 2
        sc = device.parse_screencap(result.screencap)
        ctrl = device.connect_controller(
            win["hwnd"], sc,
            device.parse_input(result.mouse),
            device.parse_input(result.keyboard),
        )
        ctrl.post_click(x, y).wait()
        print(f"[click] 已点击 ({x},{y})，请查看游戏窗口是否响应。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
