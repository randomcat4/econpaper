# DESIGN: econpaper 三档文献检索能力（v1, 2026-06-13）

> 实施状态（2026-06-13）：已落地为 `econpaper/search/` 包（v1.0）。
> L1 处方生成器 + 回流（`prescription.py`/`ingest.py`）、L2 核验层（`verify.py`）、
> Paper Store（`paper_store.py`）、L2 检索层（`open_search.py`）、L3 循环（`deep_search.py`）、
> 档位路由（`router.py`）均已实现并通过测试（CLI：`econpaper search …` / `econpaper paper-store …`）。
> 未实现项见第 6 节"不在本设计范围内"，另：S2/Unpaywall/RePEc/NBER 源、OA PDF 自动下载、
> paper-search-mcp 接入留待后续（OpenAlex+Crossref+arXiv 已覆盖核验与检索主链路）。
> 2026-06-13 边界修订：离线、源不可达、预算不足、L3 内部错误不再降级伪装为 L1/L2 成功，
> 必须显式记录为 boundary/fail-closed；如需观察真实网站/本地 PDF 能力，走 `search boundary-probe`
> 让外部 Codex 子进程执行，本实例只记录产物。

> 定位声明：本设计不违反 `econpaper_roadmap_v3/03_citation_safety_not_search.md` 的原则。
> econpaper 不做检索引擎，三档能力的**唯一合法出口**都是 structured notes
> （`external_literature_notes.json` + 规范化 `refs.bib`），随后照常通过 citation safety 门。
> 检索档位决定的是"notes 从哪来、花多少钱、覆盖多宽"，不改变下游任何硬规则。

---

## 0. 总览

| | L1 精准档（处方驱动） | L2 标准档（开放 API 聚合） | L3 深研档（双语全量 Deep Search） |
|---|---|---|---|
| 一句话 | 先想清楚"怎么搜"，再用三个高质量入口少而准地搜 | 免费/低价开放 API 自动聚合 + 元数据规范化 | GPT Deep Research / Grok DeepSearch 式多轮 agentic 检索，中英全量 |
| 数据源 | **仅** Google Scholar、Web of Science、知网（CNKI） | OpenAlex、Crossref、Semantic Scholar、arXiv、Unpaywall、RePEc/IDEAS、NBER | L1+L2 全部源 + 通用 web search + 中文源（CNKI/万方/政策文本）+（如有授权）WoS Expanded |
| 检索语言 | 用户问题决定（通常中英各一套处方） | 以英文为主（开放 API 中文覆盖弱） | **中英双语强制全量**，跨语言去重 |
| 执行者 | 人（或浏览器侧薄壳）按处方执行，系统不直接抓取 | 系统自动调 API | Agent 自主多轮规划-检索-阅读-再检索 |
| 边际成本 | ≈ 0 API 费；人的时间 | 低（free-first；OpenAlex free key 每日 $1 额度内） | 高（token + 时间 + 可选付费源） |
| 典型耗时 | 30–90 分钟（人执行） | 1–5 分钟 | 10–40 分钟（agent 自主） |
| 核心价值 | 检索处方质量（query 设计、筛选标准、停止规则） | 引用核验、BibTeX 规范化、补元数据 | 覆盖完整性、矛盾交叉验证、综述底稿 |
| 合规风险 | 无（用户用自己的机构访问权限） | 无（全部官方公开 API） | 中（web 抓取、付费源 license，需白名单管控） |

三档是**包含关系而非互斥**：L3 内部会先生成 L1 的处方、再调 L2 的 API 层。
L1 是地基，不是"丐版"。

---

## 1. L1 精准档：处方驱动检索（Google Scholar + WoS + 知网）

### 1.1 设计哲学

这三个源恰好都**没有可用的免费公开 API**（GS 官方无 REST API、WoS 要
Clarivate license、知网无公开 API），但它们是经济学研究者实际拥有机构访问权限、
质量最高的三个浏览器入口。所以 L1 的架构选择是：

**系统不负责"搜到"，系统负责"教你怎么搜 + 接住你搜回来的东西"。**

重点全部前置到检索之前——"怎么搜"比"搜了多少"重要。低档的失败模式不是
漏掉文献，而是 query 设计差导致前 50 条全是噪音、用户筛选疲劳后放弃。

