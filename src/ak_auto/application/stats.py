"""Application 层：运行统计（logs 聚合，Phase 5）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT


def run_stats(log_dir: Path | None = None, limit: int | None = 30) -> dict[str, Any]:
    """聚合 logs/run-*.json（新→旧，最多 limit 份）。

    返回 {runs, ok_runs, all_ok_rate, total_ms, tasks: {entry: {runs, ok, avg_ms}}}
    """
    logs = Path(log_dir) if log_dir else PROJECT_ROOT / "logs"
    files = sorted(logs.glob("run-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if limit:
        files = files[:limit]

    runs = 0
    ok_runs = 0
    total_ms = 0
    tasks: dict[str, dict[str, Any]] = {}
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        runs += 1
        if data.get("all_ok"):
            ok_runs += 1
        total_ms += data.get("total_ms", 0)
        for t in data.get("tasks", []):
            entry = t.get("entry") or "?"
            st = tasks.setdefault(entry, {"runs": 0, "ok": 0, "ms": 0})
            st["runs"] += 1
            if t.get("ok"):
                st["ok"] += 1
            st["ms"] += t.get("duration_ms", 0)
    for st in tasks.values():
        st["avg_ms"] = round(st["ms"] / st["runs"]) if st["runs"] else 0
    return {
        "runs": runs,
        "ok_runs": ok_runs,
        "all_ok_rate": round(ok_runs / runs, 3) if runs else None,
        "total_ms": total_ms,
        "tasks": tasks,
    }
