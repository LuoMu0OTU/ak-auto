"""设备层：窗口探测 + Win32 控制器构建 + 截图/输入方式自检。

依赖 MaaFw 的 `maa.controller.Win32Controller` 与 `maa.toolkit.Toolkit`。
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image

from maa.controller import Win32Controller
from maa.define import (
    MaaWin32InputMethodEnum as Input,
    MaaWin32ScreencapMethodEnum as Screencap,
)
from maa.toolkit import Toolkit

from .config import AppConfig, PROJECT_ROOT

# 截图组合别名（可整体引用）
SCREEN_ALIASES: dict[str, int] = {
    "Background": int(Screencap.Background),
    "Foreground": int(Screencap.Foreground),
    "All": int(Screencap.All),
}

# 单个输入方式（MaaFw 要求单选，不做按位或）
INPUT_NAMES = [
    "Seize", "SendMessage", "PostMessage", "LegacyEvent", "PostThreadMessage",
    "SendMessageWithCursorPos", "PostMessageWithCursorPos",
    "SendMessageWithWindowPos", "PostMessageWithWindowPos",
    "Interception", "AnchoredTouch",
]


def init_maa(user_path: str | Path | None = None) -> bool:
    """初始化 MaaFw 工具集（日志 / 识别可视化 / 失败截图开关）。"""
    return bool(Toolkit.init_option(
        str(user_path or PROJECT_ROOT),
        {
            "logging": True,
            "save_draw": True,
            "stdout_level": 2,
            "save_on_error": True,
            "draw_quality": 85,
        },
    ))


def list_windows() -> list[dict[str, Any]]:
    """枚举桌面窗口（hwnd 为 int，便于序列化）。"""
    out: list[dict[str, Any]] = []
    for w in Toolkit.find_desktop_windows():
        out.append({
            "hwnd": int(w.hwnd) if w.hwnd else None,
            "class_name": w.class_name,
            "window_name": w.window_name,
        })
    return out


def _process_pid_by_name(name: str) -> Optional[int]:
    """用 Toolhelp 快照按进程名（不含 .exe）查 PID。"""
    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1:
        return None
    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
    pid: Optional[int] = None
    try:
        if kernel32.Process32First(snap, ctypes.byref(entry)):
            while True:
                exe = entry.szExeFile.decode("gbk", "ignore").lower()
                if exe == name.lower() or exe == f"{name.lower()}.exe":
                    pid = int(entry.th32ProcessID)
                    break
                if not kernel32.Process32Next(snap, ctypes.byref(entry)):
                    break
    finally:
        kernel32.CloseHandle(snap)
    return pid


def _window_pid(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def find_game_window(cfg: AppConfig) -> Optional[dict[str, Any]]:
    """按优先级匹配游戏窗口。

    配置了 process_name 时：只按进程匹配（权威），进程不在或找不到窗口就返回 None，
    绝不回退到标题，避免命中标题里同样含“明日方舟”的浏览器/聊天窗口。
    未配置 process_name 时：精确标题 > 标题包含 > 窗口类名。
    """
    wm = cfg.device.window_match
    windows = list(Toolkit.find_desktop_windows())

    def to_dict(w: Any) -> dict[str, Any]:
        return {
            "hwnd": int(w.hwnd) if w.hwnd else None,
            "class_name": w.class_name,
            "window_name": w.window_name,
        }

    # 1) 进程名精确匹配（权威，配置了就不回退到标题）
    if wm.process_name:
        pid = _process_pid_by_name(wm.process_name)
        if pid is None:
            return None  # 进程未运行
        titled = [w for w in windows if w.hwnd and _window_pid(int(w.hwnd)) == pid]
        for w in titled:
            if w.window_name.strip():
                return to_dict(w)
        return to_dict(titled[0]) if titled else None

    # 2) 精确标题
    if wm.title_contains:
        for w in windows:
            if w.window_name == wm.title_contains:
                return to_dict(w)

    # 3) 标题包含
    if wm.title_contains:
        for w in windows:
            if wm.title_contains in w.window_name:
                return to_dict(w)

    # 4) 窗口类名包含
    if wm.class_name:
        for w in windows:
            if wm.class_name in w.class_name:
                return to_dict(w)

    return None


def launch_game(cfg: AppConfig, on_log: Any = None) -> bool:
    """按 config.startup.game_path 拉起游戏客户端（仅启动，不等待）。

    失败（路径无效 / 需管理员权限 / 被安全软件拦截等）时播报具体原因并返回 False，
    绝不把 OSError 抛给上层（用户看到的是干净提示，不是 traceback）。
    """
    import os
    import subprocess

    def log(msg: str) -> None:
        if on_log:
            on_log(msg)

    path = cfg.startup.game_path
    if not path or not os.path.isfile(path):
        log(f"启动失败：游戏路径不存在或不是文件：{path!r}")
        return False
    try:
        subprocess.Popen([path], cwd=os.path.dirname(path) or None)
    except PermissionError as e:
        # 常见：ERROR_ELEVATION_REQUIRED (740)，游戏需要管理员权限
        log(f"启动失败：权限不足（{e}）。可尝试：以管理员身份运行本程序，或先手动打开游戏再运行。")
        return False
    except OSError as e:
        log(f"启动失败：{e}。请确认游戏未在运行、路径正确，或先手动打开游戏再运行。")
        return False
    return True


def wait_game_window(
    cfg: AppConfig,
    timeout: float = 180.0,
    interval: float = 3.0,
) -> Optional[dict[str, Any]]:
    """轮询等待游戏窗口出现（默认最长 3 分钟）。"""
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        win = find_game_window(cfg)
        if win:
            return win
        time.sleep(interval)
    return None


def ensure_game_window(
    cfg: AppConfig,
    on_log: Any = None,
    timeout: float = 180.0,
) -> Optional[dict[str, Any]]:
    """拿到游戏窗口；没有就（在允许时）自动启动游戏并等它出现。

    on_log 可传入一个 str -> None 的回调，用于向用户播报进度。
    """
    def log(msg: str) -> None:
        if on_log:
            on_log(msg)

    win = find_game_window(cfg)
    if win:
        return win

    if not cfg.startup.launch:
        log("游戏未运行，且 config 里 startup.launch = false，不自动启动。")
        return None

    if not launch_game(cfg, on_log=on_log):
        log(f"游戏未运行且自动启动失败（startup.game_path = {cfg.startup.game_path!r}）。请手动打开游戏后重试。")
        return None

    log("游戏未运行，已拉起客户端，等待窗口出现（最长 %.0f 秒）..." % timeout)
    win = wait_game_window(cfg, timeout=timeout)
    if not win:
        log("等待超时，仍未找到游戏窗口。")
    return win


def parse_screencap(spec: str) -> int:
    """把 "FramePool|PrintWindow" / "Background" 解析为按位或的截图方式。"""
    val = 0
    for tok in spec.split("|"):
        tok = tok.strip()
        if tok in SCREEN_ALIASES:
            val |= SCREEN_ALIASES[tok]
        elif hasattr(Screencap, tok):
            val |= int(getattr(Screencap, tok))
        else:
            raise ValueError(f"未知截图方式: {tok!r}（可选: {list(SCREEN_ALIASES) + [m.name for m in Screencap if m.name not in ('Null','All','Foreground','Background')]}）")
    if val == 0:
        raise ValueError("截图方式为空")
    return val


def parse_input(name: str) -> int:
    """把输入方式名解析为枚举值（单选）。"""
    name = name.strip()
    if not hasattr(Input, name):
        raise ValueError(f"未知输入方式: {name!r}（可选: {INPUT_NAMES}）")
    return int(getattr(Input, name))


def connect_controller(hwnd: Any, screencap: int, mouse: int, keyboard: int) -> Win32Controller:
    """构建并连接 Win32 控制器；失败抛异常。"""
    ctrl = Win32Controller(hwnd, screencap, mouse, keyboard)
    ctrl.post_connection().wait()
    if not ctrl.connected:
        raise RuntimeError("控制器连接失败（窗口句柄无效或权限不足）")
    return ctrl


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def client_to_screen(hwnd: Any, x: int, y: int) -> tuple[int, int]:
    """把窗口客户区坐标换算成屏幕坐标。"""
    user32 = ctypes.windll.user32
    rect = _RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    origin = _POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(origin))
    cw = rect.right - rect.left or 1
    ch = rect.bottom - rect.top or 1
    return origin.x + int(x * cw / 1280), origin.y + int(y * ch / 720)


def native_wheel(hwnd: Any, x: int, y: int, notches: int, gap: float = 0.06) -> None:
    """在窗口客户区 (x, y) 处发真实鼠标滚轮（正数向上）。

    部分游戏（如明日方舟 PC 端）不响应 MaaFw 的 SendMessage/PostMessage 滚轮，
    必须移动真实光标 + 硬件滚轮事件才生效。
    """
    import time

    user32 = ctypes.windll.user32
    sx, sy = client_to_screen(hwnd, x, y)
    user32.SetCursorPos(sx, sy)
    time.sleep(0.15)
    step = 120 if notches > 0 else -120
    for _ in range(abs(notches)):
        user32.mouse_event(0x0800, 0, 0, step, 0)  # MOUSEEVENTF_WHEEL
        time.sleep(gap)


def bright_rows(
    img: np.ndarray,
    x0: int = 992,
    x1: int = 1020,
    y0: int = 170,
    y1: int = 620,
    threshold: int = 200,
) -> list[tuple[int, int]]:
    """扫描一列，返回 (y中心, 峰值亮度) 的亮行列表（用于判断「白色数字」）。"""
    rows: list[tuple[int, int]] = []
    y = y0
    while y < y1:
        band = img[max(0, y - 8): y + 8, x0:x1]
        if band.size and band.mean(axis=2).max() >= threshold:
            rows.append((y, int(band.mean(axis=2).max())))
            y += 20
        else:
            y += 4
    return rows


def restore_window(hwnd: Any) -> bool:
    """把被 MaaFw 伪最小化的窗口还原（挪回屏幕 + 取消最小化）。

    MaaFw 的 Win32 控制器在运行期间会把游戏窗口移到屏幕外并最小化，
    正常 destroy 时会还原；但进程被强杀就会卡在最小化状态，必须手动救。
    """
    import time

    if not hwnd:
        return False
    user32 = ctypes.windll.user32
    try:
        if user32.IsIconic(hwnd):
            user32.SendMessageW(hwnd, 0x0112, 0xF120, 0)  # WM_SYSCOMMAND / SC_RESTORE
            time.sleep(0.3)
        rect = _RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if rect.left < -10000:  # 被挪到屏幕外
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetWindowPos(hwnd, 0, 409, 0, 1295, 757, 0x0040)  # SWP_SHOWWINDOW
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:  # noqa: BLE001
        return False


def capture(ctrl: Win32Controller) -> np.ndarray:
    """抓取一帧；空图抛异常。"""
    img = ctrl.post_screencap().wait().get()
    if img is None or getattr(img, "size", 0) == 0:
        raise RuntimeError("截图失败（空图像）")
    return img


def recover_capture(ctrl: Win32Controller, attempts: int = 4) -> bool:
    """恢复截图链路（通用「截图自愈前置」，Phase 7）。

    游戏战斗的独占渲染会把桌面复制（DXGI）打进 ACCESS_LOST / 窗口失效（-32000）状态；
    还原窗口 + 主动截一张图即可自愈。每个任务执行前调用，避免战斗后连锁失败。
    """
    import time

    hwnd = (ctrl.info or {}).get("hwnd")
    for attempt in range(attempts):
        try:
            img = ctrl.post_screencap().wait().get()
            if img is not None and getattr(img, "size", 0):
                return True
        except Exception:  # noqa: BLE001
            pass
        if hwnd:
            restore_window(hwnd)
        time.sleep(2.0)
    return False


def save_image(img: np.ndarray, path: str | Path) -> Path:
    """保存截图（3 通道 BGR → RGB）。"""
    arr = img
    if arr.ndim == 3 and arr.shape[2] == 3:
        arr = arr[..., ::-1]
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr.astype("uint8")).save(p)
    return p


@dataclass
class ProbeResult:
    hwnd: int
    class_name: str
    window_name: str
    screencap: str
    mouse: str
    keyboard: str
    shape: tuple[int, ...]
    saved: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "hwnd": self.hwnd, "class_name": self.class_name, "window_name": self.window_name,
            "screencap": self.screencap, "mouse": self.mouse, "keyboard": self.keyboard,
            "shape": list(self.shape), "saved": self.saved,
        }


def probe_best(
    cfg: AppConfig,
    window: dict[str, Any],
    save_dir: str | Path | None = None,
    verbose: bool = True,
) -> ProbeResult:
    """按配置的截图优先级逐项试连 + 抓帧，返回第一个可用组合。"""
    hwnd = window["hwnd"]
    mouse_name = cfg.device.mouse_input[0] if cfg.device.mouse_input else "Seize"
    kb_name = cfg.device.keyboard_input
    last_err: Exception | None = None
    for spec in cfg.device.screencap:
        try:
            sc = parse_screencap(spec)
            mouse = parse_input(mouse_name)
            kb = parse_input(kb_name)
            ctrl = connect_controller(hwnd, sc, mouse, kb)
            img = capture(ctrl)
            saved = None
            if save_dir:
                saved = str(save_image(img, Path(save_dir) / f"shot_{spec.replace('|', '_')}.png"))
            if verbose:
                print(f"[probe] 截图方式 {spec!r} 可用，帧尺寸 {img.shape}")
            return ProbeResult(int(hwnd), window["class_name"], window["window_name"],
                               spec, mouse_name, kb_name, tuple(img.shape), saved)
        except Exception as e:  # noqa: BLE001
            last_err = e
            if verbose:
                print(f"[probe] 截图方式 {spec!r} 失败：{e}")
    raise RuntimeError(f"所有截图组合均失败，最后错误：{last_err}")
