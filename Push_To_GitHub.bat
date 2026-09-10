@echo off
chcp 65001 >nul
title Push to GitHub - NinjaGPS2/Test_Project
cd /d "%~dp0"

echo ==============================================================================
echo        ⚡ ប្រព័ន្ធបញ្ជូន និងអាប់ដេតកូដទៅកាន់ GitHub (Git Push & Sync)
echo        🔗 Repository: https://github.com/NinjaGPS2/Test_Project
echo ==============================================================================
echo.

:: 1. ស្វែងរក Git Executable
where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"
    ) else if exist "%ProgramFiles%\Git\cmd\git.exe" (
        set "PATH=%ProgramFiles%\Git\cmd;%PATH%"
    ) else if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" (
        set "PATH=%ProgramFiles(x86)%\Git\cmd;%PATH%"
    ) else (
        echo [!] រកមិនឃើញកម្មវិធី Git នៅក្នុងម៉ាស៊ីនទេ!
        echo សូមដំឡើង Git ឬទាក់ទង Admin។
        echo.
        pause
        exit /b 1
    )
)

:: 2. ពិនិត្យមើល Git Repository
if not exist ".git" (
    echo [*] កំពុងរៀបចំបង្កើត Git Repository ដំបូង...
    git init -b main
    git config user.name NinjaGPS2
    git config user.email sothealove10101010@gmail.com
)

:: 3. ពិនិត្យ និងកំណត់ Remote Origin
git remote get-url origin >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] កំពុងភ្ជាប់ទៅកាន់ GitHub: https://github.com/NinjaGPS2/Test_Project.git
    git remote add origin https://github.com/NinjaGPS2/Test_Project.git
) else (
    git remote set-url origin https://github.com/NinjaGPS2/Test_Project.git
)

echo [*] ស្ថានភាព File បច្ចុប្បន្ន (Git Status):
git status -s
echo.

:: 4. សួររក Commit Message (ឬចុច Enter ដើម្បីប្រើ Default)
set "DEFAULT_MSG=Fix deployment files and update project"
set "USER_MSG="
set /p "USER_MSG=បញ្ចូលសារសម្គាល់ការ Update (ចុច Enter យកលំនាំដើម: %DEFAULT_MSG%): "
if "%USER_MSG%"=="" set "USER_MSG=%DEFAULT_MSG%"

echo.
echo [*] 1. កំពុងបន្ថែម File ទាំងអស់ (git add .)...
git add .

echo [*] 2. កំពុងកត់ត្រាការផ្លាស់ប្ដូរ (git commit)...
git status --porcelain | findstr /R "." >nul
if %ERRORLEVEL% equ 0 (
    git commit -m "%USER_MSG%"
) else (
    echo     (ពុំមានការផ្លាស់ប្ដូរថ្មីដើម្បី commit ទេ - នឹងបន្តទៅជំហាន push)
)

echo [*] 3. កំពុងកំណត់ Main Branch...
git branch -M main

echo [*] 4. កំពុងបញ្ជូនកូដទៅកាន់ GitHub (git push origin main)...
echo.
git push -u origin main
if %ERRORLEVEL% equ 0 (
    echo.
    echo ==============================================================================
    echo [✓] ជោគជ័យត្រចះត្រចង់! កូដទាំងអស់ត្រូវបាន Push ទៅកាន់ GitHub រួចរាល់!
    echo 🌐 ពិនិត្យមើលកូដលើ GitHub: https://github.com/NinjaGPS2/Test_Project
    echo 🚀 Cloud Deployment នឹង Re-deploy ជាស្វ័យប្រវត្តិនឹងដំណើរការឡើងវិញ!
    echo ==============================================================================
) else (
    echo.
    echo ==============================================================================
    echo [!] មិនទាន់អាច Push បានទេ ដោយសារ GitHub ទាមទារការផ្ទៀងផ្ទាត់ (Authentication)។
    echo ==============================================================================
    echo.
    echo ជម្រើសដោះស្រាយ៖
    echo 1. ប្រសិនបើមានផ្ទាំង Browser លោតឡើង សូមចុច "Sign in with your browser"
    echo 2. ឬលោកអ្នកអាចបញ្ចូល GitHub Personal Access Token (PAT) ដោយផ្ទាល់
    echo.
    set /p "USE_TOKEN=តើអ្នកចង់បញ្ចូល GitHub Token ដើម្បី Push ដែរឬទេ? (y/n): "
    if /i "%USE_TOKEN%"=="y" (
        set /p "GH_TOKEN=សូម Paste GitHub Token ទីនេះ: "
        if not "%GH_TOKEN%"=="" (
            echo [*] កំពុង Push ដោយប្រើ Token...
            git push "https://%GH_TOKEN%@github.com/NinjaGPS2/Test_Project.git" main
            if %ERRORLEVEL% equ 0 (
                echo.
                echo ==============================================================================
                echo [✓] Push បានជោគជ័យ ១០០%! Cloud នឹង Re-deploy ឡើងវិញភ្លាមៗ!
                echo ==============================================================================
            )
        )
    )
)

echo.
echo ចុចប៊ូតុងណាមួយដើម្បីចាកចេញ...
pause >nul
