"""运行报告：控制台表格 + logs/run-*.json。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import PROJECT_ROOT
from .scheduler import TaskResult


@dataclass
class RunReport:
    started_at: str
    tasks: list[TaskResult] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return bool(self.tasks) and all(t.ok for t in self.tasks)

    @property
    def total_ms(self) -> int:
        return sum(t.duration_ms for t in self.tasks)

    def render(self) -> str:
        lines = [f"运行报告（{self.started_at}）", "-" * 56]
        for t in self.tasks:
            lines.append(t.summary)
        lines.append("-" * 56)
        lines.append(f"共 {len(self.tasks)} 项，{'全部成功' if self.all_ok else '存在失败'}，总耗时 {self.total_ms / 1000:.1f}s")
        return "\n".join(lines)

    def save(self, path: str | Path | None = None) -> Path:
        p = Path(path) if path else PROJECT_ROOT / "logs" / f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "started_at": self.started_at,
            "all_ok": self.all_ok,
            "total_ms": self.total_ms,
            "tasks": [
                {
                    "entry": t.entry,
                    "ok": t.ok,
                    "status": t.status,
                    "run_id": getattr(t, "run_id", ""),
                    "error": getattr(t, "error", ""),
                    "duration_ms": t.duration_ms,
                    "nodes": t.nodes,
                }
                for t in self.tasks
            ],
        }
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return p


def make_report(tasks: list[TaskResult]) -> RunReport:
    return RunReport(started_at=datetime.now().isoformat(timespec="seconds"), tasks=tasks)