### 1.2 核心产物：检索处方（Search Prescription）

输入：研究问题（来自 intake，复用 `skill4econ/skills/intake/env_econ_research_intake.md`
已有的结构化要素）。输出一份处方文档，包含以下五个部分：

**(a) 概念块分解。** 把研究问题拆成 3–5 个概念块（经济学版 PICO）：
- 政策/处理（treatment）：如 低碳城市试点 / low-carbon city pilot
- 结果变量（outcome）：如 企业绿色创新 / green innovation, green patents
- 识别策略（identification）：如 多期 DID / staggered DID, event study
- 对象与范围（population/region）：如 中国上市公司 / Chinese listed firms
- （可选）数据类型：专利文本、卫星数据等

**(b) 每块的中英术语扩展表。** 同义词、领域黑话、英译中/中译英的**非直译对应**
（这是中文文献检索最容易失败的点：英文文献叫 "staggered adoption"，中文文献叫
"多期双重差分"或"渐进性试点"，直译搜不到）。每块给 3–8 个术语，标注"必含/可选"。

**(c) 分源 query 卡。** 同一概念组合，按三个源各自的语法和强项写出可直接粘贴的
query，并写明该源在本次检索中的**分工**：

| 源 | 分工 | 语法要点 |
|---|---|---|
| Google Scholar | 召回 + 引文追踪（cited by / related） | 布尔能力弱：靠短语引号、`intitle:`、`author:`、年份区间；每个概念组合只出 1–2 条宽 query |
| Web of Science | 精确布尔 + 期刊层级过滤 + 引文报告 | `TS=()`、`NEAR/x`、`AND/OR/NOT`；用 WoS category (Economics) 和 JCR 分区收口 |
| 知网 CNKI | 中文文献 + 政策背景 + 国内试点细节 | 主题/篇名/关键词字段检索 + 专业检索 `SU=`；用 CSSCI/北大核心收口；政策文件用"篇名"精确搜 |

**(d) 种子文献滚雪球计划。** 用户提供（或处方建议）1–3 篇锚点论文，规定：
- 向后（references）：锚点的参考文献里按概念块筛
- 向前（cited by）：GS 和 WoS 各做一次 cited-by，按年份倒序取前 N
- 滚一轮即停，新锚点需用户确认后才滚第二轮

**(e) 筛选标准 + 停止规则。** 处方必须显式写出：
- 纳入/排除标准（题录层面即可判断的，如年份、国家、方法、期刊层级）
- 停止规则：每条 query 只看前 50 条；连续 20 条无新增相关项即停；
  三源合计相关项达到目标数（默认 30–60 篇题录）即停
- 检索日志模板：query 原文、源、日期、命中数、纳入数（系统性综述的最低留痕要求）

### 1.3 回流接口

用户把搜回来的题录（GS/WoS/CNKI 导出的 RIS/BibTeX/Excel，或 Zotero 库）交回系统，
系统做三件事：去重 → 规范化为 `refs.bib` → 引导用户为每篇填
`what_it_did` / `relation_to_this_paper`，生成 structured notes。
L1 不写任何文献综述 prose——这是 03 号文档的硬规则。

### 1.4 成本与边界

- 成本：零 API 费、零合规风险；主要成本是用户 30–90 分钟。
- 边界：不保证全量；WoS 收不到 working paper（NBER/SSRN 阶段的文献会漏，
  处方里用 GS 补）；知网导出格式脏，回流时需容错。
- 不做的事：不内置任何 GS/CNKI scraper（维护脆、违 ToS、与 L1 哲学冲突）。

---

## 2. L2 标准档：开放 API 聚合

### 2.1 设计哲学

L1 解决"怎么搜"，L2 解决"机器能自动做的那部分"：元数据骨干、引用存在性核验、
BibTeX 规范化、OA 全文链接。全部走官方免费/低价 API，free-first，无 scraping。

### 2.2 源与分工（按生态现状固定角色，不做万能聚合）

