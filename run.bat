@echo off
cd /d %~dp0
echo === MyshPPT ===
if not exist venv (
    echo Creating virtual environment, please wait...
    python -m venv venv
)
call venv\Scripts\activate
echo Installing packages...
pip install -r requirements.txt
if not exist .env (
    copy .env.example .env >nul
    echo.
    echo Notepad will open. Paste your OpenRouter key after OPENROUTER_API_KEY= then save and close it.
    notepad .env
)
echo.
echo Open http://127.0.0.1:5000 in your browser. Press Ctrl+C to stop.
set FLASK_DEBUG=1
python app.py
pause
