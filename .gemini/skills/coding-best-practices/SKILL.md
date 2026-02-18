# Coding Best Practices Skill

## Overview
このスキルは、Project Phantom での高品質なコード実装のためのベストプラクティスを提供します。Python を中心に、エラーハンドリング、API 呼び出し、ログ戦略、テスト手法をカバーします。

## When to Use
- 新しいスクリプトや API を実装する時
- 既存コードのリファクタリング時
- コードレビューで品質を確認する時
- エラーハンドリングの改善が必要な時

## Core Principles

### 1. Fail Fast, Fail Loudly
```python
# ❌ Bad: Silent failure
def get_token():
    token = os.environ.get("API_TOKEN")
    return token  # None if not set

# ✅ Good: Explicit error
def get_token():
    token = os.environ.get("API_TOKEN")
    if not token:
        raise ValueError("API_TOKEN environment variable is not set")
    return token
```

### 2. Always Use Timeouts
```python
# ❌ Bad: No timeout (can hang forever)
response = requests.get(url)

# ✅ Good: With timeout
response = requests.get(url, timeout=30)
```

### 3. Log Important Events
```python
import logging

logger = logging.getLogger(__name__)

# Log at appropriate levels
logger.debug("Detailed debug information")
logger.info("High-level progress update")
logger.warning("Something unexpected but recoverable")
logger.error("Error occurred", exc_info=True)
```

## Error Handling Patterns

### HTTP API Calls
```python
import requests
from typing import Optional, Dict, Any

def call_api(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Robust API call with comprehensive error handling.
    
    Args:
        url: The API endpoint
        method: HTTP method (GET, POST, etc.)
        data: Request payload
        headers: HTTP headers
    
    Returns:
        Response JSON or None on error
    """
    try:
        response = requests.request(
            method=method,
            url=url,
            json=data,
            headers=headers,
            timeout=30
        )
        
        # Check status code
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 201:
            logger.info(f"Resource created: {url}")
            return response.json()
        elif response.status_code == 401:
            logger.error("Authentication failed. Check your token.")
            return None
        elif response.status_code == 403:
            logger.error("Permission denied. Check token scopes.")
            return None
        elif response.status_code == 404:
            logger.error(f"Resource not found: {url}")
            return None
        elif response.status_code == 422:
            logger.error(f"Validation error: {response.json()}")
            return None
        elif response.status_code >= 500:
            logger.error(f"Server error ({response.status_code}): {response.text}")
            return None
        else:
            logger.warning(f"Unexpected status {response.status_code}: {response.text}")
            return None
    
    except requests.exceptions.Timeout:
        logger.error(f"Request timeout: {url}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return None
```

### Subprocess Execution
```python
import subprocess
import sys
from typing import Optional

def run_command(
    args: list[str],
    capture_output: bool = True,
    check: bool = True,
    timeout: int = 30
) -> Optional[str]:
    """
    Execute a shell command safely.
    
    Args:
        args: Command and arguments as list
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise on non-zero exit
        timeout: Command timeout in seconds
    
    Returns:
        Command output or None on error
    """
    try:
        result = subprocess.run(
            args,
            capture_output=capture_output,
            text=True,
            check=check,
            timeout=timeout
        )
        return result.stdout.strip()
    
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Command failed (exit {e.returncode}): {' '.join(args)}\n"
            f"stderr: {e.stderr}",
            exc_info=True
        )
        if check:
            raise
        return None
    
    except subprocess.TimeoutExpired:
        logger.error(f"Command timeout after {timeout}s: {' '.join(args)}")
        raise
    
    except Exception as e:
        logger.error(f"Command execution error: {e}", exc_info=True)
        raise
```

## Retry Strategies

### With exponential backoff
```python
import time
from typing import Callable, TypeVar, Optional

T = TypeVar('T')

def retry_with_backoff(
    func: Callable[[], T],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
) -> Optional[T]:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for each retry
    
    Returns:
        Function result or None if all attempts fail
    """
    delay = initial_delay
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_attempts:
                logger.error(f"All {max_attempts} attempts failed: {e}")
                return None
            
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed: {e}. "
                f"Retrying in {delay}s..."
            )
            time.sleep(delay)
            delay *= backoff_factor
    
    return None
```

### Using requests with retry
```python
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests

def create_session_with_retry(
    total: int = 3,
    backoff_factor: float = 1.0,
    status_forcelist: list[int] = [500, 502, 503, 504]
) -> requests.Session:
    """Create a requests session with automatic retry."""
    session = requests.Session()
    retry = Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
```

## Logging Best Practices

### Setup
```python
import logging
import sys

def setup_logging(level: int = logging.INFO):
    """Configure application logging."""
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # File handler (optional)
    file_handler = logging.FileHandler('app.log')
    file_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

# Usage
setup_logging()
logger = logging.getLogger(__name__)
```

