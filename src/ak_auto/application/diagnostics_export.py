"""诊断包导出（Phase 7 / P2）：一键打包日志 + 脱敏配置 + 失败截图，方便反馈 bug。

安全：配置导出前脱敏（去掉个人路径）；只收集 logs/、debug/ 与 config.json，最小化收集。
"""
from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

_SENSITIVE_KEYS = ("game_path",)


def _redact(obj):
    """递归脱敏：把敏感键（个人路径等）替换为占位符。"""
    if isinstance(obj, dict):
        return {k: ("<redacted>" if k in _SENSITIVE_KEYS else _redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


def collect_files(root: Path) -> list[Path]:
    """收集要打包的文件（logs / debug 截图 / config.json），不存在的静默跳过。"""
    files: list[Path] = []
    for pattern in ("logs/run-*.json", "logs/*.log"):
        files.extend(sorted((root).glob(pattern)))
    debug = root / "debug"
    if debug.is_dir():
        files.extend(sorted(p for p in debug.rglob("*") if p.is_file()))
    cfg = root / "config" / "config.json"
    if cfg.is_file():
        files.append(cfg)
    return files


def _redacted_config_text(cfg: Path) -> str | None:
    """返回脱敏后的 config.json 文本（解析失败返回 None）。"""
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return json.dumps(_redact(data), ensure_ascii=False, indent=2) + "\n"


def export_diagnostics(root: Path, out_dir: Path | None = None, now: datetime | None = None) -> Path:
    """打包诊断文件为 zip；返回产物路径。失败时抛出（GUI/CLI 提示）。"""
    root = Path(root)
    out_dir = Path(out_dir) if out_dir else root / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    out = out_dir / f"ak-auto-diagnostic-{ts}.zip"

    files = collect_files(root)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            rel = f.relative_to(root).as_posix()
            if f.name == "config.json" and f.parent.name == "config":
                text = _redacted_config_text(f)
                if text is not None:
                    zf.writestr(rel, text)
                continue
            zf.write(f, rel)
    return out
