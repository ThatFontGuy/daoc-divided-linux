@echo off
setlocal
cd /d "%~dp0"
python "%~dp0source\tools\world_editor\launch.py" %*
if errorlevel 1 pause
