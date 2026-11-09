@echo off
chcp 65001 >nul
title My Blog Dev Server
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo  [ERROR] .venv not found. Run:
    echo      python -m venv .venv
    echo      .venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"
echo.
echo  Starting dev server at http://127.0.0.1:8000/
echo  Press Ctrl+C to stop.
echo.
start "" /min cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8000/"
python manage.py runserver
echo.
echo  Server stopped.
pause
