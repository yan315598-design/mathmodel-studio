"""export_final_docx.py — md 真源 → docx 终稿导出 (v2.9.0 新增)

与 export_docx.py (审阅件, 单向, 保持不变) 是两条不同定位的链: 本脚本产**终稿**
docx, 供人在 Word 里只改呈现层 (白名单: 措辞/标点/间距/图位置/题注文字; 禁区:
任何数字/公式/表值/结论), 改后走 docx_to_pdf.py + docx_number_recheck.py 终检。
协议见 references/docx_final_channel.md; 入口条件是 stage 8 退出门禁全过且
数字已冻结 (md 此后冻结, 修订只发生在 docx 呈现层或回退重走 md 链)。

功能:
1. 输入: --workspace + --files 显式拼接顺序 (同 export_docx); 缺省自动发现升级:
   workspace 下有 NN_*.md 数字前缀系列时按文件名自然排序拼接 (01_abstract 在
   10_appendix 前), 否则回退 export_docx 的 main.md / abstract_draft+sections 约定。
2. 编号注入 (pandoc 之前, 对拼接后的 md 顺序扫描): 图 ![alt](path) alt 加
   "图 N " 前缀、表 ": caption" 行加 "表 N " 前缀, N 取文档序号 (已有编号项
   同样占号, 幂等: 已有编号恰等于文档序号则跳过; 不一致则报错退出, 不静默
   重号); 无题注管道表收集警告 (cn_spec §6: 终稿所有表必须有题注);
   代码围栏 (```/~~~, 变长) 内容不注入。
3. 章节编号: pandoc --number-sections --shift-heading-level-by=-1 (本仓库 md
   约定 ##=章、###=节); 摘要/参考文献/附录标题豁免编号 (标题文末加 pandoc
   "{-}", 含 md 自带 "## 摘要"); 09_references.md 的 \\bibitem 行转 "[N] "
   编号列表; 参考文献与附录文件无章标题时合成 "## 参考文献 {-}" / "## 附录 {-}"。
4. 标题块与分页 (pandoc 之后 python-docx 后处理): 文档开头插入论文标题 (黑体
   三号居中)、题号+参赛队号行 (居中)、空行; "摘　要" 标题段 (黑体居中不编号)
   插在摘要正文前 (首段已是标题时不重复插); 正文第一个非摘要一级标题前设分页。
5. 样式: 默认挂 --reference-doc templates/docx/reference.docx (W2 产物,
   build_reference_docx.py 生成); 用户可覆盖。
6. 图片: --resource-path 沿用 export_docx 逻辑 (源文件父目录 + workspace
   根/父目录); md 里 {width=95%} 等属性 pandoc 直读。
7. 输出 submission/<competition>_final_<YYYYMMDD_HHMMSS>.docx (v3.1.0 起**秒级**
   时间戳; 真实导出前用 O_EXCL 独占占位, 同秒重复导出/并发导出自动改名 _2/_3…
   ——先到先得, 谁都不覆盖谁的产物); 打印注入统计 (图 N 张/表 N 张/无题注表警告数)。
8. md 卫生 lint (v3.1.0, pandoc 前; 逐源文件在读入原貌上执行——报告行号即
   源文件行号, 不受 preprocess/\\tag 归一/拼接的行数变换影响; 代码围栏内容一律
   豁免): 自动修复并打印摘要——①标题行上一行非空且非标题 → 补空行; ②": 题注"
   行与紧随表格/图片之间缺空行 → 补; 报错拦截 (exit 2, 列 文件:行)——③TAB
   控制字符、⑤单段落内 $ 计数奇数 (行内 code span 与 \\$ 转义剔除后再计数);
   警告不阻断——④单元格 >28 字符且无空格/零宽空格 (U+200B) 的长 token (提示
   在 /、_ 后插零宽断行点)。修复只写入本次导出的内存文本, 不回写源文件。
9. 呈现层后处理 (v3.1.0, 导出落盘后同进程执行, --presentation 默认开,
   --no-presentation 关): 调 docx_presentation_postprocess.process() 七步
   (Step A 数学字体政策 / B 编号右顶格 (表宽按所在节版心) / C 数据表三线 /
   D 自适应+居中+行禁拆 / E 单元格排版 / E2 单元格对齐 (长文本列左对齐) /
   F 图与图注同页 keepNext), 打印各 Step 统计; workspace 透传给后处理, 数学
   字体政策从 decision_log 读 (未登记则保持输入 + 警告, 不替用户拍板);
   处理前自动备份 <名>.pre_pp.bak.docx。
10. md 源解析 (围栏/标题/\\bibitem/有序稿件发现) 与引用审计 (ref_order_audit.py)
   共用 scripts/md_source.py, 保证"审计扫的 md 与忽略的区段"与"本次导出的"同源。

用法:
    python scripts/export_final_docx.py --workspace paper_workspace \\
        --files 01_abstract.md 02_problem_restate.md ... 10_appendix.md \\
        --title "论文标题"

退出码: 0 成功导出 (或 dry-run 预览); 2 输入错误 (workspace/文件缺失/
reference-doc 缺失/competition 非法/输出目录不可写/md 卫生 lint 致命项) 或
pandoc/python-docx 不可用/执行失败。
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 复用审阅件导出的 pandoc 调用约定与工具函数 (只读 import, 不改其行为)
from export_docx import (PANDOC_FROM, PANDOC_INSTALL_HINT, build_resource_dirs,
                         discover_md_files, has_pandoc, is_safe_filename,
                         natural_key, resolve_competition)

# 共享 md 源解析 (有序稿件发现/围栏状态机/标题/bibitem) 的单一真源: 与
# ref_order_audit.py (引用审计) 同口径, 避免"审计扫的"与"导出的"两套规则
# (见 scripts/md_source.py 模块 docstring)。FenceTracker / iter_lines_outside_fences
# 由本模块转出 (原实现已迁 md_source), 旧 import 路径保持可用。
from md_source import (FenceTracker, HEADING_RE, INLINE_CODE_RE,
                       allocate_reference_numbers, bibitem_payload,
                       discover_ordered_sources, file_kind,
                       has_heading_attrs, has_heading_outside_fences,
                       is_bibitem_line, iter_lines_outside_fences,
                       parse_heading, reference_section_spans,
                       scan_reference_entries)

# 根路径唯一真源 (D1): 两份安装并存 (.codex 与 .zcode 符号链接) 时按调用路径推导,
# 不写死安装位置; 见 scripts/skill_paths.py
from skill_paths import describe as describe_skill_root
from skill_paths import skill_root

# ---- 编号注入的正则口径 ----
FIGURE_MD_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
FIG_NUMBERED_RE = re.compile(r"^图\s*(\d+)")  # 捕获已有编号, 与文档序号比对 (P1-1)
TABLE_CAPTION_RE = re.compile(r"^:\s+(.+?)\s*$")
TAB_NUMBERED_RE = re.compile(r"^表\s*(\d+)")
# 管道表分隔行: 仅由 | : - 空白构成且至少一个 - 与一个 | (如 |---|---|、|:--|--:|)
PIPE_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(?:\|\s*:?-{1,}:?\s*)*\|?\s*$")
HEADING_LINE_RE = HEADING_RE  # 兼容别名: 标题行正则唯一真源在 md_source
UNNUMBERED_MARK = " {-}"


class InjectStats:
    """编号注入统计: 新注入数 / 已有编号且与文档序号一致而跳过数 / 无题注表。

    fig_seq / tab_seq 是"下一个文档序号"——已有编号项同样推进文档序号,
    注入器输出与 LaTeX 自动编号在文档序上严格一致 (复审 P1-1)。
    """

    def __init__(self):
        self.n_figures = 0
        self.n_tables = 0
        self.n_figures_prefilled = 0
        self.n_tables_prefilled = 0
        self.fig_seq = 1
        self.tab_seq = 1
        self.uncaptioned_tables = []  # list[(lineno_1based, header_preview)]


class NumberingConflict(ValueError):
    """md 里已有的 图N/表N 编号与文档出现顺序不一致 (会造成终稿重号)。"""


def discover_final_files(workspace: Path) -> list:
    """终稿自动发现: NN_*.md 数字前缀系列按自然排序; 无系列回退审阅件约定。

    实现已迁 md_source.discover_ordered_sources (v3.1.0): 同一入口给引用审计
    (ref_order_audit --workspace) 复用, 保证"审计扫的 md"就是"本次导出拼的 md"。
    升级动机 (v2.9.0): 终稿工作区按 01_abstract..10_appendix 分文件成稿,
    审阅件的 main.md/sections/ 约定覆盖不到这一形态。
    """
    return discover_ordered_sources(workspace)[0]


def convert_bibitems(text: str, spans=None) -> tuple:
    """参考文献 md 的 \\bibitem{key} 行转 "[N] " 编号列表, 返回 (新文本, 条数, 警告)。

    09_references.md 按真源约定存 \\bibitem (tex 链直通 thebibliography);
    docx 链没有该环境, 不转换会在终稿里露出原始 LaTeX 命令。编号与正文 [1,4] 式
    引用天然对齐 (真源引用即按此序手写)。
    **编号分配走 md_source.allocate_reference_numbers** (与引用审计同一规则):
    文件里已有显式 "[1] Alpha" 时, \\bibitem 条目取下一个未被占用的号 (2), 不再
    两形态各编一套造成 "[1] Alpha/[1] Beta" 重号 (bug-reviewer P1)。
    只改写 bibitem 行, 显式 [N] 行一字不动; 代码围栏内不转换。
    spans: 只处理这些 (起, 止) 闭区间内的条目 —— 正文文件 (main.md 单文件稿) 内嵌
    "## 参考文献" 节时, 由 md_source.reference_section_spans 给出该节区间, 只在该节
    范围内转换与分配编号 (不整文件乱转); None = 整文件 (references 角色文件既有行为)。
    返回的警告 (显式编号重复等) 由调用方打印, 不静默吞。
    """
    entries = scan_reference_entries(text)
    if spans is not None:
        entries = [e for e in entries if any(a <= e[0] <= b for a, b in spans)]
    if not entries:
        return text, 0, []
    numbers, warnings = allocate_reference_numbers(entries)
    lines = text.split("\n")
    n_bib = 0
    for (idx, _lineno, kind, _num), num in zip(entries, numbers):
        if kind != "bibitem":
            continue
        n_bib += 1
        lines[idx] = f"[{num}] " + bibitem_payload(lines[idx])
    return "\n".join(lines), n_bib, warnings


def _convert_in_refs_sections(path: Path, text: str) -> tuple:
    """非 references 文件: 只对显式 "## 参考文献" 节内的条目做 bibitem→[N]。

    返回 (新文本, 转换条数, 警告列表)。节外的 \\bibitem **一律明确告警未转换**
    (无论文件里有没有该节), 与审计的 bibitem_outside_refs ⚠️ 对应——两端都不装作
    "已支持"; 节外行一字不动 (不整文件乱转)。
    """
    spans = reference_section_spans(text)
    warnings = []
    n_bib = 0
    if spans:
        text, n_bib, warns = convert_bibitems(text, spans=spans)
        warnings.extend(warns)
    outside = [idx + 1 for idx, line, fenced in iter_lines_outside_fences(text)
               if not fenced and is_bibitem_line(line)
               and not any(a <= idx <= b for a, b in spans)]
    if outside:
        shown = ", ".join(str(n) for n in outside[:8])
        warnings.append(
            f"{len(outside)} 行 \\bibitem 不在任何 \"## 参考文献\" 节内 (行 {shown}"
            f"{' …' if len(outside) > 8 else ''}), **未转换**: 请给文献表加 "
            f"\"## 参考文献\" 标题或在 references 角色文件里维护")
    return text, n_bib, warnings


def mark_unnumbered_headings(text: str, all_headings: bool,
                             only_if_contains=()) -> tuple:
    """给标题行文末加 pandoc "{-}" (不编号), 返回 (新文本, 标记数)。

    all_headings=True 标记文件内全部标题 (参考文献/附录文件整章豁免编号);
    否则只标记标题文本含 only_if_contains 任一关键词的标题 (正文里的
    "摘要"/"附录"/"参考文献" 章标题同样豁免, 与 CUMCM 不编号章惯例一致;
    关键词匹配忽略标题中的空格, 兼容 "摘 要" 写法)。
    标题行解析走 md_source.parse_heading (围栏与标题口径两处共用)。
    """
    lines = text.split("\n")
    marked = 0
    for idx, line, fenced in iter_lines_outside_fences(text):
        if fenced:
            continue
        parsed = parse_heading(line)
        if parsed is None:
            continue
        title = parsed[1]
        if has_heading_attrs(title):  # 已带属性 (含 {-}) 则不动
            continue
        title_cmp = re.sub(r"[\s\u3000]", "", title)
        if not all_headings and not any(w in title_cmp for w in only_if_contains):
            continue
        lines[idx] = line.rstrip() + UNNUMBERED_MARK
        marked += 1
    return "\n".join(lines), marked


def preprocess_file(path: Path, text: str) -> tuple:
    """单文件预处理: \\bibitem 转换 + 参考文献附录标题合成与不编号标记。

    返回 (新文本, 说明行列表): 说明行进导出报告, 让"合成了哪些章标题"可审计。
    """
    notes = []
    kind = file_kind(path)
    if kind == "references":
        # P2 修复点: 无标题的 references 文件在导出侧本来就会合成 "## 参考文献"
        # (下方 has_heading_outside_fences 分支), 审计侧现按同一 file_kind 认定
        # "整文件即文献表" —— 两端一致, 且合成标题只加在前面, **不改原行号**。
        text, n_bib, bib_warns = convert_bibitems(text)
        if n_bib:
            notes.append(f"{path.name}: {n_bib} 条 \\bibitem 转 [N] 编号列表")
        for w in bib_warns:
            notes.append(f"[WARN] {path.name}: {w}")
        if not has_heading_outside_fences(text):
            text = "## 参考文献" + UNNUMBERED_MARK + "\n\n" + text.lstrip("\n")
            notes.append(f"{path.name}: 合成章标题 \"参考文献\" (不编号)")
    elif kind == "appendix":
        if not has_heading_outside_fences(text):
            text = "## 附录" + UNNUMBERED_MARK + "\n\n" + text.lstrip("\n")
            notes.append(f"{path.name}: 合成章标题 \"附录\" (不编号)")
        text, n_bib, bib_warns = _convert_in_refs_sections(path, text)
        for w in bib_warns:
            notes.append(f"[WARN] {path.name}: {w}")
    else:
        # main.md 单文件稿: 正文里显式写出的 "## 参考文献" 节也在该节范围内转换
        # (区间口径与审计 in_refs 同源, 不整文件乱转)
        text, n_bib, bib_warns = _convert_in_refs_sections(path, text)
        if n_bib:
            notes.append(f"{path.name}: {n_bib} 条 \\bibitem 转 [N] 编号列表 "
                         f"(正文内嵌参考文献节)")
        for w in bib_warns:
            notes.append(f"[WARN] {path.name}: {w}")
    if kind == "references" or kind == "appendix":
        text, n_mark = mark_unnumbered_headings(text, all_headings=True)
    else:
        # 摘要/附录/参考文献章均不编号 (CUMCM 惯例; md 自带 "## 摘要" 时同样豁免)
        text, n_mark = mark_unnumbered_headings(
            text, all_headings=False,
            only_if_contains=("摘要", "附录", "参考文献"))
    if n_mark:
        notes.append(f"{path.name}: {n_mark} 个标题标记不编号 {{-}}")
    return text, notes


def _is_pipe_separator(line: str) -> bool:
    return "|" in line and PIPE_TABLE_SEP_RE.match(line) is not None


def _find_caption_above(lines: list, header_idx: int):
    """从表头行向上越过空行找 ": caption" 题注行; 无题注返回 None。

    pandoc 口径 (实测): 题注块与表之间只隔空行时题注挂接表格, 隔了其他内容
    则不挂接——本函数与该口径一致。
    """
    k = header_idx - 1
    while k >= 0 and not lines[k].strip():
        k -= 1
    if k >= 0 and TABLE_CAPTION_RE.match(lines[k]):
        return k
    return None


def inject_numbering(text: str) -> tuple:
    """拼接后 md 的图/表编号注入, 返回 (新文本, InjectStats)。

    图: ![alt](path) (alt 非空) 按出现顺序改写 alt 为 "图 N 原alt";
    表: 管道表 (以分隔行判定, 每表恰一行) 的上方题注行改写为 ": 表 N 原文";
    N 取**文档序号** (已有编号项同样占号), 与 LaTeX 自动编号口径一致;
    已有编号恰等于文档序号则跳过改写 (幂等, 重跑不重复加前缀);
    已有编号与文档序号不一致时抛 NumberingConflict——不静默重号 (复审 P1-1)。
    无题注表收警告不打号 (与 LaTeX 链一致: 无题注 longtable 不占表号)。
    代码围栏 (```/~~~, 变长) 内容不注入 (复审 P2-7)。
    """
    lines = text.split("\n")
    stats = InjectStats()

    def _fig_sub(m):
        alt = m.group(1).strip()
        if not alt:
            return m.group(0)
        existed = FIG_NUMBERED_RE.match(alt)
        if existed:
            if int(existed.group(1)) != stats.fig_seq:
                raise NumberingConflict(
                    f"图题注已有编号 {existed.group(1)} 与文档出现顺序 "
                    f"{stats.fig_seq} 不一致 (alt={alt[:30]!r}); "
                    f"请修正 md 源编号后重试, 不静默重号")
            stats.n_figures_prefilled += 1
        else:
            stats.n_figures += 1
            alt = f"图 {stats.fig_seq} {alt}"
        stats.fig_seq += 1
        return f"![{alt}]({m.group(2)})"

    for i, line, fenced in iter_lines_outside_fences(text):
        if fenced:
            continue
        lines[i] = FIGURE_MD_RE.sub(_fig_sub, line)

        # 管道表判定在分隔行: 上一行须是含 | 的表头行
        if _is_pipe_separator(line) and i > 0 and "|" in lines[i - 1] \
                and lines[i - 1].strip() and not _is_pipe_separator(lines[i - 1]):
            cap_idx = _find_caption_above(lines, i - 1)
            if cap_idx is None:
                stats.uncaptioned_tables.append(
                    (i + 1, lines[i - 1].strip()[:40]))
                continue  # 无题注表不占文档序号 (不打印表号)
            cap_text = TABLE_CAPTION_RE.match(lines[cap_idx]).group(1).strip()
            existed = TAB_NUMBERED_RE.match(cap_text)
            if existed:
                if int(existed.group(1)) != stats.tab_seq:
                    raise NumberingConflict(
                        f"表题注已有编号 {existed.group(1)} 与文档出现顺序 "
                        f"{stats.tab_seq} 不一致 (caption={cap_text[:30]!r}); "
                        f"请修正 md 源编号后重试, 不静默重号")
                stats.n_tables_prefilled += 1
            else:
                stats.n_tables += 1
                lines[cap_idx] = f": 表 {stats.tab_seq} {cap_text}"
            stats.tab_seq += 1
    return "\n".join(lines), stats


# ---- md 卫生 lint (v3.1.0, A2): pandoc 前最后关口 ----
# 实测事故驱动: "## 问题二" 缺空行被印成正文且整章编号错位; 题注-表格缺空行
# 致整表崩坏; TAB 混入; 单段落 $ 奇数让 pandoc 把公式吞进段落。

MD_LINT_LONG_TOKEN_CHARS = 28  # 单元格长 token 阈值 (字符数, 不含字节)
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")  # CJK 自身可自然断行, 豁免
# 行内 code span (同长反引号闭合, 内容可跨行): 其内的 $/反斜杠不参与公式定界计数
CODE_SPAN_RE = INLINE_CODE_RE  # 兼容别名: 行内 code span 正则唯一真源在 md_source


def _count_math_dollars(para_text: str) -> int:
    """段内数学定界 $ 计数 (H3 修复): 先剔行内 code span (反引号), 再抹掉被
    奇数个反斜杠转义的字面 \\$ ("Price \\$5." 不计; "\\\\$x" 中 \\\\ 是字面
    反斜杠、$ 未被转义仍计), 其余 $ 计数。"""
    text = CODE_SPAN_RE.sub("", para_text)

    def _drop(m):
        return m.group(0)[:-1] if len(m.group(1)) % 2 else m.group(0)

    return re.sub(r"(\\+)\$", _drop, text).count("$")


class MdLintFatal(ValueError):
    """md 卫生 lint 致命问题 (TAB 控制字符 / 单段落 $ 计数奇数)。

    .problems 为 "文件:行 描述" 列表; 导出链以 exit 2 拦截——这两类一律人工
    确认, 不自动改 (TAB 语义不明: 缩进? 对齐? 表格?)。
    """

    def __init__(self, problems: list):
        super().__init__("; ".join(problems))
        self.problems = problems


def lint_md(text: str, loc=None) -> tuple:
    """对拼接后 md 做卫生检查与自动修复, 返回 (修复后文本, fixes, warnings)。

    自动修复 (fixes 为摘要行; 只改喂给 pandoc 的拼接 md, 不回写源文件):
      ① 标题行上一行非空且非标题行 → 其上补空行 (否则 pandoc 把标题印成正文,
         且该章编号整体错位); 连续标题行之间不补 (合法写法)。
      ② ": 题注" 行与紧随的表格/图片行之间无空行 → 补空行 (否则题注挂接失败,
         整表崩坏)。
    报错 (抛 MdLintFatal, 调用方 exit 2):
      ③ 行内含 TAB 控制字符;
      ⑤ 单个段落内 $ 计数为奇数 (公式定界符未配对; 围栏行与空行为段落边界;
        行内 code span 与 \\$ 转义剔除后再计数, 不误杀字面美元/代码示例)。
    警告 (warnings, 不阻断):
      ④ 表格单元格内 >28 字符且不含空格/零宽空格 (U+200B)/CJK 的 token——
         Word 无法在长路径/文件名内断行, 提示在 /、_ 等边界后插零宽断行点
         (cn_presentation_spec §6.2, B5③)。
    代码围栏 (```/~~~, 变长) 内容与边界行一律豁免 (与编号注入共用围栏口径)。

    loc: 传入拼接 md 的 1 基行号、返回 "文件:行" 定位串的可调用对象
    (缺省 "拼接md:N"); 报告行号均取修复前的原始行号, 与用户 md 一致。
    """
    if loc is None:
        loc = lambda n: f"拼接md:{n}"  # noqa: E731
    lines = text.split("\n")
    fenced = [f for _, _, f in iter_lines_outside_fences(text)]

    fixes: list = []
    warnings: list = []
    fatals: list = []
    insert_before: set = set()  # 原始行号口径 (0 基): 在该行前插空行

    for i, line in enumerate(lines):
        if fenced[i]:
            continue
        # ① 标题行上一行非空且非标题 → 补空行
        if HEADING_LINE_RE.match(line) and i > 0 \
                and lines[i - 1].strip() \
                and not HEADING_LINE_RE.match(lines[i - 1]):
            insert_before.add(i)
            fixes.append(f"{loc(i + 1)} 标题行上一行非空且非标题, 已自动补空行")
        # ② 题注行与表格/图片之间无空行 → 补空行
        if TABLE_CAPTION_RE.match(line) and i + 1 < len(lines) \
                and lines[i + 1].strip() and not fenced[i + 1] \
                and (lines[i + 1].lstrip().startswith("|")
                     or lines[i + 1].lstrip().startswith("![")):
            insert_before.add(i + 1)
            fixes.append(f"{loc(i + 2)} 题注行与表格/图片之间缺空行, 已自动补")
        # ③ TAB 控制字符 (人工确认, 不自动改)
        if "\t" in line:
            fatals.append(f"{loc(i + 1)} 行内含 TAB 控制字符, "
                          f"请改空格/语法缩进后重试 (不自动改)")
        # ④ 表格单元格长 token 无断行点
        if line.lstrip().startswith("|"):
            for cell in line.strip().strip("|").split("|"):
                for token in cell.split():
                    if len(token) > MD_LINT_LONG_TOKEN_CHARS \
                            and "\u200b" not in token \
                            and not CJK_RE.search(token):
                        preview = token[:40] + ("…" if len(token) > 40 else "")
                        warnings.append(
                            f"{loc(i + 1)} 表格单元格长 token ({len(token)} 字符) "
                            f"无断行点: {preview}; 建议在 /、_ 等边界后插零宽空格 "
                            f"U+200B (§6.2, 防 Word 硬折)")

    # ⑤ 单段落 $ 计数奇数 (围栏行不参与段落; 空行/围栏为段落边界; H3: 行内
    # code span 与 \$ 转义剔除后再计数)
    para_start, para_lines = None, []

    def _flush():
        if para_start is not None:
            n = _count_math_dollars("\n".join(para_lines))
            if n % 2:
                fatals.append(f"{loc(para_start + 1)} 段落内 $ 计数 {n} "
                              f"为奇数 (公式定界符未配对), 请核对公式边界")

    for i, line in enumerate(lines):
        if fenced[i] or not line.strip():
            _flush()
            para_start, para_lines = None, []
            continue
        if para_start is None:
            para_start = i
        para_lines.append(line)
    _flush()

    if fatals:
        raise MdLintFatal(fatals)

    for i in sorted(insert_before, reverse=True):  # 倒序插入, 前方行号不动
        lines.insert(i, "")
    return "\n".join(lines), fixes, warnings


def normalize_md_tag(merged: str) -> str:
    """\\tag{N} 预归一为 \\qquad (N) (与 export_docx 同口径): pandoc 数学解析器
    会吞掉 \\tag 的反斜杠导致 docx 里编号直接消失 (实测)。"""
    return re.sub(
        r"\$\$(.+?)\\tag\s*\{(\d+)\}\s*\$\$",
        lambda m: f"$${m.group(1).strip()} \\qquad ({m.group(2)})$$",
        merged, flags=re.DOTALL)


def build_pandoc_cmd(tmp_md: Path, out_docx: Path, resource_dirs: list,
                     reference_doc, number_sections: bool = True) -> list:
    """组装终稿 pandoc 命令行 (dry-run 与真实执行共用, 打印的命令即真实命令)。"""
    cmd = ["pandoc", str(tmp_md), "-f", PANDOC_FROM]
    for d in resource_dirs:
        cmd += ["--resource-path", str(d)]
    if number_sections:
        cmd += ["--number-sections", "--shift-heading-level-by=-1"]
    if reference_doc is not None:
        cmd += ["--reference-doc", str(reference_doc)]
    cmd += ["-o", str(out_docx)]
    return cmd


def read_decision_log(workspace: Path) -> dict:
    """读 <workspace>/../state/decision_log.json; 读不到返回空 dict (静默回退)。"""
    log_path = workspace.parent / "state" / "decision_log.json"
    try:
        data = json.loads(log_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def resolve_paper_meta(title_arg, problem_no_arg, team_no_arg,
                       workspace: Path) -> dict:
    """终稿标题块元数据: CLI > decision_log > 占位。返回 title/problem_no/team_no。"""
    log = read_decision_log(workspace)
    meta = log.get("problem_meta") if isinstance(log.get("problem_meta"), dict) else {}
    title = title_arg or meta.get("title")
    problem_no = problem_no_arg or meta.get("letter")
    if not problem_no:
        raw = str(log.get("problem") or "")
        m = re.search(r"([A-Za-z])\s*$", raw)
        problem_no = m.group(1).upper() if m else None
    team_no = team_no_arg or log.get("team_no") or None
    return {"title": title, "problem_no": problem_no, "team_no": team_no}


# ---- 输出路径独占占位 (秒级时间戳 + 同秒/并发不覆盖) ----

def reserve_output_path(out_dir: Path, stem: str, suffix: str = ".docx",
                        max_tries: int = 100) -> Path:
    """在已存在的 out_dir 下为 <stem><suffix> 原子占位, 返回本次专属路径。

    v3.1.0: 时间戳精确到秒后同秒撞名概率仍在 (脚本连跑 / 两人同时导出), 故用
    `O_CREAT|O_EXCL` 原子创建占位文件 (Windows 与 POSIX 同语义): 撞名则把后缀
    改成 _2/_3… 重试——先到先得, 后到的换名, 任何一方都不会覆盖对方产物
    (原实现是"同分钟直接 exit 2", 秒级下既误伤连跑又挡不住并发)。
    返回的空占位文件由调用方覆写 (pandoc -o 覆盖自己的占位); 后续步骤失败时用
    cleanup_reserved() 撤掉, 不留 0 字节 docx。
    占位文件创建失败 (目录不可写等) 抛 OSError, 由调用方统一报错退出。
    """
    for i in range(1, max_tries + 1):
        name = f"{stem}{suffix}" if i == 1 else f"{stem}_{i}{suffix}"
        cand = out_dir / name
        try:
            fd = os.open(cand, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        except OSError as e:
            raise OSError(f"无法在 {out_dir} 创建输出文件 {name}: {e}") from e
        os.close(fd)
        return cand
    raise OSError(f"{out_dir} 下 {stem}{suffix} 及 _2.._{max_tries} 后缀全被占用, "
                  f"请换 --out-dir")


def cleanup_reserved(path: Path) -> None:
    """撤掉本次独占占位留下的**空**文件 (pandoc 没落盘时不留 0 字节 docx)。

    已有内容的文件不动 (那是 pandoc 的产物, 后续步骤失败时保留并提示重跑);
    清理失败只忽略——不覆盖原始错误信息。
    """
    try:
        p = Path(path)
        if p.is_file() and p.stat().st_size == 0:
            p.unlink()
    except OSError:
        pass


# ---- python-docx 后处理 (懒加载: dry-run 与无 python-docx 环境不依赖它) ----

def _set_run_font(run, east_asian: str, size_pt: float, bold: bool) -> None:
    """run 直写中英文字体/字号/加粗 (font.name 只写 ascii+hAnsi, eastAsia 补 XML)。"""
    from docx.oxml.ns import qn
    from docx.shared import Pt
    run.font.name = east_asian
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    rpr = run._r.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:eastAsia"), east_asian)


def _clear_first_line_indent(paragraph) -> None:
    """直写 w:ind firstLine=0 + firstLineChars=0: Normal 样式的 2 字符缩进会经
    firstLineChars 生效, 只清 firstLine 压不住 (Word 字符缩进优先于缇缩进)。"""
    from docx.oxml.ns import qn
    ppr = paragraph._p.get_or_add_pPr()
    ind = ppr.find(qn("w:ind"))
    if ind is None:
        ind = ppr.makeelement(qn("w:ind"), {})
        ppr.append(ind)
    ind.set(qn("w:firstLine"), "0")
    ind.set(qn("w:firstLineChars"), "0")


def postprocess_docx(out_path: Path, meta: dict) -> list:
    """标题块 + 摘要标题 + 分页 (就地改写 out_path), 返回插入说明行。"""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    doc = Document(str(out_path))
    notes = []
    paras = doc.paragraphs
    if not paras:
        return ["[WARN] docx 无正文段落, 跳过标题块后处理"]
    anchor = paras[0]

    def _insert(text, east_asian, size_pt, bold, align, space_after_pt=None):
        p = anchor.insert_paragraph_before("")
        p.alignment = align
        _clear_first_line_indent(p)
        if space_after_pt is not None:
            p.paragraph_format.space_after = Pt(space_after_pt)
        if text:
            _set_run_font(p.add_run(text), east_asian, size_pt, bold)
        return p

    # 标题块: 论文标题 (黑体三号居中) / 题号+队号行 (四号居中) / 空行
    title = meta.get("title") or "（论文标题待定）"
    if not meta.get("title"):
        notes.append("[WARN] 未提供 --title 且 decision_log 无标题, 标题块用占位文本")
    _insert(title, "黑体", 16, True, WD_ALIGN_PARAGRAPH.CENTER, space_after_pt=6)
    parts = []
    if meta.get("problem_no"):
        parts.append(f"题号：{meta['problem_no']}")
    if meta.get("team_no"):
        parts.append(f"参赛队号：{meta['team_no']}")
    else:
        parts.append("参赛队号：＿＿＿＿＿＿")  # 队号由报名系统分配, 留手填下划线
    _insert("　　".join(parts), "宋体", 14, False, WD_ALIGN_PARAGRAPH.CENTER,
            space_after_pt=6)
    _insert("", "宋体", 12, False, WD_ALIGN_PARAGRAPH.CENTER)

    # "摘　要" 标题段: 仅当首个正文段不是标题 (01_abstract 无标题块约定) 时插入
    if not paras[0].style.name.startswith("Heading"):
        _insert("摘　要", "黑体", 16, True, WD_ALIGN_PARAGRAPH.CENTER,
                space_after_pt=12)
        notes.append("已插入标题块 + \"摘　要\" 标题段")
    else:
        notes.append("已插入标题块; 首段已是标题, 未重复插 \"摘　要\"")

    # 正文第一个**非摘要**一级标题前分页: md 自带 "## 摘要" 标题时, 分页若落在
    # 摘要前会把标题块单独成页 (复审 P2-8), 故跳过摘要标题、定位第一个正文章
    for p in doc.paragraphs:
        if p.style.name == "Heading 1":
            if "摘要" in p.text.replace(" ", "").replace("\u3000", ""):
                continue
            p.paragraph_format.page_break_before = True
            notes.append(f"正文第一章 \"{p.text.split(chr(9))[-1][:20]}\" 前已设分页")
            break

    doc.save(str(out_path))
    return notes


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台中文兜底
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    script_root = skill_root(__file__)
    print(describe_skill_root(__file__))  # V0 日志: 当前使用的安装根 (D1)
    parser = argparse.ArgumentParser(
        description="md 真源 → docx 终稿导出 (v2.9.0); 冻结后专用, 人改只限呈现层, "
                    "协议见 references/docx_final_channel.md")
    parser.add_argument("--workspace", type=Path, default=Path("paper_workspace"),
                        help="md 真源目录 (默认 paper_workspace)")
    parser.add_argument("--out-dir", type=Path, default=Path("submission"),
                        help="输出目录 (默认 submission, 不存在则创建)")
    parser.add_argument("--competition", default=None,
                        help="输出文件名前缀 (须为安全文件名); 缺省读 "
                             "<workspace>/../state/decision_log.json 的 competition "
                             "字段, 再缺省用 paper")
    parser.add_argument("--files", nargs="+", metavar="MD", default=None,
                        help="显式指定 md 文件列表, 按给定顺序拼接 (相对路径按 "
                             "workspace 解析); 缺省自动发现 (NN_*.md 系列优先)")
    parser.add_argument("--reference-doc", type=Path, default=None,
                        help="pandoc --reference-doc 样式基准 docx; 缺省用 "
                             "<skill>/templates/docx/reference.docx")
    parser.add_argument("--title", default=None,
                        help="论文标题 (标题块用); 缺省读 decision_log.problem_meta.title")
    parser.add_argument("--problem-no", default=None,
                        help="题号 (如 A); 缺省读 decision_log.problem_meta.letter")
    parser.add_argument("--team-no", default=None,
                        help="参赛队号; 缺省留手填下划线")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印将拼接的文件、注入统计与 pandoc 命令, 不产 docx "
                             "(无需 pandoc/python-docx)")
    parser.add_argument("--presentation", dest="presentation",
                        action="store_true", default=True,
                        help="导出落盘后同进程执行呈现层后处理 (公式正体/编号右顶格/"
                             "表格三线/自适应居中行禁拆/单元格排版, 默认开)")
    parser.add_argument("--no-presentation", dest="presentation",
                        action="store_false",
                        help="关闭呈现层后处理 (只导出 pandoc 原始呈现; 一般仅调试用)")
    args = parser.parse_args(argv)

    workspace = args.workspace
    if not workspace.is_dir():
        print(f"[FAIL] workspace {workspace} 不存在")
        return 2

    # 拼接清单: --files 显式优先 (同 export_docx 语义), 否则终稿自动发现
    if args.files:
        md_files = []
        for raw in args.files:
            p = Path(raw)
            if not p.is_absolute():
                p = workspace / p
            md_files.append(p)
    else:
        md_files = discover_final_files(workspace)
    missing = [str(p) for p in md_files if not p.is_file()]
    if missing:
        print(f"[FAIL] 以下 md 文件不存在: {missing}")
        return 2
    if not md_files:
        print(f"[FAIL] {workspace} 下未发现任何 md (NN_*.md 系列 / main.md / "
              f"abstract_draft.md + sections/*.md 均无); 或用 --files 显式指定")
        return 2

    # 样式基准: 显式指定必须存在; 缺省路径缺失降级告警 (pandoc 默认样式仍可导出)
    default_ref = script_root / "templates" / "docx" / "reference.docx"
    if args.reference_doc is not None:
        if not args.reference_doc.is_file():
            print(f"[FAIL] --reference-doc 指定的 {args.reference_doc} 不存在")
            return 2
        reference_doc = args.reference_doc
    elif default_ref.is_file():
        reference_doc = default_ref
    else:
        reference_doc = None
        print(f"[WARN] 缺省样式基准 {default_ref} 不存在, 本次用 pandoc 默认样式; "
              f"可运行 templates/docx/build_reference_docx.py 再生成")

    competition = resolve_competition(args.competition, workspace)
    if args.competition is not None and not is_safe_filename(competition):
        print(f"[FAIL] --competition {args.competition!r} 不是安全文件名 "
              f"(须非空、不含 / \\ : * ? \" < > | 与控制字符、非 Windows 保留名、非纯点)")
        return 2

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # v3.1.0: 秒级 (原为分钟级)
    out_path = args.out_dir / f"{competition}_final_{timestamp}.docx"
    # 秒级时间戳仍会撞名 (同秒重复导出 / 两个进程并发导出), 故真实导出前用
    # O_EXCL 独占占位并换名 (reserve_output_path); dry-run 不落任何文件, 只打印
    # 将用的名字。同秒撞名的提示在占位处打印。

    # ---- 读源 + md 卫生 lint (A2, M4 修复: 逐源文件、读入原貌上执行) ----
    # 五条规则全是文件级可判定问题 (拼接边界由 join 的空行天然隔开), 在
    # preprocess/normalize_md_tag (\tag 压缩会减行)/拼接等任何行数变换之前
    # 执行——报告行号即源文件行号, 永不错位。修复只写入内存文本 (随拼接进
    # pandoc), 不回写源文件。
    contents = []
    preprocess_notes = []
    lint_fixes, lint_warnings, lint_fatals = [], [], []
    for p in md_files:
        try:
            contents.append(p.read_text(encoding="utf-8").rstrip("\n"))
        except (OSError, UnicodeError) as e:
            print(f"[FAIL] 读取 {p} 失败: {e}; md 真源请保存为 UTF-8 编码")
            return 2
    for i, p in enumerate(md_files):
        try:
            fixed, fixes, warns = lint_md(
                contents[i], loc=lambda n, _p=p: f"{_p.name}:{n}")
        except MdLintFatal as probs:
            lint_fatals.extend(probs.problems)
            continue  # 继续扫余下文件, 一次性报全再拦
        contents[i] = fixed
        lint_fixes.extend(fixes)
        lint_warnings.extend(warns)
    if lint_fatals:
        print(f"[FAIL] md 卫生 lint 拦截 {len(lint_fatals)} 处 (须人工改 md 源后"
              f"重导, 不自动修):")
        for q in lint_fatals:
            print(f"     {q}")
        return 2
    processed = []
    for p, text in zip(md_files, contents):
        new_text, notes = preprocess_file(p, text)
        processed.append(new_text)
        preprocess_notes.extend(notes)

    # ---- 拼接 + 公式编号归一 + 图表编号注入 ----
    merged = "\n\n".join(processed) + "\n"
    merged = normalize_md_tag(merged)
    try:
        merged, stats = inject_numbering(merged)
    except NumberingConflict as e:
        print(f"[FAIL] 图表编号冲突: {e}")
        return 2

    print(f"[OK] 将拼接 {len(md_files)} 个 md → {out_path}")
    for note in preprocess_notes:
        print(f"     {note}")
    print(f"     编号注入: 图 {stats.n_figures} 张"
          + (f" (另有 {stats.n_figures_prefilled} 张已有编号跳过)" if stats.n_figures_prefilled else "")
          + f"、表 {stats.n_tables} 张"
          + (f" (另有 {stats.n_tables_prefilled} 张已有编号跳过)" if stats.n_tables_prefilled else ""))
    if stats.uncaptioned_tables:
        print(f"[WARN] {len(stats.uncaptioned_tables)} 张管道表无 \": 题注\" (终稿所有表"
              f"必须有题注, cn_spec §6; 未注入表号, 与 LaTeX 链口径一致):")
        for lineno, preview in stats.uncaptioned_tables:
            print(f"     拼接 md 第 {lineno} 行, 表头: {preview}")

    # ---- md 卫生 lint 报告 (检查在读源时已做, 见上; dry-run 同样可见) ----
    if lint_fixes:
        print(f"[lint] md 卫生自动修复 {len(lint_fixes)} 处 (只改本次导出的拼接 md, "
              f"不回写源文件):")
        for f in lint_fixes:
            print(f"     {f}")
    for w in lint_warnings:
        print(f"[WARN] {w}")

    resource_dirs = build_resource_dirs(md_files, workspace)
    if args.dry_run:
        # dry-run 不落任何文件: 临时拼接 md 用展示占位名 (真实路径由 mkstemp 生成)
        shown_md = Path(tempfile.gettempdir()) / \
            f"export_final_docx_{timestamp}_xxxxxx.md"
        print(f"[OK] dry-run: 不产 docx; 将执行的 pandoc 命令:")
        print(f"     {shlex.join(build_pandoc_cmd(shown_md, out_path, resource_dirs, reference_doc))}")
        return 0

    # ---- 真实执行 ----
    try:
        args.out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"[FAIL] 创建输出目录 {args.out_dir} 失败: {e}")
        return 2

    if not has_pandoc():
        print(f"[FAIL] {PANDOC_INSTALL_HINT}")
        return 2

    # 独占占位: 同秒重复导出/并发导出换名, 谁都不覆盖谁的产物 (v3.1.0)
    requested = out_path.name
    try:
        out_path = reserve_output_path(args.out_dir, f"{competition}_final_{timestamp}")
    except OSError as e:
        print(f"[FAIL] {e}")
        return 2
    if out_path.name != requested:
        print(f"[note] {requested} 已存在 (同秒重复导出或并发导出), 本次输出改用 "
              f"{out_path.name} (不覆盖旧文件)")

    def _fail(msg: str) -> int:
        """报错并撤掉空占位 (pandoc 未落盘时不留 0 字节 docx), 返回 2。"""
        print(msg)
        cleanup_reserved(out_path)
        return 2

    # 临时拼接 md 用 mkstemp (原子且唯一): 同秒两个导出进程不会互相踩临时文件
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f"export_final_docx_{timestamp}_",
                                        suffix=".md")
    except OSError as e:
        return _fail(f"[FAIL] 创建临时拼接文件失败: {e}")
    os.close(fd)
    tmp_md = Path(tmp_name)
    cmd = build_pandoc_cmd(tmp_md, out_path, resource_dirs, reference_doc)

    try:
        try:
            tmp_md.write_text(merged, encoding="utf-8")
        except OSError as e:
            return _fail(f"[FAIL] 写临时拼接文件 {tmp_md} 失败: {e}")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        except FileNotFoundError:
            return _fail(f"[FAIL] {PANDOC_INSTALL_HINT}")
        if r.returncode != 0:
            return _fail(f"[FAIL] pandoc 退出码 {r.returncode}: {r.stderr.strip()}\n"
                         f"       {PANDOC_INSTALL_HINT}")
        if "Could not fetch resource" in r.stderr:
            print("[WARN] 部分图片资源未找到, docx 可能缺图:")
            for line in r.stderr.splitlines():
                if "Could not fetch resource" in line:
                    print(f"     {line.strip()}")
    finally:
        # 清理失败只告警, 不改变退出码 (不让 PermissionError 覆盖 pandoc 结果)
        try:
            tmp_md.unlink(missing_ok=True)
        except OSError:
            print(f"[WARN] 临时文件清理失败: {tmp_md}")

    # pandoc rc0 但没落盘 / 只留空文件 (假成功): 撤掉空占位再报错, 不留 0 字节终稿
    try:
        produced = out_path.is_file() and out_path.stat().st_size > 0
    except OSError:
        produced = False
    if not produced:
        return _fail(f"[FAIL] pandoc 声称成功但未生成有效 docx (不存在或 0 字节): "
                     f"{out_path}")

    # ---- python-docx 后处理: 标题块/摘要标题/分页 ----
    try:
        import docx  # noqa: F401  仅探测; 实际使用在 postprocess_docx 内
    except ImportError:
        return _fail(f"[FAIL] python-docx 不可用, 无法做终稿标题块后处理; "
                     f"请 pip install python-docx 后重跑")
    try:
        for note in postprocess_docx(out_path, resolve_paper_meta(
                args.title, args.problem_no, args.team_no, workspace)):
            print(f"     {note}")
    except Exception as e:  # python-docx 对损坏文件抛多类异常, 统一按失败报告
        return _fail(f"[FAIL] docx 后处理失败: {e}")

    # ---- 呈现层后处理 (v3.1.0, A3+B5): --presentation 默认开, 同进程一键串联 ----
    if args.presentation:
        try:
            import docx_presentation_postprocess as _pp
        except ImportError as e:
            return _fail(f"[FAIL] docx_presentation_postprocess 导入失败: {e}")
        try:
            # make_backup=False: 秒级时间戳 + 独占占位导出本身不覆盖旧件, 无需再落
            # 备份; 且 submission/ 的 *_final_*.docx glob 约定不得混入 .bak 备份
            # (单独跑 CLI --docx 时仍自动备份 <名>.pre_pp.bak.docx)。
            # workspace 透传: 数学字体政策从 decision_log 读 (未登记则保持输入并警告)
            pp_stats = _pp.process(out_path, make_backup=False, workspace=workspace)
        except Exception as e:
            # 此时 pandoc 产物已有内容 → cleanup_reserved 不会删它 (只清 0 字节
            # 占位), 提示保留的可单独重跑路径
            return _fail(f"[FAIL] 呈现层后处理失败: {e}; 可单独重跑: "
                         f"python scripts/docx_presentation_postprocess.py "
                         f"--docx {out_path}")
        print("     呈现层后处理 (数学字体政策/编号右顶格 + 表格三线/自适应居中行禁拆/"
              "单元格排版对齐/图与图注同页):")
        for line in _pp.format_report(pp_stats):
            print(f"     {line}")

    print(f"[OK] 已导出 docx 终稿: {out_path.resolve()} ({out_path.stat().st_size} 字节)")
    print("     后续: 人在 Word 只改呈现层 (白名单见 docx_final_channel.md), "
          "再跑 docx_to_pdf.py + docx_number_recheck.py 终检")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
