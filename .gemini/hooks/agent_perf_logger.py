#!/usr/bin/env python3
"""
AfterAgent Hook: エージェントパフォーマンスロガー

エージェント完了時にパフォーマンスデータを memory/agent_perf.jsonl に記録。
セッションJSON（.gemini/tmp/*/chats/）と組み合わせて
Before/After 比較やエージェント間のパフォーマンス分析に使う。

イベント: AfterAgent (matcher: ".*")
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

AGENT_NAMES = {
    "queen", "mona", "skull", "wolf", "panther",
    "fox", "noir", "violet", "crow", "sophie",
}


def _infer_agent_from_prompt(prompt: str) -> str:
    """プロンプト冒頭からエージェント名を推定する"""
    if not prompt:
        return ""
    lower = prompt[:500].lower()
    for name in AGENT_NAMES:
        if name in lower:
            return name
    return ""


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        print(json.dumps({"decision": "allow"}))
        return

    if input_data.get("stop_hook_active", False):
        print(json.dumps({"decision": "allow"}))
        return

    response = input_data.get("prompt_response", "")
    prompt = input_data.get("prompt", "")
    session_id = input_data.get("session_id", "")
    ts = input_data.get("timestamp", datetime.now(timezone.utc).isoformat())

    agent_name = _infer_agent_from_prompt(prompt)

    entry = {
        "timestamp": ts,
        "session_id": session_id,
        "agent": agent_name or "unknown",
        "status": "success",
        "response_length": len(response),
        "response_lines": response.count("\n") + 1 if response else 0,
        "prompt_preview": prompt[:200].replace("\n", " ") if prompt else "",
        "input_keys": sorted(input_data.keys()),
    }

    project_dir = os.environ.get("GEMINI_PROJECT_DIR", ".")
    perf_path = os.path.join(project_dir, "memory", "agent_perf.jsonl")

    try:
        os.makedirs(os.path.dirname(perf_path), exist_ok=True)
        with open(perf_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(
            f"Perf logged: {entry['agent']} ({len(response)} chars)",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"Write error: {e}", file=sys.stderr)

    print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
