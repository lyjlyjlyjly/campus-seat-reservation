"""用临时仓库中的实际 Markdown 文件验证 Note 检查行为。"""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.check_notes import check_notes


@pytest.fixture
def note_repo(tmp_path):
    directory = tmp_path / ".agents" / "notes"
    directory.mkdir(parents=True)
    (directory / "README.md").write_text("# Note 规范\n", encoding="utf-8")
    return tmp_path


def write_note(root, number="001", state="proposed", topic="architecture", extra="", created="2026-10-20"):
    sections = {
        "proposed": "## Proposal\n采用公共入口。\n\n## Acceptance criteria\nGiven 空库，When 初始化，Then 可启动。\n\n## Risks\n公共入口需要协调。",
        "implemented": "## Decision\n采用公共入口。\n\n## Consequences\n共享入口需要跨组评审。",
        "rejected": "## Why rejected\n维护成本超出本轮范围。\n\n## Reconsider only if\n部署需求改变后重议。",
    }
    record = {"implemented": "Decision record: 测试夹具的采纳记录\n", "rejected": "Rejection record: 测试夹具的否决记录\n"}.get(state, "")
    path = root / ".agents" / "notes" / state / topic / f"{created}-adr-{number}-shared-entry.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Agent Note: ADR-{number} 公共入口\n\n"
        f"Status: {state} — 测试夹具状态说明\n\n"
        f"Date: {created}\nOwner: G2\n{record}{extra}\n"
        "## Problem\n三组需要相同入口。\n\n"
        "## Alternatives considered\n方案一集中入口，便于协作；方案二分散入口，减少公共修改。\n\n"
        f"{sections[state]}\n",
        encoding="utf-8",
    )
    return path


def change(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")


def assert_error(root, expected):
    errors = check_notes(root)
    assert any(expected in error for error in errors), errors
    assert all(error.startswith(".agents/notes") for error in errors)


def test_three_states_and_placeholders_are_valid(note_repo):
    for number, state in enumerate(("proposed", "implemented", "rejected"), 1):
        path = write_note(note_repo, f"{number:03}", state)
        (path.parent.parent / ".gitkeep").touch()
    assert check_notes(note_repo) == []


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ("# Agent Note: ADR-001", "# Agent Note: ADR-002", "标题编号"),
        (" 公共入口\n\nStatus", " 公共入口\n不是空行\nStatus", "第二行"),
        ("Status: proposed — 测试夹具状态说明", "Status: proposed — ", "第三行"),
        ("Status: proposed —", "Status: proposed -", "第三行"),
        ("Status: proposed —", "Status: rejected —", "状态目录"),
        ("Date: 2026-10-20", "Date: 2026-10-21", "Date 必须"),
        ("Owner: G2", "Owner: ", "非空元数据：Owner"),
        ("Owner: G2", "Owner: G2\nOwner: G3", "字段重复：Owner"),
        ("## Problem", "## Background", "第一个二级标题"),
        ("三组需要相同入口。", "  ", "正文为空：Problem"),
        ("三组需要相同入口。", "<!-- 暂待补写 -->\n### 小标题", "正文为空：Problem"),
        ("## Risks\n公共入口需要协调。", "", "正文为空：Risks"),
    ],
)
def test_malformed_header_metadata_and_sections_fail(note_repo, old, new, expected):
    path = write_note(note_repo)
    change(path, old, new)
    assert_error(note_repo, expected)


def test_filename_must_have_real_calendar_date(note_repo):
    write_note(note_repo, created="2026-02-30")
    assert_error(note_repo, "有效日历日期")


@pytest.mark.parametrize(
    ("state", "body", "heading"),
    [("proposed", "采用公共入口。", "Proposal"), ("implemented", "采用公共入口。", "Decision"), ("rejected", "维护成本超出本轮范围。", "Why rejected")],
)
def test_each_state_requires_nonempty_body(note_repo, state, body, heading):
    path = write_note(note_repo, state=state)
    change(path, body, "\n```markdown\n## Example\n只有模板示例。\n```\n")
    assert_error(note_repo, f"正文为空：{heading}")


