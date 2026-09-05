"""
render_paper.py — markdown 中间产物 → 最终 PDF (6 竞赛纯 LaTeX 版)

功能:
1. 读 stage 8 各节 markdown 产出 (cwd/paper_workspace/)
2. 按 competition 选择 LaTeX 模板与编译器 (全部为自写模板):
     - cumcm:    templates/latex/cumcm/main.tex      + xelatex (自组装完整 paper.tex)
     - huaweibei: templates/latex/huaweibei/main.tex + xelatex
     - huashubei: templates/latex/huashubei/main.tex + xelatex
     - mcm:      templates/latex/mcm/main.tex        + pdflatex (中文 mcm)
     - diangong: templates/latex/diangong/main.tex   + xelatex
     - apmcm:    templates/latex/apmcm/main.tex      + xelatex
3. md → tex (优先 pandoc, 失败回退手工正则)
4. 三编生成 PDF

用法:
    python scripts/render_paper.py --competition cumcm --workspace cwd/paper_workspace/
    python scripts/render_paper.py --competition huaweibei --workspace ws/ --output out/
    python scripts/render_paper.py --competition 华为杯 --workspace ws/   (中文别名)
    python scripts/render_paper.py --competition diangong --workspace ws/ --no-compile  (dry-run)
"""

import argparse
import json
import os
import re
import subprocess
import shutil
from pathlib import Path


_SKILL_ROOT = Path(__file__).resolve().parent.parent

# 单层 competition key, 现存 6 套自写模板:
#   - cumcm 走 cumcm_assemble 模式 (从模板骨架自组装完整 paper.tex)
#   - 其余 5 套走 main_template 模式 (复制 main.tex + sections/<sec>.tex)
TEMPLATE_MAP = {
    "cumcm": {
        "template_dir": _SKILL_ROOT / "templates" / "latex" / "cumcm",
        "engine": "xelatex",
        "main_filename": "main.tex",
        "mode": "cumcm_assemble",
        "_doc": "cumcm 自组装完整 paper.tex (自写 ctexart 骨架, 从 md 节生成完整 .tex 主文档)",
    },
    "huaweibei": {
        "template_dir": _SKILL_ROOT / "templates" / "latex" / "huaweibei",
        "engine": "xelatex",
        "main_filename": "main.tex",
        "mode": "main_template",
        "_doc": "华为杯 (研究生数学建模), 自写 ctexart 模板",
    },
    "huashubei": {
        "template_dir": _SKILL_ROOT / "templates" / "latex" / "huashubei",
        "engine": "xelatex",
        "main_filename": "main.tex",
        "mode": "main_template",
        "_doc": "华数杯, 自写 ctexart 精简模板",
    },
    "mcm": {
        "template_dir": _SKILL_ROOT / "templates" / "latex" / "mcm",
        "engine": "pdflatex",
        "main_filename": "main.tex",
        "mode": "main_template",
        "_doc": "mcm 复制 main.tex 模板, md 节内容生成 sections/sectionname.tex 给 \\input{} 使用",
    },
    "diangong": {
        "template_dir": _SKILL_ROOT / "templates" / "latex" / "diangong",
        "engine": "xelatex",
        "main_filename": "main.tex",
        "mode": "main_template",
        "_doc": "diangong 同 mcm 模式, 用 ctex 中文",
    },
    "apmcm": {
        "template_dir": _SKILL_ROOT / "templates" / "latex" / "apmcm",
        "engine": "xelatex",
        "main_filename": "main.tex",
        "mode": "main_template",
        "_doc": "apmcm 同中文 ctex 模式, 按亚太杯中文赛骨架组织",
    },
}

# 竞赛别名映射 (用户输入 → 标准 competition key)
COMPETITION_ALIAS = {
    # 中文别名
    "国赛": "cumcm", "全国大学生数学建模": "cumcm", "CUMCM": "cumcm",
    "电工杯": "diangong",
    "亚太杯": "apmcm", "亚太赛": "apmcm", "APMCM": "apmcm",
    "华为杯": "huaweibei",
    "华数杯": "huashubei",
}


