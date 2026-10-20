"""更新检查（Phase 7 / P2）：查询 GitHub Releases 是否有新版本。

- 纯标准库（urllib），GUI 与 CLI 共用；
- 只做「检查 + 提示」，不自动下载/安装（自动升级另行评估，标记计划中）。
"""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from typing import Optional

REPO = "LuoMu0OTU/ak-auto"
UA = {"User-Agent": "ak-auto/update-check"}
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"


@dataclass
class UpdateInfo:
    current: str
    latest: str
    url: str
    published_at: str = ""

    @property
    def is_newer(self) -> bool:
        return is_newer(self.current, self.latest)


def parse_version(v: str) -> tuple[int, ...]:
    """把 'v0.1.0' / '0.1.0' / '1.2.3-beta' 解析为数字元组，非数字段忽略。"""
    v = (v or "").strip().lstrip("vV")
    m = re.match(r"(\d+(?:\.\d+)*)", v)
    if not m:
        return (0,)
    try:
        return tuple(int(x) for x in m.group(1).split("."))
    except ValueError:
        return (0,)


def is_newer(current: str, latest: str) -> bool:
    """latest 是否严格大于 current（按语义化版本的数值段比较）。"""
    return parse_version(latest) > parse_version(current)


def check_latest(
    current: str,
    repo: str = REPO,
    timeout: float = 8.0,
    url: Optional[str] = None,
) -> Optional[UpdateInfo]:
    """查询最新 release；失败（网络/解析）返回 None，绝不抛异常。"""
    api = url or f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        req = urllib.request.Request(api, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except Exception:
        return None
    latest = str(data.get("tag_name") or data.get("name") or "").strip()
    html = str(data.get("html_url") or "")
    published = str(data.get("published_at") or "")
    if not latest:
        return None
    return UpdateInfo(
        current=current,
        latest=latest,
        url=html,
        published_at=published,
    )
