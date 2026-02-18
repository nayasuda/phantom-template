# Google OAuth 設定

Gmail・Google Drive・Google Tasks を使うために OAuth 2.0 の設定が必要です。

## 手順

### 1. Google Cloud プロジェクトの作成

1. [Google Cloud Console](https://console.cloud.google.com/) を開く
2. 新しいプロジェクトを作成（例: `phantom-ops`）

### 2. APIの有効化

以下の API を有効化してください:

- **Gmail API**
- **Google Drive API**
- **Google Tasks API**
- **Google Calendar API**（オプション）
- **Admin SDK API**（Google Workspace 管理者のみ）

左メニュー → 「APIとサービス」→「ライブラリ」から検索して有効化。

### 3. OAuth 2.0 認証情報の作成

1. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuth クライアント ID」
2. アプリケーションの種類: **デスクトップアプリ**
3. 名前: `Phantom CLI`（任意）
4. 作成後、`credentials.json` をダウンロード

### 4. credentials.json の配置

```bash
# ダウンロードしたファイルをプロジェクトルートに配置
cp ~/Downloads/credentials.json ./phantom-antenna/credentials.json
```

### 5. 初回認証（トークン取得）

```bash
cd phantom-antenna
python3 scripts/generate_token.py
```

ブラウザが開くので、Googleアカウントでログインして認証を許可してください。
成功すると `token.json` が生成されます。

### ⚠️ 注意

- `credentials.json` と `token.json` は `.gitignore` に含まれています
- これらのファイルは**絶対にGitにコミットしないでください**

## 確認

```bash
# Gmail APIが使えるか確認
python3 -c "from phantom_antenna.src.skills.google_workspace import GoogleWorkspaceSkill; print('OK')"
```
