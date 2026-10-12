"""战斗任务：按理智自动设置代理指挥的最大连战次数。

思路（真机逆向出来的）：
  关卡详情页上「⟳ ×N」是次数显示，点它弹出竖直的次数列表；
  列表里**白色数字 = 当前理智还打得起**，灰色 = 打不起。
  所以「最大可连战次数」= 列表里**最上面的白色数字**。
  也可以直接算：理智 // 单次消耗。

注意：这款游戏不认 MaaFw 的 SendMessage/PostMessage 滚轮，
    必须用真实光标 + 硬件滚轮（device.native_wheel）。
"""
from __future__ import annotations

import re
import time

from maa.custom_action import CustomAction
from maa.resource import Resource

from .. import device
from ..config import AppConfig
from ..data.stages import max_loops, stage_ap_cost

# 关卡详情页：次数显示「⟳ ×N」
COUNT_DISPLAY = (997, 592)
# 次数列表里数字所在的竖直条带
LIST_X = (992, 1020)
LIST_X_CENTER = 1006
SCROLL_AT = (1006, 300)
WHITE_THRESHOLD = 200


def _first_int(text: str) -> int | None:
    m = re.search(r"\d+", text or "")
    return int(m.group()) if m else None


def _read_int(context, img, node: str) -> int | None:
    detail = context.run_recognition(node, img)
    if not detail:
        return None
    for r in detail.all_results:
        v = _first_int(getattr(r, "text", "") or "")
        if v:
            return v
    return None


class FightSetRepeatCount(CustomAction):
    """算最大连战次数，并在次数列表里选中它（最上面的白色数字）。"""

    def run(self, context, argv) -> bool:
        cfg = AppConfig.load()
        ctrl = context.tasker.controller
        img = ctrl.cached_image

        sanity = _read_int(context, img, "Fight@OcrSanity")
        count = _read_int(context, img, "Fight@OcrCount")
        total = _read_int(context, img, "Fight@OcrTotal")

        # 单次消耗：优先从画面推（总消耗 ÷ 当前次数），再退回配置里的关卡消耗
        cost = None
        if count and total and total >= count:
            cost = round(total / count)
        if not cost:
            cost = stage_ap_cost(cfg.fight.stage)

        if not sanity or not cost:
            print(f"[fight] 理智={sanity} 次数={count} 总消耗={total} → 算不出单次消耗，跳过", flush=True)
            return False

        n = max_loops(sanity, cost)
        print(f"[fight] 理智 {sanity} ÷ 单次消耗 {cost} → 最多 {n} 次", flush=True)
        if n <= 0:
            print("[fight] 理智不足一次，跳过", flush=True)
            return False

        hwnd = (ctrl.info or {}).get("hwnd")

        # 1) 打开次数列表
        ctrl.post_click(*COUNT_DISPLAY).wait()
        time.sleep(0.9)

        # 2) 滚到顶端（真实滚轮，游戏才认）
        if hwnd:
            device.native_wheel(hwnd, *SCROLL_AT, 40)
        time.sleep(0.9)

        # 3) 点最上面的白色数字
        rows = device.bright_rows(
            device.capture(ctrl), x0=LIST_X[0], x1=LIST_X[1], threshold=WHITE_THRESHOLD
        )
        if not rows:
            print("[fight] 次数列表里没有可选项（可能列表没弹出）", flush=True)
            ctrl.post_press_key(27).wait()
            return False

        y = rows[0][0]
        print(f"[fight] 选中列表最上面的白色数字 y={y}（共 {len(rows)} 个白色可选）", flush=True)
        ctrl.post_click(LIST_X_CENTER, y).wait()
        time.sleep(0.6)
        return True


def register(resource: Resource) -> None:
    resource.register_custom_action("FightSetRepeatCount", FightSetRepeatCount())
