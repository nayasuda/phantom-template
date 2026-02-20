#!/usr/bin/env bash
# =======================================================
#  Project Phantom - WSL prerequisite installer
#  Node.js / Gemini CLI / GitHub CLI をインストール
# =======================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
skip() { echo -e "  ${YELLOW}→${NC} $1 (スキップ: 既にインストール済み)"; }

echo ""
echo "========================================"
echo " WSL 前提ツール インストーラー"
echo "========================================"
echo ""

# -------------------------------------------------------------------
# nvm + Node.js
# -------------------------------------------------------------------
echo "[1/3] Node.js ..."
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    set +u
    source "$NVM_DIR/nvm.sh"
    set -u
fi

if command -v node &>/dev/null; then
    skip "Node.js $(node -v)"
else
    if ! command -v nvm &>/dev/null; then
        echo "  nvm をインストール..."
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        set +u
        source "$NVM_DIR/nvm.sh"
        set -u
    fi
    set +u
    nvm install --lts
    nvm use --lts
    set -u
    ok "Node.js $(node -v)"
fi

# -------------------------------------------------------------------
# Gemini CLI
# -------------------------------------------------------------------
echo ""
echo "[2/3] Gemini CLI ..."
if command -v gemini &>/dev/null; then
    skip "Gemini CLI ($(gemini --version 2>/dev/null || echo 'installed'))"
else
    echo "  Gemini CLI をインストール..."
    npm install -g @google/gemini-cli
    if command -v gemini &>/dev/null; then
        ok "Gemini CLI"
    else
        echo "  ⚠ Gemini CLI の自動インストールに失敗しました"
        echo "    手動: npm install -g @google/gemini-cli"
    fi
fi

# -------------------------------------------------------------------
# GitHub CLI
# -------------------------------------------------------------------
echo ""
echo "[3/3] GitHub CLI ..."
if command -v gh &>/dev/null; then
    skip "gh $(gh --version | head -1)"
else
    echo "  GitHub CLI をインストール..."
    (type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y))
    sudo mkdir -p -m 755 /etc/apt/keyrings
    wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null
    sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update -qq
    sudo apt install gh -y -qq
    ok "gh $(gh --version | head -1)"
fi

# -------------------------------------------------------------------
# Python3 (ほぼプリインストール済み)
# -------------------------------------------------------------------
echo ""
if ! command -v python3 &>/dev/null; then
    echo "Python3 をインストール..."
    sudo apt update -qq && sudo apt install python3 python3-pip -y -qq
    ok "Python3"
fi

echo ""
echo "========================================"
echo " 前提ツールのインストール完了！"
echo "========================================"
echo ""
