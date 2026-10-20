"""Run the same fail-fast checks locally and in GitHub Actions."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    checks = (
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
