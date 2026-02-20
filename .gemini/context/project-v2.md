## 💬 GitHubコメントのルール

GitHubでコメントする際は、以下のフォーマットを厳守する。

```markdown
### 🛰️ Navi

コメント本文...

**To Queen:** 〇〇を確認して。
```

- **ヘッダー**: 自分のアイコンと名前を `### 🛰️ Navi` の形式で書く
- **メンション**: GitHubの機能（`@user`）は使わない。`**To Name:**` を使う

### 各メンバーのコメントヘッダー

| メンバー | ヘッダー |
|----------|----------|
| ナビ | `### 🛰️ Navi` |
| クイーン | `### 👑 Queen` |
| モナ | `### 🐱 Mona` |
| スカル | `### 💀 Skull` |
| パンサー | `### 💃 Panther` |
| フォックス | `### 🦊 Fox` |
| ウルフ | `### 🐺 Wolf` |
| ノワール | `### 🎀 Noir` |
| ヴァイオレット | `### 🎻 Violet` |
| クロウ | `### 🪶 Crow` |
| ソフィア | `### 🛡️ Sophia` |

## 🔧 Project v2 ワークフロー（大原則）

### ⚠️ 超重要: プロジェクトはユーザーレベル！

**「Phantom Operations」はリポジトリ内のProjectではなく、ユーザー `{{GITHUB_USERNAME}}` 直下のProjectです。**
**SoT（単一ソース）は Project v2。Issueは必要時のみ作成する。**

### Project項目作成（ナビの仕事）— 二重登録を防げ！

**⚠️ draft item と Issue を同じタスクで両方作るな！ボードに同じカードが2枚できる。**

```
# パターンA: コード変更なし → draft item のみ
gh project item-create {{PROJECT_NUMBER}} --owner "{{GITHUB_USERNAME}}" --title "機能の追加" --body "概要..."

# パターンB: コード変更あり → Issue を作って Project に追加（draftは作らない！）
gh issue create --title "タイトル" --body "概要..."
gh project item-add {{PROJECT_NUMBER}} --owner "{{GITHUB_USERNAME}}" --url "https://github.com/{{GITHUB_USERNAME}}/{{REPO_NAME}}/issues/<番号>"
```

**判断フロー:**
```
コード変更 or PR が必要？
  → Yes: Issue 作成 → item-add（draft 作るな）
  → No:  draft item のみ（Issue 作るな）
```

### draft item 運用ルール（明確化）

- **draft item = ジョーカーとエージェントの共有タスクボード**。軽いタスクも重要な通知もここで管理する。
- コード変更を伴わないタスク（調査・方針決定・メモ・運用通知など）はすべて draft item で作成。
- draft item にもエージェントは進捗を残すこと（ナビ経由OK）。
- 完了したら Done に移動。対応不要の通知系は作成時に本文末尾に `Status: 完了（通知のみ）` と書く。

### コメント運用（必須）

- 各エージェントの進捗コメントは必須。
- **Issueがあるタスク**: `gh issue comment` で記録。
- **Issueなし（Project draftのみ）タスク**: ナビが代理でProject item本文に追記（`gh project item-edit --id <ITEM_ID> --body ...`）。
- どちらでも、ヘッダーは `### 👑 Queen` / `### 🐱 Mona` / `### 💀 Skull` 形式を維持する。

### Issue作成条件（簡単・厳格）

以下のどれかを満たすときだけIssueを作成する：
1. 実コード変更があり、PRと双方向リンクが必要
2. 監査・外部共有・長期追跡のためURL固定が必要
3. ジョーカーが明示的に「Issue作って」と指示した

上記に当てはまらないタスクは **Project v2 draft itemのみ** で運用する。

### タスク担当者ラベル

- `Joker`: ジョーカーが手動で対応するタスク（ブラウザ操作、外部サービス設定、権限承認等）
- ラベルなし: ナビが内容から自動判断（手動作業っぽければジョーカー、それ以外は怪盗団）
- タスク作成時、明らかにジョーカー向けなら `Joker` ラベルを付けること
- SessionStartフックの自動分類でも、`Joker` ラベルがあれば必ずジョーカー側に表示される

### 参照優先順位（情報汚染を防ぐ）

運用判断は以下の順序で参照すること：
1. GitHub Project v2 の現行アイテム状態（最優先）
2. 実行対象の現行コード・設定（`scripts/`, `.github/workflows/`, `.gemini/*.md`）
3. ジョーカーの直近指示

以下は**履歴・参考資料**として扱い、運用判断の根拠にしない（ジョーカーが明示指定した時だけ参照可）：
- `backups/**`
- `reports/daily/**`
- `docs/NOTE_DRAFT_*.md`
- `project_items.json`
- `pr_*.diff`

### ステータスの流れ（GitHub Project v2 上で管理）

```
No Status → Todo → In Progress → Done → (7日後) Archive
(起票)     (対応可能)  (作業中)     (完了)      (自動アーカイブ)
```

| ステータス | 意味 | 誰が変更する |
|:--|:--|:--|
| No Status | 起票された直後（未トリアージ） | sync スクリプトが自動で Todo に移動 |
| Todo | 対応可能なタスク | sync スクリプト / エージェント |
| In Progress | 作業中 | エージェント / 手動 |
| Done | 完了 | エージェント（Issue クローズ時）/ 手動 |
| Archive | 7日以上 Done のまま | sync スクリプトが自動アーカイブ |

### アーカイブ運用（自動化済み）

完了アイテムが溜まると `gh project item-list` の取得が重くなり、セッション起動時のタスクダッシュボードに影響する。

**ルール:**
- Done から **7日以上** 経過したアイテムは `sync_google_tasks.py` が **自動アーカイブ** する
- 直近の完了アイテムは Done に残す（達成の可視化のため）
- アーカイブは**削除ではない**。Project の「Archived items」からいつでも確認・復元可能
- 手動でアーカイブしたい場合: `gh project item-archive {{PROJECT_NUMBER}} --owner "{{GITHUB_USERNAME}}" --id <ITEM_ID>`

### Google Tasks ↔ Project v2 自動同期

Google Tasks と Project v2 は `sync_google_tasks.py` で **双方向同期** されている。

**同期タイミング:**
- GitHub Actions (`sync_tasks.yml`) が **30分おき（JST 9:00〜18:30）** に自動実行
- 即時同期したい場合: `gh workflow run sync_tasks.yml`（GitHub Actions の Web UI からも実行可能）

**同期の流れ:**
```
[Google Tasks → Project v2]
  スマホ等で Google Tasks に追加
    → 次回 sync 時に Project v2 に Draft Item として作成（Todo に自動設定）

[Project v2 → Google Tasks]
  エージェントが Issue を close、または手動で Done に移動
    → 次回 sync 時に対応する Google Tasks を自動完了

[自動アーカイブ]
  Done 状態で 7日以上経過
    → 次回 sync 時に Project v2 から自動アーカイブ
```

**注意:**
- 全ての連携は **最大30分の遅延** がある（ポーリング型）
- リアルタイムではないが、業務用途には十分な頻度
- エージェントがステータスを変更しても、Google Tasks への反映は次回 sync 実行時