| 源 | 角色 | 接入注意 |
|---|---|---|
| OpenAlex | 元数据骨干 + 扩展检索 + OA 链接 + topic 映射 | 2026 起需 free API key，每日 $1 免费额度内做预算控制 |
| Crossref | DOI 真值源 + BibTeX 生成 + reference 列表 | 免注册；用 polite pool（带 mailto） |
| Semantic Scholar | 引文图谱（citations/references/recommendations） | 申请 key 提升限额 |
| arXiv | 预印本元数据（econ.EM/econ.GN/q-fin） | Atom XML，免 key |
| Unpaywall | DOI → OA 全文位置 | 仅 DOI-centric，不做 keyword 搜索 |
| RePEc/IDEAS | 经济学 working paper 网络 | API 是 courtesy access，限速保守；超限或不可达时记录 source_boundary |
| NBER | WP 元数据（CSV/TSV，每周更新） | 直接下载结构化文件，本地缓存即可 |

### 2.3 能力清单

1. **引用核验（最高优先级）**：对 `refs.bib` 中每个条目，经 Crossref/OpenAlex
   解析 DOI/title，确认"这篇论文真实存在、元数据一致"。这直接服务于
   citation safety 的 fake-citation 硬阻断——是 L2 存在的第一理由。
2. **题录补全与规范化**：脏 BibTeX（尤其 CNKI/GS 导出的）→ 规范 BibTeX；
   补 DOI、年份、期刊全称；重复检测。
3. **结构化检索**：把 L1 处方的英文 query 卡自动在 OpenAlex/S2 上执行，
   返回去重后的候选题录列表（默认前 100 条，按相关性+引用数混合排序）。
4. **滚雪球自动化**：锚点论文的 references / citations 经 S2/OpenAlex 自动拉取，
   替代 L1 中手动的滚雪球步骤。
5. **OA 全文定位与落地**：对纳入的题录经 Unpaywall/OpenAlex 找合法 OA PDF 链接，
   下载并按第 4 节 Paper Store 规范落地（PDF + LLM 可读文本层）。

### 2.4 已知短板（明确不掩盖）

- **中文文献几乎为零**：开放 API 生态对知网体系覆盖极弱。L2 是英文档。
- 不读全文、不写综述：产出仍是题录 + 候选列表，notes 的
  `what_it_did` 字段在 L2 只能用官方 abstract 摘录填充并标注
  `confidence: low`，等待用户确认升级。
- 成本控制：单次 run 设 API 调用预算上限（OpenAlex 按免费额度、S2 按限速）。
  超限时硬阻断并保留 partial evidence，不把 L1 处方伪装成 L2 成功。

---

## 3. L3 深研档：双语全量 Deep Search

### 3.1 设计哲学：借鉴 GPT Deep Research 与 Grok DeepSearch 的循环结构

只有 L3 做中英全量。它不是"更多源的 L2"，而是换了控制流——从
"一次检索、一次返回"变成 **agentic 研究循环**。借鉴三点：

**借鉴一（GPT Deep Research 的前置澄清 + 计划确认）：**
开跑前 agent 先向用户提 2–4 个澄清问题（时间窗、地域、方法范围、综述用途），
然后给出**研究计划**（子问题分解 + 每个子问题打算用哪些源、什么语言搜），
用户确认后才烧预算。这一步直接复用 L1 的处方生成器——L3 的计划 = 双语处方 + 源扩展。

**借鉴二（Grok DeepSearch 的并行扇出 + 逐条溯源）：**
- 每个子问题在所有可用源上**并行**发多条变体 query（中英各一组），
  而不是串行试错；
- 综述底稿中**每个论断挂具体来源**（DOI/OpenAlex ID/CNKI 链接），
  无溯源的句子不允许出现——这与本项目 claim ledger 的精神同构。

**借鉴三（两者共同的 迭代加深 read–refine 循环）：**
```
计划 → 扇出检索 → 题录粗筛（re-rank）→ 全文落地到 Paper Store（第 4 节）
  → 在文本层上精读 → 提取论断与空白 → 由空白生成第二轮 query → 再检索
  → … → 饱和或预算耗尽 → 综合
```
每轮结束 agent 自问三件事：哪些子问题已覆盖？哪些论断只有单一来源（需三角验证）？
中文侧和英文侧的结论是否矛盾（如国内试点评估与国际文献结论相反——这本身是
综述的发现，不是噪音）？

