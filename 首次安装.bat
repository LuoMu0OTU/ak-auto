@echo off
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

if not exist ".venv\Scripts\python.exe" (
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

set "VPY=.venv\Scripts\python.exe"

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

if not exist "config\config.json" (
    copy "config\config.example.json" "config\config.json" >nul
    echo [4/5] 已生成 config\config.json
    echo       ^>^> 请打开它确认 startup.game_path 是你的游戏路径！
) else (
    echo [4/5] config\config.json 已存在，跳过
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
echo     2) 打开 config\config.json 检查游戏路径
echo     3) 双击「启动日常.bat」开跑
echo ============================================================
echo.
echo 正在做一次环境自检 ...
"%VPY%" -m ak_auto doctor
echo.
pause
