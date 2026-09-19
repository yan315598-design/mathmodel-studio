# -*- coding: utf-8 -*-
"""论文一致性审计器: 对 paper_workspace 正文做 5 项一致性审计。

针对用户实战高频翻车点:
  1. 未冻结数字警告   —— state/frozen_numbers.json 存在时, 比对正文 "数字+单位"
     与冻结登记值 (容差 ±1%); 未匹配且未登记的给 ⚠️ 清单 (行号+摘录),
     出现在摘要/结论章节且与冻结同口径 (同单位家族) 数值冲突的给 ❌。
  2. 摘要-结论一致性   —— 定位"摘要"与"结论"章节 (md 标题 / \\section /
     \\begin{abstract} 等), 同单位家族数值两两配对, 相距 >1% 且 <=20%
     (疑似同一指标) 给 ❌ (例: 摘要 4368 元/吨 vs 结论 4638 元/吨)。
  3. 图表式引用闭环    —— 引用了未定义的图/表/式编号 ❌; 定义了从未被引用 ⚠️;
     编号不连续 (定义 1,2,4 缺 3) ❌。
     md/pdf 行式题注 "图 1：标题" / "表 2-1 标题" 为定义;
     docx 链 md 真源 (md_authoring_spec §3) 的第三形态: ": 表 N：标题" 与
     "![图 N 说明](路径)" 同为定义 (A6 修复, 2026 A 题 92 条误报教训);
     tex: 由 \\label{fig:..}/\\ref{..} 符号闭环 + figure/table 计数器推导编号闭环;
     自动编号 (caption 不写 "图 N") 时, \\label{fig:N}/\\label{tab:N} 的数字部分
     与 figure/table/longtable 环境内 caption 计数序均计入定义集 (T-06 修复);
     公式编号闭环 (A6 新增): 定义 = $$ 块内 "\\qquad (N)", 引用 = 正文 "式（N）"
     与 "式(N)"; "结果表 50 格" 类数量短语 (编号后紧跟量词) 不算引用。
  4. 符号表脱节        —— 存在符号表 ("符号说明"标题节 / 含"符号+含义"表头) 时,
     正文 $\\alpha$、$x_i$、希腊字母等形似符号未在表内定义 → ⚠️ 清单。
     代码围栏 (``` / ~~~, 变长围栏按开栏长度配对) 与行内代码 span 不参与抽取;
     常用哑变量/单字母白名单 (SYMBOL_WHITELIST, D3 修复); 带下标复合符号
     ($r_i$) 以下标所属基名整体判定, 不拆出下标字母单独告警。
  5. 版本错乱检测      —— 工作区内 (除 _archive/、submission/ 等) 存在多个
     "v\\d|副本|最终版|修订版|final|old|backup" 命名的 .md/.tex/.docx → ⚠️,
     提示按 workspace_protocol 只留 main + _archive/。

用法:
    python scripts/consistency_audit.py [--workspace <dir>]   # 默认 cwd
    python scripts/consistency_audit.py --workspace <dir> --paper 论文.md
    python scripts/consistency_audit.py --workspace <dir> --json   # 机器版 JSON
    python scripts/consistency_audit.py --self-test                # 内置合成样例自测

正文文件: 扫描 <workspace>/paper_workspace/ 下全部 .md/.tex (可嵌套, 按文件名
顺序合并为一份文档处理, 支持 main + sections/ 拆分结构); --paper 指定单文件
(.pdf 亦可, 需 pip install pypdf 做文本提取)。
归档过滤: 扫描根下的 _archive/ submission/ tmp/ figures/ results/ state/ code/
等目录不参与审计 —— 只按**工作区相对**目录名判定 (v3.1.1 修复: 修复前按整条
绝对路径逐段匹配, 工作区绝对路径里出现 tmp/Temp 这类同名父目录时, 工作区下全部
正文都被误判为已归档, 脚本直接报"未找到正文文件"——静默漏检全部正文)。
人读输出为摘要 (每个检查最多 PRINT_FINDINGS_CAP 处逐条打印, 含文件:行与摘录);
完整清单走 --json, 或 --report <path> 落盘后按路径查看。

退出码:
    0  通过 (无 ❌ 级问题; ⚠️ 只提示不阻塞)
    1  存在 ❌ 级问题 (数字冲突/摘要结论打架/引用断链)
    2  参数或 IO 错误 (工作区/正文缺失、JSON 损坏等)
"""

from __future__ import annotations

import argparse
import bisect
import json
import os
import re
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------- 常量

# 单位候选按"长优先"排序: MWh 先于 MW; 万元 先于 元; 小时 先于 h。
_UNIT_ALT = r"\\?%|万元|MWh|元|MW|吨|小时|h|km|个|台|人|倍"
# 复合单位 (元/吨、元/小时) 作为整体家族键, 避免跨量纲误判
_UNIT_FULL = r"(?:" + _UNIT_ALT + r")(?:\s*/\s*(?:" + _UNIT_ALT + r"))?"
# 正文 "数字+单位" 提取 (支持负数与科学计数法 + \% 转义兼容)
NUM_UNIT_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\s*" + _UNIT_FULL)


def _norm_unit(u: str) -> str:
    """单位规范化: 去空白、\\%→%, 复合单位整体保留 (元/吨 ≠ 元)。"""
    return re.sub(r"\s+", "", u).replace("\\%", "%").strip()

MATCH_TOL = 0.01          # 与冻结登记值比较的 ±1% 容差
NEAR_WINDOW = 0.20        # 摘要-结论"疑似同一指标"的近邻窗口
EXCERPT_MAX = 72          # 行摘录最大宽度

# 希腊字母 (LaTeX 命令名 -> 规范名; 带 var- 变体并入基础名)
_GREEK_MAP = {
    "alpha": "alpha", "beta": "beta", "gamma": "gamma", "delta": "delta",
    "epsilon": "epsilon", "varepsilon": "epsilon", "zeta": "zeta",
    "eta": "eta", "theta": "theta", "vartheta": "theta", "iota": "iota",
    "kappa": "kappa", "lambda": "lambda", "mu": "mu", "nu": "nu", "xi": "xi",
    "omicron": "omicron", "pi": "pi", "varpi": "pi", "rho": "rho",
    "varrho": "rho", "sigma": "sigma", "varsigma": "sigma", "tau": "tau",
    "upsilon": "upsilon", "phi": "phi", "varphi": "phi", "chi": "chi",
    "psi": "psi", "omega": "omega", "Gamma": "gamma", "Delta": "delta",
    "Theta": "theta", "Lambda": "lambda", "Xi": "xi", "Pi": "pi",
    "Sigma": "sigma", "Upsilon": "upsilon", "Phi": "phi", "Psi": "psi",
    "Omega": "omega",
}
_GREEK_UNICODE = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron",
    "π": "pi", "ρ": "rho", "σ": "sigma", "τ": "tau", "υ": "upsilon",
    "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
    "Α": "alpha", "Β": "beta", "Γ": "gamma", "Δ": "delta", "Ε": "epsilon",
    "Ζ": "zeta", "Η": "eta", "Θ": "theta", "Ι": "iota", "Κ": "kappa",
    "Λ": "lambda", "Μ": "mu", "Ν": "nu", "Ξ": "xi", "Ο": "omicron",
    "Π": "pi", "Ρ": "rho", "Σ": "sigma", "Τ": "tau", "Υ": "upsilon",
    "Φ": "phi", "Χ": "chi", "Ψ": "psi", "Ω": "omega",
}
_GREEK_CMD_RE = re.compile(r"\\[A-Za-z]+")
_SINGLE_LETTER_RE = re.compile(r"(?<![A-Za-z\\])[A-Za-z](?![A-Za-z])")
_INDEXED_LETTER_RE = re.compile(r"(?<![A-Za-z\\])([A-Za-z])(?:_|\^)")
_DOLLAR_RE = re.compile(r"\$([^$\n]{1,160})\$")
_BACKTICK_RE = re.compile(r"`([^`\n]{1,40})`")


