@echo off
title Stop Electricity Billing System
cd /d "%~dp0"

echo ===================================================
echo   កំពុងបិទដំណើរការប្រព័ន្ធ Electricity Billing System...
echo ===================================================

:: Terminate process running on port 5000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo [✓] ប្រព័ន្ធត្រូវបានបិទដោយជោគជ័យ!
ping 127.0.0.1 -n 2 >nul
exit
