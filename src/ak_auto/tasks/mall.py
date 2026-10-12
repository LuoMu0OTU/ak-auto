"""采购任务：信用商店按优先级购买。"""
from __future__ import annotations

from maa.custom_action import CustomAction
from maa.resource import Resource

from ..config import AppConfig

_LABELS = {
    "售价", "商品内容", "购买物品", "可露希尔推荐", "源石交易所", "组合包",
    "时装商店", "凭证交易所", "家具商店", "信用交易所", "信用获取规则",
    "干员解锁进度", "库存更新倒计时", "已有",
}


def _is_item(text: str) -> bool:
    if not text or len(text) > 8:
        return False
    if text in _LABELS:
        return False
    return any("\u4e00" <= c <= "\u9fff" for c in text)


def _box_xywh(box) -> tuple[int, int, int, int]:
    if hasattr(box, "x"):
        return (box.x, box.y, box.w, box.h)
    t = tuple(box)
    return (t[0], t[1], t[2], t[3])


class MallSelectBuy(CustomAction):
    """读取信用商店物品，按 buy_first 优先、blacklist 排除，点击要买的物品。"""

    def run(self, context, argv) -> bool:
        cfg = AppConfig.load()
        buy_first = cfg.mall.buy_first
        blacklist = set(cfg.mall.blacklist)

        results = getattr(argv.reco_detail, "all_results", None) or []
        items: list[tuple[str, tuple[int, int, int, int]]] = []
        for r in results:
            text = (getattr(r, "text", "") or "").strip()
            box = getattr(r, "box", None)
            if _is_item(text) and box is not None:
                items.append((text, _box_xywh(box)))

        if not items:
            return False

        target = None
        for name, pos in items:
            if any(bf in name or name in bf for bf in buy_first):
                target = (name, pos)
                break
        if target is None:
            for name, pos in items:
                if name not in blacklist and not any(b in name for b in blacklist):
                    target = (name, pos)
                    break
        if target is None:
            return False

        name, (x, y, w, h) = target
        context.tasker.controller.post_click(x + w // 2, y + h // 2).wait()
        print(f"[mall] 购买 {name}", flush=True)
        return True


def register(resource: Resource) -> None:
    resource.register_custom_action("MallSelectBuy", MallSelectBuy())
