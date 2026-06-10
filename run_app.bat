@echo off
cd /d "C:\Users\olesi\OneDrive\MEE_Reflex_Trainer"

rem Free port 8501 if a stale Streamlit instance is holding it, so the app
rem never silently drifts to 8502+ (browser stats are stored per port).
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r ":8501 .*LISTENING"') do taskkill /pid %%p /f >nul 2>&1

"C:\Users\olesi\AppData\Local\Programs\Python\Python313\python.exe" -m streamlit run app.py --server.port 8501
pause
