"""公招任务：标签 OCR 结果解析 + 词条匹配 + 选择点击。"""
from __future__ import annotations

from maa.custom_action import CustomAction
from maa.resource import Resource

from ..data import recruitment


def _normalize(text: str) -> str:
    return text.strip().replace(" ", "").replace("·", "")


def _box_xywh(box) -> tuple[int, int, int, int]:
    """兼容 Rect 对象 / list / tuple 的 [x, y, w, h]。"""
    if hasattr(box, "x"):
        return (box.x, box.y, box.w, box.h)
    vals = tuple(box)
    return (vals[0], vals[1], vals[2], vals[3])


class RecruitSelectTags(CustomAction):
    """读取公招界面的 5 个标签，匹配保底组合并点击对应标签。"""

    def run(self, context, argv) -> bool:
        detail = argv.reco_detail
        results = getattr(detail, "all_results", None) or []
        tags: list[tuple[str, tuple[int, int, int, int]]] = []
        for r in results:
            text = getattr(r, "text", "")
            box = getattr(r, "box", None)
            if text and box is not None:
                tags.append((_normalize(text), _box_xywh(box)))

        if not tags:
            return True

        names = [t for t, _ in tags]
        combo = recruitment.best_selection(names)
        print(f"[recruit] 识别标签={names}", flush=True)
        print(f"[recruit] 选中标签={combo}", flush=True)
        if not combo:
            # 实在没词条可配：不选，直接招募
            return True

        ctrl = context.tasker.controller
        for name in combo:
            for text, (x, y, w, h) in tags:
                if name in text or text in name:
                    ctrl.post_click(x + w // 2, y + h // 2).wait()
                    break
        return True


def register(resource: Resource) -> None:
    resource.register_custom_action("RecruitSelectTags", RecruitSelectTags())
