"""用隔离的真实 Git 仓库验证模块推送门禁。"""

import json
from pathlib import Path
import subprocess

import pytest

from scripts.check_git_policy import _event_check, _hook_check, check_range
from scripts import install_git_hooks


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> tuple[Path, str]:
    git(tmp_path, "init")
    git(tmp_path, "checkout", "-b", "main")
    git(tmp_path, "config", "user.name", "Test User")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "README.md").write_text("base\n", encoding="utf-8")
    git(tmp_path, "add", "README.md")
    git(tmp_path, "commit", "-m", "docs(infra): 建立测试基线")
    return tmp_path, git(tmp_path, "rev-parse", "HEAD")


def commit(repo: Path, message: str, files: dict[str, str]) -> str:
    for filename, content in files.items():
        path = repo / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(repo, "add", "--all")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def test_one_module_commit_includes_its_tests_and_module_docs(repo):
    root, base = repo
    head = commit(
        root,
        "feat(m1): 实现座位搜索入口",
        {
            "app/m1/router.py": "route = 'search'\n",
            "tests/m1/test_search.py": "def test_search():\n    assert True\n",
            "docs/m1/search.md": "M1 搜索说明\n",
        },
    )

    errors = check_range(root, base, head, branch="m1/12-search", validate_branch=True)

    assert errors == []


def test_g2_can_update_m2_and_its_assigned_auth_subdomain(repo):
    root, base = repo
    head = commit(
        root,
        "feat(m2): 增加申请角色校验",
        {
            "app/m2/router.py": "route = 'apply'\n",
            "app/d/auth/rbac.py": "permission = 'room:apply'\n",
            "tests/m2/test_apply.py": "def test_apply():\n    assert True\n",
        },
    )
    assert check_range(root, base, head) == []


def test_g3_can_update_m3_spaces_and_its_migration(repo):
    root, base = repo
    head = commit(
        root,
        "feat(m3): 增加工单位置查询",
        {
            "app/m3/router.py": "route = 'ticket'\n",
            "app/d/spaces/rooms.py": "def rooms():\n    return []\n",
            "app/bootstrap.py": "def bootstrap():\n    pass\n",
            "database/migrations/V1__init.sql": "CREATE TABLE room (id INTEGER PRIMARY KEY);\n",
        },
    )
    assert check_range(root, base, head) == []


def test_separate_commits_from_two_groups_in_one_push_are_rejected(repo):
    root, base = repo
    commit(root, "feat(m1): 增加座位搜索", {"app/m1/search.py": "value = 1\n"})
    head = commit(root, "feat(m2): 增加教室申请", {"app/m2/apply.py": "value = 2\n"})

    errors = check_range(root, base, head)

    assert any("只能包含一个模块组" in error and "G1, G2" in error for error in errors), errors


def test_cross_group_file_rename_is_rejected(repo):
    root, base = repo
    commit(root, "feat(m1): 建立座位模块文件", {"app/m1/ownership.py": "owner = 'm1'\n"})
    (root / "app/m2").mkdir(parents=True)
    git(root, "mv", "app/m1/ownership.py", "app/m2/ownership.py")
    git(root, "commit", "-m", "refactor(m2): 调整文件目录")
    head = git(root, "rev-parse", "HEAD")

    errors = check_range(root, base, head)

    assert any("只能包含一个模块组" in error and "G1, G2" in error for error in errors), errors


def test_single_commit_touching_two_groups_is_rejected(repo):
    root, base = repo
    head = commit(
        root,
        "feat(m1): 同时修改两个模块",
        {"app/m1/search.py": "value = 1\n", "app/m2/apply.py": "value = 2\n"},
    )

    errors = check_range(root, base, head)

    assert any("单个提交同时修改多个模块组" in error for error in errors), errors
    assert any("只能包含一个模块组" in error for error in errors), errors


