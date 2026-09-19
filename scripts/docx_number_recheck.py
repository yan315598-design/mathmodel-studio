"""docx_number_recheck.py — docx 终稿数字回检 (v2.9.0 新增; v3.1.1 数字/数值检查修订)

终检①: 人改后的 docx 对冻结表的底线门禁 (协议见 references/docx_final_channel.md)。
md 冻结后呈现层只许改措辞/标点/间距/图位置/题注文字, 任何数字改动都会在这里暴露。

检查 1 (硬): 冻结表每条数字必须在 docx 全文出现。规范化: 去千分位逗号/窄空格、
统一 −/-/上标数字; 数字 token 带符号解析 (复审 P1-2: -4.8 冻结须命中正文的
"-4.8", 科学记数法比较保留符号, -2.30×10⁻¹³ 不得匹配 2.30e-13), 中文紧邻
不构成词边界 (温度33.5度 可取 33.5, 拉丁字母/数字/./_ 紧邻仍视为标识符排除);
正文同样采集 e/E 记法 token (复审 P1-3), 与 ×10 形态统一进科学记数等价比较;
科学记数法等价: 常规域按相对差 REL_TOL_SCI (尾数按声明位数舍入口径, 思路复用
claim_consistency_check 的 _sci_traced), 非零字面量下溢到 0 或上溢时走 log10
域比较、相对比较不设绝对容差下限 (复审 P1-4: 2.30e-400 与 9.99×10⁻⁵⁰⁰ 必须
判不等), 门禁不因大指数崩溃。冻结条目带 display 字段时按 display 核对
(原值同现也算过)。
   合法例外: 真源允许按显示精度缩写 (如冻结 -4.8822、摘要写 4.88)。原值未见但
存在**完整数值 token** 恰为原值在该精度下的四舍五入形态 → 走缩写分级;
子串命中不算 (复审 P1-5: 正文只有 104.88 时冻结 4.8822 必须 FAIL)。
连缩写形态都没有 → FAIL (exit 1)。
   缩写三级分流 (优化清单 A5, 实战教训: 0.7403 只以 0.7 出现而正文实际写的是
另一口径的 0.370, 两套数字并存的漂移没拦住):
   a) **缩写歧义 → FAIL**: 同一缩写 token 同时能命中 ≥2 个不同冻结值 (如 0.7 同时
      是 0.7403 与 0.7253 的合法四舍五入形态) 时, 该缩写无法证明指向哪个键——
      "同前缀多冻结项"强制全匹配, 未全文写出原值即 ❌;
   b) 冻结值 ≥3 位有效数字 → 「⚠️ 缩写形态需人工确认」清单 (不拦 exit, 但末行
      打印 ACTION: stage9-必查 缩写确认 N 条);
   c) 冻结值 ≤2 位有效数字 → 维持原 warn 语义。
   缺失诊断: 缺失条目附 `nearest` (同数量级同前缀的正文近值, 按相对差升序) ——
正文写 57.5403 而冻结 57.5406 这种**末位小差**必须在缺失报告里直接可见。

检查 2 (分级, v3.1.1 修订): 全文扫"看起来像结果的新数字" (≥4 位有效数字的小数/
科学记数), 白名单 (纯整数=页码/章节号/公式号/附件编号; 年份 1900-2100; 只出现在
display 公式里的常数)。分级把"冲突判定"与"数值邻近提示"彻底分开:

   ❌ 冲突 (conflicts, 计入 n_fail / exit 1) —— 高置信**显式文本关联**同一主张且
      数值不等 (即使只差末位): 全部要求显式字面紧邻, **不用数值距离, 也不用源值同值**:
        ① claim_label  冻结 claim id 完整字面紧邻在数字之前 (只隔连接符);
        ② claim_id_marker 上述标签前另有 claim/claim_id/冻结/编号/标识 等标记词;
        ③ locator_form   source_locator 叶名 (≥4 字符且非通用词) 紧邻在数字之前。
      显式关联**先于一切覆盖判定执行**, 且只与**被绑定记录**比 (复审 P1-1): 别的
      冻结值恰好等于该数字、或全局覆盖先跑, 都不能给错误绑定放行。正文 57.5403 与
      冻结 57.5406 (正确值仍在别处出现) 属此类, 必须拦 —— 不能只靠"冻结值缺失"
      门禁发现; 带标签而有效位不足者 (A 2.51 vs 冻结 2.52) 同样拦。
   ⚠️ 源值漂移 (source_drift, **独立报告**, 不拦门禁): 冻结值与源
      source_file@source_locator 当前值不一致 → 提示回 freeze_numbers verify /
      重新冻结; **不用**"正文数字与源值相同"去绑定正文主张 (复审 P1-2)。源路径
      限定工作区内 (resolve 掉 symlink/junction/..), 工作区外的源不读取、不改判;
      描述型定位符与不可解析的源如实记 note (source_notes)。
   ⚠️ 弱关联提示 (weak_associations, 不拦): 数值邻近且有单位一致 / 对象词元命中 /
      同段 claim 标签等弱证据, 但**不足以判同一主张** (单位一致不证明同对象;
      对象词元单命中不硬判) → 必查清单, 措辞一律"疑似"。
   ⚠️ 仅近邻 (near_hints, 不拦): 满足邻近窗口但无任何关联证据 → 只能提示,
      不作同主张判定 (无对象/单位/来源关联的近邻数字不得用大小/前缀/百分比
      直接认同或否定主张)。
   ℹ️ 不同量 (unit_mismatch, 不拦): 两侧单位都识别到且不同 (质量 1.0081 kg vs
      温度 1.0990 °C) → 判为不同量, 不作同主张比较, 两者不互相冲突。
   ⚠️ 未覆盖 (uncovered / 兼容旧键 warn_numbers, 不拦): 既不与登记值邻近, 登记
      来源里也没有同值 → 中性列出"未登记/未覆盖", 措辞固定 "未找到 ≠ 不存在"。
   C 级 (静默): 与冻结值精确一致 / 合法缩写 (按声明精度舍入) / display 一致 /
      display 公式常数 / 年份白名单 / 命中登记来源 (results 登记与证据账本里同值,
      按声明精度舍入 + 百分数互认 + 科学记数等价, 口径复用 claim_consistency_check
      规则 5)。显式关联冲突优先于来源覆盖判定。

   证据档口径 (v3.1.1, 只声明两档, 不构成"全文数字全部正确"的充分性证明):
     ① 值级硬证据 —— 冻结值回溯 (精确/display/声明精度缩写) + 文本显式关联不一致
        (claim 标签 / claim_id 标记 / locator 叶名紧邻): 拦门禁;
     ② 关联级提示证据 —— 单位/对象词元/同段标签弱关联 + 数值邻近 + 未覆盖 +
        源值漂移 (独立报告): 只提示, 不拦门禁。数值距离只用于挑提示候选。
   关联证据口径 (v3.1.1):
     - claim 标签: 冻结 claim id 的完整字面紧邻 (claim id 是登记项的显式身份);
       source_locator 叶名须 ≥4 字符且非通用词 (结果/数值/数据/result/data/value/
       json… 见 _OBJECT_STOPWORDS) 才参与硬判 —— 单层定位符 (value/h/data) 一并
       过滤, 通用词与短叶名只当弱对象词元;
     - 对象词元: claim id / source_locator 里 ≥3 字符的标识词命中数字邻近上下文;
     - 单位关联: 数字右侧紧邻单位串与登记单位规范化后相同 (同量纲嫌疑, 不证明同对象);
     - 来源关联: results 登记 (results/run_manifest.jsonl 的 outputs/inputs +
       results/**/*.json 数值叶) 与证据账本 (state/evidence_ledger.json /
       state/paper_plan.json, 行规范化复用 trace_claims) 里的**同号**同值 —— 只读
       复用已有登记, 不新建数据库; 读取同样限定工作区内 (resolve 链接);
       provenance.available 只表示"存在登记来源", 覆盖判定只看 value_evidence
       (run_manifest 路径登记无值证据, 不参与同值匹配);
     - 登记来源缺失/覆盖不足时如实标注"登记不足", 不推论数字为假。

文本提取: python-docx 按文档序遍历正文段落与表格单元格; 段落文本按文档序并入
OMML 公式的 m:t 并在公式块间补分隔 (python-docx 的 paragraph.text 不含公式,
不并则公式内数字全部漏检; 不分隔则相邻公式展平粘连把指数串位)。

用法:
    python scripts/docx_number_recheck.py --docx submission/xxx_final_xxx.docx \\
        --frozen state/frozen_numbers.json
    python scripts/docx_number_recheck.py --docx final.docx --frozen f.json --json
    python scripts/docx_number_recheck.py --docx final.docx --frozen f.json \\
        --report state/docx_number_recheck.json   # 完整报告落盘, 人读输出只给摘要
    容限可选覆盖: --near-sig-digits N (邻近窗口位数, 默认 2, 只挑提示候选);
                  --sci-rel-tol X (科学记数法等价相对容差, 默认 1e-3);
                  --workspace DIR (登记来源根, 默认 cwd)。

退出码: 0 检查 1 无缺失且无显式关联冲突 (缩写确认清单/提示档不影响);
1 冻结值缺失 (含缩写歧义升级) 或显式关联冲突; 2 用法/环境错误
(docx/frozen 不存在、文件损坏、python-docx 不可用、容限参数非法)。
存在缩写确认清单时, 人类可读输出的**最后一行**固定为
`ACTION: stage9-必查 缩写确认 N 条` (供 stage 9 清单消费, 不拦门禁)。

接口变更 (v3.1.1): 旧 A 级"数值距离 ≥5% 判冲突"已废除 —— 冲突只由**文本显式关联**
证据判定 (claim 标签/claim_id 标记/locator 叶名紧邻, 先于覆盖判定执行); conflicts 键
保留 (仍拦门禁), a_candidates 保留为邻近值抽查合并清单 (不拦门禁); 新增
weak_associations / near_hints / unit_mismatch / uncovered / source_drift /
source_notes / n_source_covered / provenance(value_evidence, path_registration_only) /
evidence_tiers 键。evidence 字段给出逐条关联证据串; 源值漂移单独报告, 不作正文冲突;
uncovered 条目新增 value_evidence 字段 (说明"未覆盖"是有值证据下的结论还是登记不足)。
"""

