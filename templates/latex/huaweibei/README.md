# 华为杯 (中国研究生数学建模竞赛) LaTeX 模板

自写单文件模板, 干净室实现 (未参考第三方模板源码, 未内嵌竞赛官方视觉资产), 可随 skill 以 MIT 许可分发。

## 用法

```bash
xelatex main.tex   # 连编两遍
# 或走 skill 渲染链:
python scripts/render_paper.py --competition huaweibei --workspace <paper_workspace>
```

## 结构

- 封面信息区: `[论文标题]` `[题号]` `[学校名称]` `[参赛队号]` `[队员一姓名]` 等占位符, 按当年要求增删
- 摘要页 (页码自摘要页起算, 封面不编页码)
- 目录: 默认注释掉, 需要时取消 `\tableofcontents` 注释
- 正文: 问题重述 / 分析 / 假设与符号 / 建模求解 / 灵敏度 / 评价推广
- 参考文献: GB/T 7714 顺序编码制, 手写 `thebibliography` 条目示例 (期刊/专著/学位论文/网页/英文)
- 附录: listings 代码

## 注意

- 竞赛如明确要求官方封面或承诺书, 以当年通知为准自行替换封面区
- 页眉默认"研究生数学建模论文 + 页码", 不需要可删除 fancyhdr 段落
