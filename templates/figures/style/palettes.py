# -*- coding: utf-8 -*-
"""
mathmodel-studio v7.9.0 统一图表配色源
================================================================
全 skill 图表配色以此模块为准（规范文档: references/color_typology.md,
设计令牌: references/design_tokens.md）。

v7.9.0 起新增示意图版式令牌层（DIAGRAM_GRID 4px 网格 / DIAGRAM_RADIUS 圆角
阶梯 / DIAGRAM_STROKE_W 描边三档 / DIAGRAM_FONT_RAMP 扁平字阶 /
DIAGRAM_FONT_MONO 数字标签等宽链 / DIAGRAM_FOCAL_MAX 焦点盒上限）,
纪律蒸馏自 diagram-design (MIT), 取口 get_diagram_token() / snap4()。

v7.8.0 起配色彻底分类: 数据图表(figure)用下方 PALETTES 高饱和色板区分
数据系列; 示意图(diagram/流程图/架构图/技术路线图)用 DIAGRAM_FAMILIES
浅底色族表达结构层级, 两套体系并列、互不影响。

离散色板:
  - academic_blue  中文竞赛主战色板（默认首选）
  - cool_nature    历史竞赛工作区 fig_style.py 冷色 Nature/IEEE 期刊风
  - muted_earth    历史竞赛工作区 plot_utils.py PAPER_COLORS 灰蓝金低饱和
  - okabe_ito      色盲安全兜底（MCM 英文赛/灰度打印场景）
  - npg            Nature 系期刊色板（蒸馏自 ggsci NPG 公开色值）
  - aaas           Science 系期刊色板（蒸馏自 ggsci AAAS 公开色值）
  - lancet         Lancet 系期刊色板（蒸馏自 ggsci Lancet 公开色值）
  - nejm           NEJM 系期刊色板（蒸馏自 ggsci NEJM 公开色值）

中性色令牌 (NEUTRALS): 正文/次级文字/网格/描边/箭头/面板底色统一出口,
  示意图与数据图共用, 禁止在脚本里另行硬编码灰色系。

示意图色族 (DIAGRAM_FAMILIES, v7.8.0): 与数据色板并列的"浅底色族"体系,
  色值 1:1 蒸馏自 sci-box scibox-diagram (MIT), 供流程图/架构图等结构类
  示意图表达层级, 不用于数据系列区分。

工具函数:
  get_palette / apply_palette / get_cmap      取色与注入（v7.4.0 已有）
  get_neutral / get_semantic                  中性色与语义角色取色
  get_diagram_family / get_diagram_families   示意图色族取色（v7.8.0 新增）
  get_diagram_page                            示意图页面令牌取色（v7.8.0 新增）
  tint / shade                                参数化浅化/深化（替代手写浅化常量）
  grayscale_check                             灰度可区分性校验（支持全对模式）

用法:
  from palettes import get_palette, apply_palette, tint, get_neutral
  apply_palette("academic_blue")            # 全局注入 axes.prop_cycle
  colors = get_palette("npg")               # 纯取色值, 不依赖 matplotlib
  light = tint("#1F4E79", 0.80)             # 向白混合 80%
  ok, warns = grayscale_check(colors, all_pairs=True)

自测: python palettes.py
"""
from __future__ import annotations