SECTION_TO_FILE = {
    "abstract": "01_abstract.md",
    "1_problem_restate": "02_problem_restate.md",
    "2_problem_analysis": "03_analysis.md",
    "3_assumptions": "04_assumptions.md",
    "4_notation": "05_notation.md",
    "5_models": "06_models.md",
    "6_sensitivity": "07_sensitivity.md",
    "7_evaluation": "08_evaluation.md",
    "8_references": "09_references.md",
    "appendix_code": "10_appendix.md",
}

# main_template 模式注入锚 (5 套自写模板均带, 见 templates/latex/<comp>/main.tex):
#   % __ABSTRACT__                       -> 替换为 \input{sections/abstract}
#   % __SECTIONS__ ... % __END_SECTIONS__ -> 两锚之间的演示正文替换为按序 \input
ABSTRACT_ANCHOR = "% __ABSTRACT__"
SECTIONS_ANCHOR_BEGIN = "% __SECTIONS__"
SECTIONS_ANCHOR_END = "% __END_SECTIONS__"


# ============================================================================
# 路径与配置
# ============================================================================

def resolve_competition(cli_arg: str = None, decision_log_path: Path = None) -> str:
    """优先级: CLI > env MATHMODEL_COMPETITION > decision_log.competition > 'cumcm'

    支持 COMPETITION_ALIAS 中的中文/英文别名映射.
    """
    raw = None
    if cli_arg:
        raw = cli_arg
    else:
        env = os.environ.get("MATHMODEL_COMPETITION")
        if env:
            raw = env
        elif decision_log_path and decision_log_path.exists():
            try:
                with open(decision_log_path, "r", encoding="utf-8") as f:
                    log = json.load(f)
                if log.get("competition"):
                    raw = log["competition"]
            except (json.JSONDecodeError, KeyError):
                pass
    if raw is None:
        return "cumcm"
    # 别名规范化
    return COMPETITION_ALIAS.get(raw, raw)


# ============================================================================
# md → tex 转换
# ============================================================================

def has_pandoc() -> bool:
    try:
        r = subprocess.run(["pandoc", "--version"], capture_output=True, text=True)
        return r.returncode == 0
    except FileNotFoundError:
        return False


def md_to_tex_pandoc(md_text: str) -> str:
    r = subprocess.run(
        ["pandoc", "-f", "markdown+tex_math_dollars+pipe_tables+raw_tex",
         "-t", "latex", "--no-highlight"],
        input=md_text, capture_output=True, text=True, encoding="utf-8"
    )
    if r.returncode != 0:
        raise RuntimeError(f"pandoc 失败: {r.stderr}")
    return upgrade_numbered_display_math(r.stdout)


# md 源里的 \tag{N} 预归一为规范形式 \qquad (N)——必须在 pandoc 之前做:
# pandoc 的数学解析器会吞掉 \tag 的反斜杠 (实测输出 "ag{4}"), 之后无法可靠识别
_MD_TAG_RE = re.compile(r"\$\$(.+?)\\tag\s*\{(\d+)\}\s*\$\$", re.DOTALL)

# pandoc latex 输出的编号 display 数学: \[X \qquad (N)\](归一后唯一形态)。
# 公式体用"到 \] 为止"的边界匹配 (tempered), 公式内含 ] (如 a_{[i]}) 不截断
_NUMBERED_DISPLAY_RE = re.compile(
    r"\\\[((?:(?!\\\]).)*?)\\qquad\s*\((\d+)\)\s*\\\]", re.DOTALL)

# 升级时必须跳过的代码环境 (pandoc 用 verbatim/Highlighting, fallback 用 lstlisting)。
# 三个捕获组: 定界符/内容/定界符——内容必须捕获, re.split 会丢弃未捕获的匹配文本
_CODE_ENV_RE = re.compile(
    r"(\\begin\{(?:verbatim|lstlisting|Highlighting)\*?\})(.*?)(\\end\{(?:verbatim|lstlisting|Highlighting)\*?\})",
    re.DOTALL)