def test_non_conventional_commit_is_rejected(repo):
    root, base = repo
    head = commit(root, "更新座位搜索", {"app/m1/search.py": "value = 1\n"})

    errors = check_range(root, base, head)

    assert any("不符合 Conventional Commits" in error for error in errors), errors


def test_commit_scope_must_match_changed_group(repo):
    root, base = repo
    head = commit(root, "feat(m2): 写错模块范围", {"app/m1/search.py": "value = 1\n"})

    errors = check_range(root, base, head)

    assert any("scope 'm2' 与文件责任组不一致" in error for error in errors), errors


def test_shared_infrastructure_has_its_own_scope(repo):
    root, base = repo
    head = commit(root, "docs(infra): 说明启动命令", {"README.md": "run\n"})

    errors = check_range(root, base, head, title="docs(infra): 说明启动命令")

    assert errors == []


def test_infrastructure_commit_can_accompany_one_module_group(repo):
    root, base = repo
    commit(root, "feat(m1): 实现座位搜索", {"app/m1/search.py": "value = 1\n"})
    head = commit(root, "docs(infra): 补充协作说明", {"docs/architecture.md": "分工说明\n"})

    errors = check_range(root, base, head, branch="m1/12-search", validate_branch=True)

    assert errors == []


def test_one_module_commit_with_global_file_uses_module_scope(repo):
    root, base = repo
    head = commit(
        root,
        "docs(m1): 更新座位模块说明",
        {"app/m1/search.py": "value = 1\n", "README.md": "说明\n"},
    )

    errors = check_range(root, base, head, branch="m1/12-search", validate_branch=True)

    assert errors == []


def test_empty_main_range_passes_but_main_with_new_commit_is_rejected(repo):
    root, base = repo

    assert check_range(root, base, base, branch="main", validate_branch=True) == []

    head = commit(root, "docs(infra): 更新项目说明", {"README.md": "说明\n"})
    errors = check_range(root, base, head, branch="main", validate_branch=True)

    assert any("主分支" in error and "创建 PR" in error for error in errors), errors


def test_pr_title_and_branch_prefix_must_match_module(repo):
    root, base = repo
    head = commit(root, "feat(m1): 实现座位搜索", {"app/m1/search.py": "value = 1\n"})

    errors = check_range(
        root,
        base,
        head,
        title="feat(m2): 提交错误范围",
        branch="m2/12-search",
        validate_branch=True,
    )

    assert any("PR 标题 scope" in error for error in errors), errors
    assert any("分支 'm2/12-search'" in error for error in errors), errors


def test_change_then_revert_still_cannot_mix_module_groups(repo):
    root, base = repo
    commit(root, "feat(m1): 增加座位搜索", {"app/m1/search.py": "value = 1\n"})
    commit(root, "feat(m2): 增加教室申请", {"app/m2/apply.py": "value = 2\n"})
    head = commit(root, "fix(m1): 撤回座位搜索改动", {"app/m1/search.py": "value = 0\n"})

    errors = check_range(root, base, head)

    assert any("只能包含一个模块组" in error for error in errors), errors


def test_pull_request_event_checks_title_branch_and_scope(repo, tmp_path):
    root, base = repo
    head = commit(root, "feat(m1): 实现座位搜索", {"app/m1/search.py": "value = 1\n"})
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "pull_request": {
                    "base": {"sha": base},
                    "head": {"sha": head, "ref": "m1/12-search"},
                    "title": "feat(m1): 实现座位搜索",
                }
            }
        ),
        encoding="utf-8",
    )

    errors, status = _event_check("pull_request", event_path, root)

    assert errors == []
    assert "m1/12-search" in status


