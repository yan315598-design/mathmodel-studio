# CUMCM (全国大学生数学建模竞赛) LaTeX 模板

自写单文件模板, 干净室实现 (仅依据竞赛公开发布的论文格式要求, 未参考第三方模板源码), 可随 skill 以 MIT 许可分发。

## 用法

```bash
xelatex main.tex   # 连编两遍使引用稳定
# 或走 skill 渲染链:
python scripts/render_paper.py --competition cumcm --workspace <paper_workspace>
```

## 格式要点

- A4 纸, 四边页边距 2.5 cm
- 第 1 页为摘要页: "摘 要" 黑体居中标题 + 摘要正文 + 关键词, 独占一页
- 正文自第 2 页开始; 页码从摘要页起算 (摘要页 = 第 1 页)
- 章节标题黑体, 正文宋体小四
- 公式编号 (1)(2); 三线表 (booktabs); 附录代码 (listings)
- 占位字段: `[论文标题]` `[题号]` `[参赛队号]` `[关键词1]` 等, 全文检索替换

## 注意

- 需 xelatex (中文); TeX Live / MiKTeX 均自带所需宏包
- 图占位用 `\fbox` 实现, 编译不依赖图片文件; 实际使用时取消 `\includegraphics` 注释并替换路径
- 附录代码示例保持 ASCII; 如需代码内中文注释, 建议改用 minted
