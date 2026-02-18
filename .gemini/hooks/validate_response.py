#!/usr/bin/env python3
"""
AfterAgent Hook: レポートバリデーション

エージェントの応答に必須要素が含まれているかチェックする。
不足している場合は decision: "deny" でリトライを促す。
失敗はmemory/failures.jsonlに記録される。

リトライ中（stop_hook_active=True）は再バリデーションしない。

イベント: AfterAgent (matcher: "*")
"""

import json
import os
import sys
from datetime import datetime


# バリデーションルール
# 各ルールは (チェック関数, 不足時のメッセージ) のタプル
# 緩めに始めて、必要に応じて厳しくする
VALIDATION_RULES = [
    {
        "name": "thinking_process",
        "description": "思考プロセスの記載",
        "keywords": [
            "思考プロセス",
            "思考",
            "考え",
            "分析",
            "判断",
            "検討",
            "確認",
            "調査",
            "ステップ",
            "手順",
            "方針",
            "計画",
            "Thinking",
            "Analysis",
        ],
        "min_matches": 1,
        "message": "思考プロセスや分析の記載が見当たりません。どのように考えてこの結果に至ったか記載してください。",
    },
    {
        "name": "result_section",
        "description": "結果・成果物の記載",
        "keywords": [
            "結果",
            "完了",
            "成功",
            "失敗",
            "エラー",
            "レポート",
            "報告",
            "実行結果",
            "成果",
            "Result",
            "Done",
            "Completed",
            "✅",
            "❌",
            "⚠️",
        ],
        "min_matches": 1,
        "message": "結果や成果物の記載が見当たりません。タスクの結果を明記してください。",
    },
]

# バリデーション対象外にするレスポンスパターン
# 短い応答（挨拶、確認等）はスキップ
MIN_RESPONSE_LENGTH = 100

# 明らかに会話的な応答はスキップ
SKIP_PATTERNS = [
    "了解",
    "わかった",
    "おっけ",
    "はい",
    "うん",
    "なるほど",
    "把握",
    "OK",
    "承知",
]


def _record_failure(task_type: str, error: str, solution: str) -> None:
    """Record validation failure to failures.jsonl for PDCA cycle"""
    try:
        project_dir = os.environ.get("GEMINI_PROJECT_DIR", ".")
        failures_file = os.path.join(project_dir, "memory/failures.jsonl")
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
        pass


def should_skip(response: str) -> bool:
    """バリデーションをスキップすべきか判定"""
    # 短い応答はスキップ
    if len(response) < MIN_RESPONSE_LENGTH:
        return True

    # 会話的な応答はスキップ
    first_line = response.strip().split("\n")[0].strip()
    for pattern in SKIP_PATTERNS:
        if first_line.startswith(pattern):
            return True

    return False


def validate_response(response: str) -> list[str]:
    """レスポンスをバリデーションし、不足している項目のメッセージリストを返す"""
    issues = []

    for rule in VALIDATION_RULES:
        matches = sum(1 for kw in rule["keywords"] if kw in response)
        if matches < rule["min_matches"]:
            issues.append(rule["message"])

    return issues


def main():
    # stdinからJSON入力を読み込む
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception as e:
        print(f"Failed to parse input: {e}", file=sys.stderr)
        print(json.dumps({"decision": "allow"}))
        return

    # リトライ中はスキップ（無限ループ防止）
    if input_data.get("stop_hook_active", False):
        print("Skipping validation (retry in progress)", file=sys.stderr)
        print(json.dumps({"decision": "allow"}))
        return

    # レスポンスを取得
    response = input_data.get("prompt_response", "")

    if not response:
        print(json.dumps({"decision": "allow"}))
        return

    # スキップ判定
    if should_skip(response):
        print("Skipping validation (short/conversational response)", file=sys.stderr)
        print(json.dumps({"decision": "allow"}))
        return

    # バリデーション実行
    issues = validate_response(response)

    if issues:
        reason = (
            "レポートに以下の要素が不足しています。追記してください：\n"
            + "\n".join(f"- {issue}" for issue in issues)
        )
        print(f"Validation failed: {len(issues)} issue(s)", file=sys.stderr)

        # Record failure for PDCA
        _record_failure(
            task_type="report_validation",
            error=f"レポート不足: {', '.join(r['name'] for r in VALIDATION_RULES if r['message'] in issues)}",
            solution="思考プロセスと結果を含むレポートを返すこと"
        )

        output = {
            "decision": "deny",
            "reason": reason,
            "systemMessage": f"📋 レポートバリデーション: {len(issues)}件の不足を検出。リトライします...",
        }
        print(json.dumps(output, ensure_ascii=False))
    else:
        print("Validation passed", file=sys.stderr)
        print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
