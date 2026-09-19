# -*- coding: utf-8 -*-
"""版本号四处一致性测试（v2.8.0 治理机制）。

背景：2.6.0 时代实测过 SKILL.md/CHANGELOG=2.7.0 而 plugin.json×2+README 徽章=2.6.0
的元数据漂移（deepseek 审计 111 处版本号证实）。本测试断言发版五处版本号一致：
  1. SKILL.md 版本段 "**当前版本 vX.Y.Z**"
  2. CHANGELOG.md 第一个 "## [X.Y.Z]" 条目
  3. README.md 徽章 version-vX.Y.Z
  4. .claude-plugin/plugin.json 的 version
  5. .codex-plugin/plugin.json 的 version
任何一处漏改即红。配套纪律见 CHANGELOG.md 顶部"同步清单"模板注释。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SKILL_VERSION_RE = re.compile(r"\*\*当前版本 v(\d+\.\d+\.\d+)\*\*")
CHANGELOG_VERSION_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)
README_BADGE_RE = re.compile(r"version-v(\d+\.\d+\.\d+)-blueviolet")


def skill_md_version() -> str:
    text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    matches = SKILL_VERSION_RE.findall(text)
    assert len(matches) == 1, f"SKILL.md 应恰有 1 处 '**当前版本 vX.Y.Z**'，实得 {len(matches)} 处"
    return matches[0]


def changelog_version() -> str:
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    matches = CHANGELOG_VERSION_RE.findall(text)
    assert matches, "CHANGELOG.md 未找到 '## [X.Y.Z]' 条目"
    return matches[0]


def readme_badge_version() -> str:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    matches = README_BADGE_RE.findall(text)
    assert len(matches) == 1, f"README.md 应恰有 1 枚 version 徽章，实得 {len(matches)} 枚"
    return matches[0]


def plugin_version(plugin_json: str) -> str:
    data = json.loads((REPO_ROOT / plugin_json).read_text(encoding="utf-8"))
    version = data.get("version")
    assert isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+", version), (
        f"{plugin_json} 的 version 字段缺失或非 X.Y.Z 格式: {version!r}"
    )
    return version


def test_version_sync_across_five_locations():
    versions = {
        "SKILL.md 当前版本": skill_md_version(),
        "CHANGELOG.md 首条": changelog_version(),
        "README.md 徽章": readme_badge_version(),
        ".claude-plugin/plugin.json": plugin_version(".claude-plugin/plugin.json"),
        ".codex-plugin/plugin.json": plugin_version(".codex-plugin/plugin.json"),
    }
    unique = set(versions.values())
    assert len(unique) == 1, (
        "版本号漂移（发版五处必须同改，见 CHANGELOG.md 顶部同步清单）: "
        + "; ".join(f"{k}={v}" for k, v in versions.items())
    )
