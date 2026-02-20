#!/usr/bin/env python3
"""
SessionStart Hook: Git状態 + Project v2タスクダッシュボードの自動注入

セッション開始時に以下をコンテキストに自動注入する:
1. 現在のGit状態（ブランチ、未コミット変更、最近のコミット等）
2. Project v2のアクティブタスクをジョーカー/怪盗団に分類したダッシュボード

イベント: SessionStart (matcher: "startup")
"""

import json
import os
import subprocess
import sys


# ジョーカー向けタスクを判定するキーワード（ラベルがない場合のフォールバック）
JOKER_KEYWORDS = [
    "確認", "承認", "設定", "テスト実行", "要対応", "手動",
    "ブラウザ", "Phantom要対応", "clasp pull", "GAS設定",
    "API有効化", "権限", "認証", "Slack設定", "webhook",
]

# 完了扱いのステータス（表示しない）
DONE_STATUSES = {"Done"}


def run_git(args: list[str]) -> str:
    """Gitコマンドを実行して結果を返す。失敗時は空文字。"""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.environ.get("GEMINI_PROJECT_DIR", "."),
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Git command failed: {e}", file=sys.stderr)
        return ""


def count_local_branches() -> tuple[int, list[str]]:
    """ローカルブランチ数と非mainブランチ一覧を返す。"""
    raw = run_git(["branch", "--format=%(refname:short)"])
    if not raw:
        return 0, []
    branches = [b.strip() for b in raw.splitlines() if b.strip()]
    non_main = [b for b in branches if b not in ("main", "master")]
    return len(non_main), non_main


def fetch_project_tasks() -> list[dict]:
    """gh project item-list で全アクティブ項目を取得。失敗時は空リスト。"""
    try:
        result = subprocess.run(
            ["gh", "project", "item-list", "{{PROJECT_NUMBER}}",
             "--owner", "{{GITHUB_USERNAME}}", "--format", "json", "--limit", "200"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=os.environ.get("GEMINI_PROJECT_DIR", "."),
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return data.get("items", [])
    except Exception as e:
        print(f"Project v2 fetch failed: {e}", file=sys.stderr)
        return []


def classify_tasks(items: list[dict]) -> tuple[list[dict], list[dict]]:
    """タスクをジョーカー向けと怪盗団向けに分類する。

    Returns:
        (joker_tasks, phantom_tasks)
    """
    joker_tasks = []
    phantom_tasks = []

    for item in items:
        # ステータスが完了系ならスキップ
        status = item.get("status", "")
        if status in DONE_STATUSES:
            continue

        # タイトルとラベル情報を取得
        title = item.get("title", "")
        labels = item.get("labels", [])
        content = item.get("content", {})
        item_type = content.get("type", "DraftIssue")
        number = content.get("number", "")

        task_info = {
            "title": title,
            "status": status,
            "type": item_type,
            "number": number,
            "id": item.get("id", ""),
        }

        # ラベル優先判定
        label_names = [l if isinstance(l, str) else l.get("name", "") for l in labels]
        if "Joker" in label_names:
            joker_tasks.append(task_info)
            continue

        # ラベルなしの場合: キーワードで判定
        if any(kw in title for kw in JOKER_KEYWORDS):
            joker_tasks.append(task_info)
        else:
            phantom_tasks.append(task_info)

    return joker_tasks, phantom_tasks


def format_task_line(task: dict) -> str:
    """タスク1件を表示用の行にフォーマット。"""
    title = task["title"]
    status = task["status"]
    number = task.get("number", "")
    ref = f" (#{number})" if number else ""
    return f"- [ ] {title}{ref} [{status}]"


def build_task_dashboard(joker_tasks: list[dict], phantom_tasks: list[dict]) -> list[str]:
    """タスクダッシュボードセクションを構築する。"""
    lines = []
    lines.append("")
    lines.append("## 📋 Task Dashboard (auto-injected from Project v2)")
    lines.append("")

    # 表示件数制限
    max_display = 10

    if joker_tasks:
        lines.append(f"**🃏 Joker (あなた): {len(joker_tasks)}件**")
        for task in joker_tasks[:max_display]:
            lines.append(format_task_line(task))
        if len(joker_tasks) > max_display:
            lines.append(f"  ... 他 {len(joker_tasks) - max_display} 件")
    else:
        lines.append("**🃏 Joker (あなた):** なし")

    lines.append("")

    if phantom_tasks:
        lines.append(f"**🎭 Phantom (わたしたち): {len(phantom_tasks)}件**")
        for task in phantom_tasks[:max_display]:
            lines.append(format_task_line(task))
        if len(phantom_tasks) > max_display:
            lines.append(f"  ... 他 {len(phantom_tasks) - max_display} 件")
    else:
        lines.append("**🎭 Phantom (わたしたち):** なし")

    return lines


def is_first_run() -> bool:
    """setup.sh 未実行（プレースホルダー未置換）なら True。"""
    return "{{PROJECT_NUMBER}}" in open(__file__).read()


def get_onboarding_step() -> int:
    """現在のオンボーディング進捗を判定する。
    0 = 初回起動（setup.sh 未実行）
    1 = setup.sh 済みだが GitHub 未認証
    2 = GitHub 認証済み（通常運用）
    """
    if is_first_run():
        return 0

    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return 2
    except Exception:
        pass
    return 1


def build_onboarding_context(step: int) -> tuple[str, str]:
    """オンボーディング用のコンテキストとシステムメッセージを返す。"""

    if step == 0:
        context = """## 🎯 Mission: First Contact（はじめての接触）

怪盗団のアジトへようこそ！まずは一緒にミッションをクリアしていこう。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### ✅ Step 1: ナビと話す ← 今ここ！
**できるようになること:** AIアシスタント「ナビ」に何でも相談できる。
企画のアイデア出し、文章の添削、技術的な質問、なんでもOK。

**🎮 やってみよう:** 何か気軽に話しかけてみて！
例: 「来週のプレゼンの構成を一緒に考えて」
例: 「この文章をもっとわかりやすくして」
例: 「Excelの関数でこういうことしたいんだけど」

**✅ 確認:** ナビから返事が来たらクリア！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### ⬜ Step 2: クイーンに作戦を立ててもらう
**できるようになること:** AIチーム（怪盗団）がチームで作戦を考えてくれる。
質問→回答→計画作成の流れで、プロの企画書レベルの計画が手に入る。

**🎮 やってみよう:** `/queen_plan 〇〇の企画を考えたい` と入力！
例: `/queen_plan 社内のAI活用推進の企画書を作りたい`
例: `/queen_plan 業務効率化の提案書を作りたい`

**✅ 確認:** クイーンから質問が来て、計画が出てきたらクリア！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### ⬜ Step 3: アジト（GitHub）を構える
**できるようになること:** タスク管理・進捗追跡ができる。
ミッションの実行、PRレビュー、自動記録など怪盗団のフル機能が解禁。

**🎮 やってみよう:** ナビに「セットアップを進めたい」と言うか、
ターミナルで `bash setup.sh` を実行！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### ⬜ Bonus: 情報網を手に入れる（Google Workspace 連携）
**できるようになること:** Gmail の自動分類、Google Tasks との同期、
カレンダー確認など。Google Workspace を使っている人向け。

**🎮 やってみよう:** `/initial_setup` でナビがガイドしてくれるよ！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> 💡 全部一度にやる必要はないよ！Step 1 と 2 だけで十分使えるから、
> 慣れてきたら Step 3 に進もう。"""

        system_msg = "🛰️ ようこそ！最初のミッション「First Contact」を始めよう！まずは気軽に話しかけてみて！"
        return context, system_msg

    elif step == 1:
        context = """## 🎯 Mission: First Contact（進行中）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### ✅ Step 1: ナビと話す — クリア済み！
### ✅ Step 2: クイーンに作戦を立ててもらう — 使えるよ！
### ⬜ Step 3: アジト（GitHub）を構える ← 次はここ！
**できるようになること:** タスク管理・進捗追跡ができる。
`/mission` でミッション実行、PRレビュー、自動記録が解禁される。

**🎮 やってみよう:** `gh auth login` でGitHub認証、
その後ナビに「セットアップを進めたい」と伝えてね。

### ⬜ Bonus: 情報網を手に入れる（Google Workspace 連携）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎮 Available Commands

| コマンド | 説明 |
|:--|:--|
| `/queen_plan` | クイーンに作戦を立ててもらう（質問→計画） |
| `/debug` | バグの根本原因を調査・特定 |

> 💡 GitHub 連携が完了すると `/mission` も使えるようになるよ！"""

        system_msg = "🛰️ おかえり！Step 1 & 2 は使える状態だよ。GitHub 連携で怪盗団のフル機能が解禁されるよ！"
        return context, system_msg

    return "", ""


def main():
    try:
        _input_data = json.loads(sys.stdin.read())
    except Exception:
        pass

    # --- オンボーディング判定 ---
    onboarding_step = get_onboarding_step()

    if onboarding_step < 2:
        context, system_msg = build_onboarding_context(onboarding_step)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            },
            "systemMessage": system_msg,
        }
        print(json.dumps(output, ensure_ascii=False))
        return

    # --- 通常モード: Git情報を収集 ---
    branch = run_git(["branch", "--show-current"])
    status = run_git(["status", "--short"])
    recent_commits = run_git(["log", "--oneline", "-5"])
    stash_list = run_git(["stash", "list", "--oneline"])
    branch_count, branch_names = count_local_branches()

    lines = ["## 🔍 Current Git Status (auto-injected by SessionStart hook)"]
    lines.append("")

    if branch:
        lines.append(f"**Current Branch:** `{branch}`")
    else:
        lines.append("**Current Branch:** (detached HEAD or not a git repo)")

    lines.append("")

    if status:
        lines.append("**Uncommitted Changes:**")
        lines.append("```")
        lines.append(status)
        lines.append("```")
    else:
        lines.append("**Uncommitted Changes:** なし (clean)")

    lines.append("")

    if recent_commits:
        lines.append("**Recent Commits (last 5):**")
        lines.append("```")
        lines.append(recent_commits)
        lines.append("```")

    if stash_list:
        lines.append("")
        lines.append("**Stash:**")
        lines.append("```")
        lines.append(stash_list)
        lines.append("```")

    if branch_count > 0:
        lines.append("")
        if branch_count >= 5:
            lines.append(f"**⚠️ ローカルブランチが {branch_count} 個あるよ！掃除を検討して。**")
        else:
            lines.append(f"**ローカルブランチ:** {branch_count} 個")
        lines.append("```")
        for name in branch_names[:15]:
            lines.append(f"  {name}")
        if branch_count > 15:
            lines.append(f"  ... 他 {branch_count - 15} 個")
        lines.append("```")

    # --- Project v2 タスクダッシュボード ---
    items = fetch_project_tasks()
    task_summary = ""
    if items:
        joker_tasks, phantom_tasks = classify_tasks(items)
        dashboard_lines = build_task_dashboard(joker_tasks, phantom_tasks)
        lines.extend(dashboard_lines)
        task_summary = f" | タスク: Joker {len(joker_tasks)}件 / Phantom {len(phantom_tasks)}件"
    else:
        lines.append("")
        lines.append("## 📋 Task Dashboard")
        lines.append("Project v2 の取得に失敗したか、タスクがありません。")

    lines.append("")
    lines.append("## 🎮 Available Commands")
    lines.append("")
    lines.append("| コマンド | 説明 |")
    lines.append("|:--|:--|")
    lines.append("| `/queen_plan` | クイーンに作戦を立ててもらう（質問→計画） |")
    lines.append("| `/mission` | 壁打ちの内容をミッション化して実行に移す |")
    lines.append("| `/debug` | バグの根本原因を調査・特定 |")
    lines.append("")
    lines.append("> 💡 通常モードではナビは相談相手。`/mission` で実行モードに切り替わるよ！")
    lines.append("> 💡 大きなタスクは `/queen_plan` で質問→計画→承認の流れがおすすめ！")

    context = "\n".join(lines)

    branch_warning = ""
    if branch_count >= 5:
        branch_warning = f" ⚠️ ローカルブランチ{branch_count}個 — 掃除推奨"

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        },
        "systemMessage": f"🛰️ Git状態を自動取得したよ（ブランチ: {branch or 'unknown'}）{branch_warning}{task_summary}",
    }

    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
