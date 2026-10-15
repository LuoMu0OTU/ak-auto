"""Application 层：配置服务（Phase 1 任务 5）。

文件级保障：schema_version、原子写、写前备份、损坏恢复、迁移钩子。
模型校验复用 config.AppConfig（Pydantic，缺字段回退默认）。

用法：
    svc = ConfigurationService()          # 默认 config/config.json
    cfg = svc.load()                      # 损坏时自动备份并回退默认（svc.warning 提示）
    svc.save(cfg)                         # 原子写 + 备份旧文件
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Callable, Optional

from ..config import CONFIG_SCHEMA_VERSION, AppConfig, PROJECT_ROOT

# 版本号 → 迁移函数（dict -> dict，把该版本升级到下一版）
MIGRATIONS: dict[int, Callable[[dict], dict]] = {}


class ConfigurationService:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else PROJECT_ROOT / "config" / "config.json"
        self.warning: Optional[str] = None

    def load(self) -> AppConfig:
        """读取配置；文件缺失/损坏/格式错误时回退默认，并把坏文件备份（不丢用户数据）。"""
        self.warning = None
        if not self.path.exists():
            return AppConfig()

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001 —— 损坏恢复
            self.warning = f"配置文件无法解析（{e}），已备份为 .corrupt.bak 并回退默认配置。"
            self._backup("corrupt")
            return AppConfig()

        if not isinstance(data, dict):
            self.warning = "配置文件顶层不是对象，已备份为 .corrupt.bak 并回退默认配置。"
            self._backup("corrupt")
            return AppConfig()

        data = self._migrate(data)
        return AppConfig.model_validate(data)

    def save(self, cfg: AppConfig) -> Path:
        """原子写入（临时文件 + os.replace）+ 写前备份旧文件。"""
        cfg.schema_version = CONFIG_SCHEMA_VERSION
        text = json.dumps(cfg.model_dump(), ensure_ascii=False, indent=2) + "\n"
        if self.path.exists():
            self._backup("pre-write")
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self.path)
        return self.path

    def _backup(self, tag: str) -> Path:
        bak = self.path.with_name(self.path.name + f".{tag}.bak")
        try:
            shutil.copy2(self.path, bak)
        except OSError:
            pass
        return bak

    def _migrate(self, data: dict) -> dict:
        """按 schema_version 依次应用迁移函数（缺迁移函数时保持原样，交给校验层）。"""
        version = int(data.get("schema_version", 0))
        while version < CONFIG_SCHEMA_VERSION:
            fn = MIGRATIONS.get(version)
            if fn is None:
                break
            data = fn(data)
            version += 1
        data["schema_version"] = CONFIG_SCHEMA_VERSION
        return data