# ============================================================
# 色板注册表
# ============================================================
# 每项: "色值列表" + "source 来源说明"
PALETTES: dict[str, dict] = {
    # 默认首选: 中文竞赛评委熟悉的高对比蓝橙体系, 全文主色绑定它
    "academic_blue": {
        "colors": ["#1F4E79", "#2E86AB", "#F18F01", "#C73E1D", "#3B8C6E", "#6C757D"],
        "source": "蒸馏自历史竞赛工作区实战验证配色: 深蓝主色 #1F4E79, "
                  "青蓝 #2E86AB, 橙强调 #F18F01, 红警示 #C73E1D, 绿正向 #3B8C6E, "
                  "中性灰 #6C757D (参考线/网格); 另有紫 #7E57C2 可作第 7 序列备用",
    },
    # 冷色 Nature/IEEE 期刊风: 低饱和冷色为主, 单一暖橙强调
    "cool_nature": {
        "colors": ["#2C3E50", "#1F77B4", "#17A2B8", "#6C8EBF", "#D97706", "#C0392B"],
        "source": "历史竞赛工作区 code/fig_style.py: 深蓝灰 #2C3E50 / 学术蓝 #1F77B4 / 青蓝 #17A2B8 / "
                  "浅蓝灰 #6C8EBF 为主色族, 暖橙 #D97706 为唯一强调色, 暗红 #C0392B 仅作警告; "
                  "配套 (a)(b)(c) 子图编号 + 去顶右 spines",
    },
    # 灰蓝金低饱和: 评价对比类图表, 稳重学术
    "muted_earth": {
        "colors": ["#506B84", "#A77A43", "#6E8B74", "#8B4F4A", "#7C8A96", "#39444D"],
        "source": "历史竞赛工作区 plot_utils.py PAPER_COLORS: 灰蓝 #506B84 / 金 #A77A43 / 灰绿 #6E8B74 / "
                  "灰红 #8B4F4A / 灰 #7C8A96, 第 6 色取其正文深灰 #39444D; "
                  "各色另有 *_light 浅色变体 (#DCE5EC/#E6D7BE/#DCE7DF/#EADAD8) 可作填充底色",
    },
    # 色盲安全兜底: Okabe-Ito 标准八色, MCM 英文赛或需灰度打印时用
    "okabe_ito": {
        "colors": ["#0072B2", "#E69F00", "#009E73", "#D55E00",
                   "#CC79A7", "#56B4E9", "#F0E442", "#000000"],
        "source": "Okabe & Ito (2008) 色盲通用色板, 公共领域标准色值",
    },
    # ---- v7.7.0 新增: 真·期刊色板, 色值蒸馏自 ggsci 文档公开色值 ----
    # NPG (Nature Publishing Group): 高辨识暖冷对撞, 近年 ML/生信论文出镜率最高
    "npg": {
        "colors": ["#E64B35", "#4DBBD5", "#00A087", "#3C5488",
                   "#F39B7F", "#8491B4", "#91D1C2", "#DC0000", "#7E6148", "#B09C85"],
        "source": "ggsci NPG (Nature Reviews 系列) 公开色值: 朱红 #E64B35 / 青 #4DBBD5 / "
                  "墨绿 #00A087 / 靛蓝 #3C5488 为主四色; 论文感强, 适合英文投稿与答辩 PPT",
    },
    # AAAS (Science): 深蓝主调, 克制稳重
    "aaas": {
        "colors": ["#3B4992", "#EE0000", "#008B45", "#631879",
                   "#008280", "#BB0021", "#5F559B", "#A20056", "#808180", "#1B1919"],
        "source": "ggsci AAAS (Science 系列) 公开色值: 靛蓝 #3B4992 主色, 正红 #EE0000 仅作强调, "
                  "绿 #008B45 / 紫 #631879 / 青 #008280 辅助",
    },
    # Lancet: 深蓝+正红经典医学期刊对色
    "lancet": {
        "colors": ["#00468B", "#ED0000", "#42B540", "#0099B4",
                   "#925E9F", "#FDAF91", "#AD002A", "#ADB6B6", "#1B1919"],
        "source": "ggsci Lancet 公开色值: 皇家蓝 #00468B / 正红 #ED0000 经典对色, "
                  "绿 #42B540 / 青 #0099B4 / 紫 #925E9F 辅助",
    },
    # NEJM: 砖红+钢蓝暖冷平衡, 低攻击性的高级感
    "nejm": {
        "colors": ["#BC3C29", "#0072B5", "#E18727", "#20854E",
                   "#7876B1", "#6F99AD", "#FFDC91", "#EE4C97"],
        "source": "ggsci NEJM (新英格兰医学杂志) 公开色值: 砖红 #BC3C29 / 钢蓝 #0072B5 主对色, "
                  "琥珀 #E18727 / 松绿 #20854E 辅助",
    },
}

# 向后兼容别名: 旧文档中的名称 → 新标准名
ALIASES: dict[str, str] = {
    "champion_palette": "academic_blue",  # huashubei_figure_pack.md 旧色板名
    "nature": "npg",                      # 口语化别名
    "science": "aaas",
}

