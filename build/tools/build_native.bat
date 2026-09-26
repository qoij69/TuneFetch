@echo off
rem build\tools\build_native.bat <product> <variant>
rem Called by make.bat (via build\lunch.bat) - not meant to be run directly.
setlocal enabledelayedexpansion

set "PRODUCT=%~1"
set "VARIANT=%~2"
if "%VARIANT%"=="" set "VARIANT=userdebug"

cd /d "%~dp0..\.."
set "ROOT=%CD%"

echo ============================================
echo PLATFORM_VERSION_CODENAME=REL
echo PLATFORM_VERSION=1.1
echo TARGET_PRODUCT=tunefetch_%PRODUCT%
echo TARGET_BUILD_VARIANT=%VARIANT%
echo HOST_OS=windows
echo OUT_DIR=out\target\product\%PRODUCT%
echo ============================================
echo.

if not "%PRODUCT%"=="windows" (
    echo PyInstaller can't cross-compile: this host ^(windows^) can't produce
    echo a %PRODUCT% artifact. Your options:
    echo   - Run this on an actual %PRODUCT% machine ^(or VM^): call build\envsetup.sh
    echo     ^(or .bat^), lunch tunefetch-%PRODUCT%-%VARIANT%, make tunefetch.
    echo   - lunch tunefetch-allproducts-eng here instead, to set up the GitHub
    echo     Actions build, which produces Linux + Windows + macOS artifacts
    echo     in the cloud on every push - no other machine needed.
    exit /b 1
)

set "BOARD_CONFIG=device\tunefetch\%PRODUCT%\BoardConfig.mk"
if not exist "%BOARD_CONFIG%" (
    echo Missing %BOARD_CONFIG% - is your device tree intact?
    exit /b 1
)

set "PYI_BIN_NAME=TuneFetch"
for /f "tokens=2 delims==" %%V in ('findstr /b /c:"PYI_BIN_NAME" "%BOARD_CONFIG%"') do (
    set "TMP=%%V"
    for /f "tokens=* delims= " %%T in ("!TMP!") do set "TMP=%%T"
    if not "!TMP!"=="" set "PYI_BIN_NAME=!TMP!"
)

set "PYI_WINDOWED_ARGS="
for /f "tokens=2 delims==" %%V in ('findstr /b /c:"PYI_WINDOWED_ARGS" "%BOARD_CONFIG%"') do (
    set "TMP=%%V"
    for /f "tokens=* delims= " %%T in ("!TMP!") do set "TMP=%%T"
    set "PYI_WINDOWED_ARGS=!TMP!"
)

set "PYI_ICON_FILE="
for /f "tokens=2 delims==" %%V in ('findstr /b /c:"PYI_ICON_FILE" "%BOARD_CONFIG%"') do (
    set "TMP=%%V"
    for /f "tokens=* delims= " %%T in ("!TMP!") do set "TMP=%%T"
    set "PYI_ICON_FILE=!TMP!"
)

set "ICON_ARG="
if not "%PYI_ICON_FILE%"=="" if exist "%PYI_ICON_FILE%" set "ICON_ARG=--icon=%PYI_ICON_FILE%"

echo [ 05%% ] Verifying host toolchain (tkinter)...
py -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo Tkinter isn't available for this Python install.
    echo Fix: reinstall Python from python.org with "tcl/tk and IDLE" checked.
    exit /b 1
)

echo [ 15%% ] Setting up the build sandbox (venv)...
if not exist ".tunefetch-build-venv" (
    py -m venv .tunefetch-build-venv
    if errorlevel 1 (
        echo Could not create the build sandbox.
        exit /b 1
    )
)
set "PY=%ROOT%\.tunefetch-build-venv\Scripts\python.exe"

echo [ 30%% ] Syncing build dependencies (pip)...
"%PY%" -m pip install --upgrade pip >nul
"%PY%" -m pip install --upgrade pyinstaller customtkinter yt-dlp pillow mutagen imageio-ffmpeg certifi truststore
if errorlevel 1 exit /b 1

echo [ 60%% ] Compiling %PYI_BIN_NAME% ...
set "OUT=out\target\product\%PRODUCT%"
"%PY%" -m PyInstaller --noconfirm --onefile --name "%PYI_BIN_NAME%" ^
    %PYI_WINDOWED_ARGS% %ICON_ARG% ^
    --collect-data customtkinter ^
    --collect-data imageio_ffmpeg ^
    --hidden-import=yt_dlp ^
    --distpath "%OUT%" ^
    --workpath "%OUT%\obj" ^
    --specpath "%OUT%" ^
    vendor\tunefetch\tunefetch.py
if errorlevel 1 (
    echo.
    echo #### make failed ####
    echo Scroll up for the PyInstaller error.
    exit /b 1
)

echo [100%% ] Installing artifact...
echo.
echo #### make completed successfully ####
echo Artifact: %OUT%\%PYI_BIN_NAME%.exe
