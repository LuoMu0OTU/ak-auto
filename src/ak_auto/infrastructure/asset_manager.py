"""Infrastructure 层：AssetManager（Phase 1 任务 6）。

识别资源（MAA 素材）的存在性检查与按需获取；GUI 首次启动向导与 doctor 共用。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT

OCR_FILES = ("det.onnx", "rec.onnx", "keys.txt")


class AssetManager:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root else PROJECT_ROOT

    def status(self) -> dict[str, Any]:
        """资源状态：manifest / ocr / images / ready。"""
        manifest = self.root / "assets" / "MANIFEST.json"
        ocr_dir = self.root / "assets" / "resource" / "model" / "ocr"
        img_dir = self.root / "assets" / "resource" / "image"
        ocr_ok = all((ocr_dir / f).is_file() for f in OCR_FILES)
        img_ok = img_dir.is_dir() and any(img_dir.rglob("*.png"))
        return {
            "manifest": manifest.is_file(),
            "ocr": ocr_ok,
            "images": img_ok,
            "ready": manifest.is_file() and ocr_ok and img_ok,
        }

    @property
    def ready(self) -> bool:
        return bool(self.status()["ready"])

    def ensure(self, tag: str = "v6.19.0") -> bool:
        """资源不齐时拉取（委托 tools/fetch_maa_assets.py）；返回是否就绪。"""
        if self.ready:
            return True
        script = self.root / "tools" / "fetch_maa_assets.py"
        subprocess.run([sys.executable, str(script), "--tag", tag])
        return self.ready