# 连续/矩阵类图表的 colormap 约定 (kind → matplotlib cmap 名)
CMAPS: dict[str, str] = {
    "sequential": "viridis",        # 数值梯度: 感知均匀, 灰度友好
    "diverging": "RdBu_r",          # 双向对比: 残差/灵敏度正负, 须以 0 为中心
    "correlation": "RdBu_r",        # 相关系数矩阵: -1 蓝 ~ +1 红, 须以 0 为中心
    "confusion_matrix": "Blues",    # 混淆矩阵: 计数越大越深
    "heatmap": "viridis",           # 通用热力图默认; 语义特殊时按 color_typology 换
    "sequential_alt": "cividis",    # 色盲更稳的 sequential 备选
}

# ============================================================
# 中性色令牌层 (v7.7.0)
# ============================================================
# 示意图/数据图所有"非语义灰色"一律从这里取, 禁止脚本内另行硬编码。
NEUTRALS: dict[str, str] = {
    "ink":          "#1F2A36",  # 正文/标题主文字（近黑深蓝灰, 比纯黑柔和）
    "secondary":    "#46535F",  # 次级文字/注释
    "faint":        "#8A97A3",  # 弱化文字/水印级
    "grid":         "#D9DEE4",  # 数据图网格线
    "edge":         "#C7D3DE",  # 卡片/节点盒描边
    "edge_strong":  "#A9BDD0",  # 节点盒强调描边
    "arrow":        "#6B7B8C",  # 示意图连接箭头
    "panel_bg":     "#F5F7FA",  # 面板/泳道浅底色
    "hairline":     "#E8ECF0",  # 分隔细线
    "white":        "#FFFFFF",
}

# 语义角色 → 取色规则 (角色名 → 说明; 实际色值由色板位置决定, 见 color_typology §4)
SEMANTIC_ROLES: dict[str, str] = {
    "primary":   "主模型/本文方法 → 色板第 1 色",
    "baseline":  "基线/对照 → 色板第 2 色或中性灰, 全文恒定",
    "accent":    "强调/阈值/最优 → 色板中的橙系, 每图至多一处",
    "risk":      "风险/劣化/显著负向 → 色板中的红系",
    "ok":        "达标/改进/显著正向 → 色板中的绿系",
    "reference": "参考线/基准线 → NEUTRALS['arrow'] 灰",
}


# ============================================================
# 示意图色族 (v7.8.0): 与数据色板彻底分类的第二套体系
# ============================================================
# 分类原则: 数据图表(figure)用 PALETTES 高饱和色板区分"数据系列";
# 示意图(diagram/流程图/架构图/技术路线图)用这里的浅底色族表达"结构层级"。
# 角色语义:
#   fill          内容盒浅底（卡片/节点默认底色）
#   stroke        内容盒描边（同族中明度, 比底色深一档）
#   accent        强调填充（子标题条/高亮盒）
#   deep          深一档内容填充（次级层级盒）
#   header        实色标题条底（配白字）
#   header_stroke 标题条描边（比 header 再深一档）
#   edge          连接器/箭头色（跨族不混色）
#   chevron       旗标/徽章填充（编号徽章/层名旗标底）
DIAGRAM_FAMILIES: dict[str, dict[str, str]] = {  # 色值 1:1 蒸馏自 sci-box scibox-diagram (MIT), 见 references/color_typology.md
    "blue":   {"fill": "#EEF6FD", "stroke": "#3B547F", "accent": "#B6D8F6", "deep": "#A8C0EA",
               "header": "#4060B0", "header_stroke": "#2C4488", "edge": "#1F3F6B", "chevron": "#98D0ED"},
    "orange": {"fill": "#FCEAD9", "stroke": "#C08B5C", "accent": "#FDDECD", "deep": "#F8D0B0",
               "header": "#D06818", "header_stroke": "#A04E10", "edge": "#7B5530", "chevron": "#F8D5B3"},
    "purple": {"fill": "#E5DFEB", "stroke": "#9B979F", "accent": "#CCC2DB", "deep": "#C8C1D9",
               "header": "#8D84A8", "header_stroke": "#6E6584", "edge": "#7F5FAF", "chevron": "#C8C1D9"},
    "teal":   {"fill": "#DBEEF4", "stroke": "#668D89", "accent": "#BAE2E4", "deep": "#A8E0E0",
               "header": "#1F6F6F", "header_stroke": "#14504F", "edge": "#5F8484", "chevron": "#D4EAE4"},
    "green":  {"fill": "#E6F4DC", "stroke": "#6A9A4A", "accent": "#C8E8B0", "deep": "#C8E8B0",
               "header": "#3A5A22", "header_stroke": "#2A4318", "edge": "#3A5A22", "chevron": "#D8EEC8"},
    "olive":  {"fill": "#FBF3D2", "stroke": "#B8A23A", "accent": "#F6E6A4", "deep": "#F6E6A4",
               "header": "#8A7A1A", "header_stroke": "#665A12", "edge": "#665A12", "chevron": "#F6E6A4"},
    "grey":   {"fill": "#F2F4F6", "stroke": "#8A97A3", "accent": "#DDE4EA", "deep": "#D9D9D9",
               "header": "#5B6B78", "header_stroke": "#46535F", "edge": "#5B6B78", "chevron": "#E4E9EE"},
}

