@echo off
setlocal
cd /d "%~dp0"
if not defined DEEPDRAW_EDUCATION_PYTHON set "DEEPDRAW_EDUCATION_PYTHON=C:\python\Python38\python.exe"
"%DEEPDRAW_EDUCATION_PYTHON%" data\convert_data_skp.py %*
set "conversion_result=%errorlevel%"
echo.
pause
exit /b %conversion_result%
