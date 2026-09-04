"""按文件哈希识别知识库增量，并维护可审计版本清单。"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EXTENSIONS = {".json", ".md", ".txt", ".pdf", ".docx", ".xlsx", ".csv"}
IGNORED_PARTS = {".git", "__pycache__", ".pytest_cache"}


def sha256_file(path: Path) -> str:
    """流式计算文件哈希，避免把大 PDF 一次读入内存。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_files(sources: list[Path], extensions: set[str]) -> list[Path]:
    """展开文件和目录，并过滤缓存目录与无关扩展名。"""
    files = []
    for source in sources:
        resolved = source.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"来源不存在: {source}")
        candidates = [resolved] if resolved.is_file() else resolved.rglob("*")
        for path in candidates:
            if (path.is_file() and path.suffix.lower() in extensions
                    and not any(part in IGNORED_PARTS for part in path.parts)):
                files.append(path)
    return sorted(set(files), key=lambda value: str(value).lower())


def record_key(path: Path) -> str:
    """Skill 内文件使用相对路径，外部资料使用绝对路径。"""
    try:
        return path.resolve().relative_to(SKILL_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def scan_files(paths: list[Path]) -> dict[str, dict]:
    """生成后续处理器可复用的文件指纹表。"""
    records = {}
    for path in paths:
        stat = path.stat()
        records[record_key(path)] = {
            "sha256": sha256_file(path),
            "size": stat.st_size,
            "modified_ns": stat.st_mtime_ns,
        }
    return records


def bump_version(version: str, level: str) -> str:
    """按语义版本规则递增 major、minor 或 patch。"""
    try:
        major, minor, patch = [int(value) for value in version.split(".")]
    except (ValueError, AttributeError):
        major, minor, patch = 0, 0, 0
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def compare(previous: dict, current: dict) -> dict:
    """比较两次扫描，未变化文件不会进入待处理清单。"""
    old_files = previous.get("files", {})
    added = sorted(set(current) - set(old_files))
    removed = sorted(set(old_files) - set(current))
    changed = sorted(
        key for key in set(current) & set(old_files)
        if current[key].get("sha256") != old_files[key].get("sha256")
    )
    unchanged = sorted(set(current) & set(old_files) - set(changed))
    return {
        "added": added,
        "changed": changed,
        "removed": removed,
        "unchanged": unchanged,
        "to_process": added + changed,
    }


def build_manifest(previous: dict, current: dict, changes: dict, sources: list[Path],
                   version: str) -> dict:
    """构造包含版本、指纹与增量历史的知识清单。"""
    timestamp = datetime.now(timezone.utc).isoformat()
    history = list(previous.get("history", []))
    history.append({
        "timestamp": timestamp,
        "version": version,
        "added": changes["added"],
        "changed": changes["changed"],
        "removed": changes["removed"],
        "processed_count": len(changes["to_process"]),
    })
    return {
        "schema_version": "knowledge-manifest-1.0",
        "knowledge_version": version,
        "updated_at": timestamp,
        "sources": [str(path.resolve()) for path in sources],
        "files": current,
        "last_change": changes,
        "history": history,
    }


def main() -> int:
    """扫描来源并在明确 --apply 时更新清单。"""
    parser = argparse.ArgumentParser(description="知识库增量扫描与版本管理")
    parser.add_argument("--source", type=Path, action="append",
                        help="可重复指定文件或目录；默认扫描三赛 competitions 目录")
    parser.add_argument("--manifest", type=Path, default=SKILL_ROOT / "state" / "knowledge_manifest.json")
    parser.add_argument("--extension", action="append", help="额外扩展名，例如 .tex")
    parser.add_argument("--bump", choices=("major", "minor", "patch"), default="patch")
    parser.add_argument("--version", help="显式指定新版本，优先于 --bump")
    parser.add_argument("--changed-list", type=Path, help="输出仅含新增/变化文件的清单")
    parser.add_argument("--apply", action="store_true", help="写入 manifest；默认只预览")
    args = parser.parse_args()

    sources = args.source or [
        SKILL_ROOT / "competitions" / "cumcm",
        SKILL_ROOT / "competitions" / "huaweibei",
        SKILL_ROOT / "competitions" / "huashubei",
    ]
    extensions = set(DEFAULT_EXTENSIONS)
    extensions.update(value if value.startswith(".") else f".{value}" for value in (args.extension or []))
    try:
        paths = source_files(sources, extensions)
        current = scan_files(paths)
    except (OSError, FileNotFoundError) as exc:
        parser.error(str(exc))

    previous = {}
    if args.manifest.exists():
        try:
            previous = json.loads(args.manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            parser.error(f"manifest JSON 损坏: {exc}")
    changes = compare(previous, current)
    previous_version = previous.get("knowledge_version", "0.0.0")
    has_changes = bool(changes["added"] or changes["changed"] or changes["removed"])
    version = args.version or (bump_version(previous_version, args.bump) if has_changes else previous_version)
    manifest = build_manifest(previous, current, changes, sources, version)

    if args.changed_list:
        args.changed_list.parent.mkdir(parents=True, exist_ok=True)
        args.changed_list.write_text("\n".join(changes["to_process"]) + ("\n" if changes["to_process"] else ""), encoding="utf-8")
    if args.apply:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "schema_version": manifest["schema_version"],
        "mode": "apply" if args.apply else "preview",
        "previous_version": previous_version,
        "next_version": version,
        "file_count": len(current),
        "added": len(changes["added"]),
        "changed": len(changes["changed"]),
        "removed": len(changes["removed"]),
        "unchanged": len(changes["unchanged"]),
        "to_process": changes["to_process"],
        "manifest": str(args.manifest),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
