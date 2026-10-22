@echo off
chcp 65001 > nul
title BlueWhaleLife - 一键启动器
echo =======================================================
echo          🐋 大肥鱼的B站生活 (BlueWhaleLife) 🐋
echo   自主探索、独立思考、长期记忆与成长的 Windows AI 角色养成
echo =======================================================
echo.
echo [1/3] 正在启动 FastAPI 后端服务 (端口 8000)...
start "BlueWhaleLife-Backend" cmd /c "%~dp0run_backend.bat"

timeout /t 3 /nobreak > nul

echo [2/3] 正在启动 React 管理面板前端 (端口 5173)...
start "BlueWhaleLife-Frontend" cmd /c "%~dp0run_frontend.bat"

timeout /t 2 /nobreak > nul

echo [3/3] 正在唤醒 Windows 桌面小肥鱼 (PySide6)...
start "BlueWhaleLife-Pet" cmd /c "%~dp0run_desktop_pet.bat"

echo.
echo =======================================================
echo  所有组件均已在独立窗口中启动！
echo  管理面板地址: http://localhost:5173
echo  如需退出，关闭各个命令窗口即可。
echo =======================================================
timeout /t 5
