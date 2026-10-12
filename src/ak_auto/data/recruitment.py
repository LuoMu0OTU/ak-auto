"""读取 assets/maa-vendor/recruitment.json（公开招募词条匹配）。"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from . import VENDOR_DIR


@lru_cache(maxsize=1)
def _operators() -> list[dict[str, Any]]:
    data = json.loads((VENDOR_DIR / "recruitment.json").read_text(encoding="utf-8"))
    return data["operators"]


def match_operators(selected_tags: list[str]) -> list[dict[str, Any]]:
    """返回能被这组词条组合招募到的所有干员（所选词条必须是该干员标签的子集）。"""
    tags = {t.strip() for t in selected_tags if t.strip()}
    out = [op for op in _operators() if tags.issubset(set(op["tags"]))]
    out.sort(key=lambda o: -o["rarity"])
    return out


def best_tag_combination(available_tags: list[str], min_rarity: int = 4) -> tuple[list[str], list[dict[str, Any]]]:
    """在可用词条中找一个能「保底 >= min_rarity」的最优组合。

    保底定义：这组词条能招到的所有干员星级都 >= min_rarity。
    返回 (所选词条列表, 匹配到的干员列表)；没有保底组合时返回 ([], [])。
    """
    n = len(available_tags)
    best_combo: list[str] = []
    best_ops: list[dict[str, Any]] = []
    best_score: tuple[int, int, int] | None = None  # (最小星级取负, 干员数, 词条数)
    for mask in range(1, 1 << n):
        combo = [available_tags[i] for i in range(n) if mask & (1 << i)]
        ops = match_operators(combo)
        if not ops or any(o["rarity"] < min_rarity for o in ops):
            continue
        score = (-min(o["rarity"] for o in ops), len(ops), len(combo))
        if best_score is None or score < best_score:
            best_combo, best_ops, best_score = combo, ops, score
    return best_combo, best_ops
