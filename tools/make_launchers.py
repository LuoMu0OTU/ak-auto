"""生成 Windows 一键启动脚本（GBK 编码，中文控制台可直接显示）。

用法：
    python tools/make_launchers.py

会在仓库根目录生成：
    首次安装.bat    首次安装 / 环境准备
    启动日常.bat    前台运行日常全家桶（可见窗口）
    静默日常.bat    后台运行日常（不显示窗口）

说明：批处理文件必须用系统 ANSI 代码页（简体中文 = GBK/cp936）保存，
否则 cmd 会按 936 解析 UTF-8 字节，中文乱码甚至把半行当命令执行。
"""
from __future__ import annotations

import pathlib

SETUP = """@echo off
chcp 936 >nul
cd /d "%~dp0"
title ak-auto 首次安装
set PYTHONIOENCODING=gbk

echo ============================================================
echo   ak-auto   首次安装 / 环境准备
echo ============================================================
echo.

set "PYCMD="
py -3.12 -c "import sys" >nul 2>nul && set "PYCMD=py -3.12"
if not defined PYCMD (
    py -3 -c "import sys; assert sys.version_info[:2]==(3,12)" >nul 2>nul && set "PYCMD=py -3"
)
if not defined PYCMD (
    echo [错误] 没找到 Python 3.12。
    echo        请到 python.org 下载安装 Python 3.12，
    echo        安装时务必勾选 "Add python.exe to PATH"。
    echo.
    pause
    exit /b 1
)
echo [环境] 使用 %PYCMD%
echo.

if not exist ".venv\\Scripts\\python.exe" (
    echo [1/5] 创建虚拟环境 .venv ...
    %PYCMD% -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败。
        pause
        exit /b 1
    )
) else (
    echo [1/5] 虚拟环境已存在，跳过创建
)

set "VPY=.venv\\Scripts\\python.exe"

echo [2/5] 升级 pip ...
"%VPY%" -m pip install -U pip -q

echo [3/5] 安装依赖（首次需几分钟）...
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络。
    pause
    exit /b 1
)
"%VPY%" -m pip install -e .
if errorlevel 1 (
    echo [错误] 安装本项目包失败。
    pause
    exit /b 1
)

if not exist "config\\config.json" (
    copy "config\\config.example.json" "config\\config.json" >nul
    echo [4/5] 已生成 config\\config.json
    echo       ^>^> 请打开它确认 startup.game_path 是你的游戏路径！
) else (
    echo [4/5] config\\config.json 已存在，跳过
)

echo [5/5] 拉取 MAA 识别素材（需要联网，几十 MB）...
"%VPY%" -m ak_auto fetch-assets --tag v6.19.0
if errorlevel 1 (
    echo [警告] 素材拉取失败，可稍后重跑本脚本。
)

echo.
echo ============================================================
echo   安装完成！
echo.
echo   下一步：
echo     1) 确认游戏窗口化为 1280x720，游戏内 UI 缩放为 100%%
echo     2) 打开 config\\config.json 检查游戏路径
echo     3) 双击「启动日常.bat」开跑
echo ============================================================
echo.
echo 正在做一次环境自检 ...
"%VPY%" -m ak_auto doctor
echo.
pause
"""

RUN = """@echo off
chcp 936 >nul
cd /d "%~dp0"
title ak-auto 日常
set PYTHONIOENCODING=gbk

if not exist ".venv\\Scripts\\python.exe" (
    echo [错误] 还没安装。请先双击运行「首次安装.bat」。
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo   ak-auto   日常全家桶
echo ============================================================
echo   顺序: 好友访问 -^> 基建收菜 -^> 采购 -^> 公招 -^> 刷图 -^> 领奖
echo   按 Ctrl+C 可随时中断
echo ------------------------------------------------------------
echo.

".venv\\Scripts\\python.exe" -m ak_auto daily
set "RC=%ERRORLEVEL%"

echo.
echo ------------------------------------------------------------
if "%RC%"=="0" (
    echo   全部完成。
) else (
    echo   结束，但有任务未成功（返回码 %RC%）。详情见 logs\\ 与 debug\\ 目录。
)
echo   日志: logs\\     失败截图: debug\\
echo ============================================================
echo.
pause
"""

QUIET = """@echo off
chcp 936 >nul
cd /d "%~dp0"
rem 输出走文件，用 UTF-8 写日志更好看；控制台本身是 936。
set PYTHONIOENCODING=utf-8

if not exist ".venv\\Scripts\\python.exe" (
    echo [错误] 还没安装。请先双击运行「首次安装.bat」。
    echo.
    pause
    exit /b 1
)
if not exist "logs" mkdir logs

echo 已在后台开始运行日常（最小化窗口，跑完自动关闭）。
echo 进度请看 logs\\daily.log
start "ak-auto 日常" /min cmd /c ".venv\\Scripts\\python.exe -m ak_auto daily > logs\\daily.log 2>&1"
timeout /t 3 >nul
exit
"""

FILES = {"首次安装.bat": SETUP, "启动日常.bat": RUN, "静默日常.bat": QUIET}


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent.parent
    for name, text in FILES.items():
        norm = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
        out = root / name
        out.write_bytes(norm.encode("gbk"))
        print(f"{name}  {out.stat().st_size} B  (GBK/CRLF)")


if __name__ == "__main__":
    main()
