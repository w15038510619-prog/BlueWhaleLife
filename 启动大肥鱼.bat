@echo off
chcp 65001 > nul
title 大肥鱼 · 鲨鱼娘的B站生活 (BlueWhaleLife)
echo ======================================================================
echo           🦈 大肥鱼 · 鲨鱼娘的B站生活 (BlueWhaleLife) 🦈
echo       Windows 独立打包可执行程序 | 独立人格 | 长期记忆 | 60FPS 桌宠
echo ======================================================================
echo.
cd /d "%~dp0"

if exist "dist\BlueWhaleLife\BlueWhaleLife.exe" (
    echo [启动中] 正在启动打包一体化程序 (dist\BlueWhaleLife\BlueWhaleLife.exe)...
    start "" "dist\BlueWhaleLife\BlueWhaleLife.exe"
) else (
    echo [启动中] 正在以 Python 模式启动...
    python app_launcher.py
)

echo.
echo ======================================================================
echo  ✨ 启动成功！
echo  - 桌面右下角将出现可爱的【鲨鱼娘】看板娘（支持鼠标摸头、拖拽、右键菜单）
echo  - 浏览器将自动为您打开管理控制台: http://127.0.0.1:8000
echo ======================================================================
timeout /t 3
