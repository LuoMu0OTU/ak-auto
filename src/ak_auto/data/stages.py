"""读取 assets/maa-vendor/stages.json（关卡数据）。"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Optional

from . import VENDOR_DIR


@lru_cache(maxsize=1)
def _load() -> list[dict[str, Any]]:
    return json.loads((VENDOR_DIR / "stages.json").read_text(encoding="utf-8"))


def all_stages() -> list[dict[str, Any]]:
    return _load()


def find_stage(code: str) -> Optional[dict[str, Any]]:
    """按关卡号（如 CE-6 / 1-7）查找关卡。"""
    code = code.strip().upper()
    for s in _load():
        if s.get("code", "").upper() == code:
            return s
    return None


def stage_ap_cost(code: str) -> Optional[int]:
    s = find_stage(code)
    return s.get("apCost") if s else None


def stage_id(code: str) -> Optional[str]:
    s = find_stage(code)
    return s.get("stageId") if s else None
