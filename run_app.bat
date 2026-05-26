@echo off
setlocal

cd /d "%~dp0"

call :resolve_python
if errorlevel 1 goto :fail

echo [BOOT] Using Python: %PYTHON_CMD% %PYTHON_ARGS%
"%PYTHON_CMD%" %PYTHON_ARGS% scripts\start_app.py
if errorlevel 1 goto :fail
goto :eof

:resolve_python
where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=py"
  set "PYTHON_ARGS=-3"
  exit /b 0
)

where python >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=python"
  set "PYTHON_ARGS="
  exit /b 0
)

echo [ERROR] Python 3 is not installed or not available in PATH.
echo Please install Python 3.12 and enable "Add python.exe to PATH", then run this file again.
exit /b 1

:fail
echo.
echo Startup aborted.
pause
exit /b 1
