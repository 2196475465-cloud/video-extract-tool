@echo off
chcp 65001 >nul
cd /d "%~dp0server"
echo 正在启动去水印后端...
python -u app.py
pause
