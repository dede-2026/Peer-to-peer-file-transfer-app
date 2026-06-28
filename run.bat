@echo off
:: SimpleShare launcher for Windows
cd /d "%~dp0"

:: Try py launcher first (modern Python installs)
where py >nul 2>&1
if %errorlevel% == 0 (
    py -3 simpleshare.py %*
    goto :end
)

:: Fall back to python3
where python3 >nul 2>&1
if %errorlevel% == 0 (
    python3 simpleshare.py %*
    goto :end
)

:: Fall back to python
where python >nul 2>&1
if %errorlevel% == 0 (
    python simpleshare.py %*
    goto :end
)

echo.
echo ERROR: Python 3 not found.
echo Please install it from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:end
