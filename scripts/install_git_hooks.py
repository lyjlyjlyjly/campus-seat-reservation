"""安全地为当前 clone 启用项目自带的 pre-push 检查。"""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PROJECT_HOOKS = ROOT / ".githooks"


def _git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False
    )


def _same_path(value: str) -> bool:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve() == PROJECT_HOOKS.resolve()


def main() -> int:
    if not (PROJECT_HOOKS / "pre-push").is_file():
        print("找不到 .githooks/pre-push。", file=sys.stderr)
        return 1

    local = _git("config", "--local", "--get", "core.hooksPath")
    if local.returncode not in (0, 1):
        print(local.stderr.strip() or "无法读取本地 Git hook 配置。", file=sys.stderr)
        return 1
    if local.returncode == 0 and not _same_path(local.stdout.strip()):
        print(
            f"当前仓库已配置 core.hooksPath={local.stdout.strip()!r}；未覆盖现有配置。"
            "请由仓库维护者将现有 hook 与 .githooks/pre-push 合并后再启用。",
            file=sys.stderr,
        )
        return 1

    if local.returncode == 1:
        effective = _git("config", "--get", "core.hooksPath")
        if effective.returncode == 0 and not _same_path(effective.stdout.strip()):
            print(
                f"用户或系统已配置 core.hooksPath={effective.stdout.strip()!r}；未覆盖该 hook。"
                "请由仓库维护者将现有 hook 与 .githooks/pre-push 合并后再启用。",
                file=sys.stderr,
            )
            return 1
        if effective.returncode not in (0, 1):
            print(effective.stderr.strip() or "无法读取有效 Git hook 配置。", file=sys.stderr)
            return 1

        default_hooks = _git("rev-parse", "--git-path", "hooks")
        if default_hooks.returncode:
            print(default_hooks.stderr.strip() or "无法读取 Git hooks 目录。", file=sys.stderr)
            return 1
        hooks_dir = Path(default_hooks.stdout.strip())
        if not hooks_dir.is_absolute():
            hooks_dir = ROOT / hooks_dir
        active_hooks = [
            path.name
            for path in hooks_dir.iterdir()
            if path.is_file() and not path.name.endswith(".sample")
        ] if hooks_dir.is_dir() else []
        if active_hooks:
            print(
                f"Git hooks 目录已有启用项：{', '.join(sorted(active_hooks))}；未更改 hook 路径。"
                "请先确认并合并现有 hook。",
                file=sys.stderr,
            )
            return 1

    if local.returncode == 0:
        print("项目 pre-push hook 已安装。")
        return 0

    configured = _git("config", "--local", "core.hooksPath", ".githooks")
    if configured.returncode:
        print(configured.stderr.strip() or "无法安装项目 pre-push hook。", file=sys.stderr)
        return 1
    print("已为当前 clone 安装 .githooks/pre-push；个人/全局 hook 配置未覆盖。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
