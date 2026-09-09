@echo off
title Blue Eye — AI Voice Receptionist
cd /d "C:\Users\poorn\OneDrive\Desktop\roman ai voice chllange"

:: Check if already running on port 8501
netstat -ano | findstr ":8501" >nul 2>&1
if %errorlevel% == 0 (
    echo Blue Eye is already running — opening browser...
    start "" "http://localhost:8501"
    exit
)

echo Starting Blue Eye AI Voice Receptionist...
start "" /b streamlit run app.py --server.headless true --server.port 8501

:: Wait for Streamlit to be ready (max 15 seconds) using ping sleep
echo Waiting for server to start...
set /a count=0
:wait_loop
ping 127.0.0.1 -n 2 >nul
netstat -ano | findstr ":8501" >nul 2>&1
if %errorlevel% == 0 goto open_browser
set /a count+=1
if %count% lss 15 goto wait_loop

:open_browser
echo Opening Blue Eye in browser...
start "" "http://localhost:8501"
exit
