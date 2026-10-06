@echo off
cd /d "%~dp0"
echo Installing packages (first run only)...
python -m pip install -q -r requirements.txt
python setup_and_run.py
pause