import argparse
import json
import math
import re
import sys
from collections import namedtuple
from pathlib import Path

import run_manifest  # 复用 results/run_manifest.jsonl 的路径常量
import trace_claims  # 复用证据账本的行规范化 (normalize_rows)

# ---- 文本规范化: 上标数字翻平、负号统一、千分位分隔剔除 ----
_SUPERSCRIPT_TRANS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_MINUS_CHARS = "\u2212\u2010\u2011\u2012\uff0d"  # − ﹣ 等 → -
_THOUSANDS_SEP_RE = re.compile(r"(?<=\d)[,\u2009\u00a0\u202f\u2007](?=\d)")

# ---- token 边界口径 (复审 P1-2): 拉丁字母/数字/./_ 紧邻 = 标识符, 排除;
#      中文紧邻不算边界 (温度33.5度 可取 token); 数字前的 - 视为区间连字符
#      排除其后的无符号数 (36.7-100.6 不取 100.6), 但带符号 token 的符号前
#      仅受上述拉丁类约束 (值为-4.8 / 值为 -4.8 均可取 "-4.8") ----
_ADJACENT = "A-Za-z0-9_."
NUMBER_TOKEN_RE = re.compile(
    rf"(?<![{_ADJACENT}-])([+-]?\d+(?:\.\d+)?)(?![{_ADJACENT}%])")
# 科学记数法: 带符号尾数 + 分隔符(× · * x \\times, 含 pandoc OMML 展平的 "imes")
# + 10 + 指数
SCI_TOKEN_RE = re.compile(
    rf"(?<![{_ADJACENT}-])([+-]?\d+(?:\.\d+)?)"
    rf"\s*(?:\\times|×|·|∙|\*|[xX]|imes)\s*10\s*[\^({{\[]?\s*(-?\d+)")
# e/E 记法 (复审 P1-3): 正文与冻结值统一口径
E_TOKEN_RE = re.compile(
    rf"(?<![{_ADJACENT}-])([+-]?\d+(?:\.\d+)?)[eE]([+-]?\d+)")

WARN_LIST_CAP = 20  # 软检查清单打印上限, 防刷屏
SIG_DIGITS_MIN = 4  # 软检查: ≥4 位有效数字才算"结果样"数字
REL_TOL_EXACT = 1e-12  # 同值判定 (仅书写格式差异, 如 2.5500 vs 2.55)
REL_TOL_SCI = 1e-3     # 科学记数法等价 (复用 _sci_traced 的 0.1% 口径)
ABBREV_CONFIRM_MIN_SIG = 3  # A5: 冻结值 ≥3 位有效数字时缩写命中须人工确认
# ---- 容限配置 (v3.1.1; 经 run_recheck 关键字参数 / CLI 覆盖) ----
# 邻近窗口: 同符号 + 同数量级 + 前 N 位有效数字相同。**只用于挑提示候选**,
# 不作同主张/冲突判定 —— 冲突只看显式关联证据 (claim 标签/claim_id 标记/locator
# 源值), 不按大小、前缀或百分比下结论。默认 2 位。
NEAR_PREFIX_SIG = 2
# 单个结果 json 读取上限 (超大文件跳过并计数; 登记来源只读复用, 不建库)。
MAX_RESULT_JSON_BYTES = 8 << 20
# 显式标签紧邻判定: 标签与数字之间只允许连接符 (空白/=:/中文连接词/左括号),
# 且连接符总长 ≤ _LABEL_GAP_MAX —— 标点或句读后的数字不算紧邻 (退回弱证据)。
_LABEL_GAP_CHARS = " \t=:：为是约取达到值称记作（(【["
_LABEL_GAP_MAX = 12
# claim_id 显式标记词 (标签前出现时单独记为 claim_id_marker 证据)。
_CLAIM_MARKERS = ("claim_id", "claim-id", "claimid", "claim", "冻结", "登记",
                  "编号", "标识", "标签", "标记")

# ---- 单位识别 (v3.1.1): 数字右侧紧邻单位串, 用于"同量纲嫌疑/不同量"判定 ----
# 识别不出单位一律按"无单位证据"处理 (保守: 只提示, 不判冲突)。符号/拉丁串与
# 常见中文单位词两路; 不做别名互认 (小时≠h 之外请登记单位时写全)。
_UNIT_ASCII_RE = re.compile(r"\s*([A-Za-z%‰°℃µμΩ][A-Za-z0-9%‰°℃µμΩ/·⋅^\-]{0,7})")
_CJK_UNITS = (
    "千克", "公斤", "毫克", "吨", "克", "摄氏度", "平方公里", "平方米", "立方米",
    "千米", "公里", "厘米", "毫米", "米", "毫升", "升", "分钟", "小时", "秒",
    "千瓦时", "千瓦", "瓦", "焦耳", "帕", "牛", "摩尔", "万元", "亿元", "元",
    "个百分点", "亩", "公顷", "天", "年", "月", "周", "人", "户", "次", "件",
    "台", "套", "辆", "只", "头",
)
_CJK_UNITS_BY_LEN = tuple(sorted(_CJK_UNITS, key=len, reverse=True))
_FULLWIDTH_TRANS = str.maketrans("０１２３４５６７８９％．／", "0123456789%./")

# 通用词: 任何位置都会出现, 不作对象证据, 也不作 claim 标签硬判证据。
_OBJECT_STOPWORDS = {
    "data", "result", "results", "value", "values", "val", "json", "csv", "out",
    "output", "outputs", "input", "inputs", "total", "totals", "summary", "stat",
    "stats", "main", "final", "key", "figure", "table", "equation", "code",
    "结果", "数值", "数字", "数据", "参数", "模型", "论文", "正文", "图表", "变量",
    "指标", "求解", "计算", "输出", "输入", "总计", "合计", "统计", "误差", "关键",
}
# 显式关联里 source_locator 叶名的最小长度 (短叶名 h/dt 只作弱对象词元)。
_LABEL_FORM_MIN_LEN = 4

# 登记来源的默认位置 (与 run_manifest / trace_claims 的落盘约定一致)
LEDGER_RELS = (Path("state") / "evidence_ledger.json",
               Path("state") / "paper_plan.json")

# 数字 token: raw 原文, mant 带符号尾数, exp 指数, nd 小数位数, in_display 是否
# display 公式段, seg 段序号, start/end 段内偏移, text 规范化段文本。
_Token = namedtuple("_Token", "raw mant exp nd in_display seg start end text")


def normalize_text(text: str) -> str:
    """上标翻平 + 负号统一 + 千分位分隔剔除; 幂/单位等其他字符不动。"""
    text = text.translate(_SUPERSCRIPT_TRANS)
    for ch in _MINUS_CHARS:
        text = text.replace(ch, "-")
    return _THOUSANDS_SEP_RE.sub("", text)


def _safe_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _pair_value(mant, exp):
    """mant×10^exp 的浮点值; 上溢/非有限返回 None (下溢到 0.0 原样返回,
    由 _pair_equiv 走 log10 域, 不得把非零字面量的下糊成 0 与人比较)。"""
    try:
        v = mant * 10.0 ** exp
    except OverflowError:
        return None
    return v if math.isfinite(v) else None


def _pair_equiv(am, ae, bm, be, rel_tol: float) -> bool:
    """(带符号尾数, 指数) 对的数值等价比较 (复审 P1-4 口径)。

    - 符号不同直接不等 (复审 P1-2);
    - 双方可表示且非零: 相对差 ≤ rel_tol, **不设绝对容差下限** (固定下限会把
      极小值侧的真矛盾吞掉);
    - 任一侧非零字面量下溢到 0 或上溢: log10 域比较 |log10| 差 ≤ log10(1+rel_tol)。
    """
    if am == bm and ae == be:
        return True
    if am == 0 or bm == 0:
        return am == 0 and bm == 0
    if (am > 0) != (bm > 0):
        return False
    va, vb = _pair_value(am, ae), _pair_value(bm, be)
    if va is not None and vb is not None and va != 0 and vb != 0:
        return abs(va - vb) <= rel_tol * max(abs(va), abs(vb))
    try:
        la = math.log10(abs(am)) + ae
        lb = math.log10(abs(bm)) + be
    except (ValueError, OverflowError):
        return False
    return abs(la - lb) <= math.log10(1.0 + rel_tol)


def _token_decimals(token: str) -> int:
    """token 前导带符号数字的小数位数 (四舍五入形态判定用)。"""
    m = re.match(r"[+-]?\d+(?:\.(\d+))?", token)
    return len(m.group(1)) if m and m.group(1) else 0


def _new_token(m, raw: str, exp: int, seg_no: int, in_display: bool, text: str):
    return _Token(raw=raw, mant=_safe_float(m.group(1)), exp=exp,
                  nd=_token_decimals(raw), in_display=in_display, seg=seg_no,
                  start=m.start(), end=m.end(), text=text)


