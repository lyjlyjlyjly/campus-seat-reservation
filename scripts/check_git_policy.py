"""拒绝一条提交或一次推送混入多个模块组，并检查 Conventional Commits。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
TYPES = ("feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert")
SCOPES = ("m1", "m2", "m3", "d", "infra")
HEADER = re.compile(
    rf"(?P<type>{'|'.join(TYPES)})\((?P<scope>{'|'.join(SCOPES)})\)(?P<breaking>!)?: (?P<description>\S.*)"
)
GITHUB_MERGE = re.compile(r"Merge pull request #\d+ from \S+")
ZERO_OID = re.compile(r"^0+$")

GROUP_PREFIXES = {
    "G1": ("app/m1/", "tests/m1/", "web/templates/m1/", "web/assets/m1/", "docs/m1/"),
    "G2": (
        "app/m2/", "tests/m2/", "app/d/auth/", "app/d/audit/", "tests/d/auth/", "tests/d/audit/",
        "web/templates/m2/", "web/assets/m2/", "web/templates/d/auth/", "web/assets/d/auth/",
        "web/templates/d/audit/", "web/assets/d/audit/", "docs/m2/", "docs/d/auth/", "docs/d/audit/",
    ),
    "G3": (
        "app/m3/", "tests/m3/", "app/d/spaces/", "tests/d/spaces/", "web/templates/m3/", "web/assets/m3/",
        "web/templates/d/spaces/", "web/assets/d/spaces/", "docs/m3/", "docs/d/spaces/", "database/",
    ),
    "D": ("app/d/", "tests/d/", "web/templates/d/", "web/assets/d/", "docs/d/"),
}
GROUP_SCOPES = {
    "G1": {"m1"},
    "G2": {"m2", "d"},
    "G3": {"m3", "d"},
    "D": {"d"},
}
BRANCH_PREFIXES = {
    "G1": ("m1/",),
    "G2": ("m2/", "d/"),
    "G3": ("m3/", "d/"),
    "D": ("d/",),
    "infra": ("infra/",),
}


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str
    parents: tuple[str, ...]
    paths: tuple[str, ...]

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1


class GitPolicyError(RuntimeError):
    """Git 范围或仓库信息无法安全核对。"""


def _git(repo: Path, *arguments: str, check: bool = True) -> bytes:
    result = subprocess.run(
        ["git", *arguments], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if check and result.returncode:
        details = os.fsdecode(result.stderr).strip()
        raise GitPolicyError(details or f"git {' '.join(arguments)} 失败（{result.returncode}）")
    return result.stdout


def classify_paths(paths: Iterable[str]) -> set[str]:
    """按 AGENTS.md 中已经约定的目录负责人，将文件映射到唯一责任组。"""
    groups: set[str] = set()
    for raw_path in paths:
        path = raw_path.replace("\\", "/").lstrip("./")
        if path == "app/bootstrap.py":
            groups.add("G3")
            continue
        for group, prefixes in GROUP_PREFIXES.items():
            if any(path.startswith(prefix) for prefix in prefixes):
                groups.add(group)
                break
    return groups


def _commit(repo: Path, sha: str) -> Commit:
    details = os.fsdecode(_git(repo, "rev-list", "--parents", "-n", "1", sha)).strip().split()
    if not details:
        raise GitPolicyError(f"无法读取提交：{sha}")
    parents = tuple(details[1:])
    subject = os.fsdecode(_git(repo, "show", "-s", "--format=%s", sha)).rstrip("\r\n")
    if parents:
        raw_paths = _git(repo, "diff", "--no-renames", "--name-only", "-z", parents[0], sha)
    else:
        raw_paths = _git(
            repo, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "--no-renames", "-z", sha
        )
    paths = tuple(os.fsdecode(path) for path in raw_paths.split(b"\0") if path)
    return Commit(sha=sha, subject=subject, parents=parents, paths=paths)


def _resolve(repo: Path, ref: str) -> str:
    output = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}", check=False)
    if not output:
        raise GitPolicyError(f"找不到 Git 提交 {ref}；请先 fetch 对应目标分支。")
    return os.fsdecode(output).strip()


def _range(repo: Path, base: str, head: str, *, require_fast_forward: bool = False) -> tuple[str, list[Commit]]:
    base_sha = _resolve(repo, base)
    head_sha = _resolve(repo, head)
    if require_fast_forward:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", base_sha, head_sha], cwd=repo, check=False
        )
        if result.returncode:
            raise GitPolicyError("远端分支不是本地 HEAD 的祖先；禁止改写或强制推送远端历史。")
        merge_base = base_sha
    else:
        output = _git(repo, "merge-base", base_sha, head_sha, check=False)
        if not output:
            raise GitPolicyError(f"{base} 与 {head} 没有共同祖先；无法验证单模块推送。")
        merge_base = os.fsdecode(output).strip()
    revisions = os.fsdecode(_git(repo, "rev-list", "--reverse", f"{merge_base}..{head_sha}")).splitlines()
    commits = [_commit(repo, sha) for sha in revisions]
    return merge_base, commits


def _parse_subject(subject: str, where: str, errors: list[str]) -> str | None:
    match = HEADER.fullmatch(subject)
    if match is None:
        errors.append(
            f"{where}: 提交标题不符合 Conventional Commits。使用 "
            "<type>(<scope>): <中文描述>，scope 为 m1/m2/m3/d/infra。"
        )
        return None
    return match.group("scope")


def _scopes_for(groups: set[str]) -> set[str]:
    if len(groups) == 1:
        return GROUP_SCOPES[next(iter(groups))]
    if not groups:
        return {"infra"}
    return set()


def _validate_branch(branch: str, groups: set[str], errors: list[str], *, has_changes: bool) -> None:
    if branch in {"main", "master"}:
        if has_changes:
            errors.append(f"分支 {branch} 是主分支；请从模块分支创建 PR。")
        return
    expected = BRANCH_PREFIXES[next(iter(groups))] if len(groups) == 1 else BRANCH_PREFIXES["infra"]
    if not branch.startswith(expected):
        groups_text = ", ".join(sorted(groups)) if groups else "infra"
        errors.append(
            f"分支 {branch!r} 与改动范围 {groups_text} 不匹配；分支名前缀应为：{', '.join(expected)}。"
        )


def check_range(
    repo: Path,
    base: str,
    head: str,
    *,
    title: str | None = None,
    branch: str | None = None,
    validate_branch: bool = False,
    allow_github_merge: bool = False,
    require_fast_forward: bool = False,
) -> list[str]:
    """检查 base 与 head 间的提交、变更路径、模块 scope、PR 标题及分支名。"""
    repo = Path(repo).resolve()
    errors: list[str] = []
    try:
        merge_base, commits = _range(repo, base, head, require_fast_forward=require_fast_forward)
        diff_paths = os.fsdecode(
            _git(repo, "diff", "--no-renames", "--name-only", "-z", merge_base, head)
        ).split("\0")
    except GitPolicyError as error:
        return [str(error)]

    meaningful_paths = [path for path in diff_paths if path]
    # A change and its later revert still touched both responsibility groups in this push.
    for commit in commits:
        if not commit.is_merge:
            meaningful_paths.extend(commit.paths)
    groups = classify_paths(meaningful_paths)
    group_text = ", ".join(sorted(groups)) or "infra"

    if len(groups) > 1:
        errors.append(
            f"一次推送/PR 只能包含一个模块组；当前改动涉及 {group_text}。"
            "请按负责人拆成不同分支、PR 和 push。"
        )

    for commit in commits:
        if commit.is_merge and allow_github_merge and GITHUB_MERGE.fullmatch(commit.subject):
            # GitHub 生成的 PR merge subject 不可改写；来源 PR 的提交已在 PR 检查中校验。
            continue
        where = f"{commit.sha[:12]} ({commit.subject})"
        scope = _parse_subject(commit.subject, where, errors)
        if scope is None:
            continue
        commit_groups = classify_paths(commit.paths) if not commit.is_merge else set()
        if len(commit_groups) > 1:
            owners = ", ".join(sorted(commit_groups))
            errors.append(f"{where}: 单个提交同时修改多个模块组：{owners}。")
        # A commit containing no owned module path is shared infrastructure,
        # even when another commit in this push belongs to one module group.
        allowed = _scopes_for(commit_groups) if commit_groups else {"infra"}
        if scope not in allowed and not (scope == "infra" and not commit_groups):
            allowed_text = "/".join(sorted(allowed)) if allowed else "无可用 scope"
            errors.append(f"{where}: scope {scope!r} 与文件责任组不一致；允许：{allowed_text}。")

    if title is not None:
        title_scope = _parse_subject(title, "PR 标题", errors)
        if title_scope is not None:
            allowed_title_scopes = _scopes_for(groups)
            if title_scope not in allowed_title_scopes:
                allowed_text = "/".join(sorted(allowed_title_scopes)) if allowed_title_scopes else "无可用 scope"
                errors.append(f"PR 标题 scope {title_scope!r} 与改动范围不一致；允许：{allowed_text}。")

    if validate_branch and branch is not None:
        _validate_branch(branch, groups, errors, has_changes=bool(meaningful_paths or commits))
    return errors


def _is_zero(value: str) -> bool:
    return bool(ZERO_OID.fullmatch(value))


def _event_check(event_name: str, event_path: Path, repo: Path) -> tuple[list[str], str | None]:
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"无法读取 GitHub 事件数据：{error}"], None

    if event_name == "workflow_dispatch":
        return [], "手动运行 CI 不代表新推送，push 策略检查跳过。"
    if event_name == "pull_request":
        request = payload.get("pull_request", {})
        base = request.get("base", {}).get("sha")
        head = request.get("head", {}).get("sha")
        branch = request.get("head", {}).get("ref")
        title = request.get("title")
        if not all((base, head, branch, title)):
            return ["Pull Request 事件缺少 base/head/branch/title 字段。"], None
        return (
            check_range(repo, base, head, title=title, branch=branch, validate_branch=True),
            f"检查 PR {branch} 的模块范围、标题和 Conventional Commits。",
        )
    if event_name == "push":
        ref = payload.get("ref", "")
        if not ref.startswith("refs/heads/"):
            return [], f"推送目标 {ref or '(unknown)'} 不是分支；策略检查跳过。"
        branch = ref.removeprefix("refs/heads/")
        before, after = payload.get("before"), payload.get("after")
        if not before or not after or _is_zero(after):
            return ["Push 事件缺少有效 before/after 提交。"], None

        if _is_zero(before):
            default_branch = payload.get("repository", {}).get("default_branch", "main")
            base = f"origin/{default_branch}"
        else:
            base = before
        errors = check_range(
            repo,
            base,
            after,
            branch=branch,
            validate_branch=branch not in {"main", "master"},
            allow_github_merge=branch in {"main", "master"},
            require_fast_forward=not _is_zero(before),
        )

        # A sequence of otherwise separate single-module pushes must keep one module per PR branch.
        if branch not in {"main", "master"}:
            default_branch = payload.get("repository", {}).get("default_branch", "main")
            branch_errors = check_range(
                repo, f"origin/{default_branch}", after, branch=branch, validate_branch=True
            )
            errors.extend(f"当前分支累计范围：{error}" for error in branch_errors)
        return errors, f"检查 push 到 {branch} 的提交范围和模块分支累计范围。"
    return [f"不支持的 GitHub 事件类型：{event_name}"], None


def _hook_check(repo: Path, remote: str, lines: Iterable[str]) -> list[str]:
    updates = []
    for line in lines:
        fields = line.split()
        if len(fields) != 4:
            return [f"无法解析 pre-push 更新行：{line.rstrip()}" ]
        local_ref, local_oid, remote_ref, remote_oid = fields
        if _is_zero(local_oid):
            if remote_ref in {"refs/heads/main", "refs/heads/master"}:
                return ["禁止删除 main/master 受保护主分支。"]
            continue
        updates.append((local_ref, local_oid, remote_ref, remote_oid))
    if not updates:
        return []
    if len(updates) != 1:
        return ["一次 git push 只能更新一个分支或 tag；请分次推送。"]

    local_ref, local_oid, remote_ref, remote_oid = updates[0]
    if remote_ref.startswith("refs/tags/"):
        try:
            tag_commit = _resolve(repo, f"{local_oid}^{{commit}}")
            default_head = _resolve(repo, f"{remote}/main")
            is_ancestor = subprocess.run(
                ["git", "merge-base", "--is-ancestor", tag_commit, default_head], cwd=repo, check=False
            )
        except GitPolicyError as error:
            return [str(error)]
        if is_ancestor.returncode:
            return ["release tag 只能指向已进入 main 的提交；先经单模块 PR 合并，再单独推送 tag。"]
        return []
    if not remote_ref.startswith("refs/heads/"):
        return [f"当前策略不支持推送目标：{remote_ref}"]

    branch = remote_ref.removeprefix("refs/heads/")
    if branch in {"main", "master"}:
        return [f"禁止直接推送 {branch}；请将一个模块组的分支通过 Pull Request 合并。"]

    if not _is_zero(remote_oid):
        fast_forward = subprocess.run(
            ["git", "merge-base", "--is-ancestor", remote_oid, local_oid], cwd=repo, check=False
        )
        if fast_forward.returncode:
            return ["远端分支不是本地 HEAD 的祖先；禁止改写或强制推送远端历史。"]

    default_ref = f"{remote}/main"
    errors = check_range(
        repo,
        default_ref,
        local_oid,
        branch=branch,
        validate_branch=True,
    )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Git 仓库根目录")
    parser.add_argument("--base", help="本地检查时已 fetch 的比较基线，例如 origin/main")
    parser.add_argument("--head", default="HEAD", help="比较目标，默认 HEAD")
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME"))
    parser.add_argument("--event-path", type=Path, default=os.environ.get("GITHUB_EVENT_PATH"))
    parser.add_argument("--pre-push", action="store_true", help="按 Git pre-push hook 标准输入检查推送")
    parser.add_argument("--remote", help="pre-push hook 提供的 remote 名称")
    arguments = parser.parse_args(argv)
    repo = arguments.root.resolve()

    try:
        if arguments.pre_push:
            if not arguments.remote:
                errors = ["pre-push 检查缺少 remote 名称。"]
            else:
                errors = _hook_check(repo, arguments.remote, sys.stdin)
            success = f"推送符合单模块和 Conventional Commits 规则。"
        elif arguments.event_name and arguments.event_path:
            errors, success = _event_check(arguments.event_name, arguments.event_path, repo)
        elif arguments.base:
            branch = os.fsdecode(_git(repo, "branch", "--show-current")).strip()
            errors = check_range(
                repo,
                arguments.base,
                arguments.head,
                branch=branch or None,
                validate_branch=bool(branch),
            )
            success = f"{arguments.base}..{arguments.head} 符合单模块和 Conventional Commits 规则。"
        else:
            errors = []
            success = "本地未提供 push 基线；请运行 python scripts/check_git_policy.py --base origin/main --head HEAD。"
    except GitPolicyError as error:
        errors = [str(error)]
        success = None

    if errors:
        print("Git 推送策略检查失败：", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    if success:
        print(success)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
