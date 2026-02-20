@echo off
chcp 65001 > nul 2>&1
setlocal EnableDelayedExpansion

title Phantom - Test Environment Setup

echo.
echo  ============================================
echo   テスト環境セットアップ
echo   ナツキ専用：クリーンな WSL 環境で
echo   Staff Kit の動作確認を行います
echo  ============================================
echo.
echo  ※ 既存の Ubuntu 環境には影響しません
echo  ※ Ubuntu-24.04 を新規インストールします
echo.

set "TEST_DISTRO=Ubuntu-24.04"

:: 既にテスト環境がある場合の確認
wsl -l -q 2>nul | findstr /i "%TEST_DISTRO%" >nul 2>&1
if %errorlevel% equ 0 (
    echo  ⚠ %TEST_DISTRO% が既に存在します。
    echo.
    choice /c YN /m "  削除して再作成しますか？"
    if !errorlevel! equ 1 (
        echo  %TEST_DISTRO% をアンインストール中...
        wsl --unregister %TEST_DISTRO%
        echo   OK
    ) else (
        echo  キャンセルしました。
        pause
        exit /b 0
    )
)

echo.
echo  %TEST_DISTRO% をインストールします...
wsl --install -d %TEST_DISTRO%
echo.
echo  ユーザー設定が終わったら exit して
echo  戻ってきてください。
pause

echo.
echo  テストモードでセットアップを実行します...
call "%~dp0setup-windows.bat" --test

echo.
echo  ============================================
echo   テスト完了！
echo   テスト環境を削除するには
echo   test-cleanup.bat を実行してください。
echo  ============================================
echo.
pause