def collect_tokens(segments) -> list:
    """从 (text, in_display_math) 段列表收集数字 token (含段内位置)。

    统一产出 _Token; 纯小数/整数指数为 0。×10 形态、e/E 记法、OMML 展平 "imes"
    形态一并采集 (复审 P1-3); 同一 span 至多命中一种形态 (尾数后紧跟 e/imes 等
    拉丁字符时纯数 token 被边界口径排除, 不重复计数)。
    """
    tokens = []
    for seg_no, (text, in_display) in enumerate(segments):
        norm = normalize_text(text)
        for m in SCI_TOKEN_RE.finditer(norm):
            tokens.append(_new_token(m, m.group(0), int(m.group(2)),
                                     seg_no, in_display, norm))
        for m in E_TOKEN_RE.finditer(norm):
            tokens.append(_new_token(m, m.group(0), int(m.group(2)),
                                     seg_no, in_display, norm))
        for m in NUMBER_TOKEN_RE.finditer(norm):
            tokens.append(_new_token(m, m.group(1), 0, seg_no, in_display, norm))
    return [t for t in tokens if t.mant is not None]


def _rounds_to(token_value: float, frozen_value: float, nd: int) -> bool:
    """token_value 是否为 frozen_value 按 nd 位小数显示的四舍五入形态。

    判据: |abs(token) - abs(frozen)| ≤ 半个末位 (含进位/舍位两侧, 兼容
    round-half-up 与 half-even 的口径差); 符号不敏感 (摘要以"短/降"叙述吸收
    负号属合法缩写)。nd=0 (整数 token) 不算缩写——整数到处都是, 会掏空门禁。
    """
    if nd < 1 or token_value == 0:
        return False
    half_ulp = 0.5 * 10.0 ** -nd * (1.0 + 1e-9)
    return abs(abs(token_value) - abs(frozen_value)) <= half_ulp


def _parse_frozen_value(raw) -> tuple:
    """冻结值字符串 → (带符号尾数 float, 指数 int); 解析失败返回 (None, None)。"""
    s = normalize_text(str(raw).strip())
    m = E_TOKEN_RE.fullmatch(s)
    if m:
        return _safe_float(m.group(1)), int(m.group(2))
    v = _safe_float(s)
    if v is not None:
        return v, 0
    return None, None


def _value_sig_digits(raw) -> int:
    """冻结值字符串的有效数字位数 (A5 分级阈值 / 源值一致性判定用)。

    "0.7403"→4, "39.5"→3, "46.0"→3 (小数点后尾零属有效位), "4.9"→2, "0.00025"→2,
    "2.30e-13"→3。解析失败按 0 处理 (≤2 位, 走原 warn 语义, 不升级)。
    """
    if raw is None:
        return 0
    s = str(raw).strip()
    m = re.match(r"[+-]?(\d+(?:\.\d+)?)", s)
    if not m:
        return 0
    digits = m.group(1).replace(".", "").lstrip("0")
    return len(digits) or 1


def _decade_sig(mant: float, exp: int, sig: int = NEAR_PREFIX_SIG) -> tuple:
    """(尾数, 指数) → (数量级 decade=⌊log10|v|⌋, 前 sig 位有效数字 int)。

    C7 邻近窗口的两个坐标: 同数量级且前 sig 位有效数字相同。**只用于挑出提示
    候选**, 不作同主张/冲突判定 (v3.1.1)。全程 log10 域计算, 下溢/上溢也不失真;
    mant=0 返回 (None, None) 不参与判定。
    """
    if mant == 0:
        return None, None
    try:
        lg = math.log10(abs(mant)) + exp
    except (ValueError, OverflowError):
        return None, None
    d = math.floor(lg)
    # 10^(lg-d+sig-1) ∈ [10^(sig-1), 10^sig) 即 |v| 的前 sig 位有效数字;
    # round 吸收浮点噪声
    sig_val = int(round(10.0 ** (lg - d + sig - 1), 6))
    if sig_val >= 10 ** sig:  # 9.99… 进位边界: 归一到下一数量级的 10^(sig-1)
        d, sig_val = d + 1, 10 ** (sig - 1)
    return d, sig_val


def _log10_abs(mant: float, exp: int):
    """log10|mant×10^exp|; 无法计算返回 None (0 值 / 非数值)。"""
    if not isinstance(mant, (int, float)) or isinstance(mant, bool) or mant == 0:
        return None
    try:
        return math.log10(abs(mant)) + exp
    except (ValueError, OverflowError):
        return None


def _rel_diff(am: float, ae: int, bm: float, bf: int) -> float:
    """两值相对差 |a/b - 1| (log10 域, 大指数不失真); 无法计算返回 inf。"""
    la, lb = _log10_abs(am, ae), _log10_abs(bm, bf)
    if la is None or lb is None:
        return float("inf")
    if abs(la - lb) > 300:  # 10**300 已远超任何有意义的相对差, 防溢出
        return float("inf")
    return abs(10.0 ** (la - lb) - 1.0)


def _fmt_rel(rel) -> str:
    """相对差的显示: 常规用百分数, 极小值 (末位小差) 用有效数字记法。"""
    if not isinstance(rel, (int, float)) or isinstance(rel, bool) \
            or not math.isfinite(rel):
        return "n/a"
    return f"{rel:.3%}" if rel >= 1e-4 else f"{rel:.3g}"


# ---------------------------------------------------------------- 单位/对象/标签

def _norm_unit(unit) -> str:
    """单位规范化: 全角转半角 + ℃→°C + 去空白 + 小写 (不做别名互认, 小时≠h)。"""
    if unit is None:
        return ""
    s = str(unit).translate(_FULLWIDTH_TRANS).replace("℃", "°C")
    return re.sub(r"\s+", "", s).lower()


def _adjacent_unit(tok: _Token):
    """数字右侧紧邻单位串 (符号/拉丁串优先, 其次常见中文单位词); 无则 None。

    只识别"紧邻"形态 (质量 1.0081 kg / 温度 1.0990 °C / 步长 0.7403 s);
    识别不出按无单位证据处理, 保守不判冲突。
    """
    rest = tok.text[tok.end:]
    m = _UNIT_ASCII_RE.match(rest)
    if m:
        return m.group(1)
    tail = rest[re.match(r"\s*", rest).end():]
    for word in _CJK_UNITS_BY_LEN:
        if tail.startswith(word):
            return word
    return None


def _context_window(tok: _Token, span: int = 32) -> str:
    """token 邻近上下文 (同段内左右各 span 字符, 小写), 供对象词元命中判定。"""
    lo = max(0, tok.start - span)
    hi = min(len(tok.text), tok.end + span)
    return tok.text[lo:hi].lower()


def _object_words(claim: str, rec: dict) -> set:
    """登记项的**对象词元**: claim id 与 source_locator 里 ≥3 字符的标识词。

    剔除纯数字、q\\d+ 式问号与通用词 (结果/数值/数据/result/data/json…) ——
    通用词任何位置都出现, 不构成对象证据。对象词元单命中只作弱证据 (不硬判)。
    """
    words: set = set()
    for raw in (claim, rec.get("source_locator")):
        for word in re.split(r"[^0-9A-Za-z_\u4e00-\u9fff]+", str(raw or "")):
            lw = word.lower()
            for part in (lw, *(p for p in lw.split("_") if p)):
                if len(part) < 3 or part.isdigit() or part in _OBJECT_STOPWORDS:
                    continue
                if re.fullmatch(r"q\d+", part):
                    continue
                words.add(part)
    return words


def _word_in_text(text: str, form: str) -> bool:
    """form 是否以**完整词**出现在 text 里 (前后非拉丁/数字/下划线), 非子串命中。"""
    for m in re.finditer(re.escape(form), text, flags=re.IGNORECASE):
        before = text[m.start() - 1] if m.start() > 0 else ""
        after = text[m.end()] if m.end() < len(text) else ""
        if not (before.isalnum() or before == "_") and \
                not (after.isalnum() or after == "_"):
            return True
    return False


def _excerpt_around(tok: _Token, span: int = 24) -> str:
    """token 邻近原文摘录 (便于在 docx 里 Ctrl+F 定位)。"""
    lo, hi = max(0, tok.start - span), min(len(tok.text), tok.end + span)
    text = tok.text[lo:hi].strip()
    return ("…" if lo > 0 else "") + text + ("…" if hi < len(tok.text) else "")


# ---------------------------------------------------------------- 显式关联 (硬档)

def _is_descriptive_locator(locator: str) -> bool:
    """描述型定位符: 空串 / 含 CJK / 含空白 (口径同 freeze_numbers 的同类判定)。

    描述型不参与源值绑定与叶名匹配 (无机器可解析语义), 只影响登记完整性统计。
    """
    loc = str(locator or "")
    if not loc.strip():
        return True
    if re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", loc):
        return True
    return any(ch.isspace() for ch in loc)


def _locator_leaf(locator: str) -> str:
    """定位符叶名: data.t_total → t_total; a.b[0] → b; 取不到返回空串。"""
    text = re.sub(r"(\[\d+\])+$", "", str(locator or "").strip())
    parts = [p for p in re.split(r"[.\[\]]+", text) if p]
    return parts[-1] if parts else ""


_LOCATOR_STEP_RE = re.compile(r"\.?([^.\[\]]+)|\[(\d+)\]")


def _resolve_locator_value(data, locator: str):
    """在已加载 json 里按定位符取值 (点路径 + [下标]; 口径同 freeze_numbers)。

    Returns (value, None) 或 (None, 中文原因)。
    """
    text = str(locator or "")
    if not text or text.startswith(".") or text.startswith("["):
        return None, f"定位符语法不合法: {text!r}"
    node = data
    pos = 0
    while pos < len(text):
        m = _LOCATOR_STEP_RE.match(text, pos)
        if m is None:
            return None, f"定位符语法不合法: {text!r}"
        if m.group(1) is not None:
            key = m.group(1)
            if not isinstance(node, dict) or key not in node:
                return None, f"键 '{key}' 不存在"
            node = node[key]
        else:
            idx = int(m.group(2))
            if not isinstance(node, list) or idx >= len(node):
                return None, f"下标 [{idx}] 越界或目标不是数组"
            node = node[idx]
        pos = m.end()
    return node, None


