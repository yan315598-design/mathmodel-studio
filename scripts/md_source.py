# -*- coding: utf-8 -*-
"""md_source.py — md 源解析与稿件发现的小共享函数 (v3.1.0 新增)

被 export_final_docx.py (终稿导出) 与 ref_order_audit.py (文献引用审计) 共用,
保证"审计扫的文件 / 忽略的区段"与"实际导出的文件 / 忽略的区段"完全同源。
v3.1.0 前两处各写一套口径, 三处实测偏差:

  - 稿件发现: 导出只拼 `NN_*.md` 系列 (或 main.md / abstract_draft+sections),
    审计却递归扫 `paper_workspace/**/*.md`——草稿、notes、README 里的 [N] 全被
    算成引用, 审计结论与成稿不符;
  - 围栏: 导出用变长围栏状态机 (```` 开栏时其中的 ``` 是内容), 审计只认
    "行首 ```", 四反引号围栏里的三反引号会提前闭栏 → 栏内 `[2]` 被误计;
  - 参考文献节: 导出给标题加 pandoc `{-}` 不编号标记 ("## 参考文献 {-}"),
    审计按标题文本全等匹配 "参考文献" → 认不出文献表, 报 no_reference_section。

只放**小函数**, 不建框架/类层次 (FenceTracker 是从 export_final_docx.py 原样
迁来的既有实现, 迁出只为两处共用同一口径)。

接口:
    discover_ordered_sources(workspace) -> (list[Path], mode)  有序稿件发现
    FenceTracker / iter_lines_outside_fences(text)             代码围栏状态机
    has_heading_outside_fences(text) -> bool                   围栏外是否有标题
    parse_heading(line) -> (level, title) | None               标题行解析
    strip_heading_attrs(title) -> str                          去 pandoc {…} 属性
    is_bibitem_line(line) / bibitem_payload(line)              旧 \\bibitem 条目
    file_kind(path) -> "references"|"appendix"|"body"          文件角色
    read_source_text(path) -> str                              容错读 md 源文本
"""

from __future__ import annotations

import re
from pathlib import Path

# 复用审阅件导出的自动发现约定 (只读 import, 不改其行为): md_convention 回退
# 策略就是 export_docx.discover_md_files (main.md 单文件 / abstract_draft +
# sections/*.md), 不另写一份以免两处漂移。
from export_docx import discover_md_files, natural_key

# md 标题 (pandoc 口径: ≤3 前导空格, 文末可带 ATX 收尾 #)
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
# 标题文末 pandoc 属性块 (" {-}" / " {.unnumbered}" / " {#id}" / " {key=value}"):
# 判定"已带属性"与去属性共用。首字符须是 - / . / # 或字母 (pandoc 属性块形态),
# 故 "情形 {1,2}" 这类正文花括号不被误剥。
ATTRS_TAIL_RE = re.compile(r"\s*\{(?=[-#.A-Za-z])[^{}]*\}\s*$")
# 旧式 tex 参考文献条目: \bibitem{key} / \bibitem[标签]{key}
BIBITEM_RE = re.compile(r"^\s*\\bibitem(?:\[[^\]]*\])?\{[^}]*\}\s*")
# 显式编号文献条目: 行首 [N] + 非空内容 (排除链接定义 [1]:、链接 [1](…)、[1] 空行)
REF_ENTRY_RE = re.compile(r"^\s*\[(\d{1,3})\](?![:(\]])\s*\S")
# 行内 code span (同长反引号闭合, 内容可跨行): 其内的 $/反斜杠/方括号不参与解析
INLINE_CODE_RE = re.compile(r"(`+)(?:.*?)\1", re.DOTALL)
# 终稿自动发现的数字前缀文件名 (01_abstract.md … 10_appendix.md)
SERIES_NAME_RE = re.compile(r"^\d+_")
# 参考文献节标题 (紧凑比对: 去属性块与空白后全等)
REFS_HEADING_TEXT = "参考文献"

# 发现策略名 (report/log 用): 数字前缀系列 / 审阅件约定 / 一个都没有
MODE_NN_SERIES = "nn_series"
MODE_MD_CONVENTION = "md_convention"
MODE_NONE = "none"


