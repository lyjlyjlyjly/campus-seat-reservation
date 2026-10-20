"""检查 .agents/notes 的文件格式、仓库链接和一对一替代关系。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
import re
import sys
from urllib.parse import unquote


STATES = {"proposed", "implemented", "rejected"}
TOPICS = {"feature", "bug-fix", "simplification", "architecture", "process", "testing"}
REQUIRED = {
    "proposed": ("Problem", "Alternatives considered", "Proposal", "Acceptance criteria", "Risks"),
    "implemented": ("Problem", "Alternatives considered", "Decision", "Consequences"),
    "rejected": ("Problem", "Alternatives considered", "Why rejected", "Reconsider only if"),
}
FILENAME = re.compile(r"(\d{4}-\d{2}-\d{2})-adr-(\d{3,})-[a-z0-9]+(?:-[a-z0-9]+)*\.md")
TITLE = re.compile(r"# Agent Note: ADR-(\d{3,})\s+(.+)")
STATUS = re.compile(r"Status: (proposed|implemented|rejected) — (.+)")
METADATA = re.compile(
    r"^(Status|Date|Owner|Decision record|Rejection record|Supersedes|Superseded by):[ \t]*(.*)$",
    re.MULTILINE,
)
HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
# 支持普通链接、图片、带空格的 <路径>、标题和路径中的一层括号。
LINK = re.compile(
    r"!?\[[^\]\n]*\]\([ \t]*(?:<([^>\n]+)>|((?:\\.|[^\\()\s]|\([^()\n]*\))+))"
    r"(?:[ \t]+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^()\n]*\)))?[ \t]*\)"
)
REFERENCE = re.compile(r"^ {0,3}\[[^\]\n]+\]:[ \t]*(?:<([^>\n]+)>|(\S+))", re.MULTILINE)
RELATION = re.compile(r"ADR-(\d{3,}) \(\[[^\]\n]+\]\((<[^>\n]+>|[^)\s]+)\)\)")


@dataclass
class Relation:
    number: str
    target: Path | None
    line: int


@dataclass
class Note:
    path: Path
    number: str
    state: str
    relations: dict[str, Relation] = field(default_factory=dict)


def _error(errors: list[str], root: Path, path: Path, reason: str, line: int = 1) -> None:
    errors.append(f"{path.relative_to(root).as_posix()}:{line}: {reason}")


def _prose(text: str) -> str:
    """隐藏示例代码及注释，同时保留行号；这不是通用 Markdown 渲染器。"""
    lines = []
    fence = None
    for line in text.splitlines():
        if fence is not None:
            if re.fullmatch(rf" {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}[ \t]*", line):
                fence = None
            lines.append("")
        else:
            opening = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
            if opening:
                fence = opening.group(1)
                lines.append("")
            else:
                lines.append(line)
    result = "\n".join(lines)
    result = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group().count("\n"), result, flags=re.DOTALL)
    return re.sub(r"(`+)(?!`)(.*?)\1(?!`)", lambda m: "\n" * m.group().count("\n"), result, flags=re.DOTALL)


def _local_link(root: Path, source: Path, target: str, errors: list[str], line: int) -> Path | None:
    target = target.removeprefix("<").removesuffix(">")
    target = re.sub(r"\\([\\`*_{}\[\]()#+\-.! <>])", r"\1", target)
    if target.startswith("#"):
        return None
    if re.match(r"^[A-Za-z]:", target) or target.startswith(("/", "\\")) or target.lower().startswith("file:"):
        _error(errors, root, source, f"链接必须使用仓库相对路径，不能是本机绝对路径：{target}", line)
        return None
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
        return None
    local = unquote(target.split("#", 1)[0].split("?", 1)[0]).replace("\\", "/")
    if not local:
        return None
    if local.startswith("/") or re.match(r"^[A-Za-z]:", local):
        _error(errors, root, source, f"链接必须使用仓库相对路径：{target}", line)
        return None
    destination = (source.parent / local).resolve()
    if not destination.is_relative_to(root):
        _error(errors, root, source, f"链接越出仓库：{target}", line)
        return None
    if not destination.exists():
        _error(errors, root, source, f"链接目标不存在：{target}", line)
    return destination


def _check_links(root: Path, path: Path, prose: str, errors: list[str]) -> None:
    for pattern in (LINK, REFERENCE):
        for match in pattern.finditer(prose):
            line = prose.count("\n", 0, match.start()) + 1
            _local_link(root, path, match.group(1) or match.group(2), errors, line)


def _read(root: Path, path: Path, errors: list[str]) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        _error(errors, root, path, f"无法读取 UTF-8 文本：{exc}")
        return None


def _check_note(root: Path, path: Path, state: str, errors: list[str]) -> Note | None:
    filename = FILENAME.fullmatch(path.name)
    if filename is None:
        _error(errors, root, path, "文件名须为 yyyy-mm-dd-adr-NNN-lowercase-slug.md，编号至少三位")
        return None
    created, number = filename.groups()
    try:
        date.fromisoformat(created)
    except ValueError:
        _error(errors, root, path, f"文件名日期不是有效日历日期：{created}")
    text = _read(root, path, errors)
    if text is None:
        return None
    note = Note(path, number, state)
    lines = text.splitlines()
    title = TITLE.fullmatch(lines[0]) if lines else None
    if title is None or not title.group(2).strip():
        _error(errors, root, path, "首行须为 # Agent Note: ADR-NNN 非空标题")
    elif title.group(1) != number:
        _error(errors, root, path, "标题编号与文件名编号不一致")
    if len(lines) < 2 or lines[1].strip():
        _error(errors, root, path, "第二行必须为空行", 2)
    status = STATUS.fullmatch(lines[2]) if len(lines) > 2 else None
    if status is None or not status.group(2).strip():
        _error(errors, root, path, "第三行须为 Status: 状态 — 非空说明，使用长破折号 —", 3)
    elif status.group(1) != state:
        _error(errors, root, path, "Status 与所在状态目录不一致", 3)

    prose = _prose(text)
    _check_links(root, path, prose, errors)
    headings = list(HEADING.finditer(prose))
    if not headings or headings[0].group(1) != "Problem":
        _error(errors, root, path, "正文第一个二级标题必须是 Problem")
    sections = {}
    for index, heading in enumerate(headings):
        name = heading.group(1)
        line = prose.count("\n", 0, heading.start()) + 1
        end = headings[index + 1].start() if index + 1 < len(headings) else len(prose)
        body = re.sub(r"^#{1,6}[ \t]+.*$", "", prose[heading.end():end], flags=re.MULTILINE).strip()
        if name in sections:
            _error(errors, root, path, f"二级章节重复：{name}", line)
        sections[name] = body
    for name in REQUIRED[state]:
        if not sections.get(name):
            _error(errors, root, path, f"缺少必需章节或正文为空：{name}")
    if state == "implemented":
        for name in ("Proposal", "Plan", "Acceptance criteria"):
            if name in sections:
                _error(errors, root, path, f"implemented 不得保留待实施章节：{name}")

    metadata = {}
    preamble_end = headings[0].start() if headings else len(prose)
    for match in METADATA.finditer(prose):
        key, value = match.groups()
        # 替代字段即使写在正文，也不能绕过互指及状态检查。
        if match.start() >= preamble_end and key not in ("Supersedes", "Superseded by"):
            continue
        line = prose.count("\n", 0, match.start()) + 1
        if key in metadata:
            _error(errors, root, path, f"元数据字段重复：{key}", line)
        metadata[key] = (value.strip(), line)
    for key in ("Date", "Owner"):
        if not metadata.get(key, ("", 0))[0]:
            _error(errors, root, path, f"缺少非空元数据：{key}")
    if "Date" in metadata and metadata["Date"][0] != created:
        _error(errors, root, path, "Date 必须与文件名日期一致", metadata["Date"][1])
    record = {"implemented": "Decision record", "rejected": "Rejection record"}.get(state)
    if record and not metadata.get(record, ("", 0))[0]:
        _error(errors, root, path, f"{state} 必须包含非空 {record}，确认真实性由人评审")
    for key in ("Supersedes", "Superseded by"):
        if key not in metadata:
            continue
        value, line = metadata[key]
        relation = RELATION.fullmatch(value)
        if relation is None:
            _error(errors, root, path, f"{key} 格式须为 ADR-NNN ([说明](相对路径.md))", line)
            continue
        target = _local_link(root, path, relation.group(2), errors, line)
        if target is None:
            _error(errors, root, path, f"{key} 必须链接仓库内的 Note 文件", line)
        note.relations[key] = Relation(relation.group(1), target, line)
    return note


def _check_relations(root: Path, notes: dict[int, Note], errors: list[str]) -> None:
    for identity, note in notes.items():
        for key, relation in note.relations.items():
            target = notes.get(int(relation.number))
            if note.state != "implemented" or (target and target.state != "implemented"):
                _error(errors, root, note.path, "替代关系两端必须都是 implemented Note", relation.line)
            if int(relation.number) == identity:
                _error(errors, root, note.path, "替代关系禁止自指", relation.line)
                continue
            if target is None:
                _error(errors, root, note.path, f"关联编号 ADR-{relation.number} 不存在", relation.line)
                continue
            if relation.number != target.number or relation.target != target.path.resolve():
                _error(errors, root, note.path, f"{key} 的编号与链接目标不一致", relation.line)
            inverse = "Superseded by" if key == "Supersedes" else "Supersedes"
            back = target.relations.get(inverse)
            if back is None or back.number != note.number or back.target != note.path.resolve():
                _error(errors, root, note.path, f"替代关系缺少正确互指：ADR-{target.number} 的 {inverse}", relation.line)

    visited = set()
    for identity in notes:
        route = []
        positions = {}
        current = identity
        while current in notes and current not in visited:
            if current in positions:
                cycle = route[positions[current]:] + [current]
                chain = " → ".join(f"ADR-{notes[item].number}" for item in cycle)
                _error(errors, root, notes[current].path, f"替代关系存在循环：{chain}")
                break
            positions[current] = len(route)
            route.append(current)
            next_note = notes[current].relations.get("Superseded by")
            if next_note is None:
                break
            current = int(next_note.number)
        visited.update(route)


def check_notes(root: Path) -> list[str]:
    """返回检查错误；仅检查 notes，不推断人的确认或决策质量。"""
    root = Path(root).resolve()
    notes_root = root / ".agents" / "notes"
    errors: list[str] = []
    if not notes_root.is_dir() or not notes_root.resolve().is_relative_to(root):
        _error(errors, root, notes_root, "缺少仓库内的 .agents/notes 目录")
        return errors
    notes: dict[int, Note] = {}
    for path in sorted(notes_root.rglob("*")):
        parts = path.relative_to(notes_root).parts
        parent = parts if path.is_dir() else parts[:-1]
        valid_parent = (
            not parent
            or (len(parent) == 1 and parent[0] in STATES)
            or (len(parent) == 2 and parent[0] in STATES and parent[1] in TOPICS)
        )
        if not path.resolve().is_relative_to(root):
            _error(errors, root, path, "Note 路径越出仓库")
            continue
        if not valid_parent:
            _error(errors, root, path, "路径只能使用三个状态和六类主题，不能再嵌套目录")
            continue
        if path.is_dir() or path.name == ".gitkeep":
            continue
        if parts == ("README.md",):
            text = _read(root, path, errors)
            if text is not None:
                _check_links(root, path, _prose(text), errors)
            continue
        if len(parent) != 2:
            _error(errors, root, path, "Note 必须位于 {status}/{topic}/ 下；仅根目录可放 README.md")
            continue
        note = _check_note(root, path, parent[0], errors)
        if note is not None:
            identity = int(note.number)
            if identity in notes:
                previous = notes[identity].path.relative_to(root).as_posix()
                _error(errors, root, path, f"ADR 编号重复：ADR-{note.number}，已有 {previous}")
            else:
                notes[identity] = note
    _check_relations(root, notes, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="仓库根目录")
    args = parser.parse_args(argv)
    errors = check_notes(args.root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Agent Note 检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
