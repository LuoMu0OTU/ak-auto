"""路径层：开发模式与打包（frozen）模式的分层目录解析。

- 开发模式：数据目录 = 仓库根（config/、logs/、assets/ 都挂在仓库下）。
- 打包模式（PyInstaller onedir）：数据目录 = exe 所在目录（可写：config/logs/下载的识别资源）；
  只读资源（流水线 JSON/数据表/配置模板）随包放在 _internal 里，首启复制到数据目录，
  之后所有读写与开发模式同构。

ADR-0003：配置与程序分离。
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path:
    """只读资源目录：frozen 时为 PyInstaller 解包目录，开发时为仓库根。"""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent / "_internal"
    return Path(__file__).resolve().parent.parent.parent


def data_dir() -> Path:
    """可写数据目录：frozen 时为 exe 所在目录，开发时为仓库根。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


# 只读资源（bundle 内）相对路径清单：首启复制到数据目录
_BOOTSTRAP_TREES = (
    "assets/resource/pipeline",
    "assets/maa-vendor",
    "tools",
)
_BOOTSTRAP_FILES = (
    "config/config.example.json",
)


def ensure_data_layout() -> Path:
    """frozen 首启：把只读资源从 bundle 复制到数据目录（幂等，已存在不覆盖）。"""
    data, bundle = data_dir(), bundle_dir()
    if not is_frozen() or data == bundle:
        return data
    for rel in _BOOTSTRAP_TREES:
        src, dst = bundle / rel, data / rel
        if src.is_dir() and not dst.exists():
            shutil.copytree(src, dst)
    for rel in _BOOTSTRAP_FILES:
        src, dst = bundle / rel, data / rel
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return data
