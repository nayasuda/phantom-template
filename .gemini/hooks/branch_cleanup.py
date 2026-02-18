#!/usr/bin/env python3
"""
AfterTool Hook: Safe branch cleanup assistant.

Runs after run_shell_command and performs lightweight branch hygiene:
1) git fetch --prune
2) find merged local branches
3) optionally delete merged branches with `git branch -d`

By default, this hook only reports deletion candidates.
Set PHANTOM_AUTO_BRANCH_DELETE=1 to enable automatic local deletion.
"""

import json
import os
import subprocess
import sys
from typing import List, Tuple


TRIGGER_PREFIXES = (
    "gh pr merge",
    "git pull",
    "git fetch",
    "git merge",
    "git rebase",
    "git checkout main",
    "git switch main",
    "git checkout -",       # 戻り操作でも発動
)

PROTECTED_BRANCHES = {"main", "master", "develop", "dev"}


def _run_git(project_dir: str, args: List[str], timeout: int = 10) -> Tuple[bool, str, str]:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as exc:  # pragma: no cover - hook runtime safety
        return False, "", str(exc)


def _base_branch(project_dir: str) -> str:
    for candidate in ("main", "master"):
        ok, _, _ = _run_git(project_dir, ["show-ref", "--verify", f"refs/heads/{candidate}"])
        if ok:
            return candidate
    return "main"


def _current_branch(project_dir: str) -> str:
    ok, out, _ = _run_git(project_dir, ["branch", "--show-current"])
    return out if ok else ""


def _merged_branches(project_dir: str, base: str) -> List[str]:
    ok, out, _ = _run_git(project_dir, ["branch", "--merged", base])
    if not ok or not out:
        return []
    branches: List[str] = []
    for raw_line in out.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("*"):
            line = line[1:].strip()
        branches.append(line)
    return branches


def _gone_branches(project_dir: str) -> List[str]:
    ok, out, _ = _run_git(project_dir, ["branch", "-vv"])
    if not ok or not out:
        return []
    branches: List[str] = []
    for raw_line in out.splitlines():
        line = raw_line.rstrip()
        if ": gone]" not in line:
            continue
        # examples:
        #   feature/x  abc123 [origin/feature/x: gone] ...
        # * feature/y  def456 [origin/feature/y: gone] ...
        name = line.lstrip("*").strip().split()[0]
        if name:
            branches.append(name)
    return branches


def _local_only_branches(project_dir: str, current: str) -> List[str]:
    """Find branches that have NO remote tracking branch (never pushed)."""
    ok, out, _ = _run_git(project_dir, ["branch", "-vv"])
    if not ok or not out:
        return []
    branches: List[str] = []
    for raw_line in out.splitlines():
        line = raw_line.rstrip()
        name = line.lstrip("*").strip().split()[0]
        if not name or name in PROTECTED_BRANCHES or name == current:
            continue
        # Has remote tracking → skip (tracked or gone are handled separately)
        if "[origin/" in line:
            continue
        branches.append(name)
    return branches


