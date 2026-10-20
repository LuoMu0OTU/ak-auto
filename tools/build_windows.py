#!/usr/bin/env python3
"""构建 Windows 便携包（PyInstaller onedir，ADR-0003）。

用法：
    python tools/build_windows.py            # 构建 dist/AkAuto/
    python tools/build_windows.py --smoke    # 构建 + 启动打包版 GUI 冒烟
    python tools/build_windows.py --no-clean # 增量构建

产物：
    dist/AkAuto/ak-auto.exe       窗口化入口（双击启动 GUI）
    dist/AkAuto/_internal/        运行时 + 只读资源（流水线/数据表/配置模板）
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "ak_auto.spec"
DIST = ROOT / "dist" / "AkAuto"
EXE = DIST / "ak-auto.exe"


def main() -> int:
    ap = argparse.ArgumentParser(description="构建 Windows 便携包")
    ap.add_argument("--smoke", action="store_true", help="构建后启动打包版 GUI 冒烟")
    ap.add_argument("--no-clean", action="store_true", help="增量构建（不清除上次产物）")
    args = ap.parse_args()

    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm"]
    if not args.no_clean:
        cmd.append("--clean")
    print(f"[build] {' '.join(cmd)}")
    p = subprocess.run(cmd, cwd=ROOT)
    if p.returncode != 0:
        print("[build] PyInstaller 失败")
        return p.returncode

    if not EXE.is_file():
        print("[build] 产物缺失：dist/AkAuto/ak-auto.exe")
        return 1
    size = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file()) / (1024 * 1024)
    print(f"[build] 完成：{EXE}（约 {size:.0f} MB）")

    if args.smoke:
        print("[smoke] 启动打包版 GUI（10 秒后自动关闭由人工确认窗口出现）")
        subprocess.Popen([str(EXE)], cwd=DIST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
