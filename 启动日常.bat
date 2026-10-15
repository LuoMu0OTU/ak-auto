@echo off
rem 明日方舟客户端要求管理员权限：非提权运行时自动重新以管理员启动（UAC 提示一次）
whoami /groups | find "S-1-16-12288" >nul 2>&1
if errorlevel 1 (
    echo 正在申请管理员权限（明日方舟客户端需要），请在弹窗中点「是」...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%~dp0' -Verb RunAs"
    exit /b
)

chcp 936 >nul
cd /d "%~dp0"
title ak-auto 日常
set PYTHONIOENCODING=gbk

if not exist ".venv\Scripts\python.exe" (
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

".venv\Scripts\python.exe" -m ak_auto daily
set "RC=%ERRORLEVEL%"

echo.
echo ------------------------------------------------------------
if "%RC%"=="0" (
    echo   全部完成。
) else (
    echo   结束，但有任务未成功（返回码 %RC%）。详情见 logs\ 与 debug\ 目录。
)
echo   日志: logs\     失败截图: debug\
echo ============================================================
echo.
pause
