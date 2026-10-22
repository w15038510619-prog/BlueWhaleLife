@echo off
chcp 65001 > nul
title 大肥鱼 · 鲨鱼娘的B站生活 (BlueWhaleLife)
echo ======================================================================
echo           🦈 大肥鱼 · 鲨鱼娘的B站生活 (BlueWhaleLife) 🦈
echo       Windows 优先 | 独立人格 | 长期记忆 | 深度思考 | 60FPS 桌宠
echo ======================================================================
echo.
cd /d "%~dp0"
set PYTHONPATH=%CD%

echo [1/3] 正在启动后端核心服务 (FastAPI + 内嵌管理面板)...
start "BlueWhaleLife-Server" cmd /c "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"

timeout /t 2 /nobreak > nul

echo [2/3] 正在唤醒桌面看板娘【鲨鱼娘】(PySide6)...
if exist "dist\BlueWhalePet\BlueWhalePet.exe" (
    start "" "dist\BlueWhalePet\BlueWhalePet.exe"
) else (
    start "BlueWhaleLife-Pet" cmd /c "python -m desktop_pet.main"
)

timeout /t 1 /nobreak > nul

echo [3/3] 正在为您打开管理面板网页...
start "" "http://127.0.0.1:8000"

echo.
echo ======================================================================
echo  ✨ 全部组件已成功启动！
echo  - 桌面看板娘已唤醒在屏幕右下角（支持拖拽、摸头、右键菜单、快捷聊天）
echo  - 管理面板地址: http://127.0.0.1:8000 (已自动在默认浏览器中打开)
echo ======================================================================
timeout /t 4
