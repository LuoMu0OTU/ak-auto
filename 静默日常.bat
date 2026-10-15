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
rem 输出走文件，用 UTF-8 写日志更好看；控制台本身是 936。
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 还没安装。请先双击运行「首次安装.bat」。
    echo.
    pause
    exit /b 1
)
if not exist "logs" mkdir logs

echo 已在后台开始运行日常（最小化窗口，跑完自动关闭）。
echo 进度请看 logs\daily.log
start "ak-auto 日常" /min cmd /c ".venv\Scripts\python.exe -m ak_auto daily > logs\daily.log 2>&1"
timeout /t 3 >nul
exit