def discover_ordered_sources(workspace: Path) -> tuple:
    """有序稿件发现 (与终稿导出同一套规则), 返回 (路径列表, 策略名)。

    规则 (顺序即优先级, 与 export_final_docx 原 discover_final_files 一致):
    1. workspace 顶层 `NN_*.md` 数字前缀系列 → 文件名自然排序 (01_abstract 在
       10_appendix 前), 策略 nn_series。**只取顶层该系列**——同目录下的草稿/
       notes/README 等非导出 md 不入清单;
    2. 无该系列 → 回退审阅件约定 (export_docx.discover_md_files): main.md 或
       abstract_draft.md + sections/*.md, 策略 md_convention;
    3. 两者皆空 → ([], "none")。

    返回 Path 列表 (不 resolve, 保持调用方给的形态)。
    """
    series = sorted((p for p in workspace.glob("*.md")
                     if SERIES_NAME_RE.match(p.name)),
                    key=lambda p: natural_key(p.name))
    if series:
        return series, MODE_NN_SERIES
    fallback = discover_md_files(workspace)
    if fallback:
        return fallback, MODE_MD_CONVENTION
    return [], MODE_NONE


class FenceTracker:
    """pandoc 代码围栏状态机: ``` / ~~~ 三字符以上开栏, 闭栏须同字符且不短于
    开栏长度、不带 info 串 (pandoc 语义); 反引号开栏的 info 串不得含反引号。
    围栏内容 (含开/闭行) 一律不参与编号注入与标题预处理。"""

    def __init__(self):
        self._char = None
        self._length = 0

    @property
    def in_fence(self) -> bool:
        return self._char is not None

    def update(self, line: str) -> bool:
        """喂入一行, 返回该行是否为围栏开/闭边界行。"""
        m = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if not m:
            return False
        fence = m.group(1)
        ch, ln = fence[0], len(fence)
        if self._char is None:
            if ch == "`" and "`" in line[m.end():]:
                return False  # info 串含反引号: 不是围栏 (pandoc 口径)
            self._char, self._length = ch, ln
            return True
        if ch == self._char and ln >= self._length and not line[m.end():].strip():
            self._char, self._length = None, 0
            return True
        return False


def iter_lines_outside_fences(text: str):
    """产出 (index, line, fenced); 围栏边界行与内容行 fenced=True。

    编号注入、md 卫生 lint、引用审计共用本实现, 保证围栏口径一致
    (四反引号围栏内的三反引号是内容, 不提前闭栏)。
    """
    tracker = FenceTracker()
    for idx, line in enumerate(text.split("\n")):
        if tracker.update(line) or tracker.in_fence:
            yield idx, line, True
        else:
            yield idx, line, False


def has_heading_outside_fences(text: str) -> bool:
    """围栏外是否存在 md 标题行 (标题合成判定: 无标题才补 "## 参考文献" 等)。"""
    for _, line, fenced in iter_lines_outside_fences(text):
        if not fenced and parse_heading(line) is not None:
            return True
    return False


def parse_heading(line: str):
    """解析标题行, 返回 (level, title) 或 None (非标题行)。

    title 保留文末 pandoc 属性块 (如 "参考文献 {-}")——判定"已带属性"要用原样;
    取纯标题文本用 strip_heading_attrs()。
    """
    m = HEADING_RE.match(line)
    if m is None:
        return None
    return len(m.group(1)), m.group(2).strip()


def strip_heading_attrs(title: str) -> str:
    """去掉标题文末的 pandoc 属性块与空白, 返回纯标题文本。

    例: "参考文献 {-}" → "参考文献"; "附录A 代码 {.unnumbered}" → "附录A 代码"。
    连续多个属性块一并去掉; 属性块之外的内容一字不动。
    """
    out = title.strip()
    while True:
        nxt = ATTRS_TAIL_RE.sub("", out).strip()
        if nxt == out:
            return out
        out = nxt


def has_heading_attrs(title: str) -> bool:
    """标题是否已带 pandoc 属性块 (再次标记不编号前用它跳过, 幂等)。"""
    return ATTRS_TAIL_RE.search(title) is not None


def is_bibitem_line(line: str) -> bool:
    """该行是否为旧式 tex 参考文献条目 (\\bibitem / \\bibitem[标签])。"""
    return BIBITEM_RE.match(line) is not None


def bibitem_payload(line: str) -> str:
    """\\bibitem 行去掉命令头后的条目正文 (非条目行返回原行去行尾空白)。

    编号列表化 (export) 与条目识别 (审计) 共用同一"命令头边界"口径:
    \\bibitem[模板]{key} 的标签与 key 都算命令头, 不落进正文。
    """
    m = BIBITEM_RE.match(line)
    return (line[m.end():] if m else line).rstrip()


def file_kind(path: Path) -> str:
    """按文件名把 md 分为 references / appendix / body 三类 (中文别名同判)。

    导出 (文件预处理: bibitem 转换/标题合成) 与引用审计 (无标题时整个 references
    文件即文献表) 共用这一个角色判定, 保证"审计认的文献表"就是"导出会合成的"。
    """
    name = path.name
    low = name.lower()
    if "reference" in low or "参考文献" in name:
        return "references"
    if "appendix" in low or "附录" in name:
        return "appendix"
    return "body"