# 示意图页面级令牌: 页底/墨色/通栏标题条/分带点线/外框/循环箭头/纯白
DIAGRAM_PAGE: dict[str, str] = {
    "bg": "#F2EEF7", "ink": "#262626", "title_bar": "#4F80BD", "band_sep": "#5B6B78",
    "frame": "#808080", "loop_arrow": "#CCCCD6", "white": "#FFFFFF",
}

DIAGRAM_ORDER_GENERIC = ["blue", "teal", "olive", "orange", "purple", "green", "grey"]  # 通用 n 阶段取色顺序
DIAGRAM_ORDER_ROADMAP = ["blue", "blue", "orange", "purple", "teal"]   # 五带路线图(1:1 sci-box 叙事)

# 示意图字体链: YaHei 有真 700 粗体(msyhbd.ttc)排首位; Noto Sans SC 为可变字体
# (matplotlib 只注册到 weight=100, 加粗不可用), 排在 PingFang SC 之后作末端兜底。
DIAGRAM_FONT_FAMILY = ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans SC",
                       "Arial Unicode MS", "Helvetica"]

# ============================================================
# 示意图版式令牌 (v7.9.0): 网格/圆角/描边/字阶/mono
# 蒸馏自 diagram-design (MIT) 的编辑级排版纪律, 本地化为中文论文示意图:
#   - 4px 网格硬规则: 一切坐标/宽/高/间距必须可被 4 整除(手排坐标先 snap4)
#   - 圆角阶梯 sm/md/lg = 4/6/8, 上限 10, 禁止再大(大会显"AI 味")
#   - 描边四档: 细线 0.8 / 卡片 1.0 / 默认 1.2 / 强调 2.0, 不随手给值
#     （v7.9.1 新增 card=1.0: 内容卡降重, 密集图里每一笔都不抢戏）
#   - 字阶扁平: 全图 ≤4 档(标题16/标题条12/正文10.5/注释9);
#     v7.9.1 起字重回层级制: 标题条/徽章/卡片标题加粗, 卡内正文常规字重
#   - mono 字体只用于数字/参数/公式标签(如 RMSE=2.31), 节点名一律 sans
# ============================================================
DIAGRAM_GRID = 4                      # px, 硬规则
DIAGRAM_RADIUS = {"sm": 4, "md": 6, "lg": 8}          # 圆角阶梯, 上限 10
DIAGRAM_STROKE_W = {"hairline": 0.8, "card": 1.0, "default": 1.2, "strong": 2.0}
DIAGRAM_FONT_RAMP = {"title": 16, "header": 12, "body": 10.5, "note": 9}
DIAGRAM_FONT_MONO = ["Consolas", "DejaVu Sans Mono", "Courier New"]

