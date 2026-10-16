@echo off
setlocal
cd /d "%~dp0"
if not defined DEEPDRAW_PYTHON set "DEEPDRAW_PYTHON=C:\python\Python38\python.exe"
"%DEEPDRAW_PYTHON%" -m PyInstaller --noconfirm deepdraw_v2.spec
exit /b %errorlevel%