### What to Log
```python
# ✅ Good logging examples
logger.info("Starting data sync process")
logger.info(f"Processing {len(items)} items")
logger.debug(f"API request: {url} with data: {data}")
logger.warning(f"Unexpected status code {status_code}, retrying...")
logger.error("Failed to connect to database", exc_info=True)

# ❌ Bad logging examples
logger.info("test")  # Too vague
logger.debug(huge_json_dump)  # Too verbose
print("Something happened")  # Use logger, not print
```

## Type Hints

Always use type hints for function signatures:
```python
from typing import Optional, Dict, List, Any

def process_data(
    items: List[Dict[str, Any]],
    max_count: Optional[int] = None
) -> Dict[str, int]:
    """
    Process a list of items and return statistics.
    
    Args:
        items: List of item dictionaries
        max_count: Maximum items to process (None = all)
    
    Returns:
        Dictionary with processing statistics
    """
    processed = 0
    failed = 0
    
    for item in items[:max_count]:
        try:
            # Process item...
            processed += 1
        except Exception as e:
            logger.error(f"Failed to process item: {e}")
            failed += 1
    
    return {"processed": processed, "failed": failed}
```

## Testing Strategy

### Manual Testing Checklist
- [ ] Happy path works
- [ ] Error cases handled (network error, auth error, etc.)
- [ ] Logs are informative
- [ ] Environment variables validated
- [ ] Timeouts don't hang the process

### Quick Test Script Pattern
```python
if __name__ == "__main__":
    # Quick manual test
    setup_logging(logging.DEBUG)
    
    try:
        result = your_function(test_data)
        print(f"Success: {result}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
```

## Security Checklist

- [ ] Never log sensitive data (tokens, passwords, PII)
- [ ] Environment variables for secrets (not hardcoded)
- [ ] Input validation for user-provided data
- [ ] SQL parameterized queries (no string interpolation)
- [ ] Proper file permissions for sensitive files

## Performance Tips

```python
# ✅ Use connection pooling for repeated API calls
session = requests.Session()
for url in urls:
    response = session.get(url)

# ✅ Batch operations when possible
# Instead of: for item in items: create_issue(item)
# Do: bulk_create_issues(items)

# ✅ Use generators for large datasets
def process_large_file(filename):
    with open(filename) as f:
        for line in f:  # Generator, doesn't load entire file
            yield process_line(line)
```

## Hook Development: Failure Recording Rule

新しいフック（`.gemini/hooks/*.py`）を作成する場合、**失敗をブロック or 検出したら必ず `memory/failures.jsonl` に記録すること**。
これはシステムの PDCA サイクルの核であり、Queen と Mona が失敗パターンを分析して改善策を立てるために不可欠。

### 必須: `_record_failure` 関数の実装

```python
import json
import os
from datetime import datetime

def _record_failure(task_type: str, error: str, solution: str) -> None:
    """Record failure to failures.jsonl for PDCA cycle"""
    try:
        project_dir = os.environ.get("GEMINI_PROJECT_DIR", ".")
        failures_file = os.path.join(project_dir, "memory/failures.jsonl")
        os.makedirs(os.path.dirname(failures_file), exist_ok=True)

        entry = {
            "task_type": task_type,       # e.g. "git_operation", "shell_command", "report_validation"
            "result": "blocked",          # "blocked" or "fail"
            "error": error,               # What went wrong
            "solution": solution,         # How to fix it
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        with open(failures_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
```

### 記録すべきタイミング
| フック種別 | 記録タイミング | task_type 例 |
|---|---|---|
| BeforeTool (ブロック系) | `decision: "deny"` を返す時 | `git_operation`, `write_file_security` |
| AfterTool (ログ系) | エラーを検出した時 | `shell_command` |
| AfterAgent (検証系) | バリデーション失敗時 | `report_validation` |

### 記録しないもの（ノイズ防止）
- 情報取得系コマンドの失敗（`git status`, `ls`, `cat` 等）
- 一時的なネットワークエラー（リトライで解決するもの）
- 正常なブロック（例: hookが正しくスキップした場合）

### 現在 failures.jsonl に記録するフック一覧
1. `block_risky_git.py` — 危険な git 操作のブロック
2. `block_secrets.py` — 秘密情報書き込みのブロック
3. `validate_response.py` — レポート不足でリトライ
4. `log_shell_command.py` — シェルコマンド実行失敗

**新しいフックを追加したら、このリストも更新すること。**

## Summary

Key takeaways:
1. **Always handle errors explicitly** - Don't let exceptions silently fail
2. **Set timeouts** - Prevent indefinite hangs
3. **Log appropriately** - Info for progress, Error with exc_info=True
4. **Use type hints** - Improve code clarity and catch bugs early
5. **Test error cases** - Not just the happy path
6. **Validate inputs** - Check environment variables and user data
7. **Retry transient failures** - Network errors, rate limits, etc.
8. **Record failures in hooks** - Always log to `memory/failures.jsonl` for PDCA cycle

When in doubt, prefer **clarity over cleverness** and **safety over speed**.