# 焦点盒规则 (diagram-design focal rule 本地化): 每图至多 1-2 个焦点节点,
# 焦点 = 族 accent 底 + 族 stroke 描边 2.0; 超过 2 个焦点等于没有焦点。
DIAGRAM_FOCAL_MAX = 2


# ============================================================
# 取色接口 (纯 stdlib, 不依赖 matplotlib)
# ============================================================
def get_palette(name: str | None = None) -> list[str]:
    """按名称返回色值列表。

    Args:
        name: 色板名 (academic_blue/cool_nature/muted_earth/okabe_ito/
              npg/aaas/lancet/nejm), None 取默认 academic_blue;
              别名 champion_palette/nature/science 亦可用。

    Returns:
        色值列表 (hex 字符串, 顺序即绘制顺序)。

    Raises:
        ValueError: 名称未注册时, 附可用名称清单。
    """
    if name is None:
        name = "academic_blue"
    key = ALIASES.get(name.lower(), name.lower())
    if key not in PALETTES:
        raise ValueError(
            f"未知色板 '{name}'. 可用: {sorted(PALETTES)} (别名: {ALIASES})"
        )
    return list(PALETTES[key]["colors"])


def get_cmap(kind: str) -> str:
    """按图表语义返回 colormap 名称。

    Args:
        kind: sequential/diverging/correlation/confusion_matrix/heatmap/
              sequential_alt 之一。diverging 与 correlation 使用时
              必须以 0 为色标中心 (center=0 / TwoSlopeNorm(0))。

    Returns:
        matplotlib cmap 名称字符串。
    """
    try:
        return CMAPS[kind]
    except KeyError:
        raise ValueError(
            f"未知 cmap 类型 '{kind}'. 可用: {sorted(CMAPS)}"
        ) from None


def get_neutral(name: str) -> str:
    """按令牌名取中性色。

    Args:
        name: ink/secondary/faint/grid/edge/edge_strong/arrow/panel_bg/
              hairline/white 之一。

    Returns:
        hex 色值字符串。
    """
    try:
        return NEUTRALS[name]
    except KeyError:
        raise ValueError(
            f"未知中性色令牌 '{name}'. 可用: {sorted(NEUTRALS)}"
        ) from None


# ============================================================
# 示意图色族取色接口 (v7.8.0, 纯 stdlib, 不依赖 matplotlib)
# ============================================================
def get_diagram_family(name: str) -> dict[str, str]:
    """按族名取一枝示意图色族（8 角色色值字典的副本）。

    Args:
        name: blue/orange/purple/teal/green/olive/grey 之一。

    Returns:
        族色值字典副本, 键为 fill/stroke/accent/deep/header/
        header_stroke/edge/chevron。

    Raises:
        ValueError: 族名未注册时, 附可用族清单。
    """
    key = str(name).strip().lower()
    if key not in DIAGRAM_FAMILIES:
        raise ValueError(
            f"未知示意图色族 '{name}'. 可用: {sorted(DIAGRAM_FAMILIES)}"
        )
    return dict(DIAGRAM_FAMILIES[key])


def get_diagram_families(order: list[str] | None = None,
                         n: int | None = None) -> list[dict[str, str]]:
    """按顺序取 n 族示意图色族（通用 n 阶段取色入口）。

    Args:
        order: 族名顺序列表; None 用 DIAGRAM_ORDER_GENERIC。
        n: 需要的族数; 小于顺序长度时截断, 超过时循环取; None 取全序。

    Returns:
        族色值字典列表（与 order 对齐）。

    Raises:
        ValueError: order 为空 / n < 1 / 顺序中含未注册族名（附可用清单）。
    """
    seq = list(order) if order is not None else list(DIAGRAM_ORDER_GENERIC)
    if not seq:
        raise ValueError("order 不能为空列表")
    if n is not None:
        if n < 1:
            raise ValueError(f"n 必须 >= 1, 实际 {n}")
        seq = [seq[i % len(seq)] for i in range(n)]
    return [get_diagram_family(k) for k in seq]


