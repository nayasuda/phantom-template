#!/bin/bash
# =============================================================================
# Project Phantom - Initial Setup Script
# =============================================================================
# このスクリプトを実行すると、テンプレートをあなたの環境向けに設定します。
# Run this script to configure the template for your environment.
#
# Usage: bash setup.sh
# =============================================================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   🕵️  Project Phantom - Initial Setup    ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

# =============================================================================
# 前提条件チェック
# =============================================================================
echo -e "${CYAN}[1/3] 前提条件を確認中...${RESET}"

MISSING=()
command -v git >/dev/null 2>&1 || MISSING+=("git")
command -v python3 >/dev/null 2>&1 || MISSING+=("python3")
command -v node >/dev/null 2>&1 || MISSING+=("Node.js (v18+)")
command -v npm >/dev/null 2>&1 || MISSING+=("npm")
command -v gh >/dev/null 2>&1 || MISSING+=("GitHub CLI (gh)")

if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${RED}以下のツールが見つかりません:${RESET}"
    for tool in "${MISSING[@]}"; do
        echo -e "  - $tool"
    done
    echo ""
    echo "インストール後、再度このスクリプトを実行してください。"
    exit 1
fi

# Gemini CLI チェック
if ! command -v gemini >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Gemini CLI が見つかりません。後でインストールしてください:${RESET}"
    echo "  npm install -g @google/gemini-cli"
fi

echo -e "${GREEN}✓ 前提条件 OK${RESET}"
echo ""

# =============================================================================
# ユーザー情報の入力
# =============================================================================
echo -e "${CYAN}[2/3] セットアップ情報を入力してください${RESET}"
echo ""

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

read -p "$(echo -e "${BOLD}GitHubユーザー名${RESET} (例: yourname): ")" GITHUB_USERNAME
while [ -z "$GITHUB_USERNAME" ]; do
    echo -e "${RED}GitHubユーザー名は必須です${RESET}"
    read -p "GitHubユーザー名: " GITHUB_USERNAME
done

read -p "$(echo -e "${BOLD}リポジトリ名${RESET} [phantom-ops]: ")" REPO_NAME
REPO_NAME="${REPO_NAME:-phantom-ops}"

read -p "$(echo -e "${BOLD}GitHub Project v2 番号${RESET} (例: 1): ")" PROJECT_NUMBER
while [ -z "$PROJECT_NUMBER" ]; do
    echo -e "${RED}Project番号は必須です。GitHubのProject URLから確認できます${RESET}"
    read -p "Project番号: " PROJECT_NUMBER
done

read -p "$(echo -e "${BOLD}あなたのフルネーム${RESET} (例: 山田 太郎): ")" USER_FULLNAME
while [ -z "$USER_FULLNAME" ]; do
    echo -e "${RED}フルネームは必須です${RESET}"
    read -p "フルネーム: " USER_FULLNAME
done

read -p "$(echo -e "${BOLD}メールアドレス${RESET} (例: yourname@company.com): ")" USER_EMAIL
while [ -z "$USER_EMAIL" ]; do
    echo -e "${RED}メールアドレスは必須です${RESET}"
    read -p "メールアドレス: " USER_EMAIL
done

read -p "$(echo -e "${BOLD}会社名${RESET} (例: MyCompany): ")" COMPANY_NAME
COMPANY_NAME="${COMPANY_NAME:-MyCompany}"

read -p "$(echo -e "${BOLD}会社ドメイン${RESET} (例: mycompany.com): ")" COMPANY_DOMAIN
COMPANY_DOMAIN="${COMPANY_DOMAIN:-mycompany.com}"

echo ""
echo -e "${YELLOW}以下の設定で進めます:${RESET}"
echo "  GitHubユーザー名: $GITHUB_USERNAME"
echo "  リポジトリ名:     $REPO_NAME"
echo "  Project番号:      $PROJECT_NUMBER"
echo "  フルネーム:       $USER_FULLNAME"
echo "  メールアドレス:   $USER_EMAIL"
echo "  会社名:           $COMPANY_NAME"
echo "  会社ドメイン:     $COMPANY_DOMAIN"
echo "  プロジェクトDir:  $PROJECT_DIR"
echo ""
read -p "続行しますか？ [Y/n]: " CONFIRM
CONFIRM="${CONFIRM:-Y}"
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "セットアップを中止しました。"
    exit 0