@pytest.mark.parametrize("name", ["2026-10-20-adr-01-entry.md", "2026-10-20-adr-001-Upper.md", "2026-10-20-adr-001-bad--slug.md"])
def test_invalid_filename_fails(note_repo, name):
    path = write_note(note_repo)
    path.rename(path.with_name(name))
    assert_error(note_repo, "文件名须为")


@pytest.mark.parametrize("relative", ["archived/architecture/note.md", "proposed/wrong/note.md", "proposed/architecture/nested/note.md", "proposed/note.md", "note.md"])
def test_invalid_note_location_fails(note_repo, relative):
    path = note_repo / ".agents" / "notes" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# misplaced\n", encoding="utf-8")
    assert check_notes(note_repo)


@pytest.mark.parametrize("number", ["001", "0001"])
def test_ids_are_unique_across_states_and_padding(note_repo, number):
    write_note(note_repo)
    write_note(note_repo, number, "implemented", "process")
    assert_error(note_repo, "ADR 编号重复")


@pytest.mark.parametrize("heading", ["Proposal", "Plan", "Acceptance criteria"])
def test_implemented_rejects_pending_sections(note_repo, heading):
    path = write_note(note_repo, state="implemented")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"\n## {heading}\n未来安排。\n")
    assert_error(note_repo, "不得保留待实施章节")


@pytest.mark.parametrize(("state", "record"), [("implemented", "Decision record"), ("rejected", "Rejection record")])
@pytest.mark.parametrize("replacement", ["", "{record}:  "])
def test_adoption_and_rejection_require_record(note_repo, state, record, replacement):
    path = write_note(note_repo, state=state)
    content = path.read_text(encoding="utf-8")
    line = next(line for line in content.splitlines() if line.startswith(record + ":"))
    change(path, line, replacement.format(record=record))
    assert_error(note_repo, f"必须包含非空 {record}")


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("missing.md", "链接目标不存在"),
        ("../../../../../outside.md", "链接越出仓库"),
        ("%2Ftmp%2Fnote.md", "仓库相对路径"),
        ("F:/local/note.md", "本机绝对路径"),
        ("/tmp/note.md", "本机绝对路径"),
        ("file:///tmp/note.md", "本机绝对路径"),
    ],
)
def test_missing_or_nonportable_links_fail(note_repo, target, expected):
    write_note(note_repo, extra=f"References: [说明]({target})\n")
    assert_error(note_repo, expected)


def test_links_resolve_from_note_and_code_examples_are_ignored(note_repo):
    doc = note_repo / "说明 (Review).md"
    doc.write_text("# 说明\n", encoding="utf-8")
    path = write_note(
        note_repo,
        extra="References: [资料](<../../../../说明 (Review).md#说明>)、[外链](https://example.invalid/)、[锚点](#problem)\n",
    )
    with path.open("a", encoding="utf-8") as stream:
        stream.write(
            "\n[编码路径](../../../../说明%20%28Review%29.md)\n"
            "[引用式资料][doc]\n\n[doc]: <../../../../说明 (Review).md>\n"
            "\n```markdown\n## Problem\n[示例](missing.md)\n```\n"
            "\n~~~markdown\n[示例](another-missing.md)\n~~~\n"
            "\n`[行内示例](missing.md)`\n"
        )
    readme = note_repo / ".agents" / "notes" / "README.md"
    readme.write_text(
        "# Note 规范\n\n`Supersedes: ADR-001 ([示例](example.md))`\n"
        "\n````markdown\n```text\n[示例](missing.md)\n```\n````\n",
        encoding="utf-8",
    )
    assert check_notes(note_repo) == []


def test_readme_and_reference_definition_links_are_checked(note_repo):
    readme = note_repo / ".agents" / "notes" / "README.md"
    readme.write_text("# Note 规范\n\n[规范][rules]\n\n[rules]: missing.md\n", encoding="utf-8")
    assert_error(note_repo, "README.md:5: 链接目标不存在")


def set_relation(path, field, number, target):
    change(path, "Owner: G2", f"Owner: G2\n{field}: ADR-{number} ([关联决策]({target}))")


