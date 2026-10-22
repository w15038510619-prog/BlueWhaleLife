@echo off
chcp 65001 > nul
title BlueWhaleLife - 后端服务 (FastAPI)
echo [BlueWhaleLife] 正在启动大肥鱼后端服务...
cd /d "%~dp0\.."

set PYTHONPATH=%CD%
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause
