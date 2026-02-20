@echo off
chcp 65001 > nul 2>&1
setlocal EnableDelayedExpansion

title Phantom - Test Environment Setup

echo.
echo  ============================================
echo   Phantom Test Environment Setup
echo   Creates a clean WSL instance for testing
echo  ============================================
echo.
echo   * Your existing Ubuntu is NOT affected
echo   * Installs Ubuntu-24.04 as a separate distro
echo.

set "TEST_DISTRO=Ubuntu-24.04"

:: 既にテスト環境がある場合の確認
wsl -l -q 2>nul | findstr /i "%TEST_DISTRO%" >nul 2>&1
if %errorlevel% equ 0 (
    powershell -command "Write-Host '  %TEST_DISTRO% already exists.' -ForegroundColor Yellow"
    echo.
    choice /c YN /m "  Remove and recreate?"
    if !errorlevel! equ 1 (
        echo  Unregistering %TEST_DISTRO%...
        wsl --unregister %TEST_DISTRO%
        echo   OK
    ) else (
        echo  Cancelled.
        pause
        exit /b 0
    )
)

echo.
echo  Installing %TEST_DISTRO%...
wsl --install -d %TEST_DISTRO%
echo.
powershell -command "Write-Host '  Set username/password, then type exit' -ForegroundColor Cyan"
pause

echo.
echo  Running setup in test mode...
call "%~dp0setup-windows.bat" --test

echo.
echo  ============================================
echo   Test complete!
echo   Run test-cleanup.bat to remove test env.
echo  ============================================
echo.
pause
