# 前提条件・環境準備

> **Windows の方へ:** `setup/setup-windows.bat` を管理者として実行すれば、以下のツールは自動でインストールされます。セキュリティソフトにブロックされる場合は、以下の手動手順で進めてください。

## 必要なツール

### 1. Node.js (v18 以上)

```bash
# バージョン確認
node --version

# インストール（未インストールの場合）
# https://nodejs.org/ からダウンロード、または
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2. Python (3.10 以上)

```bash
python3 --version

# Ubuntu/Debian
sudo apt-get install python3 python3-pip

# 依存パッケージのインストール
pip install -r requirements.txt
```

### 3. GitHub CLI

```bash
gh --version

# インストール
# https://cli.github.com/ を参照、または
sudo apt-get install gh

# 認証
gh auth login
```

### 4. Gemini CLI

```bash
npm install -g @google/gemini-cli
gemini --version
```

## 必要なサービスとアカウント

### Google Workspace
- **Gmail** — メール分類・自動処理に使用
- **Google Drive** — ファイル保存に使用
- **Google Tasks** — タスク管理（GitHub Project v2 と同期）
- **Google Calendar** — スケジュール確認に使用（オプション）

→ [Google OAuth 設定](02_google_oauth.md)

### GitHub
- パブリックまたはプライベートリポジトリ
- **GitHub Project v2** の作成が必要
  → [GitHub Project v2 設定](03_github_project.md)
- GitHub Personal Access Token（PAT）
  - スコープ: `repo`, `project`, `read:org`
  - 取得: https://github.com/settings/tokens

### Gemini API
- API キーの取得: https://aistudio.google.com/apikey
- 無料枠あり（制限あり）
- 推奨: 従量課金の有効化

## 環境変数の設定

`setup.sh` 実行後、`.gemini/.env` に以下を設定してください:

```env
GEMINI_API_KEY=あなたのGeminiAPIキー
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_あなたのトークン
GEMINI_SYSTEM_MD=/プロジェクトの絶対パス/.gemini/system.md
```
