@echo off
REM Double-click to publish code changes to GitHub.
REM Optional: pass a commit message in quotes when running from a terminal.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0publish_to_github.ps1" %*
pause
