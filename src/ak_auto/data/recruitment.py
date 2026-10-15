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


def best_selection(available_tags: list[str], tag_priority: list[str] | None = None) -> list[str]:
    """返回最佳标签选择。

    Phase 5 起支持 tag_priority：可用标签命中优先级列表时，选**优先级最高**的那个标签单独选
    （如「高级资深干员」单独选即保底 6★，多选反而可能破坏保底）。
    否则：保底 4★ 组合 > 保底 3★ 组合 > 单个能出最高稀有度的标签。
    数据驱动，等价于公招「选标签表」的保底逻辑。
    """
    avail = [t.strip() for t in available_tags if t.strip()]
    if tag_priority:
        wants = [w.strip() for w in tag_priority if w and w.strip()]
        # 先精确匹配（优先级顺序），避免「资深干员」⊂「高级资深干员」的误匹配
        for want in wants:
            for tag in avail:
                if tag == want:
                    return [tag]
        # 再退让：OCR 结果可能带杂字，want 包含于 tag 即命中
        for want in wants:
            for tag in avail:
                if want in tag:
                    return [tag]
    combo, _ops = best_tag_combination(avail, 4)
    if combo:
        return combo
    combo, _ops = best_tag_combination(avail, 3)
    if combo:
        return combo
    # 无保底：选单个能出最高稀有度的标签（通常是职业标签）
    best_tag = ""
    best_rarity = 0
    for tag in avail:
        ops = match_operators([tag])
        if not ops:
            continue
        top = max(o["rarity"] for o in ops)
        if top > best_rarity:
            best_tag, best_rarity = tag, top
    return [best_tag] if best_tag else []
