# -*- coding: utf-8 -*-
"""math_font_policy.py — decision_log 数学字体正斜政策解析 (v3.1.0 新增)

政策来源: `references/cn_presentation_spec.md` §5.6——全文公式字体二选一并全文
一致: (a) 全局正体 (变量一律不用斜体); (b) 按 GB 3102 惯例 (物理量斜体, 单位/
函数/说明文字正体)。选择必须显式登记 decision_log, 不得混用。

本模块只做**读取与判定**, 不改文档; 判定不了就返回 unspecified + 警告, 由调用方
(docx_presentation_postprocess Step A) 保持输入一字不动。

检索路径 (显式清单 = 优先级, 不做任意深度 DFS):
    1. cli: 调用方传入的 override ("upright" / "conventional"; "auto"/None = 读日志)
    2. decision_log.math_font          ┐ 顶层标量手写键, 三个别名"查任一"
    3. decision_log.math_font_policy   │ (先例: docx_final_channel.md 的
    4. decision_log.upright_math       ┘  docx_channel / final_chain 双键等价约定;
                                         upright_math 与 figkit.apply_style() 参数同名)
    5. decision_log.stages.0.notes     模板既有自由文本备注 (最后兜底, 命中会标注
                                       "自由文本"——文本里可能出现否定/历史表述)
**不做任意深度搜索**: events.log 与各 stage 历史字段里存着被放弃的旧方案,
深度首个命中会把历史值当现行政策。

判定纪律 (冲突/非法一律警告, 不静默决定):
  - 多路径给出**不同**政策 → 返回 unspecified + 警告 (请人工统一, 不替用户选);
  - 未知取值/非法类型 → 该路径警告并跳过; 全无有效值 → unspecified + 警告;
  - 自由文本同时命中正体与斜体两侧词、或命中否定表述 ("不用正体") → 不判定 + 警告。

用法:
    from math_font_policy import resolve_math_font_policy, read_decision_log
    policy, source, warnings = resolve_math_font_policy(read_decision_log(ws))
"""

from __future__ import annotations

import json
import re
from pathlib import Path

POLICY_UPRIGHT = "upright"          # 全局正体 (a)
POLICY_CONVENTIONAL = "conventional"  # GB 3102 惯例 (b)
POLICY_UNSPECIFIED = "unspecified"  # 未登记/无法判定

POLICY_LABELS = {
    POLICY_UPRIGHT: "全局正体 (变量也不用斜体)",
    POLICY_CONVENTIONAL: "常规正斜 (按 GB 3102 惯例: 物理量斜体, 单位/函数/说明文字正体)",
    POLICY_UNSPECIFIED: "未登记",
}

# 顶层标量手写键 (别名, 查任一; 顺序即优先级)
SCALAR_KEYS = ("math_font", "math_font_policy", "upright_math")
# 自由文本兜底路径 (模板既有字段)
TEXT_PATHS = (("stages", "0", "notes"),)
# cli override 的合法取值 ("auto" = 读 decision_log)
OVERRIDE_VALUES = ("auto", POLICY_UPRIGHT, POLICY_CONVENTIONAL)

# 值归一词表 (去掉分隔符与大小写后全等匹配)
_UPRIGHT_TOKENS = frozenset({
    "upright", "up", "regular", "roman", "正体", "全局正体", "直立体", "直立"})
_CONVENTIONAL_TOKENS = frozenset({
    "italic", "conventional", "gb3102", "gbt3102", "gb3102惯例", "惯例", "常规",
    "常规正斜", "斜体", "默认", "default"})
# 自由文本词表 (子串匹配; 长词在前避免 "常规正斜" 被 "常规" 抢先后归类混乱——
# 两者本就是同一类, 顺序只影响说明文案)
_UPRIGHT_MARKERS = ("全局正体", "正体", "直立体", "upright", "regular", "roman")
_CONVENTIONAL_MARKERS = ("常规正斜", "斜体", "常规", "惯例", "italic", "gb3102",
                         "gb/t 3102", "gb/t3102")
