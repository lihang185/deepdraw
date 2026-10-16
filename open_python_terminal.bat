@echo off
setlocal
title Python Project Terminal
cd /d "%~dp0"
if errorlevel 1 (
    echo Unable to enter the project directory.
    pause
    exit /b 1
)

rem Prefer a project virtual environment when one is available.
if exist "%~dp0.venv\Scripts\activate.bat" (
    call "%~dp0.venv\Scripts\activate.bat"
) else if exist "%~dp0venv\Scripts\activate.bat" (
    call "%~dp0venv\Scripts\activate.bat"
) else if exist "C:\python\Python38\python.exe" (
    set "PATH=C:\python\Python38;C:\python\Python38\Scripts;%PATH%"
)

echo.
echo Project: %CD%
python --version
echo.
echo Ready. Run Python commands here. Type exit to close.
echo.

rem Keep an interactive shell open with the directory and environment above.
"%ComSpec%" /D /K
endlocal
