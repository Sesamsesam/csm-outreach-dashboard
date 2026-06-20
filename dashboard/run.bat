@echo off
echo Installing Flask (one-time)...
pip install flask --quiet

echo.
echo Starting dashboard at http://localhost:5001 ...
echo Press Ctrl+C to stop.
echo.

cd /d "%~dp0"
python app.py
pause
