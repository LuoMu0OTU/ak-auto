"""运行时装配：Resource / Tasker / 推理设备选择。"""
from __future__ import annotations

from pathlib import Path

from maa.resource import Resource
from maa.tasker import Tasker

from .config import AppConfig, PROJECT_ROOT

RESOURCE_DIR = PROJECT_ROOT / "assets" / "resource"


def load_resource(cfg: AppConfig) -> Resource:
    """加载 MaaFw 资源包（pipeline/image/model），并按配置选择推理设备。"""
    res = Resource()
    inference = (cfg.device.inference or "directml").lower()
    if inference == "cpu":
        res.use_cpu()
    elif inference == "directml":
        res.use_directml()
    # 其它值（auto/空）走 MaaFw 默认自动设备

    job = res.post_bundle(str(RESOURCE_DIR))
    job.wait()
    if not res.loaded:
        raise RuntimeError(
            "资源加载失败：请先运行 `python -m ak_auto fetch-assets` 组装资源，"
            "并确保 assets/resource/pipeline 下至少有一个流水线 JSON。"
        )
    return res


def build_tasker(cfg: AppConfig, controller) -> Tasker:
    """装配 Tasker：绑定资源与控制器。"""
    res = load_resource(cfg)
    tasker = Tasker()
    if not tasker.bind(res, controller):
        raise RuntimeError("Tasker.bind 失败")
    return tasker
