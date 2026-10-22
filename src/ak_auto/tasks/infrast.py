"""基建任务：点击「发光的制造站」（已停止的制造站）自动恢复生产（Phase 7）。

真机逆向（截图确认）：
- 已停止的制造站在基地地图上是「**制造站**」+ 橙红「**已停止**」小字 + 亮黄粗边框；
- 点击方块内任意位置 → 「制造站已自动补货」、恢复生产中；
- 原流水线「点制造停工文字」会卡住，必须点这些发光的制造站。

检测（实测区分度）：OCR 读站名「制造站」→ 采样站名下方的状态小字区 →
  「生产中」为黄字（黄色像素 24~38）、「已停止」为橙字（黄色像素 0），
  以「黄色像素 < 12」判定停工。点击站名下方（方块内）恢复，循环直到没有停工站。
"""
from __future__ import annotations

import time

import numpy as np
from maa.custom_action import CustomAction
from maa.resource import Resource

# 状态文字区（站名下方）
STATE_DY = 2
STATE_W, STATE_H = 55, 14
YELLOW_MIN_STOPPED = 12   # 状态区黄色像素 < 该值 → 已停止（生产中为 24~38）
CLICK_DY = 15             # 从站名中心向下偏到方块中心


def _yellow_count(img: np.ndarray, x: int, y: int, w: int, h: int) -> int:
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(img.shape[1], x + w), min(img.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return 0
    sub = img[y0:y1, x0:x1]
    b = sub[..., 0].astype(np.int16)
    g = sub[..., 1].astype(np.int16)
    r = sub[..., 2].astype(np.int16)
    return int(((r > 180) & (g > 170) & (b < 120)).sum())


def is_stopped(img: np.ndarray, name_box: tuple[int, int, int, int]) -> bool:
    """站名所在的制造站是否处于「已停止」状态。"""
    x, y, _w, h = name_box
    yellow = _yellow_count(img, x, y + h + STATE_DY, STATE_W, STATE_H)
    return yellow < YELLOW_MIN_STOPPED


class InfrastResumeStations(CustomAction):
    """点击一个已停止的制造站；返回 True（点了一个，稍后重试）/ False（没有停工站了）。"""

    def run(self, context, argv) -> bool:
        ctrl = context.tasker.controller
        try:
            img = ctrl.cached_image
        except Exception:  # noqa: BLE001
            return False
        detail = context.run_recognition("Infrast@OcrMfgStation", img)
        if not detail:
            return False
        stopped: list[tuple[int, int]] = []
        for r in detail.all_results:
            text = (getattr(r, "text", "") or "").replace(" ", "")
            # 只认「制造站」开头的站名（排除「加工站」等误读）
            if not text.startswith("制造站"):
                continue
            box = r.box
            if is_stopped(img, (box[0], box[1], box[2], box[3])):
                stopped.append((box[0] + box[2] // 2, box[1] + box[3] // 2 + CLICK_DY))
        if not stopped:
            print("[infrast] 没有停工的制造站了", flush=True)
            return False
        cx, cy = stopped[0]
        print(f"[infrast] 点击停工制造站 ({cx},{cy})，共 {len(stopped)} 个", flush=True)
        ctrl.post_click(cx, cy).wait()
        time.sleep(1.5)
        return True


def register(resource: Resource) -> None:
    resource.register_custom_action("InfrastResumeStations", InfrastResumeStations())
    resource.register_custom_action("InfrastResetRound", InfrastResetRound())
    resource.register_custom_action("InfrastNextRound", InfrastNextRound())


# ---- 多轮收菜（用户经验：回主页再进基建可刷新待办，收菜卡住时重来一轮）----
_ROUND = {"n": 0}
ROUNDS = 2          # 基建收菜轮数（1 = 只收一轮）
BACK_BTN = (40, 40)  # 基建内「<」返回 → 主界面


class InfrastResetRound(CustomAction):
    """进入 Infrast 时重置轮次计数。"""

    def run(self, context, argv) -> bool:
        _ROUND["n"] = 0
        return True


class InfrastNextRound(CustomAction):
    """一轮收菜结束：返回 True（回主页，再进基建收下一轮）/ False（轮次用完，结束）。"""

    def run(self, context, argv) -> bool:
        _ROUND["n"] += 1
        if _ROUND["n"] >= ROUNDS:
            print(f"[infrast] 已完成 {_ROUND['n']} 轮，结束", flush=True)
            return False
        ctrl = context.tasker.controller
        print(f"[infrast] 第 {_ROUND['n']} 轮完成，回主界面准备再进基建", flush=True)
        ctrl.post_click(*BACK_BTN).wait()
        time.sleep(2.5)
        return True
