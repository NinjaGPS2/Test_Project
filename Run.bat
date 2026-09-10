@echo off
title Electricity Billing System (App Mode)
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

:: 2. បើកកម្មវិធីក្នុង App Mode (គ្មានរបារ URL / Address Bar)
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    start "" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" --app="http://127.0.0.1:5000"
    goto close_cmd
)

if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" (
    start "" "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" --app="http://127.0.0.1:5000"
    goto close_cmd
)

if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" --app="http://127.0.0.1:5000"
    goto close_cmd
)

if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" --app="http://127.0.0.1:5000"
    goto close_cmd
)

start msedge --app="http://127.0.0.1:5000" >nul 2>&1
if %ERRORLEVEL% equ 0 goto close_cmd

start chrome --app="http://127.0.0.1:5000" >nul 2>&1
if %ERRORLEVEL% equ 0 goto close_cmd

start "" "http://127.0.0.1:5000"

:close_cmd
:: 3. បិទផ្ទាំង CMD ភ្លាមៗ (Auto Exit CMD)
exit