def _greek_roots(text: str) -> set[str]:
    """提取文本中的希腊字母 (LaTeX 命令 \\alpha 或 Unicode α), 归一到规范名。"""
    out: set[str] = set()
    for m in _GREEK_CMD_RE.finditer(text):
        name = m.group(0)[1:]
        c = _GREEK_MAP.get(name)
        if c:
            out.add(c)
    for ch in text:
        c = _GREEK_UNICODE.get(ch)
        if c:
            out.add(c)
    return out

# 版本错乱检测
VERSION_RE = re.compile(r"(?:v\d+|副本|最终版|修订版|final|old|backup)", re.I)
SKIP_DIRS = {"_archive", "submission", ".git", "__pycache__", "node_modules",
             ".venv", "venv", "tmp", "figures", "results", "state", "code"}

CHECK_NAMES = {
    1: "未冻结数字", 2: "摘要-结论一致性", 3: "图表式引用闭环",
    4: "符号表脱节", 5: "版本错乱检测",
}
MARK = {"error": "❌", "warn": "⚠️ "}
# 人读摘要每个检查最多逐条打印的处数; 其余折算一行并指路完整清单 (--json/--report)。
PRINT_FINDINGS_CAP = 8

CODE_FENCE_MD = re.compile(r"^[ \t]*```")
CODE_BEGIN_TEX = re.compile(r"^[ \t]*\\(?:begin)\{(?:verbatim|lstlisting)\}")
CODE_END_TEX = re.compile(r"^[ \t]*\\(?:end)\{(?:verbatim|lstlisting)\}")
TEX_COMMENT = re.compile(r"^[ \t]*%")
MD_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*#*\s*$")
TEX_HEADING_RE = re.compile(
    r"^[ \t]*(\\(?:subsub|sub)?section\*?)(?:\[[^\]]*\])?\{([^}]*)\}"
)
TEX_ABSTRACT_ENV = re.compile(r"^[ \t]*\\begin\{abstract\}")
TEX_END_ABSTRACT = re.compile(r"^[ \t]*\\end\{abstract\}")
TEX_CAPTION_RE = re.compile(r"\\caption\{([^}]*)\}")
TEX_LABEL_RE = re.compile(r"\\label\{((?:fig|tab|table)[^}]*)\}", re.I)
TEX_REF_RE = re.compile(r"\\(?:autoref|cref|Cref|vref|Vref|ref)\{([^}]*)\}")
TEX_FIG_ENV = re.compile(r"\\begin\{figure\*?\}(?:\[[^\]]*\])?")
# table 环境含 longtable (pandoc md 表格输出形态), 自动编号按 caption 计数序覆盖它
TEX_TAB_ENV = re.compile(r"\\begin\{(?:table|longtable)\*?\}(?:\[[^\]]*\])?")
TEX_ENV_END = re.compile(r"\\end\{(figure|table|longtable)\*?\}")
TEX_COUNTER_DASH = re.compile(
    r"\\counterwithin\{(?:figure|table)\}\{section\}"
    r"|\\renewcommand\{\\the(?:figure|table)\}[^}]*\\arabic\{section\}",
    re.S,
)

# 行式题注 (md/pdf/含编号题注的 tex) 的判定辅助
_CLAUSE_MARKERS = ("所示", "可见", "如图", "见图", "见下表", "见上图",
                   "见附图", "如下", "参考", "对比图", "表明", "展示")
_PLAIN_TITLE_LINES = {"摘要", "摘 要", "Abstract", "abstract",
                      "结论", "结 论", "结语", "Conclusion", "conclusion"}

# A6: docx 链 md 真源题注第三形态 (md_authoring_spec §3)
#   表定义: 行首 ": 表 N：…" (前缀冒号, 兼容全角);  图定义: "![图 N 说明](路径)"
_DOCX_TAB_CAPTION_RE = re.compile(r"^[:：]\s*表\s*(\d[\d.\-]*)")
_DOCX_FIG_CAPTION_RE = re.compile(r"^!\[图\s*(\d[\d.\-]*)")
# A6: 公式编号闭环 —— 定义 = $$ 块内 "\qquad (N)"; 引用 = 正文 式（N）/ 式(N)
# 引用排除复合词 (方式/公式/形式/格式/样式/模式 + (N) 非编号引用)
_EQ_NUM_DEF_RE = re.compile(r"\\qquad\s*[（(]\s*(\d+(?:\.\d+)?)\s*[）)]")
_EQ_REF_RE = re.compile(r"(?<![方公形格样模])式\s*[（(]\s*(\d+(?:\.\d+)?)\s*[）)]")
_DISPLAY_MATH_RE = re.compile(r"\$\$(.+?)\$\$", re.S)
# A6: 数量短语豁免 —— "结果表 50 格逐格" 的 "表 50 格" 是格数描述而非编号引用
_REF_MEASURE_BLOCK = re.compile(r"^\s*(?:格|行|列|个|项|条|张|款|次|点|位|步)")
# A6: md 代码围栏 (变长配对: 关栏字符同、长度 ≥ 开栏、栏后仅空白)
_MD_FENCE_OPEN_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
_MD_FENCE_CLOSE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*$")

# D3: 符号白名单 —— 常用哑变量与通用单字母, 只豁免"裸单字母"形态的告警;
# 带下标的复合符号 ($r_i$) 以基名 r 整体判定, 不因下标字母 i 在白名单而整体豁免。
# 模块级常量, 项目可按需扩展 (如补 "pi"、"mu" 等普适常数名)。
SYMBOL_WHITELIST = frozenset({
    "i", "j", "k", "n", "m",    # 求和/迭代/下标哑变量
    "e",                        # 自然对数底 (指数形式 e^{-...})
    "a", "b",                   # 待定系数 / 区间端点
    "x", "y", "t",              # 通用自变量
})


# ---------------------------------------------------------------- 工具

def _fmt(v) -> str:
    """float 显示: 整数值不带小数尾。"""
    f = float(v)
    if f.is_integer() and abs(f) < 1e15:
        return str(int(f))
    return repr(f)


