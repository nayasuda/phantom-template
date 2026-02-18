#!/usr/bin/env python3
"""
AfterTool Hook: シェルコマンド自動ロギング

run_shell_command 実行後に、コマンドと結果を memory/daily_log.jsonl に自動追記する。
エラー発生時は memory/failures.jsonl にも記録し、PDCAサイクルを回す。
エージェントが手動で記録しなくても操作履歴が残る。

イベント: AfterTool (matcher: "run_shell_command")
"""

import json
import os
import sys
from datetime import datetime, timezone

# failures.jsonl に記録するコマンド失敗パターン
# 情報取得系コマンド（git status, ls等）の失敗はノイズになるので除外
TRACKABLE_FAILURE_PREFIXES = (
    "git add", "git commit", "git push", "git pull", "git merge",
    "git checkout", "git switch", "git rebase",
    "gh pr ", "gh issue ",
    "clasp ",
    "python", "python3", "node", "npm", "pip",
)


def _record_failure(project_dir: str, command: str, error: str) -> None:
    """Record shell command failure to failures.jsonl for PDCA cycle"""
    try:
        failures_file = os.path.join(project_dir, "memory/failures.jsonl")
        os.makedirs(os.path.dirname(failures_file), exist_ok=True)

        entry = {
            "task_type": "shell_command",
            "result": "fail",
            "error": f"コマンド失敗: {command[:100]}",
            "solution": error[:200] if error else "エラー内容を確認して再実行",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        with open(failures_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _should_track_failure(command: str) -> bool:
    """Track only meaningful command failures, skip info-gathering commands"""
    cmd_lower = command.lower().strip()
    return any(cmd_lower.startswith(prefix) for prefix in TRACKABLE_FAILURE_PREFIXES)


def main():
    # stdinからJSON入力を読み込む
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception as e:
        print(f"Failed to parse input: {e}", file=sys.stderr)
        print(json.dumps({}))
        return

    # ツール情報を抽出
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})
    tool_response = input_data.get("tool_response", {})

    # コマンド内容を取得
    command = tool_input.get("command", tool_input.get("cmd", "unknown"))

    # 結果の概要を取得（長すぎる場合は切り詰め）
    result_content = ""
    if isinstance(tool_response, dict):
        llm_content = tool_response.get("llmContent", "")
        if isinstance(llm_content, str):
            result_content = llm_content[:500]
        elif isinstance(llm_content, dict):
            result_content = json.dumps(llm_content, ensure_ascii=False)[:500]
        error = tool_response.get("error", "")
    else:
        result_content = str(tool_response)[:500]
        error = ""

    # ログエントリを作成
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "shell_command",
        "tool": tool_name,
        "command": command,
        "result_preview": result_content,
        "has_error": bool(error),
        "error": str(error)[:200] if error else None,
    }

    # memory/daily_log.jsonl に追記
    project_dir = os.environ.get("GEMINI_PROJECT_DIR", ".")
    log_path = os.path.join(project_dir, "memory", "daily_log.jsonl")

    try:
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        print(f"Logged command: {command[:80]}", file=sys.stderr)
    except Exception as e:
        print(f"Failed to write log: {e}", file=sys.stderr)

    # エラー時は failures.jsonl にも記録（PDCA用）
    if error and _should_track_failure(command):
        _record_failure(project_dir, command, str(error)[:200])
        print(f"Recorded failure: {command[:80]}", file=sys.stderr)

    # 空のJSONを返す（ツール結果は変更しない）
    print(json.dumps({}))


if __name__ == "__main__":
    main()