def _rescue_patch(project_dir: str, base: str, branch: str) -> str:
    rescue_dir = os.path.join(project_dir, ".gemini", "tmp", "branch_rescue")
    os.makedirs(rescue_dir, exist_ok=True)
    safe_name = branch.replace("/", "__")
    rescue_path = os.path.join(rescue_dir, f"{safe_name}.patch")
    try:
        result = subprocess.run(
            ["git", "format-patch", "--stdout", f"{base}..{branch}"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=20,
        )
        # Even if no output, create a marker file for traceability.
        with open(rescue_path, "w", encoding="utf-8") as f:
            f.write(result.stdout or f"# no unique commits found for {branch}\n")
        return rescue_path
    except Exception:
        return ""


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print(json.dumps({}))
        return

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}
    command = (tool_input.get("command") or "").strip()

    if tool_name != "run_shell_command":
        print(json.dumps({}))
        return

    if not any(command.startswith(prefix) for prefix in TRIGGER_PREFIXES):
        print(json.dumps({}))
        return

    project_dir = os.environ.get("GEMINI_PROJECT_DIR", ".")
    auto_delete = os.environ.get("PHANTOM_AUTO_BRANCH_DELETE", "0") == "1"
    auto_delete_gone = os.environ.get("PHANTOM_AUTO_BRANCH_DELETE_GONE", "1") == "1"
    force_delete_gone = os.environ.get("PHANTOM_AUTO_BRANCH_FORCE_GONE_DELETE", "1") == "1"

    # Keep remote-tracking references clean.
    _run_git(project_dir, ["fetch", "--prune"])

    base = _base_branch(project_dir)
    current = _current_branch(project_dir)
    merged = _merged_branches(project_dir, base)
    gone = _gone_branches(project_dir)
    local_only = _local_only_branches(project_dir, current)
    auto_delete_local = os.environ.get("PHANTOM_AUTO_BRANCH_DELETE_LOCAL", "1") == "1"

    candidates = [
        b
        for b in merged
        if b
        and b not in PROTECTED_BRANCHES
        and b != current
    ]

    deleted: List[str] = []
    failed: List[str] = []
    deleted_gone: List[str] = []
    failed_gone: List[str] = []
    rescued_gone: List[str] = []
    deleted_local: List[str] = []
    rescued_local: List[str] = []

    if auto_delete:
        for branch in candidates:
            ok, _, _ = _run_git(project_dir, ["branch", "-d", branch])
            if ok:
                deleted.append(branch)
            else:
                failed.append(branch)

        if auto_delete_gone:
            for branch in gone:
                if branch in PROTECTED_BRANCHES or branch == current:
                    continue
                ok, _, _ = _run_git(project_dir, ["branch", "-d", branch])
                if ok:
                    deleted_gone.append(branch)
                    continue
                # Not merged: create rescue patch, then force-delete if enabled.
                rescue_path = _rescue_patch(project_dir, base, branch)
                if rescue_path:
                    rescued_gone.append(f"{branch} -> {rescue_path}")
                if force_delete_gone:
                    ok_force, _, _ = _run_git(project_dir, ["branch", "-D", branch])
                    if ok_force:
                        deleted_gone.append(branch)
                    else:
                        failed_gone.append(branch)
                else:
                    failed_gone.append(branch)

        # Clean up local-only branches (never pushed to remote)
        if auto_delete_local:
            for branch in local_only:
                # Always rescue before deleting local-only branches
                rescue_path = _rescue_patch(project_dir, base, branch)
                if rescue_path:
                    rescued_local.append(f"{branch} -> {rescue_path}")
                ok_force, _, _ = _run_git(project_dir, ["branch", "-D", branch])
                if ok_force:
                    deleted_local.append(branch)

    total_deleted = len(deleted) + len(deleted_gone) + len(deleted_local)

    if auto_delete:
        message = (
            f"🧹 Branch cleanup: deleted {len(deleted)} merged + {len(deleted_gone)} gone "
            f"+ {len(deleted_local)} local-only branch(es)."
        )
        details = []
        if deleted:
            details.append("Deleted merged: " + ", ".join(deleted[:10]))
        if deleted_gone:
            details.append("Deleted gone: " + ", ".join(deleted_gone[:10]))
        if deleted_local:
            details.append("Deleted local-only: " + ", ".join(deleted_local[:10]))
        if failed:
            details.append("Failed: " + ", ".join(failed[:10]))
        if failed_gone:
            details.append("Failed gone: " + ", ".join(failed_gone[:10]))
        if rescued_gone or rescued_local:
            all_rescued = rescued_gone + rescued_local
            details.append("Rescued patches: " + " | ".join(all_rescued[:5]))
        additional_context = "\n".join(details)

        # Suppress output if nothing was cleaned
        if total_deleted == 0 and not failed and not failed_gone:
            print(json.dumps({}))
            return
    else:
        total_candidates = len(candidates) + len(gone) + len(local_only)
        message = (
            f"🧹 Branch cleanup check: merged={len(candidates)}, gone={len(gone)}, "
            f"local-only={len(local_only)} "
            f"(set PHANTOM_AUTO_BRANCH_DELETE=1 to auto-delete)."
        )
        additional_context = ""
        if candidates:
            additional_context = "Merged candidates: " + ", ".join(candidates[:15])
        if gone:
            extra = "Gone candidates: " + ", ".join(gone[:15])
            additional_context = (additional_context + "\n" + extra).strip()
        if local_only:
            extra = "Local-only candidates: " + ", ".join(local_only[:15])
            additional_context = (additional_context + "\n" + extra).strip()

        # Suppress output if nothing to report
        if total_candidates == 0:
            print(json.dumps({}))
            return

    output = {"systemMessage": message}
    if additional_context:
        output["hookSpecificOutput"] = {"additionalContext": additional_context}

    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
