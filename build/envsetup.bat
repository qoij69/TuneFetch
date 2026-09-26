@echo off
rem ============================================================
rem   TuneFetch build environment (Windows)
rem   Usage:  call build\envsetup.bat
rem ============================================================
set "TUNEFETCH_ROOT=%~dp0.."
set "TUNEFETCH_HOST_OS=windows"

echo ============================================
echo  TuneFetch build environment ready.
echo  Run 'call build\lunch.bat' to choose a target,
echo  then 'make tunefetch' from the repo root.
echo ============================================