def get_diagram_page(token: str) -> str:
    """按令牌名取示意图页面色。

    Args:
        token: bg/ink/title_bar/band_sep/frame/loop_arrow/white 之一。

    Returns:
        hex 色值字符串。
    """
    try:
        return DIAGRAM_PAGE[token]
    except KeyError:
        raise ValueError(
            f"未知示意图页面令牌 '{token}'. 可用: {sorted(DIAGRAM_PAGE)}"
        ) from None


# ============================================================
# 示意图版式令牌取口 (v7.9.0)
# ============================================================
_DIAGRAM_TOKEN_GROUPS = {
    "radius": DIAGRAM_RADIUS,
    "stroke_w": DIAGRAM_STROKE_W,
    "font_ramp": DIAGRAM_FONT_RAMP,
}


def get_diagram_token(group: str, key: str):
    """取示意图版式令牌（radius/stroke_w/font_ramp 三组之一的具体档位）。

    Args:
        group: "radius" | "stroke_w" | "font_ramp"。
        key:   radius → sm/md/lg; stroke_w → hairline/default/strong;
               font_ramp → title/header/body/note。

    Returns:
        数值令牌（px 或 pt）。
    """
    try:
        table = _DIAGRAM_TOKEN_GROUPS[group]
    except KeyError:
        raise ValueError(
            f"未知示意图令牌组 '{group}'. 可用: {sorted(_DIAGRAM_TOKEN_GROUPS)}"
        ) from None
    try:
        return table[key]
    except KeyError:
        raise ValueError(
            f"令牌组 '{group}' 无档位 '{key}'. 可用: {sorted(table)}"
        ) from None


def snap4(value: float, grid: int = DIAGRAM_GRID) -> float:
    """把坐标/尺寸捕捉到 grid 网格（默认 4px 硬规则, diagram-design 纪律）。

    手排示意图坐标时一律先过 snap4: 同族同宽同步距 + 全部对齐 4px 网格,
    是"不像 AI 随手摆"的最廉价手段。返回 int 或 float（恰好整除时给 int）。
    """
    if grid <= 0:
        raise ValueError(f"grid 必须为正, 实际 {grid}")
    snapped = round(value / grid) * grid
    return int(snapped) if snapped == int(snapped) else float(snapped)


# ============================================================
# 参数化浅化/深化 (v7.7.0): 替代各脚本手写的浅化常量
# ============================================================
def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    text = hex_color.strip().lstrip("#")
    if len(text) != 6 or any(c not in "0123456789abcdefABCDEF" for c in text):
        raise ValueError(f"非法色值 '{hex_color}', 需要 #RRGGBB 格式")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def tint(hex_color: str, factor: float) -> str:
    """向白色混合, 得到浅化色。

    Args:
        hex_color: #RRGGBB 原色。
        factor: 0=原色, 1=纯白; 常用 0.4-0.9 (面板底色/色带浅化)。

    Returns:
        浅化后的 #RRGGBB。
    """
    if not 0 <= factor <= 1:
        raise ValueError(f"tint factor={factor} 越界, 应在 [0, 1]")
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(
        round(r + (255 - r) * factor),
        round(g + (255 - g) * factor),
        round(b + (255 - b) * factor),
    )


def shade(hex_color: str, factor: float) -> str:
    """向黑色混合, 得到深化色。

    Args:
        hex_color: #RRGGBB 原色。
        factor: 0=原色, 1=纯黑; 常用 0.15-0.4 (描边/徽章压深)。

    Returns:
        深化后的 #RRGGBB。
    """
    if not 0 <= factor <= 1:
        raise ValueError(f"shade factor={factor} 越界, 应在 [0, 1]")
    r, g, b = _hex_to_rgb(hex_color)
    return _rgb_to_hex(
        round(r * (1 - factor)),
        round(g * (1 - factor)),
        round(b * (1 - factor)),
    )


def tint_series(hex_color: str, n: int, lo: float = 0.80, hi: float = 0.42) -> list[str]:
    """生成 n 级等差浅化序列 (供五层路线图色带等场景)。

    Args:
        hex_color: 基色。
        n: 级数。
        lo: 第一级浅化度 (最浅), hi: 最后一级浅化度 (最深); 默认与
            roadmap 模板原手写常量 strip_white=[0.80..0.44] 视觉等价。
    """
    if n < 1:
        raise ValueError("n 必须 >= 1")
    if n == 1:
        return [tint(hex_color, hi)]
    step = (lo - hi) / (n - 1)
    return [tint(hex_color, lo - i * step) for i in range(n)]