def test_valid_replacement_chain(note_repo):
    old, middle, new = [write_note(note_repo, f"{number:03}", "implemented") for number in (1, 2, 3)]
    set_relation(old, "Superseded by", "002", middle.name)
    set_relation(middle, "Supersedes", "001", old.name)
    set_relation(middle, "Superseded by", "003", new.name)
    set_relation(new, "Supersedes", "002", middle.name)
    assert check_notes(note_repo) == []


def test_replacement_requires_backlink(note_repo):
    old = write_note(note_repo, "001", "implemented")
    new = write_note(note_repo, "002", "implemented")
    set_relation(new, "Supersedes", "001", old.name)
    assert_error(note_repo, "缺少正确互指")


def test_replacement_id_must_match_link(note_repo):
    old, new, wrong = [write_note(note_repo, f"{number:03}", "implemented") for number in (1, 2, 3)]
    set_relation(old, "Superseded by", "002", wrong.name)
    set_relation(new, "Supersedes", "001", old.name)
    assert_error(note_repo, "编号与链接目标不一致")


def test_replacement_cannot_point_to_itself(note_repo):
    path = write_note(note_repo, state="implemented")
    set_relation(path, "Supersedes", "001", path.name)
    assert_error(note_repo, "禁止自指")


def test_replacement_field_in_body_is_also_checked(note_repo):
    path = write_note(note_repo, state="implemented")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"\nSupersedes: ADR-001 ([原决策]({path.name}))\n")
    assert_error(note_repo, "禁止自指")


@pytest.mark.parametrize("state", ["proposed", "rejected"])
def test_only_adopted_notes_can_replace_each_other(note_repo, state):
    old = write_note(note_repo, "001", state)
    new = write_note(note_repo, "002", "implemented")
    set_relation(old, "Superseded by", "002", f"../../implemented/architecture/{new.name}")
    set_relation(new, "Supersedes", "001", f"../../{state}/architecture/{old.name}")
    assert_error(note_repo, "两端必须都是 implemented")


def test_replacement_is_one_to_one(note_repo):
    old, new, other = [write_note(note_repo, f"{number:03}", "implemented") for number in (1, 2, 3)]
    set_relation(old, "Superseded by", "002", new.name)
    set_relation(old, "Superseded by", "003", other.name)
    set_relation(new, "Supersedes", "001", old.name)
    set_relation(other, "Supersedes", "001", old.name)
    assert_error(note_repo, "字段重复：Superseded by")


def test_replacement_cycle_fails_even_with_all_backlinks(note_repo):
    first, second, third = [write_note(note_repo, f"{number:03}", "implemented") for number in (1, 2, 3)]
    for old, new, old_id, new_id in [(first, second, "001", "002"), (second, third, "002", "003"), (third, first, "003", "001")]:
        set_relation(old, "Superseded by", new_id, new.name)
        set_relation(new, "Supersedes", old_id, old.name)
    assert_error(note_repo, "存在循环")


@pytest.mark.parametrize("value", ["ADR-001", "ADR-001 ([说明](https://example.invalid/note.md))"])
def test_replacement_requires_a_local_link(note_repo, value):
    write_note(note_repo, "002", "implemented", extra=f"Supersedes: {value}\n")
    assert check_notes(note_repo)


def test_cli_uses_requested_root_and_returns_error_exit_code(note_repo):
    path = write_note(note_repo)
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_notes.py"
    command = [sys.executable, str(script), "--root", str(note_repo)]
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    success = subprocess.run(command, cwd=note_repo, env=environment, capture_output=True, text=True, encoding="utf-8")
    assert success.returncode == 0, success.stderr
    change(path, "Owner: G2", "Owner: ")
    failure = subprocess.run(command, cwd=note_repo, env=environment, capture_output=True, text=True, encoding="utf-8")
    assert failure.returncode == 1
    assert "Owner" in failure.stderr and path.name in failure.stderr


def test_missing_notes_directory_fails(tmp_path):
    assert_error(tmp_path, "缺少仓库内的 .agents/notes 目录")
