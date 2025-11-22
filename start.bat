@echo off
chcp 65001 >nul
echo ====================================
echo AI炒币机器人启动脚本
echo ====================================
echo.

REM 检查.env文件
if not exist .env (
    echo ❌ 未找到.env配置文件
    echo.
    echo 请先复制.env.example为.env并填入你的API密钥:
    echo   copy .env.example .env
    echo   然后编辑.env文件
    echo.
    pause
    exit /b 1
)

echo ✓ 配置文件已找到
echo.
echo 请选择启动模式:
echo   1. 启动交易机器人 (run.py)
echo   2. 启动Web监控面板 (api/main.py)
echo   3. 同时启动机器人和Web面板
echo.

set /p choice=请输入选项 (1/2/3): 

if "%choice%"=="1" (
    echo.
    echo 启动交易机器人...
    python run.py
) else if "%choice%"=="2" (
    echo.
    echo 启动Web监控面板...
    python api/main.py
) else if "%choice%"=="3" (
    echo.
    echo 同时启动机器人和Web面板...
    echo 注意: 需要打开两个命令行窗口
    echo.
    start "AI炒币机器人" python run.py
    timeout /t 2 /nobreak >nul
    start "监控面板" python api/main.py
) else (
    echo 无效选项
    pause
    exit /b 1
)

pause
