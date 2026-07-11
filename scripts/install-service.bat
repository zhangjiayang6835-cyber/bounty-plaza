@echo off
chcp 65001 >/dev/null
echo ===== Bounty Plaza 本地打款守护 =====
echo.

:: 设置路径
set BPAZA=C:\bounty-plaza
set PYTHON=python

:: 创建目录
if not exist %BPAZA% mkdir %BPAZA%
if not exist %BPAZA%\data mkdir %BPAZA%\data
if not exist %BPAZA%\logs mkdir %BPAZA%\logs

:: 复制文件
copy /Y scripts\coin.py %BPAZA%\
copy /Y scripts\auto_payout.py %BPAZA%\
copy /Y BOUNTY_CONFIG.json %BPAZA%\
copy /Y data\seed_users.json %BPAZA%\data\ 2>/dev/null

:: 安装依赖
pip install python-dotenv requests -q

:: 创建 .env 模板
if not exist %BPAZA%\.env (
    echo BINANCE_API_KEY=你的_API_KEY > %BPAZA%\.env
    echo BINANCE_SECRET_KEY=你的_SECRET_KEY >> %BPAZA%\.env
    echo GH_TOKEN=你的_GITHUB_TOKEN >> %BPAZA%\.env
    echo 请编辑 %BPAZA%\.env 填入你的密钥
)

:: 创建启动脚本
echo @echo off > %BPAZA%\start.bat
echo cd /d %BPAZA% >> %BPAZA%\start.bat
echo python auto_payout.py --daemon --interval 300 >> %BPAZA%\start.bat
echo echo 打款守护已启动，日志: %BPAZA%\logs\payout.log >> %BPAZA%\start.bat

:: 加到开机启动
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
copy /Y %BPAZA%\start.bat "%STARTUP%\bounty-payout.bat"

echo.
echo ✅ 安装完成！
echo 1. 编辑 %BPAZA%\.env 填入你的密钥
echo 2. 双击 %BPAZA%\start.bat 启动
echo 3. 如需取消开机启动，删除 "%STARTUP%\bounty-payout.bat"
echo.
pause
