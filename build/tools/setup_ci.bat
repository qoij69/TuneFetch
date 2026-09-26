@echo off
rem build\tools\setup_ci.bat - wires up the GitHub Actions build
cd /d "%~dp0..\.."

if not exist ".github\workflows" mkdir ".github\workflows"
if exist "build\ci\build.yml" (
    copy /y "build\ci\build.yml" ".github\workflows\build.yml" >nul
    echo Copied build\ci\build.yml into .github\workflows\build.yml
) else (
    echo Could not find build\ci\build.yml - is your tree intact?
    exit /b 1
)

echo.
echo Next steps:
echo   1. Commit and push this tree to a GitHub repository
echo      ^(including the new .github\workflows\build.yml file^).
echo   2. Open the 'Actions' tab on GitHub - a build will run
echo      automatically and produce tunefetch_linux, tunefetch_windows
echo      and tunefetch_macos artifacts, downloadable from that run.
