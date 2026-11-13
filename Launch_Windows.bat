@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Dental Lab - Direct Launch

set "VENV_DIR=%CD%\.venv"
set "BUILD_ENV=%CD%\.build-env"
set "PIP_CACHE_DIR=%BUILD_ENV%\pip-cache"
set "PYTHONPYCACHEPREFIX=%BUILD_ENV%\pycache"
set "TEMP=%BUILD_ENV%\temp"
set "TMP=%BUILD_ENV%\temp"
set "PYTHONUTF8=1"

if not exist "%BUILD_ENV%" mkdir "%BUILD_ENV%"
if not exist "%TEMP%" mkdir "%TEMP%"

echo ============================================================
echo   Dental Lab - Direct Launch
echo   Project-local Python environment - no app install needed
echo ============================================================
echo.

if not exist "app.py" (
    echo [ERROR] app.py not found in %CD%
    pause
    exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [SETUP] Creating .venv inside this project...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.12 -m venv "%VENV_DIR%" 2>nul
        if errorlevel 1 py -3 -m venv "%VENV_DIR%"
    ) else (
        where python >nul 2>nul
        if errorlevel 1 (
            echo [ERROR] Python was not found. Install Python 3.12 x64 first.
            pause
            exit /b 1
        )
        python -m venv "%VENV_DIR%"
    )
    if errorlevel 1 (
        echo [ERROR] Failed to create .venv
        pause
        exit /b 1
    )
)

set "PY=%VENV_DIR%\Scripts\python.exe"

for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 'requirements.txt').Hash"`) do set "REQ_HASH=%%H"
set "OLD_HASH="
if exist "%VENV_DIR%\requirements.sha256" set /p OLD_HASH=<"%VENV_DIR%\requirements.sha256"

if /I not "%REQ_HASH%"=="%OLD_HASH%" (
    echo [SETUP] Installing project dependencies into .venv...
    "%PY%" -m pip install --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
    >"%VENV_DIR%\requirements.sha256" echo %REQ_HASH%
)

echo [START] Dental Lab
echo.
"%PY%" "app.py"
set "APP_EXIT=%ERRORLEVEL%"

if not "%APP_EXIT%"=="0" (
    echo.
    echo [ERROR] Application exited with code %APP_EXIT%.
    pause
)
exit /b %APP_EXIT%