def test_new_feature_push_checks_default_branch_and_module_scope(repo, tmp_path):
    root, base = repo
    git(root, "update-ref", "refs/remotes/origin/main", base)
    head = commit(root, "feat(m1): 实现座位搜索", {"app/m1/search.py": "value = 1\n"})
    payload = {
        "ref": "refs/heads/m1/12-search",
        "before": "0" * 40,
        "after": head,
        "repository": {"default_branch": "main"},
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(payload), encoding="utf-8")

    errors, status = _event_check("push", event_path, root)

    assert errors == []
    assert "m1/12-search" in status


def test_pre_push_rejects_updating_multiple_refs(repo):
    root, base = repo
    first = commit(root, "feat(m1): 实现座位搜索", {"app/m1/search.py": "value = 1\n"})
    updates = [
        f"refs/heads/m1/search {first} refs/heads/m1/search {'1' * 40}\n",
        f"refs/heads/m2/apply {first} refs/heads/m2/apply {'2' * 40}\n",
    ]

    errors = _hook_check(root, "origin", updates)

    assert any("只能更新一个分支或 tag" in error for error in errors), errors


def test_pre_push_checks_module_scope_before_ref_update(repo):
    root, base = repo
    git(root, "update-ref", "refs/remotes/origin/main", base)
    head = commit(root, "feat(m1): 实现座位搜索", {"app/m1/search.py": "value = 1\n"})
    update = f"refs/heads/m1/12-search {head} refs/heads/m1/12-search {'0' * 40}\n"

    errors = _hook_check(root, "origin", [update])

    assert errors == []


def test_pre_push_rejects_direct_main_update(repo):
    root, base = repo
    update = "refs/heads/main " + base + " refs/heads/main " + "0" * 40 + "\n"

    errors = _hook_check(root, "origin", [update])

    assert any("禁止直接推送 main" in error for error in errors), errors


def test_pre_push_allows_deleting_a_ref_without_code():
    deletion = "refs/heads/old 0000000 refs/heads/old 1111111\n"
    assert _hook_check(Path.cwd(), "origin", [deletion]) == []


def test_pre_push_rejects_deleting_main():
    deletion = "refs/heads/main " + "0" * 40 + " refs/heads/main " + "1" * 40 + "\n"
    errors = _hook_check(Path.cwd(), "origin", [deletion])

    assert any("禁止删除 main/master 受保护主分支" in error for error in errors), errors


def test_hook_installer_sets_local_path_when_no_other_hook_is_configured(tmp_path, monkeypatch, capsys):
    git(tmp_path, "init")
    hooks = tmp_path / ".githooks"
    hooks.mkdir()
    (hooks / "pre-push").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    global_config = tmp_path / "global.gitconfig"
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setattr(install_git_hooks, "ROOT", tmp_path)
    monkeypatch.setattr(install_git_hooks, "PROJECT_HOOKS", hooks)

    assert install_git_hooks.main() == 0
    assert git(tmp_path, "config", "--local", "--get", "core.hooksPath") == ".githooks"
    assert ".githooks/pre-push" in capsys.readouterr().out


def test_hook_installer_preserves_an_existing_active_hook(tmp_path, monkeypatch, capsys):
    git(tmp_path, "init")
    hooks = tmp_path / ".githooks"
    hooks.mkdir()
    (hooks / "pre-push").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    global_config = tmp_path / "global.gitconfig"
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setattr(install_git_hooks, "ROOT", tmp_path)
    monkeypatch.setattr(install_git_hooks, "PROJECT_HOOKS", hooks)
    active_hook = git(tmp_path, "rev-parse", "--git-path", "hooks")
    hooks_path = Path(active_hook)
    if not hooks_path.is_absolute():
        hooks_path = tmp_path / hooks_path
    hooks_path.mkdir(parents=True, exist_ok=True)
    (hooks_path / "pre-commit").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")

    assert install_git_hooks.main() == 1
    config = subprocess.run(
        ["git", "config", "--local", "--get", "core.hooksPath"], cwd=tmp_path,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
    )
    assert config.returncode == 1
    assert "未更改 hook 路径" in capsys.readouterr().err
