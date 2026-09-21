# 外源文献检索层 (literature_scout)

> 选型期"方法发现"最小闭环：OpenAlex 主检索 + Crossref 兜底 + arXiv 预印本补充。
> 与 `reference_skill_bridge.md`（写作期引用核验）分层：本层在选型前找方法依据，
> 本页统一研究与写作补查的预算；引用真实性与格式由桥接页维护。

本层控制外部服务和阅读负荷，不把固定篇数误当成研究充分性。正式单题研究应围绕未解决的模型风险继续检索；批量 skill 测试才使用严格总预算。

## 研究 profile 与预算

| profile | 用途 | 默认策略 | 允许继续的条件 |
|---|---|---|---|
| `benchmark_smoke` | 批量回归、限流和流程测试 | 总请求数、时间和精读篇数严格固定 | 不因预算用完宣称选型充分 |
| `contest` | 正式竞赛的一两道题 | 每轮 5–10 条方法卡、1–2 篇重点精读；按关键缺口开新轮 | 候选覆盖或最高风险尚未解决 |
| `practice` | 无硬截止的单题研究 | 与 `contest` 相同的单轮负荷，可按边际收益继续 | 新检索可能带来新机制、反例或实现依据 |

profile 是Agent资源策略，不是CLI参数或后台总量计数器；不新建流程。未指定时，单题研究默认 `practice`，批量测试默认 `benchmark_smoke`。每轮检索只需在 decision log 登记 `reason / gap_closed / new_candidates / next_action`。

---

## 引擎与限流

| 引擎 | 定位 | 限流口径 |
|---|---|---|
| OpenAlex | 主检索；脚本支持 mailto 与 `--api-key` | 认证、额度和限流以当前服务说明与实际响应为准，不承诺匿名请求始终可用 |
| Crossref | 兜底：OpenAlex 返回 429/503 时自动降级，只取 DOI/标题/期刊/年份等核验要素 | 脚本无需 key；遵守实际响应和服务限流 |
| arXiv | 预印本补充：新方法/最新进展（`export.arxiv.org/api/query`，Atom XML） | 脚本无需 key；遵守实际响应和服务限流 |

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

## 挂点协议（三个，都不是必停点；stage 3 为选型期默认触发）

| 挂点 | 触发条件 | 动作 |
|---|---|---|
| Stage 1 选题避坑 | 用户在 2-3 个候选题间比较时**默认**对每个候选题各 1 次检索（`--n 5`） | 只看命中量级（payload 的 `total_results`）与近三年密度，不精读；每次检索登记 `decision_log.stages.1.literature_searches` |
| Stage 3 选型补充 | 先按最高风险和未覆盖缺口检索基础机制、同域应用、反例/失效场景、组合方法和实现细节；对进入公平比较的路线再做定向核验；不要求每个探索候选各搜一次 | 方法卡和机制条目进入候选档案与选择卡；登记 `decision_log.stages.3.literature_searches`，并记录本轮关闭的缺口与下一步 |
| Stage 5 翻车点验证 | 某子问验证翻车（不必等到固定返工轮数），怀疑方法本身不适用 | 按profile定向检索（方法名 + 失效场景），只找失效证据与替代路线；每次检索登记 `decision_log.stages.5.literature_searches` |

Stage 2背景查证和Stage 8引用补查也沿用本页预算，调用方式见 `references/reference_skill_bridge.md`。每次挂点先查缓存；检索词从题面/模型名派生，不凭空造词。

**预算护栏**：保留单轮小批量、API 限流、24h 缓存和单篇方法卡长度预算；不再把“单挂点 ≤2 次检索”作为 `contest/practice` 的绝对总上限。`benchmark_smoke` 可显式设置总请求/总时间上限。每轮最多 5–10 条方法卡是默认阅读负荷，不是正式研究的总篇数。

### 什么时候停止或继续

继续检索，只有在它服务于一个明确缺口时，例如尚无反例、候选没有可核验实现、最高风险没有决定性实验或出现互相矛盾的证据。满足以下条件后可以停止：

1. 关键风险已经有至少一条保守路线和一条值得验证的替代路线；
2. 入围路线完成“基线失效、机制、接口前提、反例、迁移边界”的简要记录；
3. 最大风险已有决定性验证，或明确记为未验证；
4. 连续一轮检索没有增加新机制、反例、关键来源或实现信息。

预算用完只表示当前 profile 的资源耗尽，不能自动表示候选覆盖完成；应在状态中保留未覆盖项；研究状态可保持validate或给条件性recommend，效果状态可为inconclusive，不混用两类字段。

## 方法卡 schema 与 mechanism_reviews 衔接

方法卡（`literature-card-1.0`）固定 13 字段：

```json
{"paper_id": "", "title": "", "authors": [], "journal": "", "year": null,
 "doi": "", "cited_by": 0, "oa_status": "", "tier": "", "source_engine": "",
 "query": "", "fetched_at": "", "abstract_snippet": ""}
```

外源方法卡证明检索到的出处线索，不自动证明书目完整、机制正确或本题有效。将影响决策的内容转译为基线失效、机制、前提接口、反例、迁移边界；优先写入现有选择表或证据记录，不要求每篇新增全局机制条目。

已有 `competitions/<comp>/cases/mechanism_reviews.json` 的 `proposed/source_checked/locally_tested` 保留兼容，但不能当作单向质量升级链。分别核验Stage 3的书目、机制、实现和效果四轴；本地负结果也属于locally_tested。机理推导没有外源出处时如实标not_applicable，不伪造source_checked。正式正文中按证据范围区分提出的方法、已运行实现和已验证效果。

## 核验纪律

1. **四要素核验**：题名/作者/期刊/年份四项与 API 返回一致才可引用；任一要素在
   正文引用时被改写（如作者名错拼、期刊缩写歧义），按未核验处理。Crossref 兜底
   结果缺作者字段时，作者记空列表并在核验时补查 DOI 落地页。
2. **被引量档位**：兼容字段 `tier` 按论文被引量启发式 Q1(>500) / Q2(100-500) / Q3(10-100) / Q4(<10)；
   此 Q 档为被引量启发式分档，非 JCR 分区。分档只是线索不是门槛：预印本
   （source_engine=arxiv）被引恒低，不等于质量低；
   高被引老文不等于适本题。`--min-tier` 仅用于明确的被引量筛选，不能据此核验期刊等级或权威性。
3. **撤稿检查**：OpenAlex `is_retracted=true` 已在脚本层直接剔除；Crossref/arXiv
   无撤稿标记，兜底结果在 source_checked 前必须人工复核一次 DOI 页面。
4. **方法卡长度预算**：脚本按约4字符折1 token估算，将估算值限制在500以内；这不是模型 tokenizer 的精确上限。超出先裁摘要再裁标题，裁过的字段回原出处核验；
   每轮默认精读 1–2 篇全文，其余只看方法卡。若最高风险仍无答案，可以开启下一轮精读；检索结果摘要不整段贴进上下文。

## 明确不做（边界）

- **脚本不集成知网/万方后端**：中文文献按实际访问权限使用已安装的
  `cnki-*` skill（受 `reference_skill_bridge.md` 约束）。
- **不做本地向量库**：RAG 管线在 72h 赛程内是烂尾风险；检索排序交给 OpenAlex
  相关性排序 + 本层启发式过滤足够。
- **不分发获奖论文 PDF**：版权限制。本层只取元数据与摘要索引，全文可按权限通过开放获取渠道读取；不可获取时注明阅读范围。
