#!/usr/bin/env python3
"""Create a NEW local Markdown vault; dry-run unless --apply. Python 3.9+."""
import argparse
import os
from pathlib import Path
import sys

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "vault"


def plan_vault(raw_path):
    if any(ord(char) < 32 for char in raw_path):
        raise ValueError("路径不能包含控制字符或换行。")
    target = Path(raw_path).expanduser()
    if not target.is_absolute():
        raise ValueError("请使用确认过的绝对路径。")
    for part in (target, *target.parents):
        if part.is_symlink():
            raise ValueError("目标或上级目录是符号链接，请确认实际路径后再运行。")
    target = target.resolve()
    if os.path.lexists(target):
        raise ValueError("目标已存在；不覆盖旧库或空目录，请按建库指南增量合并。")
    if not target.parent.is_dir():
        raise ValueError("父目录必须已存在；不会自动创建未确认的上级目录。")
    if not ASSETS.is_dir():
        raise ValueError("技能包缺少 assets/vault，请重新获取完整技能。")
    result = []
    for source in sorted(ASSETS.rglob("*")):
        if source.is_symlink():
            raise ValueError("模板中不允许符号链接。")
        if source.is_file():
            if source.suffix != ".md":
                raise ValueError("模板中只允许 Markdown 文件。")
            relative = source.relative_to(ASSETS)
            content = source.read_text(encoding="utf-8").replace("{{VAULT_ROOT}}", str(target))
            result.append((relative, content))
    if not result:
        raise ValueError("模板为空，未创建知识库。")
    return target, result


def create_vault(target, plan):
    # Exclusive creation: another initializer cannot reuse or overwrite this root.
    target.mkdir(mode=0o700, exist_ok=False)
    # On failure retain partial output for inspection; never remove user data.
    for relative, content in plan:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, help="Absolute path of a new, nonexistent vault")
    parser.add_argument("--apply", action="store_true", help="Create files; default is read-only preview")
    args = parser.parse_args()
    try:
        target, plan = plan_vault(args.vault)
        print(f"{'创建' if args.apply else '只读预览'}：{target}")
        for relative, _ in plan:
            print(f"  {relative.as_posix()}")
        if args.apply:
            create_vault(target, plan)
            print("文件已创建；请在 Obsidian 中打开文件夹为仓库，再分别配置与验证客户端。")
        else:
            print("未修改任何文件。确认范围后可加 --apply；现有知识库不能用此脚本更新。")
        return 0
    except (OSError, ValueError) as error:
        print(f"停止：{error}\n若已产生部分文件，请先检查，不要清空旧资料后强行重试。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
