@echo off
rem build\lunch.bat [combo] - call this after build\envsetup.bat

if not "%~1"=="" (
    set "COMBO=%~1"
    goto :apply
)

echo.
echo You're building on Windows.
echo.
echo Lunch menu... pick a combo:
echo      1. tunefetch-windows-userdebug
echo      2. tunefetch-linux-userdebug        (cross-build: prints instructions on this host)
echo      3. tunefetch-macos-userdebug        (cross-build: prints instructions on this host)
echo      4. tunefetch-allproducts-eng        (sets up the GitHub Actions build for all three)
echo.
set /p CHOICE="Which would you like? [tunefetch-windows-userdebug] "
if "%CHOICE%"=="" set CHOICE=1
if "%CHOICE%"=="1" set COMBO=tunefetch-windows-userdebug
if "%CHOICE%"=="2" set COMBO=tunefetch-linux-userdebug
if "%CHOICE%"=="3" set COMBO=tunefetch-macos-userdebug
if "%CHOICE%"=="4" set COMBO=tunefetch-allproducts-eng
if "%COMBO%"=="" set COMBO=%CHOICE%

:apply
if "%COMBO%"=="tunefetch-windows-userdebug" (
    set "TUNEFETCH_PRODUCT=windows"
    set "TUNEFETCH_VARIANT=userdebug"
) else if "%COMBO%"=="tunefetch-linux-userdebug" (
    set "TUNEFETCH_PRODUCT=linux"
    set "TUNEFETCH_VARIANT=userdebug"
) else if "%COMBO%"=="tunefetch-macos-userdebug" (
    set "TUNEFETCH_PRODUCT=macos"
    set "TUNEFETCH_VARIANT=userdebug"
) else if "%COMBO%"=="tunefetch-allproducts-eng" (
    set "TUNEFETCH_PRODUCT=allproducts"
    set "TUNEFETCH_VARIANT=eng"
) else (
    echo Invalid combo: %COMBO%
    exit /b 1
)

echo.
echo ============================================
echo PLATFORM_VERSION_CODENAME=REL
echo PLATFORM_VERSION=1.1
echo TARGET_PRODUCT=tunefetch_%TUNEFETCH_PRODUCT%
echo TARGET_BUILD_VARIANT=%TUNEFETCH_VARIANT%
echo HOST_OS=windows
echo OUT_DIR=out\target\product\%TUNEFETCH_PRODUCT%
echo ============================================
echo.
