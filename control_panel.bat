@echo off
rem control_panel.bat — double-click launcher for the monsoon-watch control panel.
rem Stdlib-only server, so NO conda activation is needed (the 0xC06D007F BLAS bug
rem class only bites scripts that import numpy). Uses the project env's python if
rem present, else whatever python is on PATH.
set PY=C:\Users\varun\.conda\envs\insar_qa_env\python.exe
if not exist "%PY%" set PY=python
"%PY%" "%~dp0workflows\control_panel.py" %*
pause
