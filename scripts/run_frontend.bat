@echo off
chcp 65001 > nul
title BlueWhaleLife - 管理面板 (React + Vite)
echo [BlueWhaleLife] 正在启动管理面板前端...
cd /d "%~dp0\..\frontend"

npm run dev
pause