### 3.2 双语全量的具体含义

1. **每个概念块强制中英两套术语**（复用 L1 的术语扩展表，由 agent 生成并维护）。
2. **源的双语分工**：英文走 L2 的 API 层 + web search；中文走 CNKI
   （浏览器侧/用户授权的接入）+ 通用 web search 的中文结果 + 政策原文检索
   （政府网站、发改委/生态环境部文件——环境经济学论文的政策背景必需）。
3. **跨语言去重与对齐**：同一论文的中英版本（如先发 working paper 后发中文版，
   或中国学者中英双发）按 DOI/作者+年份+摘要相似度对齐为一条记录。
4. **覆盖审计**：终稿附"检索完整性自查"——每个子问题 × 每种语言 × 命中数矩阵，
   空格子要么解释（该方向中文文献确实空白）要么补搜。

### 3.3 产出与下游契约

L3 的产出**仍然不是可直接入稿的综述段落**，而是：

1. 全量去重题录 + 规范化 `refs.bib`（经 L2 核验层，每条引用过存在性检查）；
2. 每篇纳入文献一条 structured note（`what_it_did` 来自全文/摘要精读，
   `relation_to_this_paper` 来自 agent 分析，`confidence` 如实标注）;
3. 每篇可合法获取全文的文献一个 **Paper Store 条目**（第 4 节）：
   中英文重命名的 PDF + LLM 可读文本层，供 econpaper/skill4econ 后续精读复用；
4. 一份**综述底稿（evidence memo）**：按子问题组织、逐句挂引、显式标注
   矛盾点和文献空白——它进入 `literature_notes.md` 的位置，作为作者输入，
   而不是直接进 manuscript。Related Literature 正文仍由 econpaper
   从 structured notes 生成并过 citation safety。

### 3.4 成本与管控

- **预算三闸**：token 预算（建议默认上限按子问题数 × 每题轮数封顶）、
  时间预算（默认 30 分钟硬停）、源调用预算（继承 L2 的 API 限额）。
  任一闸触发即进入"综合现有材料"阶段，不静默续烧。
- **源白名单**：明确排除 Sci-Hub 类 workflow（生态里常见但本项目不碰）；
  WoS Expanded、Scopus 等付费源仅在用户提供 license key 时启用；
  第三方多源 MCP（paper-search-mcp 等）可作为可选接入，但只取其
  free-first 源子集，且其返回必须能映射到 DOI/官方 ID 才算数。
- **失败边界**：L3 任何环节失败（限额、源不可达、内部错误）必须显式写入边界报告并 fail closed，
  不得降级伪装成 L2 结果 + L1 处方的成功运行。允许保留已取得的 partial evidence，
  但上游状态必须显示该轮没有完成。

---

## 4. Paper Store：PDF 落地与 LLM 可读文本层

### 4.1 定位

凡是合法拿到全文的论文（L2/L3 自动获取的 OA PDF、L1 用户从机构权限里
手动下载后投喂的 PDF），统一落到本地 Paper Store。**PDF 不再只是中转品**：
它和它的文本层是 econpaper（写作链精读）与 skill4econ（方法论证、文献锚点）
后续随时可调用的本地资产。

### 4.2 目录与命名规范

```text
paper_store/
  chen2021lowcarbon/                          # 文件夹名 = citekey（稳定、ASCII、可作主键）
    低碳城市试点与企业绿色创新_Low-Carbon-City-Pilots-and-Green-Innovation.pdf
    paper.md                                  # LLM 可读全文（Markdown，保留标题层级/表格/脚注）
    paper.struct.json                         # 结构缓存：outline、分节偏移、图表清单（精读秒查）
    meta.json                                 # 题录 + 来源 URL + 获取时间 + 转换工具与版本
```

命名规则：
- 文件夹名用 citekey——与 `refs.bib`、structured notes 的 `paper_key` 同一主键，
  机器引用永远走它；
- PDF 文件名 = `中文短题_英文短题.pdf`，给人看的；中英文标题任一缺失时
  只用存在的一种（不机翻造另一种，机翻题名标注于 meta.json 而不进文件名）；
- 短题截断规则：单语 ≤ 40 字符，整个路径不超 Windows 260 字符限制，
  全题保留在 `meta.json`。

