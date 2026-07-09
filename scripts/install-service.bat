@echo off
REM install-service.bat — 注册 Windows 计划任务，每5分钟自动打款
REM 以管理员身份运行

set TASK_NAME=BountyPlazaAutoPay
set SCRIPTS_DIR=%~dp0..\scripts
set PYTHON=python

echo Installing Windows scheduled task: %TASK_NAME%
echo Script: %SCRIPTS_DIR%\auto_payout.py

schtasks /create /tn "%TASK_NAME%" /tr "%PYTHON% %SCRIPTS_DIR%\auto_payout.py --daemon --interval 300" /sc minute /mo 1 /ru "%USERNAME%" /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo ✅ 计划任务已创建！
    echo    每 1 分钟运行一次 auto_payout.py
    echo.
    echo 查看运行日志:
    echo   schtasks /run /tn "%TASK_NAME%"
    echo.
    echo 手动停止:
    echo   schtasks /end /tn "%TASK_NAME%"
    echo.
    echo 卸载:
    echo   schtasks /delete /tn "%TASK_NAME%" /f
) else (
    echo ❌ 创建失败，请以管理员身份运行此脚本
    pause
)
