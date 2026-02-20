@echo off
chcp 65001 > nul 2>&1
setlocal EnableDelayedExpansion

title Phantom - Test Environment Cleanup

set "TEST_DISTRO=Ubuntu-24.04"

echo.
echo  ============================================
echo   テスト環境クリーンアップ
echo   %TEST_DISTRO% を完全に削除します
echo  ============================================
echo.

wsl -l -q 2>nul | findstr /i "%TEST_DISTRO%" >nul 2>&1
if %errorlevel% neq 0 (
    echo  %TEST_DISTRO% は存在しません。
    pause
    exit /b 0
)

choice /c YN /m "  %TEST_DISTRO% を削除してもよいですか？"
if %errorlevel% neq 1 (
    echo  キャンセルしました。
    pause
    exit /b 0
)

echo  削除中...
wsl --unregister %TEST_DISTRO%
echo.
echo  %TEST_DISTRO% を削除しました。
echo.
pause
