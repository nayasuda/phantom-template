# スキル：Googleグループメンバー追加 (`add_google_group_member`)

## 概要
このスキルは、Google Workspace の指定したGoogleグループ（メーリングリスト）に新しいメンバーを追加します。

## 使い方
Googleグループに新しいメンバーを追加するには、以下のコマンドを実行します。

```bash
python3 phantom-antenna/src/skills/google_workspace.py --action add_member --group [GROUP_EMAIL] --member [MEMBER_EMAIL]
```

## パラメータ

- `--group [GROUP_EMAIL]` (必須):
  - メンバーを追加したいGoogleグループのメールアドレスを指定します。
  - 例: `example-group@yourdomain.com`

- `--member [MEMBER_EMAIL]` (必須):
  - Googleグループに追加するメンバーのメールアドレスを指定します。
  - 例: `new-member@yourdomain.com`

## 例
`design-team@example.com` というグループに `john.doe@example.com` を追加する場合：

```bash
python3 phantom-antenna/src/skills/google_workspace.py --action add_member --group design-team@example.com --member john.doe@example.com
```