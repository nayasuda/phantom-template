# 🕵️ Project Phantom

**Gemini CLI で動く、マルチエージェント AI システムのテンプレートです。**

10人の専門エージェントが連携して、GitHub プロジェクト管理から Gmail 分類まで、日常業務を自動化します。

## ✨ 特徴

- **10人の専門サブエージェント** — それぞれ異なる役割（戦略立案・実装・デバッグなど）
- **Gemini CLI ネイティブ** — ターミナルで動く、追加インフラ不要
- **GitHub Project v2 連携** — Google Tasks と双方向同期
- **Gmail 自動分類** — Gemini AI でメールをアクション別に仕分け
- **PDCA 自己改善** — エージェントが失敗を記録して学習
- **フック機構** — ツール実行前後のガード（シークレット検知・git 安全管理など）

## 🚀 クイックスタート

### 前提条件

**動作確認済みOS:** Linux、macOS、Windows（WSL2 / Ubuntu 推奨）

| ツール | バージョン | 用途 |
|--------|-----------|------|
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | 最新版 | メインランタイム |
| [Node.js](https://nodejs.org/) | v18以上 | Gemini CLI の依存関係 |
| [Python](https://python.org/) | 3.10以上 | スクリプト・フック |
| [GitHub CLI](https://cli.github.com/) | 最新版 | GitHub 連携 |
| [Git](https://git-scm.com/) | 最新版 | バージョン管理 |

> **Windowsの方へ:** WSL2（Ubuntu）での動作を確認済みです。PowerShell ネイティブ環境は非対応です。下記の [Windows 自動セットアップ](#windows-自動セットアップ) を参照してください。

**必要なサービス:**
- Google Workspace（Gmail、Google Drive、Google Tasks）
- GitHub アカウント（Project v2）
- Gemini API キー（[こちらから取得](https://aistudio.google.com/apikey)）

### インストール手順

#### Windows（自動セットアップ）

`setup/setup-windows.bat` を右クリック → **「管理者として実行」** するだけ。WSL、Ubuntu、Node.js、Gemini CLI、GitHub CLI のインストールからセットアップウィザードまで自動で進みます。

> **⚠️ セキュリティソフトの注意:** Norton や Windows Defender SmartScreen などのセキュリティソフトが `.bat` ファイルの実行をブロックすることがあります。その場合は:
> 1. セキュリティソフト側で許可する、または
> 2. 下の手動セットアップを WSL ターミナルから直接実行してください。

#### Linux / macOS（手動セットアップ）

```bash
# 1. このテンプレートをクローン
git clone https://github.com/あなたのID/phantom-template.git
cd phantom-template

# 2. セットアップウィザードを実行
bash setup.sh

# 3. APIキーを設定
#    .gemini/.env を開いてキーを入力

# 4. Gemini CLI をインストール（まだの場合）
npm install -g @google/gemini-cli

# 5. 起動！
bash phantom_startup.sh
tmux attach -t phantom:main

# 停止するときは Gemini CLI 内で /quit → その後:
bash phantom_shutdown.sh
```

> **💡 ナビが起動したら `/initial_setup` と入力！**
> Google OAuth・GitHub Secrets・Actions スケジュール有効化をナビと一緒に進められます。
> 各ステップで「続ける / スキップ / 中断」を選べるので、途中でやめても大丈夫です。

## 🎭 エージェント紹介

| エージェント | 役割 | 得意分野 |
|------------|------|---------|
| **ナビ** 🛰️ | オーケストレーター | 全エージェントを指揮、あなたとの対話担当 |
| **クイーン** 👑 | 戦略立案 | ミッション計画と品質チェック |
| **モナ** 🐱 | 現場監督 | タスク分解・PRレビュー |
| **スカル** 💀 | エンジニア | Git操作・シェル実行 |
| **パンサー** 💃 | ライター | ドキュメント・日報作成 |
| **ウルフ** 🐺 | バックエンド | API・サーバーサイド |
| **フォックス** 🦊 | フロントエンド | UI・クライアントサイド |
| **ノワール** 🎀 | テスター | テスト作成・検証 |
| **ヴァイオレット** 🎻 | リサーチャー | 技術調査・比較検討 |
| **クロウ** 🪶 | デバッガー | バグ分析・障害診断 |
| **ソフィア** 🛡️ | セキュリティ | 脆弱性チェック・炎上リスク確認 |

## 📁 ファイル構成

```
phantom-template/
├── .gemini/
│   ├── system.md          # ナビのコアシステムプロンプト
│   ├── agents/            # 10人のサブエージェント定義
│   ├── hooks/             # 実行前後のガード処理
│   ├── commands/          # カスタムスラッシュコマンド（/mission, /plan 等）
│   └── skills/            # 再利用可能なスキルドキュメント
├── scripts/               # 自動化スクリプト（同期・クリーンアップ等）
├── phantom-antenna/       # Gmail 分類モジュール
│   └── src/skills/
└── .github/workflows/     # スケジュール実行用 GitHub Actions
```

## 🎮 使い方

起動スクリプトを使ってナビを起動します。

```bash
# 起動
bash phantom_startup.sh
tmux attach -t phantom:main

# 停止（Gemini CLI 内で /quit してから）
bash phantom_shutdown.sh
```

**初回起動後は `/initial_setup` で初期設定をナビと進めましょう。**

### 主なコマンド

| コマンド | 説明 |
|---------|------|
| `/mission` | 会話内容をミッション化して実行に移す |
| `/plan` | 不明点を確認してから詳細計画を作成（Cursor の Plan モード相当） |
| `/debug` | バグ・エラーの根本原因を特定 |

### 動作モード

**通常モード（デフォルト）:** ナビと自由に壁打ち・相談。ファイル変更や git 操作は行わない。

**ミッションモード（`/mission` で発動）:** 計画 → 承認 → 実行の全フローが動く。

## 🔧 フック機能（自動安全ガード）

| フック | タイミング | 役割 |
|-------|-----------|------|
| `block_risky_git.py` | git 操作前 | `git add .` など危険な操作をブロック |
| `block_secrets.py` | ファイル書き込み前 | APIキーなどの秘密情報をブロック |
| `validate_response.py` | エージェント応答後 | レポート不足を検知してリトライ |
| `log_shell_command.py` | シェルコマンド後 | 操作ログを自動記録 |
| `session_start.py` | セッション開始時 | Git状態・タスクダッシュボードを自動注入 |

## 📚 詳細ドキュメント

- [💡 これ何ができるの？（具体的なユースケース）](docs/what_can_phantom_do.md)
- [🔰 はじめてのセットアップ（非エンジニア向け）](docs/setup/00_quickstart_for_beginners.md)
- [前提条件・環境準備](docs/setup/01_prerequisites.md)
- [Google OAuth 設定](docs/setup/02_google_oauth.md)
- [GitHub Project v2 設定](docs/setup/03_github_project.md)
- [Gemini CLI 設定](docs/setup/04_gemini_cli.md)

## 📄 ライセンス

MIT License
