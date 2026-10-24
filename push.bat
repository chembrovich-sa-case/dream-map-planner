@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   Horizont (Dream Map Planner) - Auto Sync to GitHub
echo ========================================================
echo.

if exist "C:\dev\flutter\bin\mingit\cmd\git.exe" (
    set "PATH=C:\dev\flutter\bin\mingit\cmd;C:\dev\flutter\bin\mingit\mingw64\bin;%PATH%"
)

set COMMIT_MSG=%*
if "%COMMIT_MSG%"=="" (
    set COMMIT_MSG=Auto update: %DATE% %TIME%
)

echo [1/3] Adding changes (git add .)...
git add .

echo [2/3] Creating commit...
git commit -m "%COMMIT_MSG%"

echo [3/3] Pushing to GitHub (git push origin main)...
git push origin main

if errorlevel 1 (
    echo.
    echo [ERROR] Push failed. Check your internet connection or repository permissions.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   [SUCCESS] Synchronization completed successfully!
echo   Live app: https://chembrovich-sa-case.github.io/dream-map-planner/
echo ========================================================
echo.

pause