def normalize_md_tag(md_text: str) -> str:
    """把 md 源中误用的 $$X \\tag{N}$$ 归一为规范形式 $$X \\qquad (N)$$。"""
    return _MD_TAG_RE.sub(lambda m: f"$${m.group(1).strip()} \\qquad ({m.group(2)})$$", md_text)


def upgrade_numbered_display_math(tex: str) -> str:
    """把 pandoc 输出的 \\[X \\qquad (N)\\] 升级为 equation/align 环境 (跳过代码块)。

    依据 references/md_authoring_spec.md: md 里的手写编号服务 docx 审阅链;
    PDF 链升级为编号环境后由 LaTeX 自动编号 (居中 + 编号右顶格 + 可引用)。
    公式体含对齐符 (&) 或换行 (\\\\) 时升级为 align 而非 equation——
    equation 内出现 & 会直接编译失败 (Misplaced alignment tab)。
    编号在本节内应逐条 +1 递增, 断档/重复只警告不阻断 (LaTeX 会重排为正确编号)。
    """
    segments = _CODE_ENV_RE.split(tex)
    # split 产出交替结构: [正文, \begin.., 代码内容, \end.., 正文, ...]
    # 正文段做编号升级; 代码环境三段原样保留 (其中的字面公式是示例代码不是论文公式)
    out, nums = [], []
    i = 0
    while i < len(segments):
        seg = segments[i]
        found = _NUMBERED_DISPLAY_RE.findall(seg)
        nums.extend(int(n) for _, n in found)
        out.append(_NUMBERED_DISPLAY_RE.sub(_upgrade_match, seg))
        if i + 3 < len(segments):
            out.extend(segments[i + 1:i + 4])
            i += 4
        else:
            break
    if nums:
        if any(b != a + 1 for a, b in zip(nums, nums[1:])):
            print(f"[WARN] 公式手写编号非逐条递增: {nums}; LaTeX 将按文档顺序自动重排, "
                  f"请核对正文'式(N)'引用")
        else:
            print(f"[INFO] 本节公式手写编号 {nums} 已升级自动编号环境; "
                  f"正文'式(N)'引用请以编译后 PDF 实际编号为准")
    return "".join(out)


def _upgrade_match(m):
    body = m.group(1).strip()
    if "&" in body or "\\\\" in body:
        return f"\\begin{{align}}\n{body}\n\\end{{align}}"
    return f"\\begin{{equation}}\n{body}\n\\end{{equation}}"


