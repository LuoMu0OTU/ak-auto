@echo off
chcp 936 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=gbk

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
