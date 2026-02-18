# Gemini CLI 設定

## インストール

```bash
npm install -g @google/gemini-cli
gemini --version
```

## 推奨拡張機能のインストール

Gemini CLI を一度起動してから、別ターミナルで以下を実行してください:

```bash
# GitHub 連携（Project v2操作に必須）
gemini extension install https://github.com/github/github-mcp-server

# ドキュメント参照（context7）
gemini extension install https://github.com/upstash/context7

# Google Workspace 連携（Gmail・Drive・Tasks）
# ※ 別途カスタム設定が必要。docs/setup/ を参照
```

インストール後、Gemini CLI を再起動してください（`/quit` → `gemini`）。

## 設定ファイル

`settings.json` はすでに設定済みです:
- ナビ: `gemini-3-flash-preview`（高速・コスパ重視）
- クイーン: `gemini-3-pro-preview`（複雑な推論向け）
- その他エージェント: `gemini-3-flash-preview`

## 起動

```bash
cd /プロジェクトのパス
gemini
```

起動時に自動的に:
- Git の状態確認
- GitHub Project v2 のタスク一覧取得
- 利用可能なコマンド案内

が実行されます。

## 主なコマンド

| コマンド | 説明 |
|---------|------|
| `/mission` | ここまでの会話をミッション化して実行に移す |
| `/plan` | 不明点を確認してから計画を立てる |
| `/debug` | バグ・エラーを調査する |
| `/agents list` | エージェント一覧を確認 |
| `/extensions list` | 拡張機能一覧を確認 |
| `/stats` | トークン使用量を確認 |
| `/compress` | コンテキストを圧縮（長いセッション向け） |

## コスト目安

| 使い方 | 月額目安 |
|--------|---------|
| 軽い利用（1日1-2時間） | $5〜20 |
| 本格開発（フルタイム） | $50〜150 |

※ Gemini 3 Flash を主体にすることでコストを抑えられます。