def md_to_tex_fallback(md_text: str) -> str:
    """5 类 markdown → LaTeX 手工正则 (代码块 / 公式块 / 图片 / 表格 / 列表 / 标题 / 行内)"""
    tex = md_text

    def replace_code_block(m):
        lang = m.group(1) or "text"
        body = m.group(2)
        return f"\\begin{{lstlisting}}[language={lang}]\n{body}\n\\end{{lstlisting}}"
    tex = re.sub(r"```(\w+)?\n(.*?)\n```", replace_code_block, tex, flags=re.DOTALL)

    def replace_eq(m):
        body = m.group(1).strip()
        # 手写编号 (\qquad (N) / \tag{N}) 剥离, 交给 equation 自动编号, 避免双重编号
        body = re.sub(r"(?:\\qquad\s*\(\d+\)|\\tag\{\d+\})\s*$", "", body).strip()
        if "\\\\" in body or "&" in body:
            return f"\\begin{{align}}\n{body}\n\\end{{align}}"
        return f"\\begin{{equation}}\n{body}\n\\end{{equation}}"
    tex = re.sub(r"\$\$(.+?)\$\$", replace_eq, tex, flags=re.DOTALL)

    def replace_img(m):
        alt = m.group(1)
        path = m.group(2)
        return (f"\\begin{{figure}}[H]\n\\centering\n"
                f"\\includegraphics[width=0.8\\textwidth]{{{path}}}\n"
                f"\\caption{{{alt}}}\n\\end{{figure}}")
    tex = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_img, tex)

    def replace_table(m):
        rows = [r.strip() for r in m.group(0).splitlines() if r.strip()]
        if len(rows) < 2:
            return m.group(0)
        cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
        header = cells[0]
        data = cells[2:] if len(cells) > 2 else []
        n_cols = len(header)
        col_spec = "l" * n_cols
        out = [f"\\begin{{table}}[H]\n\\centering",
               f"\\begin{{tabular}}{{{col_spec}}}\n\\toprule",
               " & ".join(header) + " \\\\",
               "\\midrule"]
        for row in data:
            out.append(" & ".join(row) + " \\\\")
        out.append("\\bottomrule\n\\end{tabular}\n\\end{table}")
        return "\n".join(out)
    tex = re.sub(r"^\|.+\|\s*$\n^\|[-:\s|]+\|\s*$\n(?:^\|.+\|\s*$\n?)+",
                  replace_table, tex, flags=re.MULTILINE)

    def replace_ol(m):
        items = re.findall(r"^\s*\d+\.\s+(.+)$", m.group(0), re.MULTILINE)
        if not items:
            return m.group(0)
        body = "\n".join(f"\\item {it}" for it in items)
        return f"\\begin{{enumerate}}\n{body}\n\\end{{enumerate}}"
    tex = re.sub(r"(?:^\s*\d+\.\s+.+\n?){2,}", replace_ol, tex, flags=re.MULTILINE)

    def replace_ul(m):
        items = re.findall(r"^\s*-\s+(.+)$", m.group(0), re.MULTILINE)
        if not items:
            return m.group(0)
        body = "\n".join(f"\\item {it}" for it in items)
        return f"\\begin{{itemize}}\n{body}\n\\end{{itemize}}"
    tex = re.sub(r"(?:^\s*-\s+.+\n?){2,}", replace_ul, tex, flags=re.MULTILINE)

    tex = re.sub(r"^# (.+)$", r"\\section{\1}", tex, flags=re.MULTILINE)
    tex = re.sub(r"^## (.+)$", r"\\subsection{\1}", tex, flags=re.MULTILINE)
    tex = re.sub(r"^### (.+)$", r"\\subsubsection{\1}", tex, flags=re.MULTILINE)

    tex = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", tex)
    tex = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\\textit{\1}", tex)
    tex = re.sub(r"`([^`]+?)`", r"\\texttt{\1}", tex)
    tex = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", tex)

    return tex


def md_to_tex(md_text: str, prefer_pandoc: bool = True) -> str:
    # \tag{N} 预归一为 \qquad (N)——pandoc 数学解析器会吞 \tag 的反斜杠, 必须在转换前修
    md_text = normalize_md_tag(md_text)
    if prefer_pandoc and has_pandoc():
        try:
            return md_to_tex_pandoc(md_text)
        except RuntimeError as e:
            print(f"[WARN] pandoc 失败 ({e}), 回退手工正则")
    return md_to_tex_fallback(md_text)


# ============================================================================
# 模板填充: cumcm 特殊 + 通用 main_template
# ============================================================================

def fill_template_cumcm(workspace: Path, template_dir: Path, output_dir: Path,
                         prefer_pandoc: bool = True) -> Path:
    """cumcm: 用自写 ctexart 骨架自组装完整 paper.tex

    骨架与 templates/latex/cumcm/main.tex 同源 (自写, xelatex):
    A4 四边 2.5cm, 首页摘要独占一页, 正文自第 2 页起, 页码自摘要页起算。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    if (template_dir / "figures").exists():
        shutil.copytree(template_dir / "figures", output_dir / "figures",
                         dirs_exist_ok=True)
    if (workspace.parent / "figures").exists():
        shutil.copytree(workspace.parent / "figures", output_dir / "figures",
                         dirs_exist_ok=True)

    tex_parts = {}
    for sec, fname in SECTION_TO_FILE.items():
        md_path = workspace / fname
        if md_path.exists():
            tex_parts[sec] = md_to_tex(md_path.read_text(encoding="utf-8"), prefer_pandoc)
        else:
            print(f"[WARN] 缺失 {fname}, 该节将留空")
            tex_parts[sec] = f"% TODO: 补充 {sec} 内容"

    main_tex = f"""\\documentclass[zihao=-4,a4paper]{{ctexart}}