def _load_json_cached(path: Path, cache: dict):
    """带缓存的 json 读取; 失败返回 (None, 原因), 不影响门禁。"""
    key = str(path)
    if key in cache:
        return cache[key]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        result = (None, f"源文件缺失: {path.as_posix()}")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result = (None, f"源不是可读 JSON: {exc}")
    else:
        result = (data, None)
    cache[key] = result
    return result


def _values_consistent(parsed, recorded) -> bool:
    """源值与记录值是否一致 (口径同 freeze_numbers._values_consistent)。

    三种一致口径 (任一满足): 字符串等值 / 数值相对 1e-9 / 源值按记录值有效位数
    舍入后相等 (论文数字是显示精度的舍入值)。
    """
    if parsed is None or recorded is None:
        return False
    rs = str(recorded).strip()
    if isinstance(parsed, str):
        return parsed.strip() == rs
    if isinstance(parsed, bool) or not isinstance(parsed, (int, float)):
        return False
    try:
        rv = float(rs)
    except ValueError:
        return False,  # pragma: no cover - 占位不可达
    sv = float(parsed)
    if math.isclose(sv, rv, rel_tol=1e-9, abs_tol=0.0):
        return True
    sig = _value_sig_digits(rs)
    if sig:
        try:
            rounded = float(f"{sv:.{sig}g}")
        except (ValueError, OverflowError):
            return False
        if math.isclose(rounded, rv, rel_tol=1e-12, abs_tol=1e-15):
            return True
    return False


def _inside_workspace(path: Path, workspace: Path) -> bool:
    """path 解析后是否仍在 workspace 内 (resolve 掉 symlink/junction/..; 复审 P1-2)。"""
    try:
        resolved = path.resolve()
    except OSError:
        return False
    try:
        resolved.relative_to(workspace.resolve())
    except (OSError, ValueError):
        return False
    return True


def _binding_forms(claim: str, rec: dict) -> list:
    """登记项的**显式绑定位串**: [(kind, form)], kind ∈ claim/locator_leaf。

    - claim id 取完整字面 (完整匹配, 非子串; claim id 是登记项的显式身份);
    - source_locator **只经叶名过滤后参与** (复审 P2-3): 叶名须 ≥4 字符、含字母/
      数字/汉字且非通用词 —— 单层定位符 (value / h / data …) 同样过滤, 否则通用词
      或单位名紧邻数字就会被硬判冲突; 被过滤的叶名只作弱对象词元。
    """
    forms = []
    claim_s = str(claim or "").strip()
    if claim_s:
        forms.append(("claim", claim_s))
    loc = str(rec.get("source_locator") or "").strip()
    if loc and not _is_descriptive_locator(loc):
        leaf = _locator_leaf(loc)
        if (len(leaf) >= _LABEL_FORM_MIN_LEN
                and leaf.lower() not in _OBJECT_STOPWORDS
                and re.search(r"[0-9A-Za-z\u4e00-\u9fff]", leaf)):
            forms.append(("locator_leaf", leaf))
    return forms


def _form_adjacent(tok: _Token, form: str):
    """form 是否**紧邻**在 token 之前 (只隔连接符, 且 form 前是词边界)。

    Returns form 在段文本中的起始偏移或 None。
    """
    form = form.strip()
    if not form:
        return None
    lo = max(0, tok.start - len(form) - _LABEL_GAP_MAX)
    window = tok.text[lo:tok.start].lower()
    target = form.lower()
    idx = window.rfind(target)
    while idx != -1:
        head_ok = idx == 0 or not (window[idx - 1].isalnum() or window[idx - 1] == "_")
        gap = window[idx + len(target):]
        if head_ok and all(ch in _LABEL_GAP_CHARS for ch in gap):
            return lo + idx
        idx = window.rfind(target, 0, idx)
    return None


def _has_marker(tok: _Token, form_start: int, lookback: int = 12) -> bool:
    """form 之前 lookback 字符内是否有显式 claim_id 标记词 (claim_id/冻结/编号…)。"""
    pre = tok.text[max(0, form_start - lookback):form_start].lower()
    return any(marker in pre for marker in _CLAIM_MARKERS)


def _resolve_records_sources(frozen: dict, workspace) -> dict:
    """为每条冻结记录解析 source_file@source_locator 的**当前源值** (只读, 不建库)。

    Returns {claim: {"ok", "value", "note", "label"}}; workspace 为 None 或源
    缺失/描述型/不可解析时 ok=False (只记 note, 不参与冲突判定)。
    """
    resolved: dict = {}
    cache: dict = {}
    for claim, rec in frozen.items():
        if not isinstance(rec, dict) or rec.get("status") == "stale":
            continue
        entry = {"ok": False, "value": None, "note": "", "label": ""}
        src_rel = str(rec.get("source_file") or "")
        loc = str(rec.get("source_locator") or "")
        if workspace is None:
            entry["note"] = "未提供工作区, 源值绑定未核"
        elif not src_rel:
            entry["note"] = "记录缺 source_file, 源值绑定未核"
        elif _is_descriptive_locator(loc):
            entry["note"] = "描述型定位符 (含中文/空白), 不做源值绑定"
        else:
            ws_resolved = Path(workspace).resolve()
            source_path = ws_resolved / src_rel
            if not _inside_workspace(source_path, ws_resolved):
                entry["note"] = (f"源在工作区外 ({src_rel}), 未读取 "
                                 "(源路径限定工作区, 含 resolve 链接)")
            else:
                data, err = _load_json_cached(source_path, cache)
                if data is None:
                    entry["note"] = err
                else:
                    value, err = _resolve_locator_value(data, loc)
                    if err is None:
                        entry = {"ok": True, "value": value, "note": "",
                                 "label": f"{src_rel}@{loc}"}
                    else:
                        entry["note"] = f"{src_rel}@{loc} 解析失败: {err}"
        resolved[claim] = entry
    return resolved


def _record_contexts(frozen: dict, workspace) -> list:
    """逐条冻结记录的显式绑定上下文 (位串 + 源值), 供逐 token 判定; 一次算好。"""
    resolved = _resolve_records_sources(frozen, workspace)
    out = []
    for claim in sorted(frozen):
        rec = frozen[claim]
        if not isinstance(rec, dict) or rec.get("status") == "stale":
            continue
        forms = _binding_forms(claim, rec)
        source = resolved.get(claim) or {}
        if not forms and not source.get("ok"):
            continue  # 无标签可匹配且源值不可用 → 本记录没有显式关联路径
        out.append({"claim": claim, "rec": rec, "forms": forms, "source": source})
    return out


def _record_comparable(rec: dict) -> bool:
    """记录是否至少有一个可解析的数值形态 (value/display); 否则无从与正文比。"""
    for field in ("display", "value"):
        if rec.get(field) is not None and _parse_frozen_value(rec[field])[0] is not None:
            return True
    return False


def _token_matches_record(tok: _Token, rec: dict, sci_rel_tol: float) -> bool:
    """token 是否与被**绑定记录**的某个形态一致 (精确/display/声明精度缩写)。

    只与被绑定的记录比 (复审 P1-1): 别的冻结值恰好等于该 token 不构成"这条主张
    没问题" —— 覆盖判定必须落在同一条主张上。
    """
    for field in ("display", "value"):
        raw = rec.get(field)
        if raw is None:
            continue
        fm, fe = _parse_frozen_value(raw)
        if fm is None:
            continue
        rel = REL_TOL_EXACT if fe == 0 else sci_rel_tol
        if _pair_equiv(tok.mant, tok.exp, fm, fe, rel):
            return True
        if fe == 0 and tok.exp == 0 and _rounds_to(tok.mant, fm, tok.nd):
            return True  # 该记录值的显示精度缩写 (4.88 ← -4.8822)
        if fe != 0 and tok.exp == fe and _rounds_to(tok.mant, fm, tok.nd):
            return True  # 科学记数法缩写 (2.09×10⁻³ ← 2.0932e-03)
    return False


def _fmt_source_value(value) -> str:
    """源值的显示形态 (容器只给类型, 免刷屏); 报告里存原值供机器比较。"""
    if isinstance(value, (dict, list)):
        return f"({type(value).__name__} 容器)"
    return repr(value)


def _source_drift_entries(record_ctx: list) -> list:
    """源值漂移的**独立报告** (复审 P1-2): 冻结值与源 locator 当前值不一致。

    不参与正文冲突判定 (正文写源里的当前值不等于"正文关联了该主张"), 只提示回
    freeze_numbers verify / 重新冻结, 不拦门禁。描述型 / 工作区外 / 不可解析的源
    不在此列 (各自 note 已说明)。
    """
    drift = []
    for ctx in record_ctx:
        source = ctx["source"]
        if not source.get("ok"):
            continue
        if _values_consistent(source["value"], ctx["rec"].get("value")):
            continue
        drift.append({
            "claim": ctx["claim"],
            "frozen_value": ctx["rec"].get("value"),
            "frozen_unit": str(ctx["rec"].get("unit") or ""),
            "source": source["label"],
            "source_value": source["value"],
            "note": "冻结值与源 locator 当前值不一致 (源漂移或冻结口径过期) —— "
                    "独立报告, 不据此改判正文; 请回 freeze_numbers verify/重新冻结",
        })
    return sorted(drift, key=lambda e: e["claim"])


def _explicit_evidence(tok: _Token, ctx: dict) -> list:
    """高置信**显式关联**证据 (v3.1.1 硬档; 空列表 = 无)。

    只认**文本/标签形态**: claim_label (claim id 完整字面紧邻) / claim_id_marker
    (标签前有显式标记词) / locator_form (locator 叶名紧邻)。源值一致性**不进本档**
    (复审 P1-2: 同值本身不能把正文绑到该主张; 源漂移另立独立报告)。
    """
    evidence = []
    for kind, form in ctx["forms"]:
        start = _form_adjacent(tok, form)
        if start is None:
            continue
        if kind == "claim":
            evidence.append(f"claim_label:{form}")
            if _has_marker(tok, start):
                evidence.append(f"claim_id_marker:{form}")
        else:
            evidence.append(f"locator_form:{form}")
    return evidence


