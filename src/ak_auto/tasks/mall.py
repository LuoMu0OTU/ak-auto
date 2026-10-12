"""采购任务：信用商店按优先级购买（先打折 → 再买剩下的；花到剩 <=300 停）。"""
from __future__ import annotations

import re

from maa.custom_action import CustomAction
from maa.resource import Resource

from ..config import AppConfig

_LABELS = {
    "售价", "商品内容", "购买物品", "可露希尔推荐", "源石交易所", "组合包",
    "时装商店", "凭证交易所", "家具商店", "信用交易所", "信用获取规则",
    "干员解锁进度", "库存更新倒计时", "已领取", "售罄", "售馨",
}


def _box_xywh(box) -> tuple[int, int, int, int]:
    if hasattr(box, "x"):
        return (box.x, box.y, box.w, box.h)
    t = tuple(box)
    return (t[0], t[1], t[2], t[3])


def _is_item(text: str) -> bool:
    if not text or len(text) > 10:
        return False
    if text in _LABELS:
        return False
    return any("\u4e00" <= c <= "\u9fff" for c in text)


def _near(box, marks, dx: int = 200, dy: int = 150) -> bool:
    cx, cy = box[0] + box[2] / 2, box[1] + box[3] / 2
    for m in marks:
        mx, my = m[0] + m[2] / 2, m[1] + m[3] / 2
        if abs(cx - mx) < dx and abs(cy - my) < dy:
            return True
    return False


class MallSelectBuy(CustomAction):
    """信用商店购买：读信用 → 打折优先/跳售罄 → 花到剩 <=300 停。"""

    def run(self, context, argv) -> bool:
        cfg = AppConfig.load()
        img = context.tasker.controller.cached_image

        credit = None
        cd = context.run_recognition("Mall@OcrCredit", img)
        if cd:
            for r in cd.all_results:
                digits = re.sub(r"\D", "", getattr(r, "text", "") or "")
                if digits:
                    credit = int(digits)
                    break
        print(f"[mall] 当前信用={credit}", flush=True)
        if credit is None or credit <= 300:
            print("[mall] 信用已 <=300，停止购买", flush=True)
            return False

        items: list[tuple[str, tuple[int, int, int, int]]] = []
        discounts: list[tuple[int, int, int, int]] = []
        soldout: list[tuple[int, int, int, int]] = []
        od = context.run_recognition("Mall@OcrItems", img)
        if od:
            for r in od.all_results:
                text = (getattr(r, "text", "") or "").strip()
                box = getattr(r, "box", None)
                if not text or box is None:
                    continue
                xywh = _box_xywh(box)
                if "售罄" in text or "售馨" in text:
                    soldout.append(xywh)
                elif "%" in text:
                    discounts.append(xywh)
                elif _is_item(text):
                    items.append((text, xywh))

        avail = [(n, b) for (n, b) in items if not _near(b, soldout)]
        disc = [(n, b) for (n, b) in avail if _near(b, discounts)]
        rest = [(n, b) for (n, b) in avail if not _near(b, discounts)]
        blacklist = set(cfg.mall.blacklist)
        rest = [(n, b) for (n, b) in rest if not any(bl in n for bl in blacklist)]

        ordered = disc + rest
        print(f"[mall] 可选物品={[n for n, _ in ordered]} (打折={[n for n, _ in disc]})", flush=True)
        if not ordered:
            return False

        name, (x, y, w, h) = ordered[0]
        context.tasker.controller.post_click(x + w // 2, y + h // 2).wait()
        print(f"[mall] 点击购买 {name}", flush=True)
        return True


def register(resource: Resource) -> None:
    resource.register_custom_action("MallSelectBuy", MallSelectBuy())
