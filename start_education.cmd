@echo off
setlocal
cd /d "%~dp0"
if defined DEEPDRAW_EDUCATION_PYTHON (
    "%DEEPDRAW_EDUCATION_PYTHON%" editor.py
) else if exist "C:\python\Python38\python.exe" (
    "C:\python\Python38\python.exe" editor.py
) else (
    py -3.8 editor.py
)
