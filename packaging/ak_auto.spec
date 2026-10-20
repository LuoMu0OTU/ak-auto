# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec：ak-auto 便携包（ADR-0003）。

- onedir 模式：dist/AkAuto/ak-auto.exe + _internal/（运行时与只读资源）
- 大体积识别资源（模板图/OCR 模型）不打包，首启 fetch-assets 下载
- 配置与程序分离：可写数据在 exe 旁目录（src/ak_auto/paths.py）
"""
from pathlib import Path

import PyInstaller.utils.hooks as hooks

ROOT = Path(SPECPATH).resolve()  # packaging/ 目录
PROJECT = ROOT.parent
# hooks/__init__.py → utils → PyInstaller → site-packages
MAA_BIN = Path(hooks.__file__).resolve().parent.parent.parent.parent / "maa" / "bin"

datas = [
    (str(PROJECT / "assets" / "resource" / "pipeline"), "assets/resource/pipeline"),
    (str(PROJECT / "assets" / "maa-vendor"), "assets/maa-vendor"),
    (str(PROJECT / "tools"), "tools"),
    (str(PROJECT / "config" / "config.example.json"), "config"),
    (str(PROJECT / "LICENSE"), "."),
    (str(PROJECT / "NOTICE.md"), "."),
]

binaries = []
if MAA_BIN.is_dir():
    binaries = [(str(f), "maa/bin") for f in MAA_BIN.iterdir() if f.is_file()]

# ak_auto 内部大量惰性导入（tasks/infrastructure/device 等在函数内 import），
# maa/typer 同样经 GUI 路径不可达——显式收集，避免打包版缺模块。
hiddenimports = (
    hooks.collect_submodules("ak_auto")
    + hooks.collect_submodules("maa")
    + ["typer"]
)

a = Analysis(
    [str(PROJECT / "packaging" / "launcher.py")],
    pathex=[str(PROJECT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tkinter", "unittest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ak-auto",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AkAuto",
)
