"""资源包加载集成测试（需要先 fetch-assets）。"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "assets" / "MANIFEST.json"


@pytest.fixture(scope="module")
def resource():
    if not MANIFEST.exists():
        pytest.skip("未生成资源（先运行 fetch-assets）")
    from maa.resource import Resource

    res = Resource()
    res.post_bundle(str(ROOT / "assets" / "resource")).wait()
    return res


def test_bundle_loads(resource) -> None:
    assert resource.loaded is True


def test_ocr_and_pipeline_nodes(resource) -> None:
    nodes = set(resource.node_list)
    assert "StartUp" in nodes
    assert "ReturnToHome" in nodes
