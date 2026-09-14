@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
if exist "%~dp0runtime\python.exe" (
  "%~dp0runtime\python.exe" "%~dp0bale_agent.py" %*
) else (
  python "%~dp0bale_agent.py" %*
)
exit /b %errorlevel%
