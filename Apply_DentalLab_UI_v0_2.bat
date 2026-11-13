@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Dental Lab - Apply UI UX Patch v0.2

echo ============================================================
echo   Dental Lab UI/UX Patch v0.2
echo   - Fixes invisible popup labels
echo   - Standardizes field sizes and spacing
echo   - Replaces harsh white surfaces with softer colors
echo   - Makes long Add/Edit forms scrollable
echo ============================================================
echo.

if not exist "Patch_DentalLab_UI_v0_2.py" (
    echo [ERROR] Patch_DentalLab_UI_v0_2.py must be in the same folder.
    pause
    exit /b 1
)

if not exist "dental_lab\ui.py" (
    echo [ERROR] dental_lab\ui.py was not found.
    echo Put BOTH patch files in the ROOT of your DentalLab project.
    pause
    exit /b 1
)

set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY (
    where py >nul 2>nul
    if not errorlevel 1 set "PY=py"
)
if not defined PY (
    where python >nul 2>nul
    if not errorlevel 1 set "PY=python"
)

if not defined PY (
    echo [ERROR] Python was not found.
    echo Run Launch_Windows.bat once first, then run this patch again.
    pause
    exit /b 1
)

%PY% "Patch_DentalLab_UI_v0_2.py" "."
if errorlevel 1 (
    echo.
    echo [ERROR] Patch failed. Your original ui.py was not intentionally replaced.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   PATCH COMPLETE
echo ============================================================
echo.
echo A backup is stored at:
echo   dental_lab\ui_before_v0_2.py
echo.
echo Now run:
echo   Launch_Windows.bat
echo.
pause
