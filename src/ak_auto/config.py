"""配置模型与加载。

对应 `config/config.json`（模板见 `config/config.example.json`）。
所有字段都提供默认值，缺字段/旧配置也能安全加载。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent.parent


class WindowMatch(BaseModel):
    class_name: str = ""
    title_contains: str = "明日方舟"
    process_name: str = "Arknights"


class DeviceConfig(BaseModel):
    kind: str = "win32"
    window_match: WindowMatch = Field(default_factory=WindowMatch)
    screencap: list[str] = Field(
        default_factory=lambda: ["FramePool|PrintWindow", "DXGI_DesktopDup_Window|ScreenDC"]
    )
    mouse_input: list[str] = Field(
        default_factory=lambda: [
            "SendMessageWithCursorPos",
            "PostMessageWithCursorPos",
            "AnchoredTouch",
            "Seize",
        ]
    )
    keyboard_input: str = "PostMessage"
    inference: str = "directml"  # directml | cpu

    @field_validator("kind")
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in ("win32", "adb"):
            raise ValueError(f"device.kind 只能是 win32/adb，得到 {v!r}")
        return v


class StartupConfig(BaseModel):
    game_path: str = r"E:\Arknights\Arknights.exe"
    launch: bool = True


class FightConfig(BaseModel):
    stage: str = "CE-6"
    times: int = 0          # 0 = 直到理智耗尽
    medicine: int = 0       # 用药数量
    stone: int = 0          # 碎源石数量（默认关闭）
    series: bool = True     # 连续作战


class InfrastConfig(BaseModel):
    collect: bool = True
    shift_presets: list[str] = Field(default_factory=list)
    morale_threshold: float = 0.3


class RecruitConfig(BaseModel):
    max_times: int = 4
    ensure_4star: bool = True
    time_hours: int = 9
    expedite: bool = False


class MallConfig(BaseModel):
    buy_first: list[str] = Field(default_factory=lambda: ["招聘许可", "寻访凭证"])
    blacklist: list[str] = Field(default_factory=lambda: ["家具零件"])


class AwardConfig(BaseModel):
    daily: bool = True
    weekly: bool = True
    mail: bool = True
    signin: bool = True


class RuntimeConfig(BaseModel):
    task_order: list[str] = Field(
        default_factory=lambda: [
            "StartUp", "AwardVisit", "Infrast", "Mall", "Recruit", "Fight",
            "Award", "AwardMail", "AwardSignIn", "CloseDown",
        ]
    )
    retry_per_task: int = 2
    screenshot_on_error: bool = True


class AppConfig(BaseModel):
    device: DeviceConfig = Field(default_factory=DeviceConfig)
    startup: StartupConfig = Field(default_factory=StartupConfig)
    fight: FightConfig = Field(default_factory=FightConfig)
    infrast: InfrastConfig = Field(default_factory=InfrastConfig)
    recruit: RecruitConfig = Field(default_factory=RecruitConfig)
    mall: MallConfig = Field(default_factory=MallConfig)
    award: AwardConfig = Field(default_factory=AwardConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "AppConfig":
        """从 JSON 加载；文件不存在/字段缺失时回退到默认值。"""
        p = Path(path) if path else PROJECT_ROOT / "config" / "config.json"
        data: dict[str, Any] = {}
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def dump(self, path: str | Path | None = None) -> Path:
        p = Path(path) if path else PROJECT_ROOT / "config" / "config.json"
        p.write_text(
            json.dumps(self.model_dump(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return p


def default_config_path() -> Path:
    return PROJECT_ROOT / "config" / "config.json"
