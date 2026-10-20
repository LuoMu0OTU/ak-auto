"""更新检查逻辑单元测试（Phase 7）。"""
from __future__ import annotations

from ak_auto.application.updates import is_newer, parse_version


def test_parse_version_strips_v_and_pre() -> None:
    assert parse_version("v0.1.0") == (0, 1, 0)
    assert parse_version("0.1.0") == (0, 1, 0)
    assert parse_version("1.2.3-beta") == (1, 2, 3)
    assert parse_version("v10") == (10,)


def test_parse_version_invalid_falls_back_zero() -> None:
    assert parse_version("") == (0,)
    assert parse_version("abc") == (0,)


def test_is_newer_semver() -> None:
    assert is_newer("0.1.0", "0.1.1") is True
    assert is_newer("0.1.0", "0.2.0") is True
    assert is_newer("0.1.0", "1.0.0") is True
    assert is_newer("0.1.0", "0.1.0") is False
    assert is_newer("0.2.0", "0.1.9") is False


def test_is_newer_numeric_not_lexical() -> None:
    # 9 < 10：数值比较而非字典序（"0.1.9" vs "0.1.10"）
    assert is_newer("0.1.9", "0.1.10") is True


def test_check_latest_network_failure_returns_none() -> None:
    from ak_auto.application.updates import check_latest

    # 指向不可达地址 → 应返回 None 而不是抛异常
    info = check_latest("0.1.0", url="http://127.0.0.1:1/not-a-real-api", timeout=2.0)
    assert info is None
