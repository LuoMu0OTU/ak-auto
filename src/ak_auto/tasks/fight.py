"""战斗任务：按理智与配置精确设置代理指挥连战次数（Phase 5 修复版）。

真机逆向结论（2026-10，人眼配合确认）：
  1. 战斗准备页右下：代理指挥开关（约 (1070,578)），**开启后**其左侧出现「⟳×N」次数显示
     （约 (1000,580)）。
  2. 点「⟳×N」弹出竖直次数列表：**从大到小**（顶部最大，底部是 1），列表最大 10 次；
     每个数字在列表里表现为上下两条白色亮线（间隔约 20px），相邻数字间隔约 52px；
     可选（理智足够）的数字为白色，不可选为灰色。
  3. 列表打开时自动定位到「最大可连战」可见的位置。
  4. 因此：目标次数 = 最大可连战 时点最上方白色数字；
     目标 1/2/3 时从底部往上数第 n 个白色数字（底部 = 1）。

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

# 战斗准备页：代理指挥开关 + 开启后左侧的次数显示
TOGGLE = (1070, 578)
COUNT_DISPLAY = (1000, 580)
# 次数列表里数字所在的竖直条带（数字 x≈998-1014）
LIST_X = (985, 1030)
LIST_X_CENTER = 1006
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


def decide_loops(sanity, cost, cfg: AppConfig) -> tuple:
    """纯函数：决定连战次数（可单元测试）。

    返回 (n, reason)：n=None 表示不应执行（reason 说明原因）；
    reason 为空字符串表示正常。
    """
    if not sanity or not cost:
        return None, "cost-unknown"
    if cfg.fight.min_sanity > 0 and sanity < cfg.fight.min_sanity:
        return None, "sanity-below-min"
    n = max_loops(sanity, cost)
    if cfg.fight.times > 0:
        n = min(n, cfg.fight.times)
    if n <= 0:
        return None, "sanity-insufficient"
    return n, ""


class FightRecoverCapture(CustomAction):
    """恢复截图：战斗的独占渲染会把桌面复制（DXGI）打进 ACCESS_LOST 状态，
    还原窗口 + 主动截一张图可以自愈（真机实测）。"""

    def run(self, context, argv) -> bool:
        ctrl = context.tasker.controller
        hwnd = (ctrl.info or {}).get("hwnd")
        for attempt in range(4):
            try:
                img = ctrl.post_screencap().wait().get()
                if img is not None and getattr(img, "size", 0):
                    print(f"[fight] 截图已恢复（第 {attempt + 1} 次）", flush=True)
                    return True
            except Exception:  # noqa: BLE001
                pass
            if hwnd:
                device.restore_window(hwnd)
            time.sleep(2.0)
        print("[fight] 截图恢复失败", flush=True)
        return True  # 恢复失败也继续（点击类动作不依赖截图）


class FightSetRepeatCount(CustomAction):
    """按目标次数在次数列表里精确选中（不再假定游戏内已是目标值）。"""

    def __init__(self, cfg: AppConfig) -> None:
        super().__init__()
        self.cfg = cfg

    def run(self, context, argv) -> bool:
        cfg = self.cfg
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

        n, reason = decide_loops(sanity, cost, cfg)
        if n is None:
            print(f"[fight] {reason}（理智={sanity} 消耗={cost}）跳过刷图", flush=True)
            return False
        max_affordable = max_loops(sanity, cost)
        print(f"[fight] 理智 {sanity} ÷ 单次消耗 {cost} → 目标 {n} 次（最大可连战 {max_affordable}）", flush=True)

        # 打开次数列表（代理指挥未开启时先开启开关 → 才会出现次数显示）
        rows: list[tuple[int, int]] = []
        for attempt in range(3):
            ctrl.post_click(*COUNT_DISPLAY).wait()
            time.sleep(0.9)
            rows = device.bright_rows(
                device.capture(ctrl), x0=LIST_X[0], x1=LIST_X[1], threshold=WHITE_THRESHOLD
            )
            if len(rows) >= 2:
                break
            ctrl.post_click(*TOGGLE).wait()  # 开启代理指挥 → 出现「⟳×N」
            time.sleep(0.9)

        if len(rows) < 2:
            print("[fight] 次数列表里没有可选项（列表可能没弹出）", flush=True)
            ctrl.post_press_key(27).wait()
            return False

        # 列表从大到小、每个数字两条白线、底部 = 1：
        # 目标 == 最大可连战 → 最上面；否则从底部往上第 n 个数字。
        if n >= max_affordable:
            y = (rows[0][0] + rows[1][0]) / 2
            print(f"[fight] 选最上面的白色数字（= {n} 次）y={y:.0f}", flush=True)
        elif len(rows) >= 2 * n:
            y = (rows[-2 * n][0] + rows[-2 * n + 1][0]) / 2
            print(f"[fight] 从底部往上第 {n} 个白色数字 y={y:.0f}", flush=True)
        else:
            # 目标次数不在可视区（需向上滚动才能看到更大的数）：
            # 近似取最上面白色行并如实记录（精确滚动待有图像输入后完善）
            y = (rows[0][0] + rows[1][0]) / 2
            print(f"[fight] 目标 {n} 次不在可视区，近似选最上面白色行 y={y:.0f}（如实记录）", flush=True)

        ctrl.post_click(LIST_X_CENTER, int(y)).wait()
        time.sleep(0.6)
        return True


def register(resource: Resource, cfg: AppConfig) -> None:
    resource.register_custom_action("FightSetRepeatCount", FightSetRepeatCount(cfg))
    resource.register_custom_action("FightRecoverCapture", FightRecoverCapture())
