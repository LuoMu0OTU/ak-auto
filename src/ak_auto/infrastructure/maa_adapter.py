"""Infrastructure 层：MaaFrameworkAdapter（Phase 1 任务 6）。

MaaFw 资源/任务器装配的唯一入口（GUI 与 CLI 共用）：
内部委托现有 runtime 实现，不重写识别/执行逻辑。
"""
from __future__ import annotations

from ..config import AppConfig
from ..runtime import build_tasker


class MaaFrameworkAdapter:
    """装配 MaaFw Tasker（含自定义动作注册）。"""

    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg

    def build_tasker(self, controller):
        """绑定资源与控制器，返回 Tasker。"""
        return build_tasker(self.cfg, controller)

    def task_entries(self, tasker) -> set[str]:
        """当前资源包里的全部流水线节点名。"""
        return set(tasker.resource.node_list)
