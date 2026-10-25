#!/usr/bin/env python3
"""Read-only, explicitly scoped Obsidian wikilink check; no vault traversal."""
import argparse
import json
from pathlib import Path
import re
import sys


def within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def safe_path(root, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not relative:
        raise ValueError("路径必须为库内相对路径，且不能含 ..")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("不跟随符号链接")
    if not within(current.resolve(), root):
        raise ValueError("路径越出知识库")
    return current


def without_code(content):
    result = []
    fence = None
    length = 0
    for line in content.splitlines():
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence, length = marker[0], len(marker)
            elif marker[0] == fence and len(marker) >= length and not line.strip().strip(marker[0]):
                fence = None
            continue
        if fence is None:
            result.append(re.sub(r"`+[^`]*`+", "", line))
    return "\n".join(result)


def check_notes(vault, notes):
    raw = Path(vault).expanduser()
    if not raw.is_absolute() or not raw.is_dir():
        raise ValueError("请提供已有知识库的绝对目录")
    if any(p.is_symlink() for p in (raw, *raw.parents)):
        raise ValueError("请使用非符号链接的真实知识库路径")
    root = raw.resolve()
    results = []
    for relative in notes:
        item = {"note": relative, "links_checked": 0, "errors": []}
        results.append(item)
        try:
            source = safe_path(root, relative)
            if source.suffix.lower() != ".md":
                raise ValueError("仅接受显式 Markdown 笔记")
            content = without_code(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as error:
            item["errors"].append(str(error))
            continue
        for match in re.finditer(r"!?\[\[([^\]\n]+)\]\]", content):
            raw_target = match.group(1)
            line_start = content.rfind("\n", 0, match.start()) + 1
            line_prefix = content[line_start:match.start()]
            if line_prefix.lstrip().startswith("|") and re.search(r"(?<!\\)\|", raw_target):
                item["errors"].append("表格内 wiki 别名分隔符必须转义: " + raw_target)
            target = raw_target.replace("\\|", "|").split("|", 1)[0].split("#", 1)[0].strip()
            if not target:
                continue
            item["links_checked"] += 1
            candidates = [target]
            if not Path(target).suffix:
                candidates = [target + ".md", target]
            if "/" not in target:
                local = source.parent.relative_to(root)
                candidates += [str(local / x) for x in list(candidates)]
            try:
                resolved = [safe_path(root, candidate) for candidate in candidates]
                if not any(path.is_file() for path in resolved):
                    item["errors"].append("链接目标未找到: " + target)
            except ValueError as error:
                item["errors"].append("链接越界或不安全: " + target + " (" + str(error) + ")")
    return {"ok": not any(x["errors"] for x in results), "files": len(results), "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True)
    parser.add_argument("--note", action="append", required=True,
                        help="Vault-relative Markdown path; repeat to check multiple explicit notes")
    args = parser.parse_args()
    try:
        result = check_notes(args.vault, args.note)
    except (OSError, ValueError) as error:
        result = {"ok": False, "error": str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
