@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Taiwan Stock Radar
echo ============================================
python -m pip install -q -r requirements.txt
python app.py
pause
