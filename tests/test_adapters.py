"""基础设施适配器测试（Phase 1 任务 6）。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.config import AppConfig  # noqa: E402
from ak_auto.infrastructure import (  # noqa: E402
    AssetManager,
    GameWindowAdapter,
    MaaFrameworkAdapter,
    WindowNotFound,
)


# ---- AssetManager ----
def _make_ready_assets(root: Path) -> None:
    (root / "assets" / "resource" / "model" / "ocr").mkdir(parents=True, exist_ok=True)
    for f in ("det.onnx", "rec.onnx", "keys.txt"):
        (root / "assets" / "resource" / "model" / "ocr" / f).write_bytes(b"x")
    img = root / "assets" / "resource" / "image" / "t.png"
    img.parent.mkdir(parents=True, exist_ok=True)
    img.write_bytes(b"png")
    (root / "assets" / "MANIFEST.json").write_text("{}", encoding="utf-8")


def test_asset_manager_status_missing(tmp_path: Path) -> None:
    st = AssetManager(tmp_path).status()
    assert st["ready"] is False and st["manifest"] is False


def test_asset_manager_status_ready(tmp_path: Path) -> None:
    _make_ready_assets(tmp_path)
    am = AssetManager(tmp_path)
    assert am.ready is True


def test_asset_manager_ensure_shortcut_when_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_ready_assets(tmp_path)
    calls: list = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append(a))
    assert AssetManager(tmp_path).ensure() is True
    assert not calls  # 已就绪时不调 fetcher


def test_asset_manager_ensure_invokes_fetcher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list = []

    class _Done:
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append(a) or _Done())
    AssetManager(tmp_path).ensure(tag="v6.19.0")
    assert calls and "v6.19.0" in calls[0][0]


# ---- MaaFrameworkAdapter ----
def test_maa_adapter_task_entries() -> None:
    class _T:
        class resource:
            node_list = ["A", "B", "B"]

    ad = MaaFrameworkAdapter(AppConfig())
    assert ad.task_entries(_T()) == {"A", "B"}


# ---- GameWindowAdapter ----
def test_window_adapter_acquire_reuse_release(monkeypatch: pytest.MonkeyPatch) -> None:
    from ak_auto import device

    calls = {"connect": 0, "restore": 0}

    class _Ctrl:
        pass

    monkeypatch.setattr(device, "ensure_game_window", lambda cfg, on_log=None: {"hwnd": 123, "window_name": "x"})
    monkeypatch.setattr(
        device,
        "connect_controller",
        lambda *a, **k: (calls.__setitem__("connect", calls["connect"] + 1) or _Ctrl()),
    )
    monkeypatch.setattr(device, "restore_window", lambda hwnd: calls.__setitem__("restore", calls["restore"] + 1))

    ad = GameWindowAdapter(AppConfig())
    hwnd, ctrl = ad.acquire()
    assert hwnd == 123 and isinstance(ctrl, _Ctrl)
    assert calls["connect"] == 1

    hwnd2, ctrl2 = ad.acquire()  # 复用：同一时间只允许一个控制器
    assert ctrl2 is ctrl and calls["connect"] == 1

    ad.release()
    assert calls["restore"] == 1
    assert ad.acquired is False


def test_window_adapter_raises_when_no_window(monkeypatch: pytest.MonkeyPatch) -> None:
    from ak_auto import device

    monkeypatch.setattr(device, "ensure_game_window", lambda cfg, on_log=None: None)
    with pytest.raises(WindowNotFound):
        GameWindowAdapter(AppConfig()).acquire()
