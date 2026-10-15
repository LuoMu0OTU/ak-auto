"""配置服务测试（Phase 1 任务 5）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.application import ConfigurationService  # noqa: E402
from ak_auto.config import CONFIG_SCHEMA_VERSION, AppConfig  # noqa: E402


def test_load_missing_file_uses_defaults(tmp_path: Path) -> None:
    svc = ConfigurationService(tmp_path / "nope.json")
    cfg = svc.load()
    assert cfg.fight.stage == "CE-6" and cfg.schema_version == CONFIG_SCHEMA_VERSION
    assert svc.warning is None


def test_save_and_roundtrip(tmp_path: Path) -> None:
    svc = ConfigurationService(tmp_path / "c.json")
    cfg = AppConfig()
    cfg.fight.stage = "1-7"
    svc.save(cfg)

    text = (tmp_path / "c.json").read_text(encoding="utf-8")
    assert json.loads(text)["schema_version"] == CONFIG_SCHEMA_VERSION
    assert not (tmp_path / "c.json.tmp").exists()  # 原子写：不留临时文件

    loaded = svc.load()
    assert loaded.fight.stage == "1-7"
    assert loaded.schema_version == CONFIG_SCHEMA_VERSION


def test_save_backs_up_existing_file(tmp_path: Path) -> None:
    svc = ConfigurationService(tmp_path / "c.json")
    svc.save(AppConfig())  # 第一次写
    svc.save(AppConfig())  # 第二次写 → 应产生 pre-write 备份
    assert (tmp_path / "c.json.pre-write.bak").exists()


def test_corrupt_json_backup_and_defaults(tmp_path: Path) -> None:
    p = tmp_path / "c.json"
    p.write_text("{ 这不是 JSON", encoding="utf-8")
    svc = ConfigurationService(p)
    cfg = svc.load()
    assert cfg.fight.stage == "CE-6"  # 回退默认
    assert svc.warning is not None
    assert (tmp_path / "c.json.corrupt.bak").exists()  # 坏文件被备份，不丢用户数据


def test_non_object_json_backup_and_defaults(tmp_path: Path) -> None:
    p = tmp_path / "c.json"
    p.write_text("[1,2,3]", encoding="utf-8")
    svc = ConfigurationService(p)
    cfg = svc.load()
    assert cfg.fight.stage == "CE-6" and svc.warning is not None
    assert (tmp_path / "c.json.corrupt.bak").exists()


def test_migration_framework(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ak_auto.application import configsvc

    # 注册一个 0→1 的迁移：给 fight.times 打补丁
    monkeypatch.setitem(
        configsvc.MIGRATIONS,
        0,
        lambda d: {**d, "fight": {**d.get("fight", {}), "times": 99}},
    )
    p = tmp_path / "c.json"
    p.write_text('{"schema_version": 0}', encoding="utf-8")
    cfg = ConfigurationService(p).load()
    assert cfg.schema_version == CONFIG_SCHEMA_VERSION
    assert cfg.fight.times == 99


def test_partial_config_still_uses_defaults(tmp_path: Path) -> None:
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"schema_version": 1, "fight": {"stage": "1-7"}}), encoding="utf-8")
    cfg = ConfigurationService(p).load()
    assert cfg.fight.stage == "1-7"
    assert cfg.recruit.max_times == 4  # 未覆盖字段仍走默认


def test_v1_file_migrates_to_v2(tmp_path: Path) -> None:
    p = tmp_path / "c.json"
    p.write_text(
        json.dumps({"schema_version": 1, "fight": {"times": 5}, "runtime": {"retry_per_task": 1}}),
        encoding="utf-8",
    )
    cfg = ConfigurationService(p).load()
    assert cfg.schema_version == CONFIG_SCHEMA_VERSION == 2
    assert cfg.fight.times == 5  # 旧字段保留
    assert cfg.ui.mode == "simple" and cfg.ui.theme == "dark"  # v2 新字段有默认值
    assert cfg.custom_presets == []
    assert cfg.fight.min_sanity == 0


def test_ui_mode_validation(tmp_path: Path) -> None:
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"schema_version": 2, "ui": {"mode": "pro"}}), encoding="utf-8")
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ConfigurationService(p).load()


def test_custom_presets_roundtrip(tmp_path: Path) -> None:
    from ak_auto.config import PresetConfig

    svc = ConfigurationService(tmp_path / "c.json")
    cfg = svc.load()
    cfg.custom_presets = [
        PresetConfig(name="收菜+公招", task_ids=["Infrast", "Recruit"]),
        PresetConfig(name="深夜刷图", task_ids=["Fight"]),
    ]
    svc.save(cfg)
    loaded = svc.load()
    assert len(loaded.custom_presets) == 2
    assert loaded.custom_presets[0].name == "收菜+公招"
    assert loaded.custom_presets[0].task_ids == ["Infrast", "Recruit"]