### 4.3 三个环节直接复用现成工具，不自研

生态已把这条链做完了，我们的工作是选型 + 接到 Paper Store 契约上：

| 环节 | 现成方案 | 选型理由 |
|---|---|---|
| 检索→下载→初步读取 | openags/paper-search-mcp（search/download/read 三件套，free-first 多源，MCP+CLI 同库）；LinXueyuanStdio/academic-mcp（`paper_download` 返回本地路径、`paper_read` 直接 PDF→Markdown，19+ 源） | 拿来即用的获取层；其下载产物重命名后入 Paper Store |
| PDF→高质量 Markdown | **MinerU**（首选：2026 横评公认 CJK 与复杂学术版面最强，输出 Markdown+JSON，对知网中文 PDF 关键）；Marker（批量/多语言备选）；PyMuPDF 直抽（轻量路径，版面简单时省 GPU） | `paper.md` 的质量上限决定精读质量上限，中文 PDF 必须走 MinerU 级别的解析 |
| 精读接口 | agent-papers-cli 模式：`outline`（标题树）/`skim`/`read --section`/`search`（带上下文关键词检索）/`bibtex`，解析结构缓存为 JSON | econ/pap 精读时**按节取用，不整本吞 PDF**——`paper.struct.json` 就是这个缓存 |

### 4.4 硬规则

- 只落地合法获取的全文：OA 渠道（Unpaywall/OpenAlex/arXiv/PMC 等）或用户
  自有权限下载后投喂；维持第 3.4 节的源白名单（无 Sci-Hub）。
- Paper Store 是**本地缓存，不是文献库**：不做云同步、不替代 Zotero；
  用户的 Zotero 库可以是投喂来源（P1 adapter），但主键对齐到 citekey。
- `paper.md` 生成时记录转换工具与版本（meta.json），转换失败不阻塞主流程——
  该篇退回"仅题录 + abstract"状态，structured note 的 `confidence` 相应下调。
- 精读引用要可定位：L3 综述底稿和 structured notes 里来自全文的论断，
  应附 `paper.md` 中的节锚点（如 `chen2021lowcarbon#5.2`），方便人工复核。

---

## 5. 档位路由（什么时候用哪档）

| 场景 | 推荐档 |
|---|---|
| 作者已有 refs.bib，只需核验+补元数据 | L2 核验子集（最便宜路径） |
| 写国内政策评估论文，需要中文文献+政策背景，预算敏感 | L1（处方里中文 query 卡占比加重） |
| 英文 working paper 定位，需要快速摸清引文图谱 | L2 |
| 投稿前的系统性文献定位 / 审稿人质疑"漏了 XX 文献" | L3 |
| 开题阶段不确定方向 | L3 的"计划+第一轮"截断模式（只跑澄清+处方+一轮扇出，不进深读循环） |

默认档位 = L1。升档永远是显式选择（涉及钱和时间），不自动升档。

---

## 6. 与现有路线图的接缝

- 本设计属于 `03_citation_safety_not_search.md` 中 P1（L2 的核验/规范化 =
  "Metadata enrichment adapter" 的扩写）和 P2（L3 = "discovery" 的具体方案）；
  L1 是新增的 P0.5——零代码依赖外部 API，先于 L2/L3 就能交付价值。
- Paper Store（第 4 节）是 econpaper 与 skill4econ 的**共享本地资产层**：
  写作链精读、方法文献锚点（`skill4econ/skills/_shared/08_domain_literature_anchor_rules.md`）
  都从同一个 citekey 主键取全文文本层。
- 实施顺序建议：**L1 处方生成器 → L2 核验层 → Paper Store（落地+转换+精读接口）
  → L2 检索层 → L3 循环**。L1 是纯 prompt/模板工程；L2 核验直接强化现有
  citation safety 硬规则；Paper Store 三个环节全部复用现成工具（4.3 节），
  集成成本低；L3 最后做，且做之前前四步已经能覆盖 80% 日常需求。
- 不在本设计范围内：Zotero 双向同步（已有 P1 adapter 规划，Zotero 只作为
  投喂来源）、RAG/向量检索 over Paper Store（P2 另议，文本层已为其备好原料）。