def scan_reference_entries(text: str) -> list:
    """扫描文献表文本的条目行, 返回 [(行内序号, 1 基行号, 形态, 显式编号|None)]。

    形态 ∈ "explicit" (行首 [N] + 内容) | "bibitem" (旧式 \\bibitem 行);
    代码围栏内的行不算 (与编号注入/审计共用 FenceTracker 口径)。只识别条目,
    **不分配编号** —— 分配规则在 allocate_reference_numbers (两端共用)。
    """
    out = []
    for idx, line, fenced in iter_lines_outside_fences(text):
        if fenced:
            continue
        if is_bibitem_line(line):
            out.append((idx, idx + 1, "bibitem", None))
            continue
        m = REF_ENTRY_RE.match(line)
        if m:
            out.append((idx, idx + 1, "explicit", int(m.group(1))))
    return out


def reference_section_spans(text: str) -> list:
    """正文文件里显式 "## 参考文献" 节的 [(起行, 止行)] 闭区间列表 (0 基, 含边界)。

    与引用审计的 in_refs 状态机同规则: 标题级 ≤2 且紧凑标题 == REFS_HEADING_TEXT
    开节; 遇到**同级或更高级**标题闭节 (级更深的小标题不闭节)。
    用途: main.md 这类单文件稿在正文里内嵌文献表时, 导出只对**该节内**的条目做
    bibitem→[N] 转换与编号分配 (不整文件乱转), 审计也只把该节当定义区, 两端同一
    区间。references 角色文件不用本函数 (整文件即文献表, 既有行为不变)。
    """
    spans = []
    start = None
    refs_level = 0
    for idx, line, fenced in iter_lines_outside_fences(text):
        if fenced:
            continue
        parsed = parse_heading(line)
        if parsed is None:
            continue
        level, raw_title = parsed
        title_cmp = compact_title(strip_heading_attrs(raw_title))
        if start is not None and level <= refs_level:
            spans.append((start, idx - 1))
            start, refs_level = None, 0
        if start is None and level <= 2 and title_cmp == REFS_HEADING_TEXT:
            start, refs_level = idx, level
    if start is not None:
        spans.append((start, len(text.split("\n")) - 1))
    return spans


def compact_title(title: str) -> str:
    """标题比对用紧凑形态: 去掉空白 (兼容 "参 考 文 献" 这类写法)。"""
    return re.sub(r"[\s\u3000]+", "", title)


def allocate_reference_numbers(entries: list) -> tuple:
    """给文献条目分配编号, 返回 (与 entries 同序的编号列表, 警告列表)。

    规则: 显式 [N] 条目保留自身编号; \\bibitem 条目按出现顺序取**未被显式编号占用
    的最小正整数** (先收集全部显式编号再分配, 故与顺序无关、两端结果一致)。

    为什么必须共用: 混排 ([1] Alpha + \\bibitem{b} Beta) 时, 导出原实现只给
    bibitem 顺序编号 → 产出 "[1] Alpha" + "[1] Beta" 重号; 审计原实现按"自增游标
    跳过显式号" → defined={1,2} 判 pass。同一份稿子两端给出不同结论 (bug-reviewer
    P1)。现在导出改写 bibitem 行与审计登记 defined 都调本函数, 结论必然一致。
    显式编号重复 (两行同为 [1]) 时只警告: 条目仍各按自身编号登记, 由审计的
    集合一致性检查暴露 (重复号在 defined 里只留首个位置)。
    """
    explicit = [num for _, _, kind, num in entries if kind == "explicit"]
    warnings = []
    dups = sorted({n for n in explicit if explicit.count(n) > 1})
    if dups:
        warnings.append("文献表显式编号重复: " + ", ".join(f"[{n}]" for n in dups))
    used = set(explicit)
    numbers = []
    nxt = 1
    for _, _, kind, num in entries:
        if kind == "explicit":
            numbers.append(num)
            continue
        while nxt in used:
            nxt += 1
        numbers.append(nxt)
        used.add(nxt)
        nxt += 1
    return numbers, warnings


def read_source_text(path: Path) -> str:
    """容错读 md 源文本 (UTF-8; 非法字节替换)。

    审计/只读扫描用: 单个文件编码异常不中断全稿扫描 (导出链另有严格读入 +
    "请保存为 UTF-8" 的 exit 2 拦截, 两者口径不同属预期)。
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
