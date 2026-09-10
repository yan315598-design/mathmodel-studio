# 外源文献检索层 (literature_scout)

> 选型期"方法发现"最小闭环：OpenAlex 主检索 + Crossref 兜底 + arXiv 预印本补充。
> 与 `reference_skill_bridge.md`（写作期引用核验）分层：本层在选型前找方法依据，
> 写作期引用仍走 reference_skill_bridge 的硬上限与 T1-T3 路由，互不替代。

---

## 引擎与限流

| 引擎 | 定位 | 限流口径 |
|---|---|---|
| OpenAlex | 主检索，免 key；带 mailto 进礼貌池 | 匿名约 100 次/天（实测限流）；注册 key（`--api-key`）可提额 |
| Crossref | 兜底：OpenAlex 返回 429/503 时自动降级，只取 DOI/标题/期刊/年份等核验要素 | 宽松，无需 key |
| arXiv | 预印本补充：新方法/最新进展（`export.arxiv.org/api/query`，Atom XML） | 宽松，无需 key |

CLI（只接受英文 query；中文题面→英文检索词由 agent 转换）：

```bash
python scripts/literature_scout.py "domain adaptation fault diagnosis" --n 5
python scripts/literature_scout.py "graph neural network routing" --n 5 --engine arxiv
python scripts/literature_scout.py "..." --n 5 --api-key <KEY> --min-tier Q2 --cache-ttl 86400
```

- 缓存：同一 `(engine, n, query)` 在 TTL（默认 24h）内直接读 `state/literature_cache.json`，不耗配额。
- 方法卡落盘：`state/literature/<timestamp>.json`；stdout 同步输出完整 JSON。
- state 目录解析与其他脚本一致：`--state-dir` > `MATHMODEL_STATE_DIR` > `cwd/state`。
- stdout payload 顶层字段（除 `cards` 外）：`total_results` 为命中总量（OpenAlex 取
  `meta.count`，Crossref 取 `total-results`，arXiv 无此概念为 `null`）；`engine` 为
  请求引擎，`engine_effective` 为实际产出卡片的引擎，二者不同即发生了降级
  （`fallback_used: true`）；`cache_hit` 为是否命中缓存（缓存命中时降级事实与
  命中总量从缓存条目回填，不遮蔽）。

## 挂点协议（三个，都不是必停点）

| 挂点 | 触发条件 | 动作 |
|---|---|---|
| Stage 1 选题避坑 | 用户在 2-3 个候选题间摇摆，需要判断"这道题的方法域是否有人做过/是否过热" | 每个候选题 1 次检索（`--n 5`），只看命中量级（payload 的 `total_results`）与近三年密度，不精读；每次检索登记 `decision_log.stages.1.literature_searches` |
| Stage 3 选型补充 | **playbook / 本地案例库未命中当前题域**（检索得分普遍低、无同构案例）时触发；命中时不触发，不重复检索 | 1-2 次检索，方法卡进入选择卡的候选档案作佐证；每次检索登记 `decision_log.stages.3.literature_searches` |
| Stage 5 翻车点验证 | 某子问验证翻车（L1 verdict=refine 且 iter=2 仍无改善），怀疑方法本身不适用 | 1 次定向检索（方法名 + 失效场景），只找失效证据与替代路线；每次检索登记 `decision_log.stages.5.literature_searches` |

其他阶段不触发本层。每次挂点先查缓存；检索词从题面/模型名派生，不凭空造词。

## 方法卡 schema 与 mechanism_reviews 衔接

方法卡（`literature-card-1.0`）固定 13 字段：

```json
{"paper_id": "", "title": "", "authors": [], "journal": "", "year": null,
 "doi": "", "cited_by": 0, "oa_status": "", "tier": "", "source_engine": "",
 "query": "", "fetched_at": "", "abstract_snippet": ""}
```

与 `competitions/<comp>/cases/mechanism_reviews.json` 的衔接：外源方法卡只提供
"这个方法存在、出处可核"的证据；要进入建模决策，agent 必须把它转写成机制条目
（基线失效/机制/前提接口/反例/迁移边界五要素）并逐条标 `review_status`：

```text
proposed        外源方法卡已到手，四要素核验未做
  → source_checked   四要素核验通过（题名/作者/期刊/年份与 API 返回一致），且非撤稿
  → locally_tested   已在本题数据上跑了最小验证（哪怕 toy 规模）
```

`proposed` 条目只允许出现在候选档案，不得作为选择卡拍板依据；`source_checked`
可入围短名单；只有 `locally_tested` 的机制才能写进正文模型链。跳级（proposed 直读
locally_tested）视为伪造验证状态。

## 核验纪律

1. **四要素核验**：题名/作者/期刊/年份四项与 API 返回一致才可引用；任一要素在
   正文引用时被改写（如作者名错拼、期刊缩写歧义），按未核验处理。Crossref 兜底
   结果缺作者字段时，作者记空列表并在核验时补查 DOI 落地页。
2. **期刊分档**：按被引量启发式 Q1(>500) / Q2(100-500) / Q3(10-100) / Q4(<10)；
   此 Q 档为被引量启发式分档，非 JCR 分区。分档只是线索不是门槛：预印本
   （source_engine=arxiv）被引恒低，不等于质量低；
   高被引老文不等于适本题。`--min-tier` 只在明确要权威佐证时使用。
3. **撤稿检查**：OpenAlex `is_retracted=true` 已在脚本层直接剔除；Crossref/arXiv
   无撤稿标记，兜底结果在 source_checked 前必须人工复核一次 DOI 页面。
4. **token 预算**：单篇方法卡 ≤500 token（脚本已内置裁剪，超出先裁摘要再裁标题）；
   每个挂点最多精读 2 篇全文，其余只看方法卡。检索结果摘要不整段贴进上下文。

## 明确不做（边界）

- **不接入知网/万方**：无合规 API，爬取违反 ToS。中文文献走已安装的
  `cnki-*` skill（受 `reference_skill_bridge.md` 约束）。
- **不做本地向量库**：RAG 管线在 72h 赛程内是烂尾风险；检索排序交给 OpenAlex
  相关性排序 + 本层启发式过滤足够。
- **不分发获奖论文 PDF**：版权限制。本层只取元数据与摘要索引，全文由用户自行
  通过 oa_status 指示的开放获取渠道获取。