\\usepackage{{geometry}}
\\geometry{{a4paper, top=2.5cm, bottom=2.5cm, left=2.5cm, right=2.5cm}}
\\usepackage{{amsmath,amssymb}}
\\usepackage{{graphicx}}
\\usepackage{{float}}
\\usepackage{{booktabs}}
\\usepackage{{multirow}}
\\usepackage{{longtable}}
\\usepackage{{caption}}
\\usepackage{{listings}}
\\usepackage{{xcolor}}
\\usepackage{{enumitem}}
\\usepackage[hidelinks]{{hyperref}}
\\ctexset{{
  section = {{format = {{\\Large\\bfseries\\heiti}}}},
  subsection = {{format = {{\\large\\bfseries\\heiti}}}},
  subsubsection = {{format = {{\\bfseries\\heiti}}}},
}}
\\captionsetup{{font={{small,bf}}, labelsep=quad}}
\\lstset{{
  basicstyle=\\small\\ttfamily,
  breaklines=true,
  frame=single,
  numbers=left,
  numberstyle=\\tiny\\color{{gray}},
  showstringspaces=false,
  columns=flexible,
}}
\\providecommand{{\\tightlist}}{{\\setlength{{\\itemsep}}{{0pt}}\\setlength{{\\parskip}}{{0pt}}}}
\\begin{{document}}
\\pagenumbering{{arabic}}

% ===== 第 1 页: 摘要 (独占一页) =====
\\begin{{center}}
  {{\\Large\\heiti 论文标题: [论文标题]}}\\\\[0.3em]
  {{\\large 题号: [题号]\\qquad 参赛队号: [参赛队号]}}
\\end{{center}}
\\vspace{{0.5em}}
\\begin{{center}}
  {{\\Large\\heiti 摘\\quad 要}}
\\end{{center}}

{tex_parts.get("abstract", "% 摘要")}

\\vspace{{1em}}
\\noindent{{\\heiti 关键词:}} 关键词1; 关键词2; 关键词3
\\newpage

% ===== 正文 (自第 2 页开始) =====
\\section{{问题重述}}
{tex_parts.get("1_problem_restate", "")}

\\section{{问题分析}}
{tex_parts.get("2_problem_analysis", "")}

\\section{{模型假设}}
{tex_parts.get("3_assumptions", "")}

\\section{{符号说明}}
{tex_parts.get("4_notation", "")}

\\section{{模型建立与求解}}
{tex_parts.get("5_models", "")}

\\section{{灵敏度与稳健性分析}}
{tex_parts.get("6_sensitivity", "")}

\\section{{模型评价与推广}}
{tex_parts.get("7_evaluation", "")}

\\begin{{thebibliography}}{{9}}
{tex_parts.get("8_references", "")}
\\end{{thebibliography}}

\\appendix
\\section{{程序代码}}
{tex_parts.get("appendix_code", "")}

