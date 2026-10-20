"""诊断包导出单元测试（Phase 7）。"""
from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path

from ak_auto.application.diagnostics_export import collect_files, export_diagnostics


def _make_root(tmp: Path) -> Path:
    logs = tmp / "logs"
    logs.mkdir(parents=True)
    (logs / "run-1.json").write_text('{"all_ok": true}', encoding="utf-8")
    (logs / "console.log").write_text("hello", encoding="utf-8")
    cfg = tmp / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.json").write_text(
        json.dumps({"startup": {"game_path": r"C:\Users\me\Arknights.exe", "medicine": 0}}),
        encoding="utf-8",
    )
    shots = tmp / "debug"
    shots.mkdir(parents=True, exist_ok=True)
    (shots / "shots" / "fail.png").parent.mkdir(parents=True, exist_ok=True)
    (shots / "shots" / "fail.png").write_bytes(b"png")
    return tmp


def test_collect_files() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = _make_root(Path(td))
        files = collect_files(root)
        rels = {f.relative_to(root).as_posix() for f in files}
        assert "logs/run-1.json" in rels
        assert "logs/console.log" in rels
        assert "config/config.json" in rels
        assert "debug/shots/fail.png" in rels


def test_export_redacts_game_path() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = _make_root(Path(td))
        out = export_diagnostics(root, now=datetime(2026, 10, 20, 12, 0, 0))
        assert out.name == "ak-auto-diagnostic-20261020-120000.zip"
        with zipfile.ZipFile(out) as zf:
            names = set(zf.namelist())
            assert "config/config.json" in names
            text = zf.read("config/config.json").decode("utf-8")
            assert r"C:\Users\me" not in text
            assert "<redacted>" in text
            assert "debug/shots/fail.png" in names


def test_export_writes_into_out_dir() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = _make_root(Path(td))
        outdir = Path(td) / "out"
        out = export_diagnostics(root, out_dir=outdir)
        assert out.parent == outdir
        assert out.exists()