# ============================================================
# 应用到 matplotlib
# ============================================================
def apply_palette(name: str | None = None, ax=None) -> list[str]:
    """把色板注入 matplotlib 取色循环。

    Args:
        name: 色板名, 同 get_palette; None 取默认 academic_blue。
        ax: 给定 Axes 时只改该子图的 prop_cycle; None 时改全局 rcParams。

    Returns:
        实际注入的色值列表 (方便调用方再绑定图例/标注)。

    Raises:
        ImportError: matplotlib 未安装时给出安装指引而非裸报错。
    """
    colors = get_palette(name)
    try:
        import matplotlib as mpl
    except ImportError as exc:  # pragma: no cover - 环境缺依赖时给出友好提示
        raise ImportError(
            "apply_palette 需要 matplotlib。请先 `pip install matplotlib`, "
            "或改用 get_palette() 取色值后自行绑定。"
        ) from exc
    if ax is None:
        mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=colors)
    else:
        ax.set_prop_cycle(color=colors)
    return colors


# ============================================================
# 灰度可区分性校验
# ============================================================
def _srgb_to_linear(c: float) -> float:
    """sRGB 通道值 (0-1, 非线性) → 线性光 (IEC 61966-2-1)。"""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color: str) -> float:
    """hex (#RRGGBB) → 相对亮度 L = 0.2126R + 0.7152G + 0.0722B (线性光, 0-1 归一)。"""
    r, g, b = _hex_to_rgb(hex_color)
    return (0.2126 * _srgb_to_linear(r / 255.0)
            + 0.7152 * _srgb_to_linear(g / 255.0)
            + 0.0722 * _srgb_to_linear(b / 255.0))


def grayscale_check(colors: list[str], min_delta: float = 0.15,
                    all_pairs: bool = False) -> tuple[bool, list[str]]:
    """校验色板在灰度打印下是否可区分。

    把每个 hex 转相对亮度, 默认检查绘制顺序中相邻两色的亮度差是否 >= min_delta;
    all_pairs=True 时检查所有两两组合 (更严, 适合多系列同图场景)。
    不达标的色对, 打印时需用线型/marker/填充纹理补区分。

    Args:
        colors: hex 色值列表。
        min_delta: 最小亮度差阈值, 默认 0.15。
        all_pairs: True 检查全组合, False 只查相邻对 (v7.4.0 行为)。

    Returns:
        (是否全部达标, 警告消息列表)。
    """
    if not colors:
        return False, ["色板为空列表, 无可校验颜色, 视为不达标"]
    if not 0 <= min_delta <= 1:
        return False, [f"min_delta={min_delta} 越界, 应在 [0, 1] (相对亮度差取值范围)"]
    luminances = [_relative_luminance(c) for c in colors]
    warnings: list[str] = []
    pairs = ((i, j) for i in range(len(colors))
             for j in range(i + 1, len(colors))
             if all_pairs or j == i + 1)
    for i, j in pairs:
        delta = abs(luminances[i] - luminances[j])
        if delta < min_delta:
            warnings.append(
                f"第 {i + 1}-{j + 1} 色 {colors[i]} 与 {colors[j]} "
                f"亮度差 {delta:.3f} < {min_delta}, 灰度打印难区分, "
                f"建议配不同线型/marker"
            )
    return (len(warnings) == 0, warnings)


