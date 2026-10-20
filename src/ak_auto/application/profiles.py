"""多配置方案（Phase 7 / P2）：把当前配置保存为命名方案、载入/删除。

方案 = `config/profiles/<name>.json` 的快照；当前生效配置仍是 `config/config.json`。
载入方案会覆盖当前配置（下次启动/立即刷新生效）。
"""
from __future__ import annotations

import json
from pathlib import Path

from ..config import AppConfig, PROJECT_ROOT

PROFILES_DIR = PROJECT_ROOT / "config" / "profiles"


def _profiles_dir(root: Path | None = None) -> Path:
    return (Path(root) if root else PROJECT_ROOT) / "config" / "profiles"


def _sanitize(name: str) -> str:
    """方案名 → 安全文件名（只保留字母数字下划线横线，去路径分隔符）。"""
    return "".join(c for c in name.strip() if c.isalnum() or c in "_-") or "unnamed"


def list_profiles(root: Path | None = None) -> list[str]:
    d = _profiles_dir(root)
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def save_profile(cfg: AppConfig, name: str, root: Path | None = None) -> Path:
    """把当前配置保存为命名方案；返回方案文件路径。"""
    d = _profiles_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{_sanitize(name)}.json"
    p.write_text(json.dumps(cfg.model_dump(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def load_profile(name: str, root: Path | None = None) -> AppConfig:
    """读取命名方案为 AppConfig（不存在抛 FileNotFoundError）。"""
    p = _profiles_dir(root) / f"{_sanitize(name)}.json"
    if not p.is_file():
        raise FileNotFoundError(f"方案不存在：{name}")
    return AppConfig.model_validate(json.loads(p.read_text(encoding="utf-8")))


def delete_profile(name: str, root: Path | None = None) -> bool:
    """删除命名方案；返回是否真的删除了。"""
    p = _profiles_dir(root) / f"{_sanitize(name)}.json"
    if not p.is_file():
        return False
    p.unlink()
    return True


def apply_profile(cfg: AppConfig, name: str, root: Path | None = None) -> AppConfig:
    """把命名方案应用到当前 cfg（原地更新字段）；返回 cfg。"""
    loaded = load_profile(name, root)
    for key, value in loaded.__dict__.items():
        setattr(cfg, key, value)
    return cfg
