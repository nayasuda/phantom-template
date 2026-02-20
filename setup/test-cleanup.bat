@echo off
chcp 65001 > nul 2>&1
setlocal EnableDelayedExpansion

title Phantom - Test Environment Cleanup

set "TEST_DISTRO=Ubuntu-24.04"

echo.
echo  ============================================
echo   Test Environment Cleanup
echo   Removes %TEST_DISTRO% completely
echo  ============================================
echo.

wsl -l -q 2>nul | findstr /i "%TEST_DISTRO%" >nul 2>&1
if %errorlevel% neq 0 (
    echo  %TEST_DISTRO% does not exist.
    pause
    exit /b 0
)

choice /c YN /m "  Remove %TEST_DISTRO%?"
if %errorlevel% neq 1 (
    echo  Cancelled.
    pause
    exit /b 0
)

echo  Removing...
wsl --unregister %TEST_DISTRO%
echo.
echo  %TEST_DISTRO% removed.
echo.
pause