def _excerpt(text: str, limit: int = EXCERPT_MAX) -> str:
    text = text.replace("\t", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _canon_ref(tok: str) -> str:
    """编号 token 规范化: '01'->'1', '1.10'->'1.1', '2-01'->'2-1'。"""
    parts = re.split(r"([.\-])", tok.strip())
    out = []
    for p in parts:
        if p in (".", "-"):
            out.append(p)
        elif p.isdigit():
            out.append(str(int(p)))
        else:
            try:
                f = float(p)
                out.append(_fmt(f))
            except ValueError:
                out.append(p)
    return "".join(out)


def _within(value: float, ref: float, tol: float) -> bool:
    denom = max(abs(ref), 1e-12)
    return abs(value - ref) <= tol * denom


def _rel_dist(a: float, b: float) -> float:
    denom = max(abs(a), abs(b), 1e-12)
    return abs(a - b) / denom


def _parse_num_unit(g0: str) -> tuple[float, str] | None:
    """把 '数字+单位' 匹配串解析为 (数值, 规范化单位)。"""
    num_m = re.match(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", g0)
    if not num_m:
        return None
    value = float(num_m.group(0))
    unit_part = g0[num_m.end():]
    unit_m = re.search(_UNIT_FULL, unit_part)
    if not unit_m:
        return None
    return value, _norm_unit(unit_m.group(0))


def _read_doc_file(path: Path) -> list[str]:
    """读正文文本; .pdf 依赖可选 pypdf 提取。返回行列表 (保留换行符位置语义, 不含 \\n)。"""
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader  # 可选依赖
        except ImportError:
            raise AuditIOError(
                f"{path} 是 PDF, 文本提取需要可选依赖 pypdf: pip install pypdf"
            )
        text = "\n".join(
            (page.extract_text() or "") for page in PdfReader(str(path)).pages
        )
    else:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="gb18030", errors="replace")
    return text.split("\n")


class AuditIOError(Exception):
    """工作区/正文输入错误 (退出码 2)。"""


# ---------------------------------------------------------------- 文档装配

class Doc:
    """把多个正文文件按文件名序合并为一份文档, 提供行级坐标与章节定位。"""

    def __init__(self, files: list[Path]):
        self.files = files
        self.names: list[str] = []
        self.lines: list[str] = []
        self.excluded: set[int] = set()   # 代码块/注释行, 各扫描忽略
        self.headings: list[tuple[int, str, int]] = []  # (level, title, line_idx)
        self.sections: list[str] = []     # 每行的章节标签: "", "abstract", "conclusion", "symbol"
        self.figdefs: list[tuple[str, int]] = []     # (canon token, line_idx)
        self.tabdefs: list[tuple[str, int]] = []
        # 行文可见的"字面题注"定义 (A6): md 行式题注 "图 N：" 与 docx 链
        # ": 表 N" / "![图 N"。tex 计数器/\label 推导的定义不在此列 ——
        # 编号连续性检查只对字面题注做 (自动编号由编译器管理, 文件级重构不可靠)。
        self.figdefs_lit: list[tuple[str, int]] = []
        self.tabdefs_lit: list[tuple[str, int]] = []
        # label 派生的自动编号定义 (T-06): 只用于"引用了未定义编号"的闭环判定,
        # 不参与"已定义但从未引用"告警——纯 \label+\ref 文档没有纯文本引用,
        # 数字定义必未被引用, 参与告警会产生噪声 (复审 P1-4)。
        self.figdefs_autonum: list[tuple[str, int]] = []
        self.tabdefs_autonum: list[tuple[str, int]] = []
        self.eqdefs: list[tuple[str, int]] = []      # A6: $$ 块内 \qquad (N)
        self.eqrefs: list[tuple[str, int]] = []      # A6: 正文 式（N）/式(N)
        self.figrefs: list[tuple[str, int]] = []
        self.tabrefs: list[tuple[str, int]] = []
        self.symrefs: list[tuple[str, int]] = []     # tex \\ref 符号引用 (id, line)
        self.symlabels: list[tuple[str, int]] = []
        self._assembled = False

    # -- 装配 -------------------------------------------------------
    def assemble(self) -> None:
        if self._assembled:
            return
        for path in self.files:
            for text in _read_doc_file(path):
                self.lines.append(text)
                self.names.append(path.as_posix())
        self._compute_exclusions()
        self._classify_lines()
        self._compute_spans()
        self._number_tex_float_envs()
        self._collect_cross_refs()
        self._collect_equation_defs()
        self._assembled = True

    # -- 标题行分类 (跳过注释与代码围栏行) ----------------------------
    def _classify_lines(self) -> None:
        for i, raw in enumerate(self.lines):
            if i in self.excluded:
                continue
            kind = self._kind_at(i)
            title = None
            level = 1
            if kind == "tex":
                m = TEX_HEADING_RE.match(raw)
                if m:
                    cmd = m.group(1)
                    if cmd.startswith("\\subsub"):
                        level = 3
                    elif cmd.startswith("\\sub"):
                        level = 2
                    else:
                        level = 1
                    title = m.group(2).strip()
            else:
                m = MD_HEADING_RE.match(raw)
                if m:
                    level = len(m.group(1))
                    title = m.group(2).strip()
                elif raw.strip() in _PLAIN_TITLE_LINES:
                    title = raw.strip()
            if title:
                self.headings.append((level, title, i))

    def _compute_exclusions(self) -> None:
        """标记 md 代码围栏 / tex verbatim/lstlisting / tex 行注释。

        md 围栏按 CommonMark 配对 (D3): ``` 与 ~~~ 均可开栏; 关栏须同字符、
        长度 ≥ 开栏、栏后仅空白 —— ```` 外栏内的 ``` 行不再被误判为关栏。
        """
        md_fence: tuple[str, int] | None = None   # (fence 字符, 开栏长度)
        tex_block = False
        for i, raw in enumerate(self.lines):
            if self._kind_at(i) == "tex":
                if tex_block:
                    self.excluded.add(i)
                    if CODE_END_TEX.match(raw):
                        tex_block = False
                    continue
                if CODE_BEGIN_TEX.match(raw):
                    tex_block = True
                    self.excluded.add(i)
                    continue
                if TEX_COMMENT.match(raw):
                    self.excluded.add(i)
                    continue
                continue
            if md_fence is None:
                m = _MD_FENCE_OPEN_RE.match(raw)
                # 反引号开栏的信息串不得再含反引号 (CommonMark); ~~~ 无此限制
                if m and (m.group(1)[0] == "~" or "`" not in raw[m.end():]):
                    md_fence = (m.group(1)[0], len(m.group(1)))
                    self.excluded.add(i)
            else:
                self.excluded.add(i)
                m = _MD_FENCE_CLOSE_RE.match(raw)
                if m and m.group(1)[0] == md_fence[0] \
                        and len(m.group(1)) >= md_fence[1]:
                    md_fence = None

    # -- 章节区间 ----------------------------------------------------
    def _compute_spans(self) -> None:
        n = len(self.lines)
        self.sections = [""] * n
        by_kind: dict[str, list[tuple[int, int]]] = {"abstract": [], "conclusion": [], "symbol": []}

        def tag(kind_tag: str, start: int, end: int) -> None:
            for k in range(start, min(end, n)):
                if not self.sections[k]:
                    self.sections[k] = kind_tag

        for idx, (level, title, ln) in enumerate(self.headings):
            kind_tag = None
            low = title.lower()
            if re.search(r"摘\s*要|abstract", low):
                kind_tag = "abstract"
            elif re.search(r"结\s*论|结语|conclusion", low):
                kind_tag = "conclusion"
            elif "符号" in title:
                kind_tag = "symbol"
            if not kind_tag:
                continue
            nxt = len(self.lines)
            for l2, t2, ln2 in self.headings[idx + 1:]:
                if l2 <= level:
                    nxt = ln2
                    break
            tag(kind_tag, ln + 1, nxt)

        # tex: \\begin{abstract}..\\end{abstract} 环境区间
        for i, raw in enumerate(self.lines):
            if i in self.excluded:
                continue
            if TEX_ABSTRACT_ENV.search(raw):
                end = i + 1
                while end < len(self.lines) and not TEX_END_ABSTRACT.search(self.lines[end]):
                    end += 1
                tag("abstract", i + 1, end)
        # 拆分式论文的摘要常放独立文件 (sections/00_abstract.tex / abstract.md):
        # 先按文件名整文件判为摘要区, 再叠加首页 "摘 要" 裸标题区间
        if not any(s == "abstract" for s in self.sections):
            ranges: list[tuple[int, int]] = []
            start = 0
            for k, name in enumerate(self.names):
                if k > 0 and name != self.names[k - 1]:
                    ranges.append((start, k))
                    start = k
            ranges.append((start, len(self.names)))
            for a, b in ranges:
                stem = Path(self.names[a]).stem.lower()
                if "abstract" in stem or "摘要" in stem:
                    tag("abstract", a, b)
                    break
        # tex: 首页 "摘 要" 裸标题 (模板无 \\begin{abstract}), 如
        #      {\\Large\\heiti 摘\\quad 要} / {\\heiti\\bfseries 摘\\hspace{1em}要}
        for i, raw in enumerate(self.lines):
            if i in self.excluded or self._kind_at(i) != "tex":
                continue
            cleaned = re.sub(r"\\[a-zA-Z]+|\{|\}", "", raw)
            cjk = "".join(ch for ch in cleaned if "\u4e00" <= ch <= "\u9fff")
            latin = cleaned.strip().lower()
            if cjk == "摘要" or latin == "abstract":
                j = i + 1
                while j < len(self.lines) and \
                        not re.search(r"关键词|\\section|\\newpage", self.lines[j]):
                    j += 1
                tag("abstract", i + 1, j)
        # md/tex 表格表头 "| 符号 | 含义 |" -> 符号表区间 (其表格行块)
        for i, raw in enumerate(self.lines):
            if i in self.excluded:
                continue
            if self.sections[i] == "" and \
                    re.search(r"^\s*\|.*(?:符号|Symbol).*\|.*(?:含义|说明|意义)", raw):
                j = i
                while j < len(self.lines) and self.lines[j].strip().startswith("|"):
                    self.sections[j] = "symbol"
                    j += 1
        self._abstract = [i for i, s in enumerate(self.sections) if s == "abstract"]
        self._conclusion = [i for i, s in enumerate(self.sections) if s == "conclusion"]
        self._symbol = [i for i, s in enumerate(self.sections) if s == "symbol"]

    def _kind_at(self, idx: int) -> str:
        return "tex" if self.names[idx].endswith(".tex") else "text"

    # -- tex float 环境计数器 -> 图/表编号定义 --------------------------
    def _number_tex_float_envs(self) -> None:
        if not any(nm.endswith(".tex") for nm in self.names):
            return
        text = "\n".join(self.lines[i] for i in range(len(self.lines))
                         if i not in self.excluded)
        dash = bool(TEX_COUNTER_DASH.search(text)
                    or re.search(r"(?:图|表)\s*\d+\s*-\s*\d+", text))
        sec_no = 0
        fig_sec = tab_sec = 0
        fig_glob = tab_glob = 0
        in_fig = in_tab = False
        cur_file: str | None = None
        for i, raw in enumerate(self.lines):
            if i in self.excluded:
                continue
            if self.names[i] != cur_file:
                cur_file = self.names[i]
                in_fig = in_tab = False  # float 环境不跨文件
            hd = TEX_HEADING_RE.match(raw)
            if hd and not hd.group(1).startswith("\\sub") and "*" not in hd.group(1):
                sec_no += 1
                fig_sec = tab_sec = 0
            if TEX_FIG_ENV.search(raw):
                in_fig = True
            if TEX_TAB_ENV.search(raw):
                in_tab = True
            e = TEX_ENV_END.search(raw)
            if e:
                in_fig = in_tab = False
            cm = TEX_CAPTION_RE.search(raw)
            if cm and in_fig and not in_tab:
                fig_sec += 1
                fig_glob += 1
                tok = f"{sec_no}-{fig_sec}" if (dash and sec_no) else str(fig_glob)
                self.figdefs.append((tok, i))
            elif cm and in_tab and not in_fig:
                tab_sec += 1
                tab_glob += 1
                tok = f"{sec_no}-{tab_sec}" if (dash and sec_no) else str(tab_glob)
                self.tabdefs.append((tok, i))

    # -- 引用与定义采集 -------------------------------------------------
    def _collect_cross_refs(self) -> None:
        n = len(self.lines)
        for i in range(n):
            raw = self.lines[i]
            if i in self.excluded:
                continue
            kind = self._kind_at(i)
            st = raw.strip()
            # A6: docx 链题注第三形态 —— ": 表 N：…" 与 "![图 N …](路径)"。
            # 定义行整体跳过 (题注文本里的 "表 N/图 N" 不计为引用)
            m = _DOCX_TAB_CAPTION_RE.match(st)
            if m:
                tok = _canon_ref(m.group(1))
                self.tabdefs.append((tok, i))
                self.tabdefs_lit.append((tok, i))
                continue
            m = _DOCX_FIG_CAPTION_RE.match(st)
            if m:
                tok = _canon_ref(m.group(1))
                self.figdefs.append((tok, i))
                self.figdefs_lit.append((tok, i))
                continue
            # 行式题注 -> 定义 (tex 中显式编号题注或 md/pdf 题注行)
            tok = _caption_token(raw)
            if tok:
                head = raw.strip().lstrip("-*+>#!| \t")
                if head.startswith(("表", "Table")):
                    self.tabdefs.append((tok, i))
                    self.tabdefs_lit.append((tok, i))
                else:
                    self.figdefs.append((tok, i))
                    self.figdefs_lit.append((tok, i))
                continue  # 题注行不计引用
            # 图片 markdown 行整体跳过 (避免路径/替代文本里的 "图 N")
            if re.search(r"^\s*!\[", raw):
                continue
            # A6: 公式引用 "式（N）" / "式(N)"
            for m in _EQ_REF_RE.finditer(raw):
                self.eqrefs.append((_canon_ref(m.group(1)), i))
            if TEX_REF_RE.search(raw):
                for body in TEX_REF_RE.findall(raw):
                    for lab in (x.strip() for x in body.split(",") if x.strip()):
                        if re.match(r"^(fig|tab|table)[^}]*", lab):
                            self.symrefs.append((lab, i))
            if kind == "tex":
                for lab in TEX_LABEL_RE.findall(raw):
                    low = lab.lower()
                    is_fig = low.startswith("fig:")
                    is_tab = not is_fig and low.startswith(("tab:", "table:"))
                    if not (is_fig or is_tab):
                        continue
                    defs = self.figdefs if is_fig else self.tabdefs
                    defs.append((lab, i))
                    # 自动编号 (T-06 修复): \label{fig:N}/\label{tab:N} (前缀大小写
                    # 兼容) 的数字部分计入数值定义集, 供正文纯文本 "图 N/表 N" 闭环;
                    # 进 autonum 侧表, 不参与"已定义但从未引用"告警 (P1-4)
                    m_num = re.match(r"^[A-Za-z]+\s*:\s*(\d+)\s*$", lab)
                    if m_num:
                        autonum = (self.figdefs_autonum if is_fig
                                   else self.tabdefs_autonum)
                        autonum.append((_canon_ref(m_num.group(1)), i))
            # 文字引用 "图 2-1"/"表 1" (中文与英文写法)
            for m in re.finditer(
                r"(?<![A-Za-z])(?:(?:图|表)\s*(\d[\d.\-]*)|"
                r"(?:Figure|Table|Fig)\.?[\s]*(\d[\d.\-]*))", raw, re.I
            ):
                tokraw = m.group(1) or m.group(2)
                if tokraw is None:
                    continue
                # A6: 数量短语不算引用 —— "结果表 50 格逐格" 的 50 是格数
                if _REF_MEASURE_BLOCK.match(raw[m.end():]):
                    continue
                head = raw[m.start():m.start() + 2]
                if "图" in head:
                    self.figrefs.append((_canon_ref(tokraw), i))
                elif "表" in head:
                    self.tabrefs.append((_canon_ref(tokraw), i))
                elif m.group(0).lower().startswith(("tab", "table")):
                    self.tabrefs.append((_canon_ref(tokraw), i))
                else:
                    self.figrefs.append((_canon_ref(tokraw), i))

    # -- 公式编号定义 (A6): $$ 块内 \qquad (N) --------------------------
    def _collect_equation_defs(self) -> None:
        parts: list[str] = []
        starts: list[int] = []
        pos = 0
        for i, line in enumerate(self.lines):
            if i in self.excluded:
                continue
            starts.append(pos)
            parts.append(line)
            pos += len(line) + 1
        text = "\n".join(parts)
        for m in _DISPLAY_MATH_RE.finditer(text):
            for mm in _EQ_NUM_DEF_RE.finditer(m.group(1)):
                tok = _canon_ref(mm.group(1))
                off = m.start(1) + mm.start()
                ln = bisect.bisect_right(starts, off) - 1
                self.eqdefs.append((tok, ln))

    # 便于取章节标签列表
    @property
    def abstract_lines(self) -> list[int]:
        return self._abstract

    @property
    def conclusion_lines(self) -> list[int]:
        return self._conclusion

    @property
    def symbol_lines(self) -> list[int]:
        return self._symbol


def _caption_token(raw: str) -> str | None:
    """行式题注判定: '图 2-1：标题' / '表4-2 标题' / 'Figure 1: xxx' 独立行。

    排除: 标题行 (#)、图片行 (!)、表格行 (|)、代码围栏 (装配阶段已滤)、
    以及整行纯引用句 (含 所示/可见/见图/如表 等语境词或句末标点)。
    """
    st = raw.strip()
    if not st or st[0] in "#!|`>":
        return None
    # 剥列表/加粗装饰: "- 图 1：.." / "**图 1：..**"
    while st and st[0] in "*-_":
        st = st[1:]
    st = st.lstrip(" \t")
    m = re.match(r"^(?:图|表|Figure|Table)\s*(\d[\d.\-]*)\s*(.*)$", st)
    if not m:
        return None
    rest = m.group(2).strip()
    rest = rest.lstrip("：:，, ").strip().strip("*_")
    if not rest or len(rest) < 2:
        return None
    if rest[-1] in "。！？；;.!?":
        return None
    if any(k in rest for k in _CLAUSE_MARKERS):
        return None
    return _canon_ref(m.group(1))


# ---------------------------------------------------------------- 各检查

def check_numbers(doc: Doc, workspace: Path, findings: list[dict],
                  frozen: dict | None) -> dict:
    """检查 1: 未冻结数字 / 摘要结论与冻结冲突。frozen=None 时跳过。"""
    if not frozen:
        return {"skipped": True, "reason": "未找到 state/frozen_numbers.json, 跳过"}
    claims = []
    for cid, rec in frozen.items():
        if not isinstance(rec, dict):
            continue  # 坏记录跳过 (防御 frozen_numbers.json 手写失误)
        try:
            value = float(rec.get("value"))
        except (TypeError, ValueError):
            continue
        unit = _norm_unit(str(rec.get("unit", "")))
        claims.append({"id": cid, "value": value, "unit": unit,
                       "label": f"{cid}={_fmt(value)} {unit}".strip()})
    by_token: dict[str, list] = {}
    for c in claims:
        by_token.setdefault(c["unit"], []).append(c)

    hits = errs = warns = 0
    n = len(doc.lines)
    for i in range(n):
        if i in doc.excluded:
            continue
        raw = doc.lines[i]
        sec = doc.sections[i]
        for m in NUM_UNIT_RE.finditer(raw):
            parsed = _parse_num_unit(m.group(0))
            if not parsed:
                continue
            value, unit = parsed
            fam = by_token.get(unit, [])
            ok = any(_within(value, c["value"], MATCH_TOL) for c in fam)
            if ok:
                continue
            hits += 1
            summary = sec in ("abstract", "conclusion")
            if summary and fam:
                errs += 1
                recs = "、".join(sorted({f'{c["label"]}' for c in fam})[:3])
                findings.append({
                    "check": 1, "severity": "error", "file": doc.names[i],
                    "line": i + 1,
                    "msg": f"摘要/结论章节数字 {_fmt(value)} {unit} 与冻结登记同口径数值不符"
                           f" (登记: {recs}), 疑似同 claim 口径不一致",
                    "excerpt": _excerpt(raw),
                })
            else:
                warns += 1
                kind = "该单位家族未冻结" if not fam else "未匹配任何冻结登记值"
                findings.append({
                    "check": 1, "severity": "warn", "file": doc.names[i],
                    "line": i + 1,
                    "msg": f"正文数字 {_fmt(value)} {unit} 为未登记数字 ({kind}, "
                           f"frozen_numbers.json 共 {len(claims)} 条 claim, 容差 ±1%)",
                    "excerpt": _excerpt(raw),
                })
    return {"claims": len(claims), "hit": hits, "error": errs, "warn": warns}


def check_abstract_conclusion(doc: Doc, findings: list[dict]) -> dict:
    """检查 2: 摘要-结论数值一致性 (按单位家族就近配对)。"""
    if not doc.abstract_lines or not doc.conclusion_lines:
        return {"skipped": True,
                "reason": "未定位到摘要或结论章节 (需要 '摘要'/'结论' 标题或 \\section)"}

    def collect(lineset: set[int]) -> dict[str, list[tuple[float, int]]]:
        out: dict[str, list[tuple[float, int]]] = {}
        for i in sorted(lineset):
            if i in doc.excluded:
                continue
            raw = doc.lines[i]
            for m in NUM_UNIT_RE.finditer(raw):
                parsed = _parse_num_unit(m.group(0))
                if parsed:
                    value, unit = parsed
                    out.setdefault(unit, []).append((value, i))
        return out

    abs_occ = collect(set(doc.abstract_lines))
    con_occ = collect(set(doc.conclusion_lines))
    errs = 0
    for unit in sorted(set(abs_occ) & set(con_occ)):
        A = sorted(abs_occ[unit], key=lambda x: (x[0], x[1]))
        C = sorted(con_occ[unit], key=lambda x: (x[0], x[1]))
        # 最近邻贪心配对 (允许窗口内), 剩余不配对的不下结论
        pairs = []
        used_c: set[int] = set()
        for a in A:
            cand = [c for c in C if c[1] not in used_c]
            if not cand:
                break
            best = min(cand, key=lambda c: _rel_dist(a[0], c[0]))
            if _rel_dist(a[0], best[0]) <= NEAR_WINDOW:
                pairs.append((a, best))
                used_c.add(best[1])
        for a, c in pairs:
            if _within(a[0], c[0], MATCH_TOL):
                continue
            errs += 1
            findings.append({
                "check": 2, "severity": "error",
                "file": doc.names[a[1]], "line": a[1] + 1,
                "msg": f"同一指标数值不一致: 摘要 {_fmt(a[0])} {unit} (行 {a[1] + 1})"
                       f" vs 结论 {_fmt(c[0])} {unit} (行 {c[1] + 1}), "
                       f"偏差 {_rel_dist(a[0], c[0]) * 100:.1f}% > 1% 容差",
                "excerpt": _excerpt(doc.lines[a[1]]),
            })
    abs_n = sum(len(v) for v in abs_occ.values())
    con_n = sum(len(v) for v in con_occ.values())
    return {"abstract_numbers": abs_n, "conclusion_numbers": con_n,
            "error": errs, "warn": 0}


def check_figures(doc: Doc, findings: list[dict]) -> dict:
    """检查 3: 图/表/式引用闭环。数值编号系统 + tex 符号 (\\label/\\ref) 系统。"""

    def closure(defs, refs, cname, warn_defs=None,
                miss_hint="(未找到对应题注/\\label)") -> tuple[int, int]:
        # warn_defs: 参与"已定义但从未引用"告警的定义集, 缺省等于 defs;
        # label 派生的自动编号定义只进 defs (闭环用) 不进 warn_defs (P1-4)
        errs = warns = 0
        ref_seen: set[tuple] = set()
        def_warned: set[tuple] = set()
        refs = _uniq(refs)
        used_tokens = {t for t, _ in refs}
        for tok, ln in refs:
            key = (tok, doc.names[ln], ln)
            if key in ref_seen:
                continue
            ref_seen.add(key)
            if not any(d[0] == tok for d in defs):
                errs += 1
                findings.append({
                    "check": 3, "severity": "error", "file": doc.names[ln],
                    "line": ln + 1,
                    "msg": f"引用了未定义的{cname}编号 [{tok}] {miss_hint}",
                    "excerpt": _excerpt(doc.lines[ln]),
                })
        # 定义了从未被引用 (同一编号跨多文件/双路径推导只告警一次)
        # 符号 token (含 ":", 如 fig:1) 跳过: 其未引用提示由下方符号系统路径
        # ("\label 定义了但从未被 \ref 引用") 负责, 数值闭环不再重复告警
        for tok, ln in (warn_defs if warn_defs is not None else defs):
            if isinstance(tok, str) and ":" in tok:
                continue
            key = (tok, doc.names[ln])
            if tok in used_tokens or key in def_warned:
                continue
            def_warned.add(key)
            warns += 1
            findings.append({
                "check": 3, "severity": "warn", "file": doc.names[ln],
                "line": ln + 1,
                "msg": f"{cname} [{tok}] 已定义但正文从未引用",
                "excerpt": _excerpt(doc.lines[ln]),
            })
        return errs, warns

    def continuity(defs, cname) -> int:
        """A6: 编号连续性 (1..N 无缺号)。只对字面题注/公式编号做;
        混合编号风格 (含 2-1 或符号 token) 时无法可靠判定, 跳过。"""
        toks = {t for t, _ in defs}
        nums = sorted(int(t) for t in toks if re.fullmatch(r"\d+", str(t)))
        if not nums or len(nums) != len(toks):
            return 0
        if nums == list(range(1, len(nums) + 1)):
            return 0
        missing = sorted(set(range(1, nums[-1] + 1)) - set(nums))
        first_def = min((ln for t, ln in defs if str(t) == str(nums[0])),
                        default=0)
        findings.append({
            "check": 3, "severity": "error", "file": doc.names[first_def],
            "line": first_def + 1,
            "msg": f"{cname}编号不连续: 已定义编号 {nums}, 缺少 {missing}",
            "excerpt": _excerpt(doc.lines[first_def]),
        })
        return 1

    e1, w1 = closure(_uniq(doc.figdefs) + _uniq(doc.figdefs_autonum),
                     doc.figrefs, "图", warn_defs=_uniq(doc.figdefs))
    e2, w2 = closure(_uniq(doc.tabdefs) + _uniq(doc.tabdefs_autonum),
                     doc.tabrefs, "表", warn_defs=_uniq(doc.tabdefs))
    # A6: 公式编号闭环 (定义 = $$ 块内 \qquad (N); 引用 = 式（N）/式(N))
    e3, w3 = closure(_uniq(doc.eqdefs), doc.eqrefs, "式",
                     miss_hint="(未找到对应 \\qquad (N) 公式编号)")
    c1 = continuity(doc.figdefs_lit, "图")
    c2 = continuity(doc.tabdefs_lit, "表")
    c3 = continuity(doc.eqdefs, "式")

    # ---- 符号系统 (tex \ref{fig:..}) ----
    # 无条件执行: tex 标签可能被归入 figdefs/tabdefs 的符号 token, 不能只依赖 symlabels 非空
    sym_errs = sym_warns = 0
    labels = {lab for lab, _ in doc.symlabels}
    labels |= {tok for tok, _ in doc.figdefs if isinstance(tok, str) and ":" in tok}
    labels |= {tok for tok, _ in doc.tabdefs if isinstance(tok, str) and ":" in tok}
    if doc.symrefs or doc.symlabels:
        used = set()
        for lab, ln in doc.symrefs:
            if (lab, ln) in used:
                continue
            used.add((lab, ln))
            if lab not in labels:
                sym_errs += 1
                findings.append({
                    "check": 3, "severity": "error", "file": doc.names[ln],
                    "line": ln + 1,
                    "msg": f"\\ref{{{lab}}} 引用了未定义的 \\label",
                    "excerpt": _excerpt(doc.lines[ln]),
                })
        used_labels = {lab for lab, _ in doc.symrefs}
        for lab, ln in _uniq(doc.symlabels):
            if lab not in used_labels:
                sym_warns += 1
                findings.append({
                    "check": 3, "severity": "warn", "file": doc.names[ln],
                    "line": ln + 1,
                    "msg": f"\\label{{{lab}}} 定义了但从未被 \\ref/\\autoref 引用",
                    "excerpt": _excerpt(doc.lines[ln]),
                })
    total_defs = (len(set(doc.figdefs) | set(doc.figdefs_autonum))
                  + len(set(doc.tabdefs) | set(doc.tabdefs_autonum))
                  + len(set(doc.eqdefs))
                  + len(set(doc.symlabels)))
    total_refs = (len(set(doc.figrefs)) + len(set(doc.tabrefs))
                  + len(set(doc.eqrefs)) + len(set(doc.symrefs)))
    return {"defs": total_defs, "refs": total_refs,
            "error": e1 + e2 + e3 + c1 + c2 + c3 + sym_errs,
            "warn": w1 + w2 + w3 + sym_warns}


def _uniq(items: list[tuple]) -> list[tuple]:
    out: list[tuple] = []
    seen: set[tuple] = set()
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def _chunk_roots(chunk: str) -> set[str]:
    """从一段数学/符号文本提取符号根名: 希腊字母 + 单拉丁字母。

    D3 口径:
      - \\text/\\mathrm/\\operatorname 花括内容 (单位、罗马体文字) 不算符号;
      - 下标位置的字母 (r_i / r_{i+1} 的 i) 是复合符号 $r_i$ 的组成部分,
        吸收进基名整体判定, 不再作为独立单字母根 —— 避免哑变量海量化误报;
        上标 (指数) 内容可能含真实符号, 保持原行为。
    """
    chunk = re.sub(r"\\(?:text|mathrm|operatorname)\s*\{(?:[^{}]*)\}", "", chunk)
    roots = _greek_roots(chunk)
    chunk = _GREEK_CMD_RE.sub(" ", chunk)  # 移除 LaTeX 命令后再取拉丁单字母
    for ch in _GREEK_UNICODE:
        chunk = chunk.replace(ch, " ")
    chunk = re.sub(r"_\{[^{}]*\}", " ", chunk)   # _{i+1} -> 下标表达式吸收
    chunk = re.sub(r"_[A-Za-z]", "  ", chunk)    # _i     -> 单字符下标吸收
    for m in _SINGLE_LETTER_RE.finditer(chunk):
        roots.add(m.group(0))
    return roots


def check_symbols(doc: Doc, findings: list[dict]) -> dict:
    """检查 4: 符号表脱节。有符号表才检查; 警告正文用而未定义表内符号。"""
    if not doc.symbol_lines:
        return {"skipped": True,
                "reason": "未找到符号表 (含'符号'的标题节或 '| 符号 | 含义 |' 表格)"}
    defined: set[str] = set()
    sym_line_set = set(doc.symbol_lines)
    for i in doc.symbol_lines:
        raw = doc.lines[i]
        for m in _DOLLAR_RE.finditer(raw):
            defined |= _chunk_roots(m.group(1))
        for m in _BACKTICK_RE.finditer(raw):
            defined |= _chunk_roots(m.group(1))
        defined |= _greek_roots(raw)
        for m in _INDEXED_LETTER_RE.finditer(raw):
            defined.add(m.group(1))
    if not defined:
        return {"skipped": True, "reason": "符号表存在但未解析出任何符号", "defined": 0}

    warns = 0
    n = len(doc.lines)
    for i in range(n):
        if i in doc.excluded or i in sym_line_set:
            continue
        # D3: 行内代码 span 不参与符号抽取 (代码变量 ≠ 论文符号)
        raw = _BACKTICK_RE.sub(" ", doc.lines[i])
        found: dict[str, str] = {}
        chunks: list[str] = []
        for m in _DOLLAR_RE.finditer(raw):
            chunks.append(m.group(1))
        # 裸希腊字母/命令 (未包 $ 也统计), 未定义才登记 (白名单豁免)
        for r in _greek_roots(raw):
            if r not in defined and r not in SYMBOL_WHITELIST:
                found.setdefault(r, "greek")
        for chunk in chunks:
            roots = _chunk_roots(chunk)
            has_index = bool(_INDEXED_LETTER_RE.search(chunk))
            greek_in = bool(_greek_roots(chunk))
            is_short_pure = len(chunk) <= 8 and not re.search(r"[0-9=\s]", chunk)
            for r in roots:
                if r in defined or r in SYMBOL_WHITELIST:
                    continue  # D3: 裸单字母白名单 (只豁免单字母形态)
                if has_index or greek_in or is_short_pure:
                    found.setdefault(r, "latin")
        if found:
            warns += 1
            syms = ", ".join(sorted(found))
            findings.append({
                "check": 4, "severity": "warn", "file": doc.names[i],
                "line": i + 1,
                "msg": f"正文出现未在符号表登记的符号: {syms} (符号表现有 {len(defined)} 个)",
                "excerpt": _excerpt(raw),
            })
    return {"defined": len(defined), "warn": warns, "error": 0}


def check_versions(workspace: Path, findings: list[dict]) -> dict:
    """检查 5: 版本错乱 (多份 v\\d/副本/最终版/修订版/final/old/backup 命名的论文文件)。"""
    hits: list[Path] = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith(".")]
        for fn in files:
            ext = Path(fn).suffix.lower()
            if ext not in (".md", ".tex", ".docx"):
                continue
            stem = Path(fn).stem
            if VERSION_RE.search(stem):
                hits.append(Path(root) / fn)
    if len(hits) <= 1:
        return {"skipped": len(hits) == 0, "found": len(hits), "warn": 0, "error": 0}
    warns = 1
    rel = "\n".join(f"    - {p.relative_to(workspace).as_posix()}" for p in sorted(hits))
    findings.append({
        "check": 5, "severity": "warn", "file": workspace.as_posix(), "line": None,
        "msg": f"发现 {len(hits)} 个疑似论文版本文件 (v\\d/副本/最终版/修订版/final/old/backup), "
               f"建议按 workspace_protocol 只保留 main + _archive/ 归档:\n{rel}",
        "excerpt": "",
    })
    return {"found": len(hits), "warn": warns, "error": 0}


