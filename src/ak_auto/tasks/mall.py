"""采购任务：信用商店购买（只买「加急许可」，买一次就停）。"""
from __future__ import annotations

from maa.custom_action import CustomAction
from maa.resource import Resource

from ..config import AppConfig

_bought = False


def _box_xywh(box) -> tuple[int, int, int, int]:
    if hasattr(box, "x"):
        return (box.x, box.y, box.w, box.h)
    t = tuple(box)
    return (t[0], t[1], t[2], t[3])


class MallSelectBuy(CustomAction):
    """在信用商店里找到「加急许可」并点击；买过一次后停止。"""

    def run(self, context, argv) -> bool:
        global _bought
        if _bought:
            print("[mall] 已买过加急许可，停止", flush=True)
            return False

        img = context.tasker.controller.cached_image
        od = context.run_recognition("Mall@OcrItems", img)
        if not od:
            return False

        for r in od.all_results:
            text = (getattr(r, "text", "") or "").strip()
            box = getattr(r, "box", None)
            if text and box is not None and "加急许可" in text:
                x, y, w, h = _box_xywh(box)
                context.tasker.controller.post_click(x + w // 2, y + h // 2).wait()
                _bought = True
                print(f"[mall] 点击购买 加急许可 ({x},{y},{w},{h})", flush=True)
                return True

        print("[mall] 未找到加急许可，停止", flush=True)
        return False


def register(resource: Resource) -> None:
    global _bought
    _bought = False
    resource.register_custom_action("MallSelectBuy", MallSelectBuy())
