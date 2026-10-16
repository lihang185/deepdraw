@echo off
setlocal
cd /d "%~dp0"
if not defined DEEPDRAW_EDUCATION_PYTHON set "DEEPDRAW_EDUCATION_PYTHON=C:\python\Python38\python.exe"
"%DEEPDRAW_EDUCATION_PYTHON%" -m PyInstaller --noconfirm packaging/education.spec
exit /b %errorlevel%