def _weak_signals(tok: _Token, claim: str, rec: dict, forms) -> dict:
    """弱关联证据 (提示档; 只提示, 不硬判同一主张)。

    Returns {"signals", "token_unit", "registry_unit", "objects", "veto"}:
      单位一致 (unit:…) —— 只表示同量纲嫌疑, **不证明同对象**;
      对象词元命中 (object:…) —— 单命中不硬判;
      同段 claim 标签 (claim_label_segment:…) —— 非紧邻的段落级标签;
      veto=True: 两侧单位都识别到且不同 → 判为不同量, 不作同主张比较。
    """
    token_unit = _adjacent_unit(tok) or ""
    registry_unit = str(rec.get("unit") or "")
    n_token, n_reg = _norm_unit(token_unit), _norm_unit(registry_unit)
    veto = bool(n_token and n_reg and n_token != n_reg)
    signals = []
    if n_token and n_reg and n_token == n_reg:
        signals.append(f"unit:{token_unit}")
    objects = sorted(w for w in _object_words(claim, rec)
                     if w in _context_window(tok))
    signals.extend(f"object:{w}" for w in objects)
    for kind, form in forms:
        if _word_in_text(tok.text, form):
            signals.append(f"claim_label_segment:{form}")
            break
    return {"signals": signals, "token_unit": token_unit,
            "registry_unit": registry_unit, "objects": objects, "veto": veto}


# ---------------------------------------------------------------- 来源登记 (C7)

