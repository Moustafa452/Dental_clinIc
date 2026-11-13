@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Dental Lab - Build Portable EXE and Installer

set "VENV_DIR=%CD%\.venv"
set "BUILD_ENV=%CD%\.build-env"
set "PIP_CACHE_DIR=%BUILD_ENV%\pip-cache"
set "PYTHONPYCACHEPREFIX=%BUILD_ENV%\pycache"
set "PYINSTALLER_CONFIG_DIR=%BUILD_ENV%\pyinstaller"
set "TEMP=%BUILD_ENV%\temp"
set "TMP=%BUILD_ENV%\temp"
set "PYTHONUTF8=1"

if not exist "%BUILD_ENV%" mkdir "%BUILD_ENV%"
if not exist "%TEMP%" mkdir "%TEMP%"
if not exist "%PYINSTALLER_CONFIG_DIR%" mkdir "%PYINSTALLER_CONFIG_DIR%"

echo ============================================================
echo   Dental Lab - Windows Packaging
echo ============================================================
echo   Portable:  dist\DentalLab\DentalLab.exe
echo   Installer: release\DentalLab_Setup.exe
echo ============================================================
echo.

if not exist "app.py" (echo [ERROR] app.py not found.& pause & exit /b 1)
if not exist "requirements.txt" (echo [ERROR] requirements.txt not found.& pause & exit /b 1)
if not exist "packaging\DentalLab.spec" (echo [ERROR] PyInstaller spec not found.& pause & exit /b 1)
if not exist "installer\DentalLab.iss" (echo [ERROR] Inno Setup script not found.& pause & exit /b 1)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/6] Creating project-local .venv...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.12 -m venv "%VENV_DIR%" 2>nul
        if errorlevel 1 py -3 -m venv "%VENV_DIR%"
    ) else (
        where python >nul 2>nul
        if errorlevel 1 (echo [ERROR] Python not found. Install Python 3.12 x64.& pause & exit /b 1)
        python -m venv "%VENV_DIR%"
    )
    if errorlevel 1 (echo [ERROR] Could not create .venv& pause & exit /b 1)
) else (
    echo [1/6] Reusing project-local .venv
)

set "PY=%VENV_DIR%\Scripts\python.exe"

echo.
echo [2/6] Installing/updating build dependencies...
"%PY%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (echo [ERROR] requirements installation failed.& pause & exit /b 1)
"%PY%" -m pip install --disable-pip-version-check pyinstaller==6.11.1
if errorlevel 1 (echo [ERROR] PyInstaller installation failed.& pause & exit /b 1)

echo.
echo [3/6] Running automated tests...
"%PY%" -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (
    echo.
    echo [ERROR] Tests failed. Packaging stopped so a broken installer is not produced.
    pause
    exit /b 1
)

echo.
echo [4/6] Cleaning previous generated build output...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "release" rmdir /s /q "release"
mkdir "release" >nul 2>nul

echo.
echo [5/6] Building portable Windows application...
"%PY%" -m PyInstaller --noconfirm --clean "packaging\DentalLab.spec"
if errorlevel 1 (echo [ERROR] PyInstaller build failed.& pause & exit /b 1)
if not exist "dist\DentalLab\DentalLab.exe" (echo [ERROR] Portable EXE was not created.& pause & exit /b 1)

echo.
echo [6/6] Building Windows installer...
set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not defined ISCC (
    echo.
    echo [WARNING] Inno Setup 6 was not found.
    echo Portable app built successfully at:
    echo   dist\DentalLab\DentalLab.exe
    echo Install Inno Setup 6 and rerun this file to create the installer too.
    pause
    exit /b 2
)

"%ISCC%" "installer\DentalLab.iss"
if errorlevel 1 (echo [ERROR] Inno Setup failed.& pause & exit /b 1)

echo.
echo ============================================================
echo   BUILD SUCCESSFUL
echo ============================================================
echo Portable:
echo   %CD%\dist\DentalLab\DentalLab.exe
echo.
echo Installer:
echo   %CD%\release\DentalLab_Setup.exe
echo.
echo Real database/backups are stored under:
echo   %%LOCALAPPDATA%%\DentalLabSystem
echo They are NOT deleted by rebuilding this project.
echo ============================================================
start "" "release"
pause
exit /b 0