fi

# =============================================================================
# プレースホルダーの置換
# =============================================================================
echo ""
echo -e "${CYAN}[3/3] ファイルを設定中...${RESET}"

FILES=$(find "$PROJECT_DIR" -type f \( -name "*.py" -o -name "*.md" -o -name "*.sh" -o -name "*.toml" -o -name "*.json" -o -name "*.yml" \) ! -path '*/.git/*' ! -name 'setup.sh')

echo "$FILES" | xargs sed -i "s|{{GITHUB_USERNAME}}|$GITHUB_USERNAME|g"
echo "$FILES" | xargs sed -i "s|{{REPO_NAME}}|$REPO_NAME|g"
echo "$FILES" | xargs sed -i "s|{{PROJECT_NUMBER}}|$PROJECT_NUMBER|g"
echo "$FILES" | xargs sed -i "s|{{USER_FULLNAME}}|$USER_FULLNAME|g"
echo "$FILES" | xargs sed -i "s|{{USER_EMAIL}}|$USER_EMAIL|g"
echo "$FILES" | xargs sed -i "s|{{COMPANY_NAME}}|$COMPANY_NAME|g"
echo "$FILES" | xargs sed -i "s|{{COMPANY_DOMAIN}}|$COMPANY_DOMAIN|g"
echo "$FILES" | xargs sed -i "s|{{PROJECT_DIR}}|$PROJECT_DIR|g"

echo -e "${GREEN}✓ ファイルの設定完了${RESET}"

# =============================================================================
# .env ファイルの生成
# =============================================================================
if [ ! -f "$PROJECT_DIR/.gemini/.env" ]; then
    cp "$PROJECT_DIR/.gemini/.env.example" "$PROJECT_DIR/.gemini/.env"
    sed -i "s|/absolute/path/to/{{REPO_NAME}}/.gemini/system.md|$PROJECT_DIR/.gemini/system.md|g" "$PROJECT_DIR/.gemini/.env"
    echo -e "${GREEN}✓ .gemini/.env を生成しました${RESET}"
else
    echo -e "${YELLOW}⚠ .gemini/.env は既に存在するためスキップしました${RESET}"
fi

# =============================================================================
# 次のステップ案内
# =============================================================================
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   ✅ 基本設定完了！次のステップへ        ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${BOLD}📋 残りの手順:${RESET}"
echo ""
echo -e "${BOLD}1. APIキーの設定${RESET}"
echo "   .gemini/.env を開いて以下を設定してください:"
echo "   - GEMINI_API_KEY: https://aistudio.google.com/apikey"
echo "   - GITHUB_PERSONAL_ACCESS_TOKEN: https://github.com/settings/tokens"
echo ""
echo -e "${BOLD}2. Google OAuth の設定${RESET}"
echo "   Gmail・Drive・Tasks の連携に必要です:"
echo "   - Google Cloud Console でプロジェクト作成"
echo "   - OAuth 2.0 認証情報を作成"
echo "   - credentials.json を phantom-antenna/ に配置"
echo "   詳細: docs/setup/02_google_oauth.md"
echo ""
echo -e "${BOLD}3. GitHub Project v2 の確認${RESET}"
echo "   プロジェクト番号 $PROJECT_NUMBER が正しいか確認:"
echo "   gh project list --owner $GITHUB_USERNAME"
echo ""
echo -e "${BOLD}4. Gemini CLI のインストールと拡張機能${RESET}"
echo "   npm install -g @google/gemini-cli"
echo "   詳細: docs/setup/04_gemini_cli.md"
echo ""
echo -e "${BOLD}5. 動作確認${RESET}"
echo "   cd $PROJECT_DIR && gemini"
echo ""
echo -e "${GREEN}🎉 セットアップ完了！ enjoy Project Phantom!${RESET}"
echo ""