# 否定表述: "不用正体" / "没有采用常规正斜" 这类句子按不判定处理 (不反推用户意图)
_NEGATION_RE = re.compile(
    r"(?:不用|不采用|未采用|没有采用|不要|不使用|未使用|没有使用|不选|不考虑|"
    r"不取|禁止|拒绝|取消|非|放弃)\s*.{0,3}?"
    r"(?:" + "|".join(re.escape(m) for m in _UPRIGHT_MARKERS + _CONVENTIONAL_MARKERS) + r")",
    re.IGNORECASE)


def decision_log_path(workspace: Path) -> Path:
    """工作区骨架约定的 decision_log 路径: <workspace>/../state/decision_log.json。

    与 export_docx / export_final_docx 的既有口径完全一致 (workspace 是
    `paper_workspace/`, 其父目录下是 `state/`)。
    """
    return Path(workspace).parent / "state" / "decision_log.json"


def locate_decision_log(docx_path: Path, max_up: int = 3) -> tuple:
    """从 docx 路径上溯找 state/decision_log.json, 返回 (路径 | None, 说明)。

    供 docx_presentation_postprocess.py 单跑 CLI 时使用 (导出链会显式传
    workspace, 不走本函数): 终稿 docx 通常在 <项目根>/submission/ 下, 上溯 1 级
    即命中 <项目根>/state/decision_log.json; 找不到时返回 None + 原因 (调用方按
    "未登记政策" 处理并保持输入)。
    """
    base = Path(docx_path).resolve().parent
    levels = [base] + list(base.parents)[:max_up]
    for depth, d in enumerate(levels):
        cand = d / "state" / "decision_log.json"
        if cand.is_file():
            return cand, f"自动定位 (上溯 {depth} 级): {cand}"
    return None, f"上溯 {max_up} 级未找到 state/decision_log.json: {base}"


def read_decision_log(workspace: Path) -> dict:
    """读 <workspace>/../state/decision_log.json; 读不到/损坏/非对象 → 空 dict。

    审计脚本口径: 读不到不是错误 (与 export_docx.resolve_competition 同约定),
    政策解析层会把它落成 unspecified + 警告。
    """
    return read_decision_log_file(decision_log_path(workspace))


def read_decision_log_file(path: Path) -> dict:
    """读指定 decision_log.json; 任何读取/解析失败 → 空 dict (静默回退口径)。"""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _dig(obj, keys: tuple):
    """按显式路径取值 (逐级 dict 精确命中); 中途缺键/非 dict → None。不做 DFS。"""
    for k in keys:
        if not isinstance(obj, dict) or k not in obj:
            return None
        obj = obj[k]
    return obj


def normalize_policy_token(value) -> str | None:
    """单个标量值 → 政策常量; 无法归一返回 None (不猜)。"""
    if isinstance(value, bool):  # bool 是 int 子类, 必须先判
        return POLICY_UPRIGHT if value else POLICY_CONVENTIONAL
    if not isinstance(value, str):
        return None
    token = re.sub(r"[\s_\-/]+", "", value.strip().lower())
    if token in _UPRIGHT_TOKENS:
        return POLICY_UPRIGHT
    if token in _CONVENTIONAL_TOKENS:
        return POLICY_CONVENTIONAL
    return None


def scan_free_text(text: str) -> str | None:
    """自由文本 → 政策常量; 两侧词都命中/含否定表述/无命中 → None (不判定)。"""
    low = text.lower()
    reasons = []
    upright = any(m.lower() in low for m in _UPRIGHT_MARKERS)
    conventional = any(m.lower() in low for m in _CONVENTIONAL_MARKERS)
    if _NEGATION_RE.search(text):
        return None
    if upright and conventional:
        return None
    if upright:
        return POLICY_UPRIGHT
    if conventional:
        return POLICY_CONVENTIONAL
    return None


