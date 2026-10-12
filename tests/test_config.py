"""配置模型测试。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ak_auto.config import AppConfig


def test_defaults() -> None:
    cfg = AppConfig()
    assert cfg.device.kind == "win32"
    assert cfg.runtime.task_order[0] == "StartUp"
    assert cfg.recruit.ensure_4star is True
    assert cfg.fight.medicine == 0 and cfg.fight.stone == 0


def test_load_missing_file_uses_defaults() -> None:
    cfg = AppConfig.load(Path("/nonexistent/does/not/exist.json"))
    assert cfg.fight.stage == "CE-6"
    assert cfg.award.daily is True


def test_load_partial_overrides(tmp_path: Path) -> None:
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"fight": {"stage": "1-7", "times": 5}}), encoding="utf-8")
    cfg = AppConfig.load(p)
    assert cfg.fight.stage == "1-7"
    assert cfg.fight.times == 5
    # 未覆盖的字段仍走默认
    assert cfg.recruit.max_times == 4


def test_invalid_kind_raises() -> None:
    with pytest.raises(ValidationError):
        AppConfig.model_validate({"device": {"kind": "foo"}})


def test_roundtrip(tmp_path: Path) -> None:
    cfg = AppConfig()
    p = cfg.dump(tmp_path / "dump.json")
    cfg2 = AppConfig.load(p)
    assert cfg2 == cfg
