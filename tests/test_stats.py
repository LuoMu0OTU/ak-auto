"""运行统计聚合测试（Phase 5）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ak_auto.application.stats import run_stats  # noqa: E402


def _write(logs: Path) -> None:
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "run-1.json").write_text(
        json.dumps({
            "all_ok": True,
            "total_ms": 1000,
            "tasks": [
                {"entry": "StartUp", "ok": True, "duration_ms": 500},
                {"entry": "Infrast", "ok": True, "duration_ms": 1500},
            ],
        }),
        encoding="utf-8",
    )
    (logs / "run-2.json").write_text(
        json.dumps({
            "all_ok": False,
            "total_ms": 2000,
            "tasks": [
                {"entry": "StartUp", "ok": False, "duration_ms": 700},
                {"entry": "Fight", "ok": False, "duration_ms": 1300},
            ],
        }),
        encoding="utf-8",
    )


def test_run_stats_aggregates(tmp_path: Path) -> None:
    _write(tmp_path / "logs")
    st = run_stats(tmp_path / "logs")
    assert st["runs"] == 2
    assert st["ok_runs"] == 1
    assert st["all_ok_rate"] == 0.5
    assert st["total_ms"] == 3000
    assert st["tasks"]["StartUp"]["runs"] == 2
    assert st["tasks"]["StartUp"]["ok"] == 1
    assert st["tasks"]["StartUp"]["avg_ms"] == 600
    assert st["tasks"]["Fight"]["runs"] == 1
    assert st["tasks"]["Fight"]["ok"] == 0


def test_run_stats_empty(tmp_path: Path) -> None:
    st = run_stats(tmp_path / "no_such_dir")
    assert st["runs"] == 0 and st["all_ok_rate"] is None


def test_run_stats_limit(tmp_path: Path) -> None:
    _write(tmp_path / "logs")
    st = run_stats(tmp_path / "logs", limit=1)
    assert st["runs"] == 1
