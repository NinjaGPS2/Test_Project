@echo off
title Electricity Billing System (Browser Mode)
cd /d "%~dp0"

:: 1. ពិនិត្យមើលថាតើ Server កំពុងដំណើរការស្រាប់លើ Port 5000 ឬនៅ
netstat -ano | findstr :5000 | findstr LISTENING >nul
if %ERRORLEVEL% neq 0 (
    if not exist "electricity_system.db" (
        python seed_data.py
    )
    start "" pythonw app.py
    ping 127.0.0.1 -n 3 >nul
)

:: 2. បើកកម្មវិធីលើ Web Browser ធម្មតា (មានរបារ URL និង Tabs)
start http://127.0.0.1:5000

:: 3. បិទផ្ទាំង CMD ភ្លាមៗ
exit
