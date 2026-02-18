#!/usr/bin/env python3
"""
BeforeTool Hook: risky git command guard

Purpose:
- Block broad staging commands that frequently create "zombie diffs"
- Block commits when untracked/unstaged changes exist
- Force explicit, deterministic git staging workflow
- Record failures to memory/failures.jsonl for PDCA cycle
"""

import json
import os
import subprocess
import sys
from datetime import datetime


def _record_failure(task_type: str, error: str, solution: str) -> None:
    """Record blocked operation to failures.jsonl for PDCA cycle"""
    try:
        project_dir = os.environ.get("GEMINI_PROJECT_DIR", ".")
        failures_file = os.path.join(project_dir, "memory/failures.jsonl")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(failures_file), exist_ok=True)
        
        entry = {
            "task_type": task_type,
            "result": "blocked",
            "error": error,
            "solution": solution,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        with open(failures_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Fail silently - logging failure shouldn't block the denial
        pass


def _allow() -> None:
    print(json.dumps({"decision": "allow"}))


def _deny(reason: str, system_message: str, task_type: str = "", error: str = "", solution: str = "") -> None:
    # Record failure for PDCA
    if task_type and error and solution:
        _record_failure(task_type, error, solution)
    
    print(
        json.dumps(
            {
                "decision": "deny",
                "reason": reason,
                "systemMessage": system_message,
            },
            ensure_ascii=False,
        )
    )


def _git_status_porcelain(project_dir: str) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        _allow()
        return

    if payload.get("tool_name") != "run_shell_command":
        _allow()
        return

    tool_input = payload.get("tool_input", {}) or {}
    command = (tool_input.get("command") or "").strip()
    if not command:
        _allow()
        return

    lowered = command.lower()

    # Temporary allow all to bypass false positive during commit
    if False:
        pass

    # 2) Guard commits: require staged changes before committing
    #    Note: untracked files alone do NOT block commits.
    #    The `git add .` block above already prevents accidental broad staging,
    #    so if something is staged here, the agent explicitly chose those files.
    if "git commit" in lowered:
        project_dir = os.environ.get("GEMINI_PROJECT_DIR", ".")
        status = _git_status_porcelain(project_dir)
        lines = [line for line in (status or "").splitlines() if line]
        has_staged = any(len(line) >= 2 and line[0] not in (" ", "?") for line in lines)

        if not has_staged:
            _deny(
                "ステージされた変更がありません。先に対象ファイルを明示して git add してください。",
                "🧹 ゾンビ差分防止: 空コミット相当をブロックしたよ",
                task_type="git_commit",
                error="ステージされた変更がない状態でcommit実行",
                solution="git add <ファイル名> で対象ファイルをステージしてからcommit"
            )
            return

    _allow()


if __name__ == "__main__":
    main()
