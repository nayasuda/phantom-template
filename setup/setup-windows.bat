@echo off
chcp 65001 > nul 2>&1
setlocal EnableDelayedExpansion

title Project Phantom - Windows Setup

echo.
echo  ============================================
echo    Project Phantom - Windows Setup
echo    WSL + Gemini CLI 環境を自動構築します
echo  ============================================
echo.

:: -------------------------------------------------------------------
:: 引数チェック（テストモード対応）
:: -------------------------------------------------------------------
if not defined DISTRO set "DISTRO=Ubuntu"
set "TEST_MODE=0"
if not defined REPO_URL set "REPO_URL=https://github.com/nayasuda/phantom-template.git"
if not defined WORKSPACE_NAME set "WORKSPACE_NAME=phantom-ops"

if "%~1"=="--test" (
    set "DISTRO=Ubuntu-24.04"
    set "TEST_MODE=1"
    echo  [テストモード] ディストロ: !DISTRO!
    echo.
)

:: -------------------------------------------------------------------
:: Step 1: 管理者権限チェック
:: -------------------------------------------------------------------
echo  [1/7] 管理者権限の確認...
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  管理者権限が必要です。
    echo  右クリック → 「管理者として実行」してください。
    echo.
    pause
    exit /b 1
)
echo   OK

:: -------------------------------------------------------------------
:: Step 2: WSL の確認・インストール
:: -------------------------------------------------------------------
echo.
echo  [2/7] WSL の確認...
wsl --status >nul 2>&1
if %errorlevel% neq 0 (
    echo   WSL をインストールします...
    wsl --install --no-distribution
    echo.
    echo  ================================================
    echo    WSL のインストールが完了しました。
    echo    PC を再起動してから、もう一度このファイルを
    echo    実行してください。
    echo  ================================================
    echo.
    pause
    exit /b 0
)
echo   OK

:: -------------------------------------------------------------------
:: Step 3: Ubuntu ディストロの確認・インストール
:: -------------------------------------------------------------------
echo.
echo  [3/7] %DISTRO% の確認...
wsl -l -q 2>nul | findstr /i "%DISTRO%" >nul 2>&1
if %errorlevel% neq 0 (
    echo   %DISTRO% をインストールします（数分かかります）...
    wsl --install -d %DISTRO%
    echo.
    echo  ユーザー名とパスワードの設定が求められる場合があります。
    echo  設定が終わったら exit と入力してください。
    echo.
    pause
)
echo   OK

:: -------------------------------------------------------------------
:: Step 4: WSL内の前提ツールをインストール
:: -------------------------------------------------------------------
echo.
echo  [4/7] WSL 内の環境構築中...
echo   （Node.js, Gemini CLI, GitHub CLI をインストール）
echo.

set "PREREQS_WIN=%~dp0install-prereqs.sh"
for /f "delims=" %%i in ('wsl -d %DISTRO% -- wslpath -u "%PREREQS_WIN%"') do set "PREREQS_WSL=%%i"

wsl -d %DISTRO% -- bash "%PREREQS_WSL%"
if %errorlevel% neq 0 (
    echo.
    echo  WSL 内セットアップでエラーが発生しました。
    pause
    exit /b 1
)

:: -------------------------------------------------------------------
:: Step 5: テンプレートをクローン
:: -------------------------------------------------------------------
echo.
echo  [5/7] プロジェクトのセットアップ...

wsl -d %DISTRO% -- bash -lc "if [ -d ~/%WORKSPACE_NAME%/.git ]; then echo 'リポジトリは既に存在します'; else git clone %REPO_URL% ~/%WORKSPACE_NAME% && echo 'クローン完了'; fi"

echo.
echo  ============================================
echo   セットアップウィザード（GitHub連携）を
echo   今実行しますか？
echo.
echo   後からでも実行できます。
echo   スキップしても、ナビとの会話や
echo   クイーンの作戦立案は使えます。
echo  ============================================
echo.
choice /c YN /m "  今すぐ実行しますか？"
if !errorlevel! equ 1 (
    echo.
    echo  セットアップウィザードを起動します。
    echo  いくつかの質問に答えてください。
    echo.
    wsl -d %DISTRO% -- bash -lc "cd ~/%WORKSPACE_NAME% && bash setup.sh"
) else (
    echo.
    echo  スキップしました。後で実行するには:
    echo  Ubuntu ターミナルで:
    echo    cd ~/%WORKSPACE_NAME% ^&^& bash setup.sh
    echo.
)

:: -------------------------------------------------------------------
:: Step 6: 認証ガイド
:: -------------------------------------------------------------------
echo.
echo  [6/7] 認証の設定
echo.
echo  ============================================
echo   これから認証を行います。
echo   ブラウザが開くので、Google アカウントで
echo   ログインしてください。
echo  ============================================
echo.

:: Gemini CLI 認証
echo  --- 認証 1/2: Gemini CLI ---
echo  ブラウザが開きます。
wsl -d %DISTRO% -- bash -lc "gemini --auth 2>/dev/null || echo '手動で gemini を起動して認証してください'"
echo.

:: GitHub CLI 認証
echo  --- 認証 2/2: GitHub ---
wsl -d %DISTRO% -- bash -lc "gh auth status 2>/dev/null && echo 'GitHub: 認証済み' || (echo 'ブラウザで GitHub にログインしてください' && gh auth login -h github.com -p https -w)"
echo.

:: -------------------------------------------------------------------
:: Step 7: ショートカット作成
:: -------------------------------------------------------------------
echo.
echo  [7/7] デスクトップにショートカットを作成...

set "DESKTOP=%USERPROFILE%\Desktop"

if not exist "%DESKTOP%\Phantom.bat" (
    (
        echo @echo off
        echo chcp 65001 ^> nul 2^>^&1
        echo title Phantom
        echo wsl -d %DISTRO% -- bash -lc "cd ~/%WORKSPACE_NAME% ^&^& gemini"
    ) > "%DESKTOP%\Phantom.bat"
    echo   Phantom.bat を作成しました
)

if not exist "%DESKTOP%\Phantom Update.bat" (
    (
        echo @echo off
        echo chcp 65001 ^> nul 2^>^&1
        echo title Phantom Update
        echo echo Phantom を更新しています...
        echo wsl -d %DISTRO% -- bash -lc "cd ~/%WORKSPACE_NAME% ^&^& git pull origin main --ff-only"
        echo echo.
        echo echo 更新完了！
        echo pause
    ) > "%DESKTOP%\Phantom Update.bat"
    echo   Phantom Update.bat を作成しました
)

echo   OK

:: -------------------------------------------------------------------
:: 完了
:: -------------------------------------------------------------------
echo.
echo  ============================================
echo    セットアップ完了！
echo.
echo    デスクトップの「Phantom」をダブルクリック
echo    するだけで使えます。
echo.
echo    .gemini/.env の APIキー設定を忘れずに！
echo    詳細は ~/%WORKSPACE_NAME%/README.md を
echo    確認してください。
echo  ============================================
echo.
pause
