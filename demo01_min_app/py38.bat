@echo off
setlocal
title Python Project Terminal
cd /d "%~dp0"
if errorlevel 1 (
    echo Unable to enter the project directory.
    pause
    exit /b 1
)

set "PATH=C:\python\Python38;C:\python\Python38\Scripts;%PATH%"

echo.
echo Project: %CD%
python --version
echo.
echo Ready. Run Python commands here. Type exit to close.
echo.

rem Keep an interactive shell open with the directory and environment above.
"%ComSpec%" /D /K
endlocal
