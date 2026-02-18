# GitHub Project v2 設定

## Project v2 の作成

### GitHub Web から作成

1. GitHubにログイン
2. 右上のプロフィールアイコン → 「Your projects」
3. 「New project」→「Board」テンプレートを選択
4. プロジェクト名: `Phantom Operations`（任意）

### プロジェクト番号の確認

作成後、プロジェクトの URL を確認:
```
https://github.com/users/あなたのID/projects/1
                                                ↑ この番号
```

`setup.sh` 実行時に入力したプロジェクト番号と一致しているか確認してください。

## ステータスフィールドの設定

Project v2 に以下のステータスを追加してください:

| ステータス | 意味 |
|-----------|------|
| `No Status` | 起票直後（未トリアージ） |
| `Todo` | 対応可能なタスク |
| `In Progress` | 作業中 |
| `Done` | 完了 |

設定方法:
1. プロジェクトを開く
2. 右上の「...」→「Settings」
3. 「Fields」→「Status」を編集

## ラベルの設定

GitHubリポジトリに以下のラベルを作成してください:

```bash
# Jokerラベル（人間が対応するタスク）
gh label create "Joker" --color "FF6B6B" --repo あなたのID/あなたのリポジトリ名
```

## GitHub Actions の設定

`.github/workflows/sync_tasks.yml` でタスクの自動同期が設定されています。

必要なシークレット（リポジトリの Settings → Secrets から設定）:
- `GEMINI_API_KEY`: Gemini API キー
- `GOOGLE_CREDENTIALS`: Google OAuth の credentials.json の内容（JSON文字列）
- `GOOGLE_TOKEN`: token.json の内容（JSON文字列）

```bash
# シークレットの設定（GitHub CLI）
gh secret set GEMINI_API_KEY --body "あなたのAPIキー"
```