\\end{{document}}
"""

    main_tex_path = output_dir / "paper.tex"
    main_tex_path.write_text(main_tex, encoding="utf-8")
    print(f"[OK] 已生成 {main_tex_path}")
    return main_tex_path


def _inject_section_inputs(main_path: Path, sections_dir: Path) -> None:
    """把 sections/<sec>.tex 按序注入 main.tex 的锚点 (v7.5.0 修复空壳论文 bug)。

    锚点约定 (5 套 main_template 模板均带):
      - % __ABSTRACT__: 单行, 替换为 \\input{sections/abstract}
      - % __SECTIONS__ ... % __END_SECTIONS__: 两锚之间 (含锚行) 的演示正文
        替换为其余各节按 SECTION_TO_FILE 顺序的 \\input 行
    无锚点时回退: 全部正文注入到 \\end{document} 前 (摘要保持模板占位)。
    失败保护: 注入后逐节检查, sections/*.tex 非空但 main.tex 未引用 → RuntimeError。

    Raises:
        RuntimeError: 模板无注入点 (既无锚点也无 \\end{document}), 或注入后
            仍有非空章节文件未被 main.tex 引用。
    """
    content = main_path.read_text(encoding="utf-8")

    def input_line(sec: str) -> str:
        return f"\\input{{sections/{sec}}}"

    body_secs = [s for s in SECTION_TO_FILE if s != "abstract"]

    # 整行匹配锚点 (锚名可能出现在解释注释的字面文本里, 必须独占一行才生效)
    begin_re = re.compile(r"^[ \t]*" + re.escape(SECTIONS_ANCHOR_BEGIN) + r"[ \t]*$",
                          re.MULTILINE)
    end_re = re.compile(r"^[ \t]*" + re.escape(SECTIONS_ANCHOR_END) + r"[ \t]*$",
                        re.MULTILINE)
    begin_m = begin_re.search(content)
    if begin_m is not None:
        end_m = end_re.search(content, begin_m.end())
        if end_m is None:
            raise RuntimeError(
                f"{main_path} 有 {SECTIONS_ANCHOR_BEGIN} 锚点但缺少 {SECTIONS_ANCHOR_END}, "
                f"无法定位正文注入区, 拒绝生成空壳论文"
            )
        body_block = "\n".join(
            f"% ---- {sec} (render_paper.py 注入) ----\n{input_line(sec)}"
            for sec in body_secs
        )
        content = content[:begin_m.start()] + body_block + content[end_m.end():]
    elif "\\end{document}" in content:
        # 回退: 无锚点模板, 注入到 \end{document} 前
        body_block = "\n".join(input_line(sec) for sec in body_secs)
        content = content.replace(
            "\\end{document}", body_block + "\n\n\\end{document}", 1
        )
        print(f"[WARN] {main_path} 无 {SECTIONS_ANCHOR_BEGIN} 锚点, "
              f"正文已回退注入到 \\end{{document}} 前; 建议给模板补锚点")
    else:
        raise RuntimeError(
            f"{main_path} 既无 {SECTIONS_ANCHOR_BEGIN} 锚点也无 \\end{{document}}, "
            f"正文无法注入, 拒绝生成空壳论文"
        )

    abstract_re = re.compile(r"^[ \t]*" + re.escape(ABSTRACT_ANCHOR) + r"[ \t]*$",
                             re.MULTILINE)
    if abstract_re.search(content) is not None:
        # 替换串含 \input, 用函数形式避免 re 模板转义解析
        content = abstract_re.sub(lambda _m: input_line("abstract"), content, count=1)
    else:
        print(f"[WARN] {main_path} 无 {ABSTRACT_ANCHOR} 锚点, "
              f"摘要保持模板占位文本 (sections/abstract.tex 未被引用)")

    main_path.write_text(content, encoding="utf-8")

    # 失败保护: 注入后复查, 非空章节文件必须被 main.tex 引用
    final = main_path.read_text(encoding="utf-8")
    missing = []
    for sec in SECTION_TO_FILE:
        sec_file = sections_dir / f"{sec}.tex"
        text = sec_file.read_text(encoding="utf-8") if sec_file.exists() else ""
        if text.strip() and input_line(sec) not in final:
            missing.append(f"sections/{sec}.tex")
    if missing:
        raise RuntimeError(
            f"注入失败: 以下非空章节文件未被 main.tex 引用: {missing}, "
            f"拒绝生成空壳论文"
        )


def fill_template_main(workspace: Path, template_dir: Path, output_dir: Path,
                       main_filename: str, prefer_pandoc: bool = True) -> Path:
    """huaweibei / huashubei / mcm / diangong / apmcm: 复制 main.tex + md 节渲染到
    sections/<sec>.tex, 并按锚点自动注入 \\input{sections/...} 到 main.tex"""
    output_dir.mkdir(parents=True, exist_ok=True)
    sections_dir = output_dir / "sections"
    sections_dir.mkdir(exist_ok=True)

    # 复制 main.tex
    main_src = template_dir / main_filename
    main_dst = output_dir / main_filename
    if not main_src.exists():
        raise FileNotFoundError(f"模板 {main_src} 不存在")
    shutil.copy(main_src, main_dst)

    # 最小兼容性补丁 — 只补 \tightlist (pandoc 生成, 自写模板未定义)
    compat_patch = (
        "\n"
        "% ===== compat patch (auto-injected by render_paper.py) =====\n"
        "% 仅 \tightlist 兜底 (pandoc 生成, 模板自身未定义).\n"
        "\\providecommand{\\tightlist}{\\setlength{\\itemsep}{0pt}\\setlength{\\parskip}{0pt}}\n"
        "% ===== end compat patch =====\n"
    )
    main_content = main_dst.read_text(encoding="utf-8")
    # 在 \begin{document} 之前插入补丁
    begin_doc = main_content.find("\\begin{document}")
    if begin_doc != -1:
        patched = main_content[:begin_doc] + compat_patch + "\n" + main_content[begin_doc:]
        main_dst.write_text(patched, encoding="utf-8")
        print(f"[OK] 已注入 \tightlist 补丁到 {main_dst}")
    else:
        print(f"[WARN] 找不到 \\begin{{document}}, 跳过补丁注入")

    # 复制其他 sty / cls / bib 文件 (自写模板目前均单 main.tex, 此处留作扩展)
    for ext in ("*.cls", "*.sty", "*.bib", "*.tex"):
        # 跳过 main_filename 本身 (已复制)
        for f in template_dir.glob(ext):
            if f.name != main_filename and f.name != "references.tex":
                shutil.copy(f, output_dir)
    # references.tex 单独复制 (不进 sections/)
    ref_src = template_dir / "references.tex"
    if ref_src.exists():
        shutil.copy(ref_src, output_dir)

    # 复制所有非 .tex 资源 (图片 pdf/png 等, 模板目录若附带图片时需要)
    for f in template_dir.iterdir():
        if f.is_file() and f.suffix.lower() not in (".tex",) and not f.name.startswith("."):
            dst = output_dir / f.name
            if not dst.exists():
                shutil.copy(f, dst)

    # 复制 figures
    if (template_dir / "figures").exists():
        shutil.copytree(template_dir / "figures", output_dir / "figures",
                         dirs_exist_ok=True)
    if (workspace.parent / "figures").exists():
        shutil.copytree(workspace.parent / "figures", output_dir / "figures",
                         dirs_exist_ok=True)

    # md → sections/<sec>.tex
    for sec, fname in SECTION_TO_FILE.items():
        md_path = workspace / fname
        sec_tex_path = sections_dir / f"{sec}.tex"
        if md_path.exists():
            tex = md_to_tex(md_path.read_text(encoding="utf-8"), prefer_pandoc)
            sec_tex_path.write_text(tex, encoding="utf-8")
        else:
            sec_tex_path.write_text(f"% TODO: 补充 {sec} 内容\n", encoding="utf-8")
            print(f"[WARN] 缺失 {fname}, sections/{sec}.tex 留 TODO")

    print(f"[OK] 已复制 {main_dst} + 渲染 {len(SECTION_TO_FILE)} 个 sections/*.tex")

    # 按锚点把 \input{sections/...} 注入 main.tex (v7.5.0 修复空壳论文 bug)
    _inject_section_inputs(main_dst, sections_dir)
    print(f"[OK] 已注入 \\input{{sections/...}} 到 {main_dst}")
    return main_dst


def fill_template(competition: str, workspace: Path, output_dir: Path,
                   prefer_pandoc: bool = True) -> tuple[Path, str]:
    """竞赛分发: 返回 (main_tex_path, engine)"""
    cfg = TEMPLATE_MAP.get(competition)
    if cfg is None:
        all_comps = list(TEMPLATE_MAP.keys())
        raise ValueError(f"未知 competition: {competition}; 支持 {all_comps}")

    template_dir = cfg["template_dir"]
    if not template_dir.exists():
        raise FileNotFoundError(f"模板目录 {template_dir} 不存在")

    if cfg["mode"] == "cumcm_assemble":
        main_tex_path = fill_template_cumcm(workspace, template_dir, output_dir, prefer_pandoc)
    elif cfg["mode"] == "main_template":
        main_tex_path = fill_template_main(workspace, template_dir, output_dir,
                                            cfg["main_filename"], prefer_pandoc)
    else:
        raise ValueError(f"未知 template mode: {cfg['mode']}")

    return main_tex_path, cfg["engine"]


# ============================================================================
# 编译
# ============================================================================

def compile_pdf(tex_path: Path, engine: str = "xelatex", runs: int = 3) -> bool:
    workdir = tex_path.parent
    for i in range(runs):
        print(f"\n--- {engine} 第 {i+1}/{runs} 次 ---")
        result = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error", str(tex_path.name)],
            cwd=workdir, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        if result.returncode != 0:
            print(f"[FAIL] {engine} 失败 (返回码 {result.returncode})")
            print(result.stdout[-2000:])
            print("--- stderr ---")
            print(result.stderr[-1000:])
            return False
    pdf_path = tex_path.with_suffix(".pdf")
    if pdf_path.exists():
        print(f"\n[OK] PDF 已生成: {pdf_path} ({pdf_path.stat().st_size // 1024} KB)")
        return True
    print(f"[FAIL] PDF 未生成")
    return False


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=str, required=True,
                        help="cwd/paper_workspace/ 目录, 含 01..10_*.md 节文件")
    parser.add_argument("--competition", type=str, default=None,
                        help="竞赛 key 或别名 (如 cumcm / huaweibei / 华为杯). "
                             "默认从 decision_log 读, 缺失则 cumcm. "
                             "全部支持: cumcm, huaweibei, huashubei, mcm, diangong, apmcm")
    parser.add_argument("--decision-log", type=str, default=None,
                        help="可选: 指定 decision_log.json 路径用于自动检测 competition")
    parser.add_argument("--output-dir", type=str, default="paper_output")
    parser.add_argument("--no-pandoc", action="store_true",
                        help="禁用 pandoc, 直接用手工正则 (调试用)")
    parser.add_argument("--no-compile", action="store_true",
                        help="只填充模板, 不调用 LaTeX 引擎 (dry-run)")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    output_dir = Path(args.output_dir)

    if not workspace.exists():
        print(f"[FAIL] workspace {workspace} 不存在")
        return 1

    decision_log_path = Path(args.decision_log) if args.decision_log else (Path.cwd() / "state" / "decision_log.json")
    competition = resolve_competition(args.competition, decision_log_path)
    print(f"competition: {competition}")

    prefer_pandoc = not args.no_pandoc
    if prefer_pandoc and not has_pandoc():
        print("[WARN] pandoc 未安装, 自动回退手工正则。建议安装: https://pandoc.org/installing.html")

    try:
        tex_path, engine = fill_template(competition, workspace, output_dir, prefer_pandoc)
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"[FAIL] {e}")
        return 1

    if args.no_compile:
        print(f"[OK] dry-run 完成 (--no-compile). engine={engine}, tex={tex_path}")
        return 0

    return 0 if compile_pdf(tex_path, engine=engine, runs=3) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
