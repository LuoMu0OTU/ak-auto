"""校验 assets/MANIFEST.json 与磁盘一致、来源与许可证字段齐全。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "assets" / "MANIFEST.json"
SOURCE_MAP = ROOT / "assets" / "resource" / "image" / "source-map.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="module")
def manifest() -> dict:
    if not MANIFEST.exists():
        pytest.skip("未生成 MANIFEST.json（先运行 fetch-assets）")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_schema(manifest: dict) -> None:
    assert manifest.get("schema_version") == 1
    src = manifest["source"]
    assert src["repo"] == "MaaAssistantArknights/MaaAssistantArknights"
    assert src["tag"].startswith("v")
    assert src["license"] == "AGPL-3.0"
    assert manifest["file_count"] == len(manifest["entries"])
    assert manifest["file_count"] > 1000  # 模板图数量级


def test_entries_on_disk_match(manifest: dict) -> None:
    for entry in manifest["entries"]:
        dst = ROOT / entry["dst"]
        assert dst.is_file(), f"缺失文件: {entry['dst']}"
        assert _sha256(dst) == entry["sha256"], f"哈希不一致: {entry['dst']}"


def test_ocr_models_present(manifest: dict) -> None:
    dsts = {e["dst"] for e in manifest["entries"]}
    assert "assets/resource/model/ocr/det.onnx" in dsts
    assert "assets/resource/model/ocr/rec.onnx" in dsts
    assert "assets/resource/model/ocr/keys.txt" in dsts


def test_data_tables_present(manifest: dict) -> None:
    dsts = {e["dst"] for e in manifest["entries"]}
    for name in ("stages.json", "recruitment.json", "infrast.json", "item_index.json"):
        assert f"assets/maa-vendor/{name}" in dsts, f"缺少数据表 {name}"


def test_source_map_present(manifest: dict) -> None:
    assert SOURCE_MAP.exists()
    sm = json.loads(SOURCE_MAP.read_text(encoding="utf-8"))
    assert sm["source"] == f"MaaAssistantArknights/MaaAssistantArknights@{manifest['source']['tag']}"
    assert len(sm["images"]) > 1000