# ============================================================
# 自测: python palettes.py
# ============================================================
if __name__ == "__main__":
    print("=" * 62)
    print("mathmodel-studio v7.8.0 统一色板自测")
    print("=" * 62)
    for name, spec in PALETTES.items():
        colors = spec["colors"]
        print(f"\n[{name}] {len(colors)} 色")
        print(f"  色值: {colors}")
        print(f"  来源: {spec['source']}")
        ok, warns = grayscale_check(colors)
        print(f"  灰度校验(相邻): {'通过' if ok else '有相邻色对需补区分'}")
        for w in warns:
            print(f"    - {w}")
    print(f"\n[CMAPS] {CMAPS}")
    print(f"[NEUTRALS] {len(NEUTRALS)} 令牌: {sorted(NEUTRALS)}")
    print(f"\ntint('#1F4E79', 0.8) = {tint('#1F4E79', 0.8)}")
    print(f"tint_series('#1F4E79', 5) = {tint_series('#1F4E79', 5)}")
    print(f"shade('#F18F01', 0.2) = {shade('#F18F01', 0.2)}")
    print("\n别名: get_palette('champion_palette') == get_palette('academic_blue') ->",
          get_palette("champion_palette") == get_palette("academic_blue"))
    print("别名: get_palette('nature') == get_palette('npg') ->",
          get_palette("nature") == get_palette("npg"))

    # ---- v7.8.0: 示意图色族自测 ----
    roles = ("fill", "stroke", "accent", "deep", "header", "header_stroke",
             "edge", "chevron")
    print(f"\n[DIAGRAM_FAMILIES] {len(DIAGRAM_FAMILIES)} 族, 角色完备性校验:")
    for fam_name, fam in DIAGRAM_FAMILIES.items():
        missing = [r for r in roles if r not in fam]
        bad = []
        for role, value in fam.items():
            try:
                _hex_to_rgb(value)
            except ValueError:
                bad.append(f"{role}={value}")
        status = "通过"
        if missing:
            status = f"缺角色 {missing}"
        if bad:
            status += f"; 非法色值 {bad}"
        print(f"  [{fam_name}] {status}; fill={fam['fill']} stroke={fam['stroke']} "
              f"header={fam['header']} edge={fam['edge']}")
        assert not missing and not bad, f"色族 {fam_name} 校验失败"
    print(f"[DIAGRAM_PAGE] {len(DIAGRAM_PAGE)} 令牌: {sorted(DIAGRAM_PAGE)}")
    for token, value in DIAGRAM_PAGE.items():
        _hex_to_rgb(value)  # 非法即抛
    print(f"[DIAGRAM_ORDER_GENERIC] {DIAGRAM_ORDER_GENERIC}")
    print(f"[DIAGRAM_ORDER_ROADMAP] {DIAGRAM_ORDER_ROADMAP}")
    fams = get_diagram_families(n=9)  # 超过族数时循环取
    print(f"get_diagram_families(n=9) -> {[f['fill'] for f in fams]}")
    assert get_diagram_family("blue")["edge"] == "#1F3F6B"
    assert get_diagram_page("ink") == "#262626"
    try:
        get_diagram_family("magenta")
    except ValueError as exc:
        assert "magenta" in str(exc)
    else:
        raise AssertionError("未知族名未报错")

    # ---- v7.9.0: 版式令牌自测 ----
    print(f"\n[DIAGRAM_GRID] {DIAGRAM_GRID}px  [RADIUS] {DIAGRAM_RADIUS}  "
          f"[STROKE_W] {DIAGRAM_STROKE_W}")
    print(f"[FONT_RAMP] {DIAGRAM_FONT_RAMP}  [FOCAL_MAX] {DIAGRAM_FOCAL_MAX}")
    print(f"[FONT_MONO] {DIAGRAM_FONT_MONO}")
    assert get_diagram_token("radius", "lg") == 8
    assert get_diagram_token("stroke_w", "strong") == 2.0
    assert get_diagram_token("font_ramp", "body") == 10.5
    assert max(DIAGRAM_RADIUS.values()) <= 10          # 圆角上限 10 (diagram-design 纪律)
    assert len(DIAGRAM_FONT_RAMP) <= 4                 # 字阶扁平 ≤4 档
    assert snap4(13) == 12 and snap4(14) == 16 and snap4(7.7) == 8
    for bad_group, bad_key in (("radius", "xxl"), ("nope", "sm")):
        try:
            get_diagram_token(bad_group, bad_key)
        except ValueError as exc:
            assert bad_key in str(exc) or bad_group in str(exc)
        else:
            raise AssertionError(f"非法令牌 {bad_group}/{bad_key} 未报错")
    print("版式令牌与 snap4 校验: 通过")
    print("自测完成, 无异常。")
