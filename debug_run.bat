@echo off
chcp 65001 >nul
echo ====================================
echo 调试模式 - AI炒币机器人
echo ====================================
echo.

echo 正在启动交易机器人...
echo.

python run.py

echo.
echo ====================================
if errorlevel 1 (
    echo ❌ 程序出错了！
) else (
    echo ✅ 程序正常退出
)
echo ====================================
echo.
pause
