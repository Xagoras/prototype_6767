@echo off
chcp 65001 >nul
cd /d %~dp0
title 法律论证标注系统
python start_manager.py
echo.
pause
