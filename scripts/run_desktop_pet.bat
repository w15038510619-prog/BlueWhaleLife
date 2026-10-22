@echo off
chcp 65001 > nul
title BlueWhaleLife - 桌面小肥鱼 (PySide6)
echo [BlueWhaleLife] 正在唤醒桌面小肥鱼...
cd /d "%~dp0\.."

set PYTHONPATH=%CD%
python -m desktop_pet.main
pause