def searched_paths_note() -> str:
    """人读的检索路径说明 (警告文案用, 直接告诉用户该在哪登记)。"""
    keys = " / ".join(f"decision_log.{k}" for k in SCALAR_KEYS)
    texts = " / ".join("decision_log." + ".".join(p) for p in TEXT_PATHS)
    return f"已查 {keys} 与 {texts} (自由文本)"


def resolve_math_font_policy(log, override: str | None = None) -> tuple:
    """解析数学字体政策, 返回 (policy, source, warnings)。

    policy ∈ POLICY_UPRIGHT / POLICY_CONVENTIONAL / POLICY_UNSPECIFIED;
    source 是命中位置 (或空串 / "conflict: …" 说明); warnings 是给用户看的
    诊断行 (调用方原样打印)。override 非 None/"auto" 时直接采用 (须是
    OVERRIDE_VALUES 之一, 否则 ValueError——这是编程/CLI 参数错误, 不静默吞)。

    层级 (高层命中即定, 不再看低层; **同级**冲突/非法一律警告不判定):
      1. cli override;
      2. 顶层标量手写键 SCALAR_KEYS (同级多键取值不同 → unspecified + 警告);
      3. 自由文本备注 TEXT_PATHS (仅第 2 级无有效值时采用; 与第 2 级取值不一致
         时只报告不改判——标量键是显式登记, 自由文本是兜底)。
    """
    warnings: list = []
    if override not in (None, "auto"):
        if override not in OVERRIDE_VALUES:
            raise ValueError(
                f"override 取值 {override!r} 非法; 合法值: {list(OVERRIDE_VALUES)}")
        return override, f"cli --math-font={override}", warnings

    log = log if isinstance(log, dict) else {}

    # ---- 第 2 级: 顶层标量手写键 ----
    hits: list = []      # [(policy, source)]
    for key in SCALAR_KEYS:
        if key not in log:
            continue
        raw = log[key]
        pol = normalize_policy_token(raw)
        src = f"decision_log.{key}={raw!r}"
        if pol is None:
            warnings.append(
                f"[政策] {src} 无法归一 (支持 upright/conventional 或 true/false), "
                f"该键未采用")
            continue
        hits.append((pol, f"decision_log.{key}"))
    distinct = {p for p, _ in hits}
    if len(distinct) > 1:
        detail = "; ".join(f"{s} → {p}" for p, s in hits)
        warnings.append(
            f"[政策] 同级标量键给出不同政策 ({detail}); 不替用户选, 按未登记处理 "
            f"(保持输入)。请统一为一处后重跑")
        return POLICY_UNSPECIFIED, "conflict: " + detail, warnings

    # ---- 第 3 级: 自由文本备注 (只在第 2 级无有效值时才作为答案) ----
    text_hits: list = []
    for path in TEXT_PATHS:
        text = _dig(log, path)
        if not isinstance(text, str) or not text.strip():
            continue
        pol = scan_free_text(text)
        src = "decision_log." + ".".join(path)
        if pol is None:
            warnings.append(
                f"[政策] {src} (自由文本) 未判定: 无政策词/两侧词并存/含否定表述; "
                f"建议改用手写标量键 {SCALAR_KEYS[0]}=\"upright\"|\"conventional\"")
            continue
        text_hits.append((pol, src))

    if hits:
        pol, src = hits[0]
        for tpol, tsrc in text_hits:
            if tpol != pol:
                warnings.append(
                    f"[政策] {tsrc}(自由文本) 与 {src} 不一致, 按显式标量键取值 "
                    f"({pol}); 建议清理自由文本里的旧表述")
        return pol, src, warnings
    if text_hits:
        pol, src = text_hits[0]
        return pol, f"{src}(自由文本)", warnings
    warnings.append(f"[政策] 未登记数学字体政策 ({searched_paths_note()}); "
                    f"可加 --math-font 显式指定")
    return POLICY_UNSPECIFIED, "", warnings
