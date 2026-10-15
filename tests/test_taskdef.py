"""任务定义目录测试（Phase 1 任务 1）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.domain import all_tasks, resolve_task  # noqa: E402


def test_catalog_complete_and_unique() -> None:
    tasks = all_tasks()
    assert len(tasks) == 10
    ids = [t.id for t in tasks]
    assert len(ids) == len(set(ids)), "任务 ID 必须唯一"
    for t in tasks:
        assert t.id and t.name and t.category
        assert t.entry, f"{t.id} 缺少执行入口"
        assert t.risk_level in ("low", "medium", "high"), f"{t.id} 风险等级非法"


def test_required_tasks_present() -> None:
    ids = {t.id for t in all_tasks()}
    for required in (
        "StartUp", "ReturnToHome", "AwardVisit", "Infrast", "Mall",
        "Recruit", "Fight", "Award", "AwardMail", "AwardSignIn",
    ):
        assert required in ids, f"缺少任务定义 {required}"


def test_resolve_by_id_and_name() -> None:
    assert resolve_task("Recruit").id == "Recruit"
    assert resolve_task("公开招募").id == "Recruit"
    assert resolve_task("recruit").id == "Recruit"
    assert resolve_task("  自动刷图  ").id == "Fight"
    assert resolve_task("") is None
    assert resolve_task("不存在任务") is None


def test_fight_safety_defaults() -> None:
    fight = resolve_task("Fight")
    assert fight is not None and fight.risk_level == "high"
    p = {x.key: x.default for x in fight.params}
    assert p["medicine"] == 0 and p["stone"] == 0  # 付费资源默认关闭


def test_default_task_order_in_catalog() -> None:
    from ak_auto.config import RuntimeConfig

    ids = {t.id for t in all_tasks()}
    for entry in RuntimeConfig().task_order:
        assert entry in ids, f"默认 task_order 里的 {entry} 不在任务目录中"


def test_catalog_entries_exist_in_pipeline() -> None:
    """目录里的执行入口必须真实存在于流水线。"""
    from ak_auto.config import PROJECT_ROOT

    manifest = PROJECT_ROOT / "assets" / "MANIFEST.json"
    if not manifest.exists():
        pytest.skip("未生成识别资源（先运行 fetch-assets）")

    from maa.resource import Resource

    res = Resource()
    res.post_bundle(str(PROJECT_ROOT / "assets" / "resource")).wait()
    nodes = set(res.node_list)
    missing = [t.id for t in all_tasks() if (t.entry or t.id) not in nodes]
    assert not missing, f"任务目录里的入口在流水线中不存在：{missing}"