def _iter_json_values(obj, path=""):
    """递归产出 (定位符, 键名小写, 值) 供结果值索引 (口径同 claim_consistency_check)。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield (f"{path}.{k}", str(k).lower(), v)
            yield from _iter_json_values(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                yield from _iter_json_values(v, f"{path}[{i}]")
            else:
                yield (f"{path}[{i}]", f"[{i}]", v)


def _load_manifest(workspace: Path) -> tuple:
    """读 results/run_manifest.jsonl: (记录数, 登记文件相对路径集, note)。

    只认路径与结构 (outputs/inputs 的 path), 不复算哈希 —— 运行有效性由
    run_manifest.py verify 负责; 逐行容错, 坏行跳过并在 note 里说明。
    """
    path = workspace / run_manifest.MANIFEST_REL
    if not path.is_file():
        return 0, set(), "无 run_manifest.jsonl"
    records, files, note = 0, set(), ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return 0, set(), f"run_manifest.jsonl 不可读: {exc}"
    for line_no, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            note = f"run_manifest.jsonl 第 {line_no} 行不是合法 JSON, 已跳过"
            continue
        if not isinstance(rec, dict):
            continue
        records += 1
        for item in list(rec.get("outputs") or []) + list(rec.get("inputs") or []):
            if isinstance(item, dict) and item.get("path"):
                files.add(str(item["path"]))
    return records, files, note


def _load_result_values(workspace: Path) -> tuple:
    """读 results/**/*.json 的数值叶: (登记值, 文件数, 跳过数)。

    登记值 = (尾数, 指数, 来源相对路径, 定位符); 只读复用, 不新建数据库。
    超过 MAX_RESULT_JSON_BYTES 与不可解析的文件计入跳过数。
    """
    results_dir = workspace / "results"
    if not results_dir.is_dir():
        return [], 0, 0
    entries, files_read, skipped = [], 0, 0
    for path in sorted(results_dir.rglob("*.json")):
        try:
            if path.stat().st_size > MAX_RESULT_JSON_BYTES:
                skipped += 1
                continue
            if not _inside_workspace(path, workspace):
                skipped += 1  # symlink/junction 指向工作区外的结果文件不读
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            skipped += 1
            continue
        files_read += 1
        source = path.relative_to(workspace).as_posix()
        for loc, _key, value in _iter_json_values(data):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                v = float(value)
                if math.isfinite(v):
                    entries.append((v, 0, source, loc))
    return entries, files_read, skipped


def _load_ledger_entries(workspace: Path) -> tuple:
    """读证据账本 (state/evidence_ledger.json, 缺则 state/paper_plan.json) 的登记值。

    行结构复用 trace_claims.normalize_rows (evidence_ledger/claims/数组三种输入);
    取每行 result 字段里的数字 (问题→模型→结果→验证 链上的"结果"一列)。
    Returns (登记值, 行数, note)。
    """
    for rel in LEDGER_RELS:
        path = workspace / rel
        if not path.is_file():
            continue
        if not _inside_workspace(path, workspace):
            return [], 0, f"证据账本在工作区外 (resolve 后): {rel.as_posix()}, 未读取"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = trace_claims.normalize_rows(payload)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            return [], 0, f"证据账本不可用: {rel.as_posix()} ({exc})"
        entries = []
        for idx, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                continue
            text = row.get("result")
            if not isinstance(text, str) or not text.strip():
                continue
            rid = str(row.get("question") or row.get("question_id") or f"row{idx}")
            for tok in collect_tokens([(text, False)]):
                entries.append((tok.mant, tok.exp, f"{rel.as_posix()}#{rid}", "result"))
        return entries, len(rows), ""
    return [], 0, "无证据账本 (state/evidence_ledger.json / state/paper_plan.json)"


def load_provenance(workspace: Path) -> dict:
    """读**已有**来源登记 (只读复用, 不新建数据库): 冻结表以外的结果出处。

    来源: ① results/run_manifest.jsonl 的运行登记 (outputs/inputs 路径清单);
    ② results/**/*.json 的数值叶; ③ 证据账本 (trace_claims 的两种输入)。

    available 只表示"存在登记来源" (路径登记**或**值证据), 不代表有可用于同值匹配
    的证据 —— 只看 available 会误解: run_manifest 路径本身不含数值, 覆盖判定无从
    进行。故另给 value_evidence (是否有可匹配的值) 与 path_registration_only
    (仅有路径登记), 未覆盖口径按 value_evidence 措辞。
    """
    workspace = Path(workspace)
    entries, ledger_rows, ledger_note = _load_ledger_entries(workspace)
    if not workspace.is_dir():
        return {"entries": entries, "available": False, "value_evidence": bool(entries),
                "path_registration_only": False, "workspace": workspace.as_posix(),
                "manifest_records": 0, "manifest_files": [],
                "result_files": 0, "skipped_files": 0, "ledger_rows": ledger_rows,
                "note": f"工作区不存在: {workspace.as_posix()}; 登记来源未核; {ledger_note}"}
    manifest_records, manifest_files, manifest_note = _load_manifest(workspace)
    result_entries, result_files, skipped = _load_result_values(workspace)
    entries = result_entries + entries
    value_evidence = bool(entries)
    available = bool(value_evidence or manifest_files)
    path_only = bool(manifest_files) and not value_evidence
    notes = [n for n in (manifest_note, ledger_note) if n]
    if skipped:
        notes.append(f"{skipped} 个结果文件超限/不可解析, 已跳过")
    if not available:
        notes.append("登记不足: 无可用 results 登记与证据账本")
    elif path_only:
        notes.append("仅有路径登记 (run_manifest 记录), 无值证据: 同值覆盖判定"
                     "无从进行, 未覆盖口径不得当作已核出处")
    return {"entries": entries, "available": available,
            "value_evidence": value_evidence,
            "path_registration_only": path_only,
            "workspace": workspace.as_posix(),
            "manifest_records": manifest_records,
            "manifest_files": sorted(manifest_files),
            "result_files": result_files, "skipped_files": skipped,
            "ledger_rows": ledger_rows, "note": "; ".join(notes)}


def _registry_hit(tok: _Token, entries) -> dict:
    """token 能否在登记来源里溯源到同值 (口径复用 claim_consistency_check 规则 5)。

    - 整数 token 要求精确同值;
    - 小数 token 按声明精度舍入匹配, 并接受百分数口径互认 (98.96% ↔ 0.9896);
    - 科学记数法 token 走缩放尾数舍入 / 相对 0.1% / log10 域等价。
    Returns 命中明细 {"source", "locator"} 或 None (未找到 ≠ 不存在)。
    """
    for mant, exp, source, locator in entries:
        if _pair_equiv(tok.mant, tok.exp, mant, exp, REL_TOL_EXACT):
            return {"source": source, "locator": locator}
        if _registry_rounding_hit(tok, mant, exp):
            return {"source": source, "locator": locator}
    return None


def _registry_rounding_hit(tok: _Token, mant: float, exp: int) -> bool:
    """登记值按 token 声明精度舍入后是否等于 token 值 (百分数互认)。

    整数 token (nd=0) 不做舍入匹配; 科学记数法 token 先缩放到尾数口径,
    缩放不可表示 (极大/极小指数) 时退化为 log10 域 REL_TOL_SCI 比较。
    """
    value = _pair_value(mant, exp)
    if value is None:
        return False
    if tok.exp == 0:
        if tok.nd == 0:
            return value == tok.mant
        target = round(tok.mant, tok.nd)
        return any(round(cand, tok.nd) == target
                   for cand in (value, value * 100.0, value / 100.0))
    scale = _pair_value(1.0, tok.exp)
    if scale is None or scale == 0.0:
        # 指数下溢 (10^-400 → 0.0) 或上溢: 走 log10 域。**必须复用 _pair_equiv** ——
        # 只比 log10(|v|) 会丢掉符号 (复审 P2: 源值 2.345e-400 曾覆盖 -2.345×10⁻⁴⁰⁰),
        # 也不设绝对容差下限 (与检查 1 同一口径)。
        return _pair_equiv(tok.mant, tok.exp, mant, exp, REL_TOL_SCI)
    scaled = value / scale
    if not math.isfinite(scaled):
        return False
    if round(scaled, tok.nd) == round(tok.mant, tok.nd):
        return True
    target = _pair_value(tok.mant, tok.exp)
    return (target is not None and target != 0
            and abs(value - target) <= REL_TOL_SCI * abs(target))


# ---------------------------------------------------------------- 文档文本提取

def extract_docx_segments(docx_path: Path) -> list:
    """按文档序提取 (text, in_display_math) 段: 正文段落 + 表格单元格。

    段落文本按文档序交错并入 OMML 公式内容 (python-docx 的 paragraph.text 不含
    公式, 不并则公式里的冻结数字全部漏检); 每个公式块后补一个空格, 防相邻公式
    展平后首尾粘连把指数串位 (实测 "6.65×10-4"+"2.30×10-13" 会粘成 ×10-42.30)。
    纯公式段 (prose 为空且带 oMathPara) 标记 display, 供软检查豁免公式常数。
    """
    from docx import Document
    from docx.oxml.ns import qn

    def _para_segment(p) -> tuple:
        parts = []

        def _walk(el):
            for child in el:
                tag = child.tag
                if tag == qn("w:t"):
                    parts.append(child.text or "")
                elif tag in (qn("m:oMath"), qn("m:oMathPara")):
                    parts.append("".join(t.text or "" for t in child.iter(qn("m:t"))) + " ")
                else:
                    _walk(child)

        _walk(p)
        text = "".join(parts)
        prose = "".join(t.text or "" for t in p.iter(qn("w:t")))
        display = (not prose.strip()) and p.find(qn("m:oMathPara")) is not None
        return text, display

    doc = Document(str(docx_path))
    segments = []
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            segments.append(_para_segment(child))
        elif child.tag == qn("w:tbl"):
            segments.extend(_para_segment(p)
                            for p in child.iter(qn("w:p")))
    # 去掉全空段, 减少无谓扫描
    return [s for s in segments if s[0].strip()]


# ---------------------------------------------------------------- 主检查

def _nearest_tokens(tokens, forms, near_sig: int, limit: int = 3) -> list:
    """与冻结形态数值邻近 (同符号 + 同数量级 + 前 near_sig 位有效数字) 的 token。

    供"缺失"条目的近值诊断: 正文没写原值而写了末位小差的近值 (57.5406 → 57.5403)
    时, 缺失报告里必须直接指出这个近值。按相对差升序, 最多 limit 条。
    """
    out: dict = {}
    for tok in tokens:
        for _claim, _raw, fm, fe, _rec in forms:
            if fm == 0 or (fm > 0) != (tok.mant > 0):
                continue
            d_t, s_t = _decade_sig(tok.mant, tok.exp, near_sig)
            d_f, s_f = _decade_sig(fm, fe, near_sig)
            if d_t is None or d_t != d_f or s_t != s_f:
                continue
            rel = _rel_diff(tok.mant, tok.exp, fm, fe)
            if tok.raw not in out or rel < out[tok.raw]:
                out[tok.raw] = rel
    return [{"token": raw, "rel_diff": rel}
            for raw, rel in sorted(out.items(), key=lambda kv: kv[1])[:limit]]


def _tier_entry(tok: _Token, claim: str, raw: str, rec: dict, rel: float,
                signals: list, note: str) -> dict:
    """提示档条目 (弱关联/仅近邻): 只描述证据与建议, 不宣称同主张成立。"""
    return {
        "token": tok.raw,
        "frozen_claim": claim,
        "frozen_value": raw,
        "frozen_unit": str(rec.get("unit") or ""),
        "token_unit": _adjacent_unit(tok) or "",
        "rel_diff": round(rel, 12) if math.isfinite(rel) else None,
        "evidence": list(signals),
        "segment": tok.seg,
        "excerpt": _excerpt_around(tok),
        "note": note,
    }


def run_recheck(segments, frozen: dict, *, near_sig: int = NEAR_PREFIX_SIG,
                sci_rel_tol: float = REL_TOL_SCI, provenance: dict | None = None) -> dict:
    """执行检查 1 (硬: 冻结数字必须可回溯, A5 缩写三级分流) 与检查 2 (分级)。

    provenance: load_provenance() 的结果; None 时按"登记不足"处理 (只影响提示措辞,
    且不启用 source locator 源值绑定 —— 源值绑定需要工作区)。near_sig /
    sci_rel_tol 为容限配置, 默认取模块常量。
    """
    tokens = collect_tokens(segments)
    plain_tokens = [(t.raw, t.mant) for t in tokens if t.exp == 0]
    full_norm = normalize_text("\n".join(t for t, _ in segments))
    prov = provenance or {}
    prov_entries = list(prov.get("entries") or [])
    # 值证据: 只有"有数值可匹配"才算覆盖判定有依据; 仅路径登记不算 (见 load_provenance)
    has_value_evidence = bool(prov.get("value_evidence", prov.get("entries")))
    workspace = prov.get("workspace")
    record_ctx = _record_contexts(frozen, workspace)
    forms_by_claim = {rc["claim"]: rc["forms"] for rc in record_ctx}
    n_bindings_resolved = sum(1 for rc in record_ctx if rc["source"].get("ok"))

    # ---- 冻结形态全集 (非 stale, display+value): 命中/歧义/邻近判定的共同底座 ----
    frozen_forms = []  # (claim, raw_str, fm, fe, rec)
    for claim, rec in frozen.items():
        if not isinstance(rec, dict) or rec.get("status") == "stale":
            continue
        for field in ("display", "value"):
            raw = rec.get(field)
            if raw is None:
                continue
            fm, fe = _parse_frozen_value(raw)
            if fm is not None:
                frozen_forms.append((claim, str(raw), fm, fe, rec))

    def _form_vkey(fm, fe):
        """数值去重键: 同值不同写法 (0.74 与 7.4e-1) 折叠, 不虚增歧义计数。"""
        if fm == 0:
            return ("0", 0.0)
        sign = ">" if fm > 0 else "<"
        try:
            return (sign, round(math.log10(abs(fm)) + fe, 9))
        except (ValueError, OverflowError):
            return (sign, fm, fe)

    distinct_forms = {}  # vkey → (claim, raw, fm, fe) — 同值只留一个代表
    for claim, raw, fm, fe, _rec in frozen_forms:
        distinct_forms.setdefault(_form_vkey(fm, fe), (claim, raw, fm, fe))

    def _frozen_hit(fm, fe, raw) -> bool:
        if fm is None:  # 非常规数字格式: 按原文包含兜底
            return str(raw).strip() in full_norm
        rel = REL_TOL_EXACT if fe == 0 else sci_rel_tol
        return any(_pair_equiv(fm, fe, t.mant, t.exp, rel) for t in tokens)

    def _token_hits_form(tm: float, nd: int, fm: float, fe: int) -> bool:
        """缩写 token 是否命中某冻结形态 (精确等价, 或该精度四舍五入形态)。"""
        if fe != 0:
            return _pair_equiv(tm, 0, fm, fe, sci_rel_tol)
        if _pair_equiv(tm, 0, fm, 0, REL_TOL_EXACT):
            return True
        return _rounds_to(tm, fm, nd)

    missing, abbrev_only, abbrev_confirm = [], [], []
    n_pass = 0
    for claim, rec in frozen.items():
        if not isinstance(rec, dict) or rec.get("status") == "stale":
            continue  # stale 条目不在终稿核对范围 (须先回填再冻结)
        checked = 0
        hit = False
        for field in ("display", "value"):
            raw = rec.get(field)
            if raw is None:
                continue
            checked += 1
            fm, fe = _parse_frozen_value(raw)
            hit = _frozen_hit(fm, fe, raw)
            if hit:
                break
        if not checked:
            missing.append({"claim": claim, "value": None,
                            "note": "条目缺 value 字段", "nearest": []})
            continue
        if hit:
            n_pass += 1
            continue
        # 未命中: 查缩写形态——必须是**完整数值 token** 且恰为该精度的四舍五入
        # (复审 P1-5: 子串命中不算)。仅对带小数的纯小数冻结值生效。
        fm_v, fe_v = _parse_frozen_value(rec.get("value"))
        nearest = _nearest_tokens(tokens, frozen_forms, near_sig)
        abbrevs = set()
        if fm_v is not None and fe_v == 0 and "." in str(rec.get("value")):
            for tok, mant in plain_tokens:
                if "." in tok and _rounds_to(mant, fm_v, _token_decimals(tok)):
                    abbrevs.add(tok)
        if not abbrevs:
            missing.append({"claim": claim, "value": rec.get("value"),
                            "note": "全文未见原值, 也无缩写形态",
                            "nearest": nearest})
            continue
        # A5-a 缩写歧义 (同前缀多冻结项): token 还能命中**其他键**的冻结形态时,
        # 无法证明它指向本键 (0.7 同时是 0.7403 与 0.7253 的合法缩写) ——
        # 该组强制全匹配, 未全文写出原值即按缺失拦截 (❌)
        unambiguous, rivals = set(), []
        for tok in sorted(abbrevs):
            tm, nd = _safe_float(tok), _token_decimals(tok)
            tok_rivals = sorted({f"{c}={r}" for c, r, fm2, fe2
                                 in distinct_forms.values()
                                 if c != claim and _token_hits_form(tm, nd, fm2, fe2)})
            if not tok_rivals:
                unambiguous.add(tok)
            else:
                rivals = tok_rivals
        if not unambiguous:
            missing.append({"claim": claim, "value": rec.get("value"),
                            "note": f"缩写 {'/'.join(sorted(abbrevs)[:3])} 歧义"
                                    f" (亦可命中 {'/'.join(rivals[:2])}), "
                                    "须全文写出原值",
                            "nearest": nearest})
            continue
        entry = {"claim": claim, "value": rec.get("value"),
                 "abbrev_seen": sorted(unambiguous)[:3]}
        if _value_sig_digits(rec.get("value")) >= ABBREV_CONFIRM_MIN_SIG:
            # A5-b: 冻结值 ≥3 位有效数字 → 人工确认清单 (不拦门禁, stage 9 必查)
            entry["suggestion"] = ("正文该处是否应为原值, 或确认为合法显示精度缩写; "
                                   "并核对同量级他键未与本值串写")
            abbrev_confirm.append(entry)
        else:
            abbrev_only.append(entry)  # A5-c: 冻结值 ≤2 位有效数字 → 维持 warn

    # ---- 检查 2 (v3.1.1): 显式关联冲突 ❌ / 弱关联·邻近提示 ⚠️ / 未覆盖 ⚠️ ----
    def _sig_digits(token: str) -> int:
        m = re.match(r"[+-]?(\d+(?:\.\d+)?)", token)
        digits = (m.group(1) if m else token).replace(".", "").lstrip("0")
        return len(digits) or 1

    def _covered(tok: _Token) -> bool:
        if tok.in_display:
            return True  # display 公式常数豁免 (T-09 口径)
        v = _pair_value(tok.mant, tok.exp)
        if v is not None and v.is_integer() and 1900 <= v <= 2100:
            return True  # 年份白名单
        for _claim, _raw, fm, fe, _rec in frozen_forms:
            rel = REL_TOL_EXACT if fe == 0 else sci_rel_tol
            if _pair_equiv(tok.mant, tok.exp, fm, fe, rel):
                return True
            if fe == 0 and tok.exp == 0 and _rounds_to(tok.mant, fm, tok.nd):
                return True  # 冻结值的缩写形态 (4.88 ← -4.8822), 仅纯小数 token
            if fe != 0 and tok.exp == fe and _rounds_to(tok.mant, fm, tok.nd):
                return True  # 科学记数法缩写形态 (2.09×10⁻³ ← 2.0932e-03),
                # 同指数按尾数舍入判定; 不补此口, 邻近档会把合法缩写当口径冲突拦死
        return False

    conflicts = {}
    weak_assoc, near_hints, unit_mismatch, uncovered = {}, {}, {}, {}
    n_covered, n_source_covered = 0, 0
    for tok in tokens:
        # 1) 显式关联**先判** (复审 P1-1): 不能被"全局冻结值覆盖"抢跑, 也不能被
        #    "有效位数 <4"筛掉 —— 带显式标签的数字即使位数少也是主张表述。
        #    只与被绑定的**可比较**记录比: 该记录自己对得上 → C 级静默; 对不上 →
        #    口径冲突 (含末位小差; 正确值在别处出现也不放过)。
        bound = []
        if not tok.in_display:  # display 公式常数豁免 (T-09 口径)
            for ctx in record_ctx:
                evidence = _explicit_evidence(tok, ctx)
                if evidence and _record_comparable(ctx["rec"]):
                    bound.append((ctx, evidence))
        if bound:
            unmatched = [(ctx, ev) for ctx, ev in bound
                         if not _token_matches_record(tok, ctx["rec"], sci_rel_tol)]
            if not unmatched:
                n_covered += 1  # 绑定的记录自己就一致 → C 级静默
                continue
            ctx, evidence = unmatched[0]
            fm, fe = _parse_frozen_value(ctx["rec"].get("value"))
            rel = _rel_diff(tok.mant, tok.exp, fm, fe) if fm is not None \
                else float("inf")
            conflicts[tok.raw] = {
                "token": tok.raw,
                "frozen_claim": ctx["claim"],
                "frozen_value": ctx["rec"].get("value"),
                "frozen_unit": str(ctx["rec"].get("unit") or ""),
                "rel_diff": round(rel, 12) if math.isfinite(rel) else None,
                "evidence": evidence,
                "also_bound": [c["claim"] for c, _ev in unmatched[1:]],
                "segment": tok.seg,
                "excerpt": _excerpt_around(tok),
                "note": "显式关联同一主张 (证据见 evidence) 但数值不等 (末位小差同判) "
                        "—— 口径冲突, 须修 docx 回退 md 或修冻结后重跑",
            }
            continue
        # 2) 结果样筛选: 纯整数 (页码/章节号/公式号/附件编号) 与位数不足者到此为止
        if tok.exp == 0:
            if tok.nd == 0:
                continue
            if _sig_digits(tok.raw) < SIG_DIGITS_MIN:
                continue
        elif _sig_digits(tok.raw) < 2:
            continue  # 10^-4 这类整尾数量级不算结果数字
        if _covered(tok):
            n_covered += 1  # C 级: 与冻结值/白名单对得上, 静默不打扰
            continue
        # 3) 登记来源覆盖 (非绑定结果值): 有同值即静默 (来源关联)
        if _registry_hit(tok, prov_entries) is not None:
            n_source_covered += 1
            continue
        # 3) 邻近窗口 (同符号 + 同数量级 + 前 near_sig 位有效数字): **只挑提示候选**。
        #    关联证据依次判: 不同量 (单位打架) → 弱关联 → 仅近邻。
        d_t, s_t = _decade_sig(tok.mant, tok.exp, near_sig)
        lg_t = _log10_abs(tok.mant, tok.exp)
        best = None  # (rel_diff, claim, raw, rec)
        if d_t is not None and lg_t is not None:
            for claim, raw, fm, fe, rec in frozen_forms:
                if fm == 0 or (fm > 0) != (tok.mant > 0):
                    continue  # 符号不同不算同前缀口径
                d_f, s_f = _decade_sig(fm, fe, near_sig)
                if d_f != d_t or s_f != s_t:
                    continue
                rel = _rel_diff(tok.mant, tok.exp, fm, fe)
                if best is None or rel < best[0]:
                    best = (rel, claim, raw, rec)
        if best is None:
            uncovered[tok.raw] = {
                "token": tok.raw, "segment": tok.seg,
                "excerpt": _excerpt_around(tok),
                "provenance_available": bool(prov.get("available")),
                "value_evidence": has_value_evidence,
                "note": ("未在冻结表与登记来源中检索到同值; 未登记/未覆盖, "
                         "未找到 ≠ 不存在, 请人工确认口径与出处"
                         + ("" if has_value_evidence
                            else " (登记来源不足: 无可匹配的值证据, 无法核验出处)")),
            }
            continue
        rel, claim, raw, rec = best
        sig = _weak_signals(tok, claim, rec,
                            forms_by_claim.get(claim) or _binding_forms(claim, rec))
        if sig["veto"]:
            unit_mismatch[tok.raw] = _tier_entry(
                tok, claim, raw, rec, rel, sig["signals"],
                f"两侧单位不同 ({sig['token_unit']} vs {sig['registry_unit']}) —— "
                "判为不同量, 不作同主张比较 (数值邻近不构成冲突)")
        elif sig["signals"]:
            weak_assoc[tok.raw] = _tier_entry(
                tok, claim, raw, rec, rel, sig["signals"],
                f"有 {'/'.join(sig['signals'])} 弱关联 (同量纲/对象嫌疑, 不证明同对象) "
                f"且数值不等 (相对差 {_fmt_rel(rel)}, 含末位小差) —— 疑似同主张口径"
                "漂移, 必查; 弱证据不足以硬判, 本档只提示不拦门禁")
        else:
            near_hints[tok.raw] = _tier_entry(
                tok, claim, raw, rec, rel, sig["signals"],
                "仅数值邻近, 无对象/单位/来源关联 —— 不能据此判定同一主张或冲突, "
                "请人工核对 (未找到关联 ≠ 不存在)")
    a_candidates = sorted(
        [dict(e) for e in list(weak_assoc.values()) + list(near_hints.values())
         + list(unit_mismatch.values())],
        key=lambda e: (e["rel_diff"] is None, e["rel_diff"]))
    source_drift = _source_drift_entries(record_ctx)
    source_notes = [{"claim": rc["claim"], "note": rc["source"].get("note") or ""}
                    for rc in record_ctx if not rc["source"].get("ok")]
    return {
        "frozen_total": sum(1 for r in frozen.values()
                            if isinstance(r, dict) and r.get("status") != "stale"),
        "n_pass": n_pass,
        "missing": missing,
        "abbrev_only": abbrev_only,
        "abbrev_confirm": abbrev_confirm,
        "n_fail": len(missing) + len(conflicts),
        # ---- 检查 2 分级 (v3.1.1) ----
        "conflicts": sorted(conflicts.values(),
                            key=lambda e: (e["rel_diff"] is None, e["rel_diff"])),
        "weak_associations": sorted(weak_assoc.values(),
                                    key=lambda e: (e["rel_diff"] is None, e["rel_diff"])),
        "near_hints": sorted(near_hints.values(),
                             key=lambda e: (e["rel_diff"] is None, e["rel_diff"])),
        "unit_mismatch": sorted(unit_mismatch.values(),
                                key=lambda e: (e["rel_diff"] is None, e["rel_diff"])),
        "uncovered": [uncovered[t] for t in sorted(uncovered)],
        "warn_numbers": sorted(uncovered),  # 兼容旧键: 未覆盖 token 摘要
        "a_candidates": a_candidates,  # 兼容旧键: 邻近值抽查 (弱关联/仅近邻/不同量)
        "n_soft_covered": n_covered,
        "n_source_covered": n_source_covered,
        "n_explicit_bindings": n_bindings_resolved,
        "source_drift": source_drift,
        "source_notes": source_notes,
        "provenance": {k: v for k, v in prov.items() if k != "entries"},
        "evidence_tiers": {
            "hard": "冻结值回溯 (精确/display/声明精度缩写) + 文本显式关联不一致 "
                    "(claim 标签/claim_id 标记/locator 叶名紧邻) —— 拦门禁",
            "hint": "单位/对象词元/同段标签弱关联 + 数值邻近 + 未覆盖 + 源值漂移 "
                    "(独立报告) —— 只提示, 不拦门禁",
            "scope_note": "只声明这两档检查证据; 不构成全文数字全部正确的充分性证明; "
                          "数值距离只用于挑提示候选, 源值同值不绑定正文主张",
        },
    }


def load_frozen(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"[FAIL] 冻结表不可读: {path} ({e})")
        raise SystemExit(2)
    if not isinstance(data, dict):
        print(f"[FAIL] 冻结表顶层应为对象: {path}")
        raise SystemExit(2)
    return data


def _check_tolerances(args):
    """校验容限参数; 非法返回中文错误文本 (None = 合法), 由 main 统一 exit 2。"""
    if not 1 <= args.near_sig_digits <= 6:
        return "--near-sig-digits 须为 1-6 的整数 (邻近窗口位数)"
    try:
        tol = float(args.sci_rel_tol)
    except (TypeError, ValueError):
        tol = float("nan")
    if not (0.0 < tol < 1.0):
        return "--sci-rel-tol 须为 (0, 1) 内的相对容差 (默认 1e-3)"
    return None


def _print_items(title: str, items: list, render) -> None:
    """提示档清单: 最多打印 WARN_LIST_CAP 条, 其余折算一行指向完整报告。"""
    if not items:
        return
    print(f"{title} ({len(items)} 条)")
    for item in items[:WARN_LIST_CAP]:
        print(f"  - {render(item)}")
    if len(items) > WARN_LIST_CAP:
        print(f"  … 其余 {len(items) - WARN_LIST_CAP} 条见 --json / --report")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台中文兜底
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="docx 终稿数字回检: 冻结数字必须在 docx 全文出现 (v2.9.0)")
    parser.add_argument("--docx", type=Path, required=True, help="终稿 docx")
    parser.add_argument("--frozen", type=Path, required=True,
                        help="state/frozen_numbers.json")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("--report", type=Path, default=None,
                        help="完整报告落盘路径 (人读输出只给摘要与路径)")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(),
                        help="登记来源根 (results 登记与证据账本; 默认 cwd)")
    parser.add_argument("--near-sig-digits", type=int, default=NEAR_PREFIX_SIG,
                        help=f"邻近窗口位数 (默认 {NEAR_PREFIX_SIG}; 只挑提示候选)")
    parser.add_argument("--sci-rel-tol", type=float, default=REL_TOL_SCI,
                        help=f"科学记数法等价相对容差 (默认 {REL_TOL_SCI:g})")
    args = parser.parse_args(argv)
    tol_err = _check_tolerances(args)
    if tol_err is not None:
        print(f"[FAIL] {tol_err}")
        return 2

    if not args.docx.is_file():
        print(f"[FAIL] docx 不存在: {args.docx}")
        return 2
    if not args.frozen.is_file():
        print(f"[FAIL] 冻结表不存在: {args.frozen}")
        return 2
    try:
        segments = extract_docx_segments(args.docx)
    except ImportError:
        print("[FAIL] python-docx 不可用; 请 pip install python-docx 后重试")
        return 2
    except Exception as e:  # docx 损坏/非 zip 等统一按环境错误报告
        print(f"[FAIL] docx 解析失败: {e}")
        return 2

    frozen = load_frozen(args.frozen)
    provenance = load_provenance(args.workspace.expanduser())
    report = run_recheck(segments, frozen, near_sig=args.near_sig_digits,
                         sci_rel_tol=args.sci_rel_tol, provenance=provenance)

    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")

    if args.json:
        # 纯 JSON 输出 (机器可读), 人间可读结论不混入 stdout
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if report["n_fail"] else 0

    n_confirm = len(report["abbrev_confirm"])
    print(f"数字回检: 冻结 {report['frozen_total']} 条, 命中 {report['n_pass']}, "
          f"缺失 {len(report['missing'])}, 显式关联冲突 {len(report['conflicts'])} (❌), "
          f"缩写确认 {n_confirm} (人工必查), "
          f"缩写warn {len(report['abbrev_only'])} (≤2位), C7 覆盖 "
          f"{report['n_soft_covered']} + 登记来源覆盖 {report['n_source_covered']}, "
          f"弱关联 {len(report['weak_associations'])} (⚠️), "
          f"仅近邻 {len(report['near_hints'])} (⚠️), "
          f"不同量 {len(report['unit_mismatch'])} (ℹ️), "
          f"未覆盖 {len(report['uncovered'])} (⚠️), "
          f"源漂移 {len(report['source_drift'])} (⚠️独立)")
    for item in report["missing"]:
        near = "".join(f", 近值 {n['token']}(相对差 {_fmt_rel(n['rel_diff'])})"
                       for n in item.get("nearest") or [])
        print(f"  [FAIL] {item['claim']} = {item['value']} ({item['note']}{near})")
    if report["conflicts"]:
        print(f"显式关联冲突 (❌ 拦门禁, {len(report['conflicts'])} 条): 与登记项有"
              "显式文本关联 (claim 标签/claim_id 标记/locator 叶名紧邻) 但数值不等, "
              "含末位小差 —— 须回退 md 或修冻结后重跑")
        for c in report["conflicts"]:
            rel = _fmt_rel(c["rel_diff"]) if c["rel_diff"] is not None else "n/a"
            print(f"  [FAIL-A] {c['token']} ↔ 冻结 {c['frozen_claim']}="
                  f"{c['frozen_value']} (相对差 {rel}; 证据 {'/'.join(c['evidence'])}; "
                  f"段 {c['segment']} “{c['excerpt']}”)")
    # ---- 提示档 (v3.1.1: 只提示, 不拦门禁) ----
    _print_items(
        "弱关联 (⚠️ 单位/对象词元/同段标签, 证据不足硬判; 必查, 不拦门禁)",
        report["weak_associations"],
        lambda e: f"{e['token']} ↔ {e['frozen_claim']}={e['frozen_value']} "
                  f"(相对差 {_fmt_rel(e['rel_diff'])}; 证据 "
                  f"{'/'.join(e['evidence']) or '无'}; 段 {e['segment']} "
                  f"“{e['excerpt']}”)")
    _print_items(
        "仅近邻 (⚠️ 无对象/单位/来源关联, 只提示, 不能判定同一主张或冲突)",
        report["near_hints"],
        lambda e: f"{e['token']} ↔ {e['frozen_claim']}={e['frozen_value']} "
                  f"(相对差 {_fmt_rel(e['rel_diff'])}; 段 {e['segment']} "
                  f"“{e['excerpt']}”)")
    _print_items(
        "不同量对照 (ℹ️ 数值邻近但单位不同, 判为不同量, 不作同主张比较)",
        report["unit_mismatch"],
        lambda e: f"{e['token']} ({e['token_unit']}) ↔ {e['frozen_claim']}="
                  f"{e['frozen_value']} ({e['frozen_unit']})")
    _print_items(
        "未覆盖 (⚠️ 冻结表与登记来源均未见同值; 未登记 ≠ 不存在, 不拦门禁)",
        report["uncovered"],
        lambda e: f"{e['token']} (段 {e['segment']} “{e['excerpt']}”)")
    _print_items(
        "源值漂移 (⚠️ 冻结值与源 locator 当前值不一致; 独立报告, 不据此改判正文)",
        report["source_drift"],
        lambda e: f"{e['claim']}: 冻结 {e['frozen_value']} vs 源 "
                  f"{e['source']}={_fmt_source_value(e['source_value'])}")
    prov = report["provenance"]
    prov_line = (f"登记来源: run_manifest 记录 {prov.get('manifest_records', 0)} 条 / "
                 f"结果文件 {prov.get('result_files', 0)} 个 / "
                 f"证据账本 {prov.get('ledger_rows', 0)} 行 / "
                 f"值证据 {'有' if prov.get('value_evidence') else '无'} / "
                 f"源 locator 可核 {report['n_explicit_bindings']} 条"
                 + (f" / 未核 {len(report['source_notes'])} 条"
                    if report["source_notes"] else ""))
    if not prov.get("available"):
        prov_line += " — 登记不足"
    elif prov.get("path_registration_only"):
        prov_line += " — 仅路径登记 (无值证据, 同值覆盖判定无从进行)"
    if prov.get("note"):
        prov_line += f" ({prov['note']})"
    print(prov_line)
    tiers = report["evidence_tiers"]
    print(f"证据口径: 只声明两档 —— ① {tiers['hard']}; ② {tiers['hint']}。"
          f"{tiers['scope_note']}")
    # ---- A5 缩写确认清单: 单独一节, stage 9 必查 ----
    if n_confirm:
        print(f"⚠️ 缩写形态需人工确认（{n_confirm} 条）: 冻结值 ≥3 位有效数字, "
              "正文仅见缩写形态, 门禁不拦但 stage 9 必查")
        for item in report["abbrev_confirm"]:
            print(f"  - {item['claim']} = {item['value']} | 正文缩写: "
                  f"{'/'.join(item['abbrev_seen'])} | 核对点: {item['suggestion']}")
    for item in report["abbrev_only"]:
        print(f"  [WARN] {item['claim']} = {item['value']} "
              f"仅见缩写 {'/'.join(item['abbrev_seen'])} (冻结值 ≤2 位)")

    if args.report is not None:
        print(f"详细报告: {args.report.expanduser().resolve()}")
    if report["n_fail"]:
        print(f"[FAIL] 缺失/显式关联冲突 共 {report['n_fail']} 条: docx 呈现层改动"
              "触及禁区数字或口径打架, 须回退 md 修改重走导出 (提示档不拦门禁)")
        if n_confirm:
            print(f"ACTION: stage9-必查 缩写确认 {n_confirm} 条")
        return 1
    print("[OK] 冻结数字全部可回溯 (缩写确认清单/提示档不影响门禁)")
    if n_confirm:
        print(f"ACTION: stage9-必查 缩写确认 {n_confirm} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
