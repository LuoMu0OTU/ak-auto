"""launch_game 失败处理测试：启动失败必须干净报错，绝不把 OSError 抛给上层。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto import device  # noqa: E402
from ak_auto.config import AppConfig  # noqa: E402


def _cfg(tmp_path: Path) -> AppConfig:
    cfg = AppConfig()
    cfg.startup.game_path = str(tmp_path / "Arknights.exe")
    return cfg


def _exe(tmp_path: Path) -> Path:
    p = tmp_path / "Arknights.exe"
    p.write_bytes(b"x")
    return p


def test_missing_path_returns_false(tmp_path: Path) -> None:
    logs: list[str] = []
    assert device.launch_game(_cfg(tmp_path), on_log=logs.append) is False
    assert logs and "路径不存在" in logs[0]


def test_permission_error_returns_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _exe(tmp_path)
    logs: list[str] = []

    def _raise(*a, **k):
        raise PermissionError(740, "客户端要求管理员权限", "Arknights.exe")

    monkeypatch.setattr(subprocess, "Popen", _raise)
    assert device.launch_game(_cfg(tmp_path), on_log=logs.append) is False
    assert any("权限" in m for m in logs)  # 提示用户可尝试管理员运行


def test_oserror_returns_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _exe(tmp_path)
    logs: list[str] = []

    def _raise(*a, **k):
        raise OSError("拒绝访问")

    monkeypatch.setattr(subprocess, "Popen", _raise)
    assert device.launch_game(_cfg(tmp_path), on_log=logs.append) is False
    assert logs


def test_launch_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    exe = _exe(tmp_path)
    calls: list = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: calls.append(a))
    assert device.launch_game(_cfg(tmp_path), on_log=lambda m: None) is True
    assert calls and calls[0][0] == [str(exe)]
