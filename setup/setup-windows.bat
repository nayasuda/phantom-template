@echo off
chcp 65001 > nul 2>&1
setlocal EnableDelayedExpansion

title Project Phantom - Windows Setup

echo.
echo  ============================================
echo    Project Phantom - Windows Setup
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
    powershell -command "Write-Host '  [Test Mode] Distro: Ubuntu-24.04' -ForegroundColor Yellow"
    echo.
)

:: -------------------------------------------------------------------
:: Step 1: 管理者権限チェック
:: -------------------------------------------------------------------
echo  [1/5] Checking admin privileges...
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    powershell -command "Write-Host '  Admin rights required.' -ForegroundColor Red"
    powershell -command "Write-Host '  Right-click -> Run as administrator' -ForegroundColor Red"
    echo.
    pause
    exit /b 1
)
echo   OK

:: -------------------------------------------------------------------
:: Step 2: WSL の確認・インストール
:: -------------------------------------------------------------------
echo.
echo  [2/5] Checking WSL...
wsl --status >nul 2>&1
if %errorlevel% neq 0 (
    echo   Installing WSL...
    wsl --install --no-distribution
    echo.
    echo  ================================================
    powershell -command "Write-Host '  WSL installed. Please restart your PC' -ForegroundColor Green"
    powershell -command "Write-Host '  and run this file again.' -ForegroundColor Green"
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
echo  [3/5] Checking %DISTRO%...
wsl -l -q 2>nul | findstr /i "%DISTRO%" >nul 2>&1
if %errorlevel% neq 0 (
    echo   Installing %DISTRO%...
    wsl --install -d %DISTRO%
    echo.
    powershell -command "Write-Host '  Set username and password, then type exit' -ForegroundColor Cyan"
    echo.
    pause
)
echo   OK

:: -------------------------------------------------------------------
:: Step 4: WSL内の前提ツールをインストール
:: -------------------------------------------------------------------
echo.
echo  [4/5] Installing tools in WSL...
echo   (Node.js, Gemini CLI, GitHub CLI, wslu)
echo.

set "PREREQS_WIN=%~dp0install-prereqs.sh"
for /f "delims=" %%i in ('wsl -d %DISTRO% -- wslpath -u "%PREREQS_WIN%"') do set "PREREQS_WSL=%%i"

wsl -d %DISTRO% -- bash "%PREREQS_WSL%"
if %errorlevel% neq 0 (
    echo.
    powershell -command "Write-Host '  WSL setup failed.' -ForegroundColor Red"
    pause
    exit /b 1
)

:: -------------------------------------------------------------------
:: Step 5: テンプレートをクローン + ショートカット作成
:: -------------------------------------------------------------------
echo.
echo  [5/5] Setting up project...

wsl -d %DISTRO% -- bash -lc "if [ -d ~/%WORKSPACE_NAME%/.git ]; then echo 'Already cloned.'; else git clone %REPO_URL% ~/%WORKSPACE_NAME% && echo 'Clone complete.'; fi"

:: デスクトップパスを正確に取得（日本語Windows / OneDrive対応）
for /f "delims=" %%i in ('powershell -command "[Environment]::GetFolderPath('Desktop')"') do set "DESKTOP=%%i"

if not exist "!DESKTOP!" (
    set "DESKTOP=%USERPROFILE%\Desktop"
)

if not exist "!DESKTOP!\Phantom.bat" (
    > "!DESKTOP!\Phantom.bat" echo @echo off
    >> "!DESKTOP!\Phantom.bat" echo title Phantom
    >> "!DESKTOP!\Phantom.bat" echo wsl -d %DISTRO% -- bash ~/%WORKSPACE_NAME%/start.sh
    echo   Created: Phantom.bat
)

if not exist "!DESKTOP!\Phantom Update.bat" (
    > "!DESKTOP!\Phantom Update.bat" echo @echo off
    >> "!DESKTOP!\Phantom Update.bat" echo title Phantom Update
    >> "!DESKTOP!\Phantom Update.bat" echo wsl -d %DISTRO% -- bash ~/%WORKSPACE_NAME%/update.sh
    >> "!DESKTOP!\Phantom Update.bat" echo pause
    echo   Created: Phantom Update.bat
)

echo   OK

:: -------------------------------------------------------------------
:: 完了 → そのまま Phantom を起動
:: -------------------------------------------------------------------
echo.
echo  ============================================
echo    Setup complete!
echo.
echo    Launching Phantom...
echo    Navi will guide you through the rest.
echo  ============================================
echo.

wsl -d %DISTRO% -- bash ~/%WORKSPACE_NAME%/start.sh
