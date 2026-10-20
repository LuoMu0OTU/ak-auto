"""多配置方案单元测试（Phase 7）。"""
from __future__ import annotations

from pathlib import Path

import pytest

from ak_auto.application.profiles import (
    apply_profile,
    delete_profile,
    list_profiles,
    load_profile,
    save_profile,
)
from ak_auto.config import AppConfig


def test_save_list_load_roundtrip(tmp_path: Path) -> None:
    cfg = AppConfig()
    cfg.fight.times = 7
    cfg.recruit.tag_priority = ["高级资深干员"]
    save_profile(cfg, "清体力", root=tmp_path)

    assert list_profiles(tmp_path) == ["清体力"]
    loaded = load_profile("清体力", root=tmp_path)
    assert loaded.fight.times == 7
    assert loaded.recruit.tag_priority == ["高级资深干员"]


def test_apply_profile_updates_in_place(tmp_path: Path) -> None:
    save_profile(AppConfig(), "默认", root=tmp_path)

    cfg = AppConfig()
    cfg.fight.times = 99
    save_profile(cfg, "刷图", root=tmp_path)

    target = AppConfig()  # times=0
    apply_profile(target, "刷图", root=tmp_path)
    assert target.fight.times == 99


def test_load_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_profile("不存在", root=tmp_path)


def test_delete_profile(tmp_path: Path) -> None:
    save_profile(AppConfig(), "A", root=tmp_path)
    assert delete_profile("A", root=tmp_path) is True
    assert delete_profile("A", root=tmp_path) is False
    assert list_profiles(tmp_path) == []


def test_sanitize_name(tmp_path: Path) -> None:
    save_profile(AppConfig(), "账号 A/../B", root=tmp_path)
    # 非法字符被过滤，不会产生路径穿越
    assert all("/" not in n and ".." not in n for n in list_profiles(tmp_path))
