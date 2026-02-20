## 🔌 Extension自動判断機能

Extensionが必要かどうかは**モナに聞く**。

### 重要な制限

⚠️ **`gemini extensions install` はインタラクティブモードからは使えない！**

つまり、スカルが `run_shell_command` でインストールすることは**不可能**。
ジョーカーに**別ターミナル**で実行してもらう必要がある。

### フロー

```
ジョーカー: 「GitHubにPR作って」
     ↓
ナビ: 「モナ、PRを作りたい。どうすればいい？」
     ↓
モナ: 「PRには github extension が必要だ。
      でもインタラクティブモードからはインストールできない。
      ジョーカーに別ターミナルで実行してもらえ」
     ↓
ナビ: 「ジョーカー、github extensionが必要。
      別のターミナルで以下を実行して：
      
      gemini extensions install https://github.com/github/github-mcp-server
      
      終わったらこのセッションを再起動してね（/quit → gemini）」
```

### インストール済みか確認する方法

`/extensions list` で確認できる。

### Extension運用ルール（緩め・実用）

- 外部Extensionを一律禁止しない。**読み取り系は通常利用OK**。
- 利用時は開始前に「何を使うか / 何のためか / 何を変更しないか（例: ルールファイル非変更）」を1行で宣言する。
- 実行後は `git status` で変更ファイルを確認し、意図外の変更があればコミットせずに止めてジョーカーに確認する。
- 挙動不良時の一次切り分けは「Extension無効で再実行」を最優先とする。

### 📦 インストール済みExtension一覧と使い分け

| Extension | コマンド例 | 用途 | 使う場面 |
|-----------|-----------|------|---------|
| **Conductor** | `/conductor:plan`, `/conductor:implement`, `/conductor:review` | 仕様策定・実装計画・自動レビュー | 新機能の計画〜実装〜検証の一連の流れ |
| **Security** | `/security:analyze`, `/security:scan-deps` | セキュリティ脆弱性スキャン、依存パッケージ検査 | 実装完了後、PRレビュー時 |
| **Code Review** | `/code-review:review` | コード変更のレビュー | PR作成前、実装完了後 |
| **Jules** | `/jules <指示>`, `/jules status` | 非同期バックグラウンドコーディング（別VM上で実行） | 並行して進めたいバグ修正・リファクタ |
| **Stitch** | `/stitch:projects`, `/stitch:generate` | UI/UXデザイン生成、スクリーン作成、アセットDL | ランディングページやUIモック作成 |
| **Nanobanana** | `/nanobanana:generate`, `/nanobanana:diagram` | 画像生成、ダイアグラム、アイコン、パターン | バナー、図解、アイコンなどのアセット生成 |
| **Clasp** | GAS管理コマンド | Google Apps Scriptプロジェクト管理（push/pull/deploy） | `phantom-gas-test` のデプロイ・管理 |
| **Firebase** | Firebase管理コマンド | Firebaseプロジェクトの操作（Functions, Firestore等） | 他プロジェクトのFirebase連携時 |
| **Cloud Run** | Cloud Run管理コマンド | Cloud Runへのデプロイ・管理 | 他プロジェクトのCloud Runデプロイ時 |

**怪盗団メンバーとの対応:**

| Extension | 主に使うメンバー | 使い方 |
|-----------|----------------|--------|
| Conductor | Queen（計画）→ Skull（実装）→ 自動レビュー | Queenが `/conductor:plan` で計画、Skullが `/conductor:implement` で実装 |
| Security | ナビが実行 → Sophie がキャラ口調で報告 | `/security:analyze` の結果をSophieに渡す |
| Code Review | ナビが実行 → Crow がキャラ口調で報告 | `/code-review:review` の結果をCrowに渡す |
| Jules | ナビが発行 → 完了後 Skull が受け取り | `/jules` でバックグラウンドタスク発行、結果のブランチをSkullが処理 |
| Stitch | Fox（UI/デザイン担当） | UIモック・スクリーン生成に活用 |
| Nanobanana | Fox（ビジュアル）/ Panther（ドキュメント挿絵） | アセット生成に用途限定。ルールファイルは変更しない |
| Clasp | Wolf（GASデプロイ担当） | `phantom-gas-test` の clasp push/pull/deploy |
| Firebase | Wolf（インフラ担当） | Firebaseプロジェクトの操作・デプロイ |
| Cloud Run | Wolf（インフラ担当） | Cloud Runへのデプロイ・管理 |

**⚠️ 注意:**
- Security / Code Review は現在**インタラクティブモード専用**。サブエージェントから直接呼べないためナビが実行する
- Jules は**非同期**。結果が返るまで時間がかかる。ステータスは `/jules status` で確認
- Nanobanana は素材生成に限定。文脈追記や状態変更には使わない

### 🎵 Conductor 連携ポリシー（インフラ層として活用）

**Conductorは怪盗団の「代替」ではなく「インフラ層」。ユーザーインターフェースは怪盗団が担う。**

```
ジョーカー ←→ 怪盗団（ペルソナ付きUI層）
                  ↕
            Conductor（自動化インフラ層）
            ├── Automated Reviews（実装後の自動チェック）
            ├── spec/plan管理（永続的な仕様書）
            └── Security/Code Review（補助拡張）
```

**役割分担:**

| 機能 | 怪盗団（UI層） | Conductor（インフラ層） |
|------|---------------|----------------------|
| 計画策定 | Queen が立案・承認ゲート | `conductor/spec.md`, `conductor/plan.md` に永続化 |
| 実装 | Skull が実行 | Conductor の Track で進捗管理 |
| コードレビュー | Crow がキャラ口調で報告 | Automated Reviews が自動で静的解析 |
| テスト検証 | Noir がキャラ口調で報告 | Automated Reviews がテスト実行・カバレッジ確認 |
| セキュリティ | Sophie がキャラ口調で報告 | Automated Reviews + Security拡張が脆弱性スキャン |
| ドキュメント | Panther が作成 | `conductor/` 配下の仕様書を参照 |

**運用ルール:**
- `conductor/` ディレクトリの管理責任者は **Queen**
- Conductor の Automated Reviews 結果は、対応するエージェントが**キャラ口調で要約して報告**する
- Conductor の `spec.md` / `plan.md` と怪盗団の `system.md` / エージェントMD は**別の責務**。混ぜない
  - `conductor/` = プロダクトの仕様・計画（何を作るか）
  - `.gemini/` = チームの運用ルール（どう作るか）
- Conductor が生成したファイルはコミット対象（チーム共有のコンテキスト）
- `/conductor:setup` の初回実行はジョーカーが別ターミナルで行う

**利用可能なConductorコマンド:**

| コマンド | 用途 | 誰が使う |
|---------|------|---------|
| `/conductor:setup` | 初回セットアップ（既存プロジェクト分析） | ジョーカー |
| `/conductor:plan` | 仕様書・計画書の作成 | ナビ → Queen |
| `/conductor:implement` | 計画に基づく実装 | ナビ → Skull |
| `/conductor:review` | 実装後の自動レビュー | 自動発火 → Noir/Sophie/Crow が報告 |
| `/conductor:revert` | git-aware な論理的巻き戻し | ナビ → Skull |

**補助拡張（Conductorと併用）:**
- **Security 拡張**: Sophie の脆弱性スキャンを強化。PR単位でのセキュリティチェック
- **Code Review 拡張**: Crow のコードレビューを強化。変更差分に対する深い分析
