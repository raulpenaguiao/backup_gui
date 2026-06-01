@echo off
:: Build Pigmy Backup for Windows.
:: Usage: build.bat --version X.X.X
setlocal enabledelayedexpansion

:: ── Argument parsing ──────────────────────────────────────────────────────────
set "VERSION="
:parse
if "%~1"=="" goto check_version
if /I "%~1"=="--version" (
    set "VERSION=%~2"
    shift & shift
    goto parse
)
echo Unknown argument: %~1 >&2
exit /b 1

:check_version
if "%VERSION%"=="" (
    echo Usage: build.bat --version X.X.X >&2
    exit /b 1
)

:: Basic X.X.X validation via findstr regex
echo %VERSION%| findstr /R "^[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$" >nul 2>&1
if errorlevel 1 (
    echo Version must be X.X.X format ^(e.g. 2.1.3^) >&2
    exit /b 1
)

:: Run from the project root regardless of call location
pushd "%~dp0"

set "PLATFORM_DIR=releases\%VERSION%\windows"

echo ==============================
echo  Pigmy Backup -- Build %VERSION%
echo  Platform : windows
echo  Output   : %PLATFORM_DIR%
echo ==============================
echo.

:: ── 1. Virtual environment ^& dependencies ─────────────────────────────────────
if not exist ".venv" (
    echo [1/4] Creating virtual environment...
    python -m venv .venv
)
echo [1/4] Installing dependencies...
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
pip install -q pyinstaller

:: ── 2. Tests ──────────────────────────────────────────────────────────────────
echo.
echo [2/4] Running tests...
python -m unittest discover -s tests -v
if errorlevel 1 (
    echo.
    echo Tests FAILED. Build aborted. >&2
    exit /b 1
)
echo.
echo All tests passed.

:: ── 3. PyInstaller build ──────────────────────────────────────────────────────
echo.
echo [3/4] Building executable...
if exist "%PLATFORM_DIR%" rmdir /S /Q "%PLATFORM_DIR%"
mkdir "%PLATFORM_DIR%"

python -m PyInstaller ^
  --onefile ^
  --windowed ^
  --name "PigmyBackup" ^
  --distpath "%PLATFORM_DIR%" ^
  --workpath "build\_pyinstaller" ^
  --specpath "build" ^
  backup_gui.py

if errorlevel 1 (
    echo PyInstaller build FAILED. >&2
    exit /b 1
)

:: ── 4. Stamp version ─────────────────────────────────────────────────────────
echo %VERSION%> "releases\%VERSION%\VERSION"

echo.
echo [4/4] Done.
echo.
dir "%PLATFORM_DIR%"

echo.
echo Windows note: SmartScreen may warn on first run of an unsigned executable.
echo Click "More info" then "Run anyway" to proceed.

popd
endlocal
