"""Run the same fail-fast checks locally and in GitHub Actions."""

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    git_policy_check = ["scripts/check_git_policy.py"]
    if not (os.environ.get("GITHUB_EVENT_NAME") and os.environ.get("GITHUB_EVENT_PATH")):
        # Local runs should check the same committed range as a pending push.
        git_policy_check.extend(["--base", "origin/main", "--head", "HEAD"])
    checks = (
        ("Git push scope and Conventional Commits", git_policy_check),
        ("Agent Note format and links", ["scripts/check_notes.py"]),
        ("Python compilation", ["-m", "compileall", "-q", "app", "scripts", "tests"]),
        ("Behavior tests", ["-m", "pytest"]),
    )
    for label, arguments in checks:
        print(f"[CI] {label}", flush=True)
        result = subprocess.run([sys.executable, *arguments], cwd=ROOT, check=False)
        if result.returncode:
            print(f"[CI] Failed: {label} (exit {result.returncode})", flush=True)
            return result.returncode
    print("[CI] All checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
