"""流水线静态校验测试。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from pipeline_lint import lint_pipelines  # noqa: E402


def test_pipeline_lint_clean() -> None:
    errors, warnings = lint_pipelines()
    assert not errors, "流水线校验存在错误:\n" + "\n".join(errors)


def test_required_entries_exist() -> None:
    errors, _ = lint_pipelines()
    assert not errors
    # 关键入口节点必须存在
    from maa.resource import Resource

    res = Resource()
    res.post_bundle(str(ROOT / "assets" / "resource")).wait()
    nodes = set(res.node_list)
    for entry in ("StartUp", "ReturnToHome", "Home"):
        assert entry in nodes, f"缺少入口节点 {entry}"


def test_task_order_entries_exist() -> None:
    """task_order 里的每个任务都必须有对应流水线节点（防止配出不存在的任务）。"""
    from ak_auto.config import AppConfig, RuntimeConfig
    from maa.resource import Resource

    res = Resource()
    res.post_bundle(str(ROOT / "assets" / "resource")).wait()
    nodes = set(res.node_list)

    orders = {"默认顺序": RuntimeConfig().task_order}
    example = ROOT / "config" / "config.example.json"
    if example.is_file():
        orders["config.example.json"] = AppConfig.load(example).runtime.task_order

    for label, order in orders.items():
        missing = [t for t in order if t not in nodes]
        assert not missing, f"{label} 的 task_order 含不存在的任务节点：{missing}"