# ---------------------------------------------------------------- 审计入口

def _archive_base(workspace: Path, root: Path) -> Path:
    """归档过滤基准目录: 扫描根在工作区内时用工作区, 否则退化为扫描根本身。

    只用**基准相对**目录名匹配 SKIP_DIRS，避免工作区父目录名影响正文发现。
    整条绝对路径的每一段做匹配时，工作区路径里只要有一段叫 tmp/results/state/code…
    (CI 的 /tmp、Windows Temp、自建 temp 根), 工作区下**全部**正文都会被判为已归档,
    collect_body_files 直接抛"未找到正文文件"——静默漏检全部正文。
    """
    try:
        root.relative_to(workspace)
    except ValueError:
        return root
    return workspace


def _body_files(root: Path, base: Path) -> list[Path]:
    """root 下全部 .md/.tex; 归档过滤按 base 相对目录名判定 (base 见 _archive_base)。"""
    return sorted(x for pat in ("*.md", "*.tex")
                  for x in root.rglob(pat) if _not_archived(x, base))


def collect_body_files(workspace: Path, paper: str | None) -> list[Path]:
    if paper:
        p = Path(paper)
        if not p.is_absolute():
            p = workspace / p
        p = p.resolve()
        if not p.exists():
            raise AuditIOError(f"--paper 文件不存在: {p}")
        out = _body_files(p, _archive_base(workspace, p)) if p.is_dir() else [p]
    else:
        base = workspace / "paper_workspace"
        if not base.is_dir():
            raise AuditIOError(f"未找到正文目录: {base} (可用 --workspace 指定, 或 --paper 指定单文件)")
        out = _body_files(base, _archive_base(workspace, base))
    if not out:
        raise AuditIOError("paper_workspace 下未找到 .md/.tex 正文文件")
    return out


