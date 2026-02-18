#!/usr/bin/env python3
"""
BeforeTool Hook: シークレット漏洩防止

write_file や replace 操作時に、書き込み内容にシークレット情報が
含まれていないかチェックする。検出したらブロック。
失敗はmemory/failures.jsonlに記録される。

イベント: BeforeTool (matcher: "write_file|replace")
"""

import json
import os
import re
import sys
from datetime import datetime

# 検出パターン（正規表現）
SECRET_PATTERNS = [
    # 一般的なシークレットキー
    (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{16,}", "API Key"),
    (r"(?i)(secret[_-]?key|secretkey)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{16,}", "Secret Key"),
    (r"(?i)(access[_-]?token|accesstoken)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{16,}", "Access Token"),
    (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{8,}", "Password"),
    # GitHub Personal Access Token
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub PAT"),
    (r"github_pat_[a-zA-Z0-9_]{82}", "GitHub Fine-grained PAT"),
    # Google API Key
    (r"AIza[0-9A-Za-z_\-]{35}", "Google API Key"),
    # Bearer Token
    (r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}", "Bearer Token"),
    # Private Key
    (r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----", "Private Key"),
    # .env 形式の機密変数（値付き）
    (r"(?i)(GEMINI_API_KEY|GITHUB_MCP_PAT|CONTEXT7_API_KEY)\s*=\s*[^\s]{10,}", "Environment Variable with Secret"),
]

# 除外パターン（プレースホルダーやドキュメント内の例示）
EXCLUDE_PATTERNS = [
    r"<your[_-]",           # <your-key> 等のプレースホルダー
    r"YOUR[_-]",            # YOUR_API_KEY 等のプレースホルダー
    r"xxx+",                # xxx... のプレースホルダー
    r"\.\.\.",              # ... のプレースホルダー
    r"example",             # example values
    r"placeholder",         # placeholder values
    r"sk-[.]{3,}",          # sk-... のプレースホルダー
]


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


def is_excluded(matched_text: str) -> bool:
    """マッチしたテキストがプレースホルダーかどうか判定"""
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, matched_text, re.IGNORECASE):
            return True
    return False


def check_content(content: str) -> list[tuple[str, str]]:
    """コンテンツ内のシークレットパターンを検出"""
    findings = []
    for pattern, label in SECRET_PATTERNS:
        matches = re.finditer(pattern, content)
        for match in matches:
            matched_text = match.group(0)
            if not is_excluded(matched_text):
                # マッチしたテキストを短縮表示（全文は出さない）
                preview = matched_text[:20] + "..." if len(matched_text) > 20 else matched_text
                findings.append((label, preview))
    return findings


def main():
    # stdinからJSON入力を読み込む
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception as e:
        print(f"Failed to parse input: {e}", file=sys.stderr)
        print(json.dumps({"decision": "allow"}))
        return

    tool_input = input_data.get("tool_input", {})

    # write_file の content、replace の new_string を取得
    content = tool_input.get("content", "")
    new_string = tool_input.get("new_string", "")
    check_target = content + "\n" + new_string

    if not check_target.strip():
        print(json.dumps({"decision": "allow"}))
        return

    # シークレットチェック
    findings = check_content(check_target)

    if findings:
        finding_details = "\n".join(
            [f"  - {label}: {preview}" for label, preview in findings]
        )
        reason = (
            f"🔒 Security Policy: シークレット情報の書き込みをブロックしました。\n"
            f"検出された項目:\n{finding_details}\n\n"
            f"シークレット情報は .env ファイルや環境変数で管理してください。"
        )

        print(f"BLOCKED: Found {len(findings)} secret(s)", file=sys.stderr)
        
        # Record failure for PDCA
        secret_types = ", ".join([label for label, _ in findings])
        _record_failure(
            task_type="write_file_security",
            error=f"シークレット情報検出: {secret_types}",
            solution="シークレットは .env や環境変数で管理。プレースホルダー（YOUR_KEY等）を使う"
        )

        output = {
            "decision": "deny",
            "reason": reason,
            "systemMessage": f"🛡️ セキュリティ: {len(findings)}件のシークレットを検出してブロックしたよ",
        }
        print(json.dumps(output, ensure_ascii=False))
    else:
        print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
