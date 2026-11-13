@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Dental Lab UI v0.3 Patch

echo ============================================================
echo   Dental Lab UI/UX v0.3 - Reference-Inspired Redesign
echo ============================================================
echo.

set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY (
    where py >nul 2>nul
    if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
    where python >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo [ERROR] Python was not found.
    echo Run Launch_Windows.bat once or install Python 3.12 x64.
    pause
    exit /b 1
)

%PY% "%~dp0Patch_DentalLab_UI_v0_3.py" "%~dp0"
if errorlevel 1 (
    echo.
    echo [ERROR] Patch failed. Your original files are still available in ui_patch_backups.
    pause
    exit /b 1
)

echo.
echo [SUCCESS] UI v0.3 applied.
echo Launch the app using Launch_Windows.bat
echo.
pause