def _not_archived(path: Path, base: Path) -> bool:
    """path 是否不在归档目录内: 只看它**相对 base** 的目录段。

    base 之外的路径 (如 --paper 指向工作区外部) 不做归档过滤, 保持可审计。
    """
    try:
        rel = path.relative_to(base)
    except ValueError:
        return True
    return not any(part.lower() in SKIP_DIRS for part in rel.parts)


def run_audit(workspace: Path, paper: str | None) -> dict:
    files = collect_body_files(workspace, paper)
    doc = Doc(files)
    doc.assemble()
    findings: list[dict] = []

    frozen_path = workspace / "state" / "frozen_numbers.json"
    frozen: dict | None = None
    if frozen_path.exists():
        try:
            payload = json.loads(frozen_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AuditIOError(f"frozen_numbers.json 不可读: {exc}")
        frozen = payload if isinstance(payload, dict) else {}

    stats = {
        1: check_numbers(doc, workspace, findings, frozen),
        2: check_abstract_conclusion(doc, findings),
        3: check_figures(doc, findings),
        4: check_symbols(doc, findings),
        5: check_versions(workspace, findings),
    }
    errs = sum(1 for f in findings if f["severity"] == "error")
    warns = sum(1 for f in findings if f["severity"] == "warn")
    return {
        "workspace": workspace.as_posix(),
        "body_files": [x.as_posix() for x in files],
        "frozen_file": frozen_path.as_posix() if frozen is not None else None,
        "stats": stats,
        "findings": findings,
        "error": errs, "warn": warns,
        "exit": 1 if errs else 0,
    }


def to_json(result: dict) -> dict:
    """机器可读版: 结果树去冗余序列化。"""
    checks = []
    for no in (1, 2, 3, 4, 5):
        st = result["stats"][no]
        if st.get("skipped"):
            checks.append({"no": no, "name": CHECK_NAMES[no], "status": "skipped",
                           "reason": st.get("reason", "")})
            continue
        status = ("error" if st.get("error") else "warn" if st.get("warn") else "ok")
        checks.append({
            "no": no, "name": CHECK_NAMES[no], "status": status,
            "error": st.get("error", 0), "warn": st.get("warn", 0),
            "detail": {k: v for k, v in st.items()
                       if k not in ("skipped", "reason", "error", "warn")},
        })
    return {
        "workspace": result["workspace"],
        "body_files": result["body_files"],
        "frozen_file": result["frozen_file"],
        "checks": checks,
        "findings": result["findings"],
        "summary": {"error": result["error"], "warn": result["warn"]},
        "exit_code": result["exit"],
    }


def _print_report(result: dict, report_path: Path | None = None) -> None:
    """人读摘要: 统计 + 失败位置 (文件:行/摘录) + 详细报告路径。

    每个检查最多逐条打印 PRINT_FINDINGS_CAP 处 (完整清单走 --json 或 --report),
    保证默认输出是"能立刻定位的摘要"而不是整份长报告。
    """
    print("=" * 62)
    print("论文一致性审计报告")
    print("=" * 62)
    print(f"工作区: {result['workspace']}")
    print(f"正文   : {len(result['body_files'])} 个文件")
    for f in result["body_files"]:
        print(f"         {f}")
    print()
    for no in (1, 2, 3, 4, 5):
        st = result["stats"][no]
        print(f"[{no}] {CHECK_NAMES[no]}")
        if st.get("skipped"):
            print(f"    - 跳过: {st.get('reason', '')}")
            continue
        if no == 1:
            meta = f"登记 claim {st.get('claims', 0)} 条 · 命中 {st.get('hit', 0)} 处"
        elif no == 2:
            meta = f"摘要 {st.get('abstract_numbers', 0)} 个数字 vs 结论 {st.get('conclusion_numbers', 0)} 个数字"
        elif no == 3:
            meta = f"定义 {st.get('defs', 0)} · 引用 {st.get('refs', 0)}"
        else:
            meta = f"符号表 {st.get('defined', 0)} 个符号" if no == 4 else \
                   f"版本文件 {st.get('found', 0)} 个"
        e, w = st.get("error", 0), st.get("warn", 0)
        print(f"    {meta} -> ❌{e} ⚠️{w}")
        if e == 0 and w == 0:
            print("    ✅ 通过")
    print()
    by_file: dict[str, list] = {}
    for f in result["findings"]:
        by_file.setdefault(f["file"], []).append(f)
    printed: dict[int, int] = {}
    hidden: dict[int, int] = {}
    for file, items in sorted(by_file.items()):
        rows = []
        for it in items:
            no = it["check"]
            if printed.get(no, 0) >= PRINT_FINDINGS_CAP:
                hidden[no] = hidden.get(no, 0) + 1
                continue
            printed[no] = printed.get(no, 0) + 1
            loc = f"行 {it['line']}" if it["line"] is not None else ""
            rows.append(f"  {MARK[it['severity']]} [{CHECK_NAMES[no]}] {loc}: {it['msg']}")
            if it.get("excerpt"):
                rows.append(f"      “{it['excerpt']}”")
        if rows:
            print(f"--- {file} ---")
            for row in rows:
                print(row)
    for no in sorted(hidden):
        print(f"  … [{CHECK_NAMES[no]}] 另有 {hidden[no]} 处未逐条打印 "
              "(完整清单见 --json / --report)")
    print("-" * 62)
    print(f"总计: ❌ {result['error']} 处 | ⚠️ {result['warn']} 处")
    if report_path is not None:
        print(f"详细报告: {report_path}")
    else:
        print("完整清单: --json (机器可读) 或 --report <path> (落盘 JSON)")
    if result["exit"]:
        print("存在 ❌ 级问题 (数字冲突/摘要结论打架/引用断链), 修复后重跑 (exit 1)")
    else:
        print("未检出 ❌ 级问题 (⚠️ 提示项请酌情处理) (exit 0)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="论文一致性审计: 未冻结数字/摘要-结论一致性/图表引用闭环/符号表脱节/版本错乱"
    )
    parser.add_argument("--workspace", default=".", help="工作区目录 (默认 cwd)")
    parser.add_argument("--paper", default=None,
                        help="指定单个正文文件 (默认扫描 paper_workspace/ 下 .md/.tex; "
                             ".pdf 需 pypdf)")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("--report", type=Path, default=None,
                        help="完整报告落盘路径 (人读输出只给摘要与路径)")
    parser.add_argument("--self-test", action="store_true", help="内置合成样例自测")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    if args.self_test:
        return _self_test()

    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        print(f"❌ 工作区不存在: {workspace}")
        return 2
    try:
        result = run_audit(workspace, args.paper)
    except AuditIOError as exc:
        print(f"❌ {exc}")
        return 2
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(to_json(result), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    if args.json:
        print(json.dumps(to_json(result), ensure_ascii=False, indent=2))
    else:
        _print_report(result, args.report.expanduser().resolve()
                      if args.report is not None else None)
    return result["exit"]


# ---------------------------------------------------------------- 自测

_CLEAN_MD = """# 摘要
针对问题一, 18 个板块序列通过复合泊松检验, 全系统日口径预测误差为 0.16。
针对问题二, 碳感知调度使运行成本降低 46%。

# 符号说明
| 符号 | 含义 | 单位 |
|------|------|------|
| $x_i$ | 板块 $i$ 的调度量 | MWh |
| $\\alpha$ | 置信水平 | % |

# 模型建立与求解
目标函数包含决策变量 $x_i$, 置信水平 $\\alpha$ 取 0.95。模型结构如图 1 所示。

图 1：模型整体流程

# 结论
18 个板块序列假设成立, 日口径预测误差为 0.16, 运行成本降低 46%, 与摘要一致。
"""

_DIRTY_MD = """# 摘要
本文单位调度成本为 4368 元/吨, 碳减排量较基准提升 12.5%。
关键技术路线如图 2 所示, 相关参数取值见表 1。

# 符号说明
| 符号 | 含义 | 单位 |
|------|------|------|
| $x_i$ | 板块 $i$ 的调度量 | MWh |
| $\\beta$ | 折算系数 | % |

# 模型建立与求解
模型参数 $\\gamma$ 取 0.9, 经 $\\alpha = 0.95$ 置信校验; 每时段调度总量不超过 1234.5 MWh。
单次求解耗时约 24 小时, 内存峰值 3.2 GB, 未出现数值溢出。

表 1：参数取值范围
图 1：整体技术路线

# 结论
本文单位调度成本为 4638 元/吨, 减排提升 12.5%, 各约束均满足。
"""

_DIRTY_FROZEN = {
    "q2.unit_cost": {"value": 4368, "unit": "元/吨",
                     "source_file": "results/q2.json", "source_sha256": "x"},
    "q2.reduce": {"value": 12.5, "unit": "%"},
    "q3.cap": {"value": 2000, "unit": "MWh"},
}


def _write_ws(tmp: Path, md: str, frozen: dict | None,
              extra_files: dict[str, str] | None = None) -> None:
    (tmp / "paper_workspace").mkdir(parents=True, exist_ok=True)
    (tmp / "paper_workspace" / "main.md").write_text(md, encoding="utf-8")
    if frozen is not None:
        (tmp / "state").mkdir(exist_ok=True)
        (tmp / "state" / "frozen_numbers.json").write_text(
            json.dumps(frozen, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, content in (extra_files or {}).items():
        p = tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def _expect(result: dict, ok: bool, *must: tuple[int, str]) -> list[str]:
    """断言 finding 分类命中; 返回失败描述。"""
    bad: list[str] = []
    have = {(f["check"], f["severity"]) for f in result["findings"]}
    for no, sev in must:
        if (no, sev) not in have:
            bad.append(f"检查 {no}({CHECK_NAMES[no]}) 未检出预期 {MARK[sev]}{sev} 问题")
    if ok and (result["error"] or result["warn"]):
        bad.append(f"干净样例误报: {result['error']} ❌ / {result['warn']} ⚠️")
    return bad


def _self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="consistency_audit_selftest_") as td:
        root = Path(td)
        # 1) 干净样例: 数字一致 + 图表引用闭环 + 符号表齐全
        ws_clean = root / "clean"
        _write_ws(ws_clean, _CLEAN_MD, None)
        try:
            rc = run_audit(ws_clean, None)
        except AuditIOError as exc:
            failures.append(f"干净样例执行失败: {exc}")
            rc = {"error": 99, "warn": 99}
        if rc["error"] == 0 and rc["warn"] == 0:
            print("[自测] ✅ 干净文本 (数字一致/图表闭环/符号齐备) 0 检出, exit 0")
        else:
            failures.append(f"干净文本误报 {rc['error']} ❌ / {rc['warn']} ⚠️")
            print(f"[自测] ❌ 干净文本误报 {rc['error']} ❌ / {rc['warn']} ⚠️")

        # 2) 脏样例: 摘要-结论数字打架 + 引用断链 + 符号表脱节 + 版本错乱
        ws_dirty = root / "dirty"
        _write_ws(ws_dirty, _DIRTY_MD, _DIRTY_FROZEN, extra_files={
            "论文_最终版.docx": "x",
            "摘要_副本.md": "# 副本\n",
        })
        try:
            rc = run_audit(ws_dirty, None)
        except AuditIOError as exc:
            failures.append(f"脏样例执行失败: {exc}")
            rc = {"error": 0, "warn": 0, "findings": []}
        checks = {
            "冻结数字冲突检出 (摘要/结论 4638 元 vs 冻结 4368 元/吨)":
                (1, "error"),
            "正文未登记数字检出 (1234.5 MWh / 24 小时)": (1, "warn"),
            "摘要-结论数字打架检出 (摘要 4368 vs 结论 4638)": (2, "error"),
            "图表引用断链检出 (图 2 未定义)": (3, "error"),
            "定义未引用检出 (图 1 / 表 1)": (3, "warn"),
            "符号表脱节检出 ($\\gamma$/α 未登记)": (4, "warn"),
            "版本错乱检出 (论文_最终版/摘要_副本)": (5, "warn"),
        }
        for label, need in checks.items():
            if (need[0], need[1]) in {(f["check"], f["severity"]) for f in rc["findings"]}:
                print(f"[自测] ✅ {label}")
            else:
                failures.append(f"{label} 未检出")
                print(f"[自测] ❌ {label}")
        if rc.get("error", 0) == 0:
            failures.append("脏样例应 exit 1 (存在 ❌ 问题)")
            print("[自测] ❌ 脏样例未返回 ❌ 问题")
        else:
            print(f"[自测] ✅ 脏样例退出码 = 1 ({rc['error']} ❌ / {rc['warn']} ⚠️)")

    if failures:
        print("[自测] 存在失败 ❌")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("[自测] 全部通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
