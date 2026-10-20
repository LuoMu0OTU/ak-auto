#!/usr/bin/env python3
"""组装 MAA 识别资源（模板图 / OCR 模型 / 数据表）——开发模式命令行入口。

实现已迁入 `ak_auto.assets_fetch`（进程内可调用，打包版复用）；本脚本保留原 CLI。

用法：
    python tools/fetch_maa_assets.py [--tag v6.19.0] [--force] [--verify]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ak_auto.assets_fetch import DEFAULT_TAG, fetch, verify  # noqa: E402
from ak_auto.config import PROJECT_ROOT  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="组装 MAA 识别资源")
    ap.add_argument("--tag", default=DEFAULT_TAG, help="MAA 发版 tag")
    ap.add_argument("--force", action="store_true", help="忽略已有结果，强制重拉")
    ap.add_argument("--verify", action="store_true", help="仅校验现有资源")
    args = ap.parse_args()

    if args.verify:
        return 0 if verify(PROJECT_ROOT) else 1
    fetch(PROJECT_ROOT, tag=args.tag, force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
