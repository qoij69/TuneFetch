@echo off
rem Repo-root make.bat - lets "make tunefetch" work in cmd.exe without
rem requiring GNU Make to be installed. (On Linux/macOS the real
rem Makefile is used instead - see build/envsetup.sh.)
if not "%~1"=="tunefetch" if not "%~1"=="clean" if not "%~1"=="help" (
    echo Usage: make tunefetch ^| make clean ^| make help
    exit /b 1
)

if "%~1"=="help" (
    echo Usage:
    echo   call build\envsetup.bat
    echo   call build\lunch.bat
    echo   make tunefetch
    exit /b 0
)

if "%~1"=="clean" (
    if exist out rmdir /s /q out
    if exist .tunefetch-build-venv rmdir /s /q .tunefetch-build-venv
    exit /b 0
)

if "%TUNEFETCH_PRODUCT%"=="" (
    echo You haven't chosen a target product yet.
    echo Try:  call build\envsetup.bat  ^&^&  call build\lunch.bat
    exit /b 1
)

if "%TUNEFETCH_PRODUCT%"=="allproducts" (
    call build\tools\setup_ci.bat
) else (
    call build\tools\build_native.bat %TUNEFETCH_PRODUCT% %TUNEFETCH_VARIANT%
)
