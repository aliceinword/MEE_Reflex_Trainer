@echo off
REM Launch the MEE Reflex Trainer from this script's own folder.
cd /d "%~dp0"

REM Activate a local virtual environment if one exists.
if exist ".venv\Scripts\activate" call .venv\Scripts\activate

streamlit run app.py
pause
