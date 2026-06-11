# easypaper 0.2.4 Audit — v2 校验与加深 (差异稿)

日期: 2026-06-10
关系: 增量于 `_AUDIT.md`(2026-05-31)。**只标差异、确认、新发现、加深点**,不重复已答内容。
范围: 静态读取,无 pip install / 无执行。代码包是 PyPI sdist 0.2.4(自 5/31 起未变)。

---

## 0. TL;DR

5/31 audit 的结构性结论(三档可行性、Tier 1.5 PoC 路径、L2 schema 难度、figure 路线、boto3 用途)**全部成立**。

但 v2 抓到两项被 5/31 漏掉的事实,会改变 Tier 2 的**实施策略**(不改变工时):

1. **`DocumentInput` 是预留的通用抽象,有 converter 和测试,但 planner/section 一个 reader 也没有。** 它就是 easypaper 团队自己画好、但没接通的迁移目标层 — Tier 2 schema 替换应该瞄准它,而不是发明新 alias。
2. **`GenerationConstraints.required_sections` 存在于通用层(document_spec.py:81,90)。** 5/31 找的 grep 命中其实就是它,但当时被当成"无消费"。真实情况是:它是**接口设计意图**,planner 只是没去读 — 这才是 required_sections 应当接入的入口,不是 venue_config 字段。

另外 v2 抓到 3 个"压软结论"的具体证据(figure role allowlist、tool factory 真实条目数、venue token 容忍匹配),记录在 §C。

---

## A. 5/31 audit 的逐点校验结果

行号采用 5/31 audit 的引用,在 6/10 静态扫描下复核:

| 5/31 claim | 复核结果 |
| --- | --- |
| `PaperMetaData` at `metadata_agent/models.py:159-188` | ✓ 精确成立(field 顺序: title, idea_hypothesis, method, data, experiments, references) |
| `DEFAULT_EMPIRICAL_SECTIONS` fallback at `planner_agent/models.py:545-553` | ✓ 精确成立,7 个 section,无 econ 章节 |
| section 直接喂旧字段 at `section_generation.py:147-151` | ✓ 精确成立 |
| section fallback to `metadata.method` at `section_generation.py:238-249` | ✓ 成立,真实拼接在 line 249 `or metadata.method` |
| assembly hardcoded `_default_order` at `assembly_helper.py:50-63` | ✓ 精确成立 |
| prompt_contracts.py:53 "Choose sections appropriate for {style_guide}" | ✓ 精确成立 |
| `TOOL_FACTORY` 硬编码 at `shared/tools/__init__.py:136-144` | ✓ 成立,但实际条目数有出入 — 见 §B |
| `academic_dreamer` 动态 import at `figure_generation.py:293-304` | ✓ 精确成立 |
| `figure_supplementation.py:228-230, 258` 拒绝 data viz / 拒绝 result curves | ✓ 精确成立,且**比 5/31 描述更严** — 见 §C.3 |
| `citation_grounding.py:257-295` token overlap 判定 | ✓ 精确成立(实际范围 253-296) |
| `citation_grounding.py:315-319` section-authorized 检查 | ✓ 精确成立 |
| `bootstrap.py:80-103` builtin-first / user-overwrite | ✓ 精确成立 |
| `registry.py:33-48` register 同名 overwrite | ✓ 精确成立 |
| `registry.py:72-104` get_writing_skills 按 priority 排序 | ✓ 精确成立 |
| `storage_client.py:21, 34, 49-63, 70` boto3 包 OSS S3 | ✓ 精确成立,逐行命中 |
| `tests/` 50 个 `test_*.py` | ✓ 精确成立,绝对值 50 |

**字段全词出现计数有偏差**(5/31 vs 6/10,只扫 `src` 不含 `tests` 的 `rg --type py -w` 结果):

| 字段 | 5/31 全词 | 6/10 全词 (src only) |
| --- | ---: | ---: |
| title | 590 | 446 |
| idea_hypothesis | 84 | 67 |
| method | 263 | 234 |
| data | 346 | 305 |
| experiments | 82 | 68 |
| references | 332 | 303 |

差距约 15-25%,最可能解释是 5/31 把 `tests/` 也算进来了。**结论不变**: 量级远超 alias 兼容能覆盖的范围。

---

## B. 必须修正/精化的 5/31 表述

### B.1 TOOL_FACTORY 真实是 7 条,不是 4 条

5/31 audit §6.1 写"现有 tools: `validate_citations / count_words / check_key_points / search_papers`"。
实际 `shared/tools/__init__.py:136-144` 是 7 条:

```python
TOOL_FACTORY = {
    "validate_citations": _create_citation_validator,
    "count_words": _create_word_count,
    "check_key_points": _create_key_point_coverage,
    "search_papers": _create_paper_search,
    "ask": _create_ask_tool,            # ← 5/31 漏
    "show_markdown": _create_show_markdown,   # ← 5/31 漏
    "show_json_data": _create_show_json_data, # ← 5/31 漏
}
```

`ask` 路由到 memory/planner/reviewer 三个 handler,**是用户跨 agent 提问的统一入口**,对 IM 聊天式交互(EvoScientist 主线场景)有直接价值。`show_markdown/show_json_data` 是 UI 流式输出工具。

**含义**: 加 `check_pre_trends` 等 econ tool 时,3-4 个文件改动估算 5/31 仍准;但参考实现选 `_create_ask_tool` 模板比选 `_create_word_count` 更接近"需要读 session state"的形态。

### B.2 测试套件 integration 标记比 5/31 描述少

5/31 audit §7.2 写"`test_table_visual_preview.py` 和 `test_table_converter_enhanced.py` 对 `pdflatex`/真实 fixture 有 skip"。

我用 `pytest.mark.integration|pytest.mark.skip|requires.*network` 案例不敏感全文 grep,只命中 **1 个文件** `test_table_visual_preview.py`。`test_table_converter_enhanced.py` 没有显式 skip/integration 标记 — 它可能仍依赖真实 latex,但**没有 pytest 标记保护**,需要实际跑一次才能知道是 hang 还是 fail。

`pyproject.toml` 注册了 `integration` marker(`pyproject.toml:50`),但代码里几乎没用过。**没有现成的方式按 marker 区分线下/线上测试**;fork 后需要自己加 marker 或维护 ignore list。

### B.3 字段直接属性引用计数

5/31 §5.1 表格"直接属性引用"列(`title=53, idea_hypothesis=18, method=18, data=12, experiments=13, references=9`)在 6/10 复核中近乎一致(我看到 idea_hypothesis 17 命中,5/31 数 18,差 1)。**结论"alias 不够,需要逐点改"成立。**

---

## C. 5/31 没写或写得太软的关键事实

### C.1 `DocumentInput` 抽象是 aspirational dead scaffolding(★ 重要)

`src/models/document_spec.py` 定义了三个通用 model:
- `ContentSection`(line 12-36)— `SectionPlan` 的泛化
- `DocumentSpec`(line 39-63)— `PaperPlan` 的泛化
- `DocumentInput`(line 94-119)— `PaperMetaData` 的泛化,核心字段是 `content_brief: Dict[str, str]`

`PaperMetaData.to_document_input()`(`metadata_agent/models.py:208-234`)和 `PaperPlan.to_document_spec()`(`planner_agent/models.py:449`)都已实现 converter。
`tests/test_dag_migration.py:574-613` 覆盖 round-trip。

**但是**: `rg "DocumentInput|DocumentSpec|content_brief"` 在 src 里只命中 4 个文件,全部是**定义点 + converter 自身**。没有任何 planner / section_generation / writer / orchestrator reader。

= **这是 easypaper 团队画好但没接通的迁移层**。

**对 Tier 2 的意义**:
- 5/31 建议的"加 `research_question/identification_strategy` alias/derived properties"是绕开 `to_document_input`、在 `PaperMetaData` 旁边塞字段。
- 更干净的路径:**替换 `to_document_input` 内部映射**,把新 econ schema 折叠成 `content_brief: dict[str, str]`,然后**让 planner 和 section_generation 改吃 DocumentInput** 而不是 PaperMetaData。
- 工时仍是 L2(planner/section 改动量未变),但**架构对齐了 upstream 已经画出的方向**,fork 长期维护成本更低。

### C.2 `GenerationConstraints.required_sections` 才是真正的接入点

`document_spec.py:81,90`:
```python
class GenerationConstraints(BaseModel):
    required_sections: List[str] = Field(default_factory=list)
```

5/31 audit §5.3 的 grep 命中**正是这里**,但被解读为"无消费"。实际语义是:**这是预留的通用约束接口,planner 应当从 `DocumentInput.constraints.required_sections` 读取并 honor**。

5/31 建议改 `venue_config.required_sections`,但那是 venue YAML 的字段;真正的下游接口在 `GenerationConstraints`。两者最终都要走到同一个 prompt slot,但选 `GenerationConstraints` 路径意味着:

- Tier 1.5 PoC 的实际改动:让 `to_document_input()` 把 venue_config.required_sections 拷到 `GenerationConstraints.required_sections`,然后改 planner 从 constraints 读 — **比直接 patch venue_config 通道更通用**,也支持非 venue 来源的章节约束(用户自定义、profile 模板等)。

### C.3 Figure 生成不是"AI 画图工具",是"硬阻断 data visualization"(更严)

5/31 audit §6.3 写"academic_dreamer 是 AI 概念图工具,不是 matplotlib/真实数据作图"— **方向对,但低估了拒绝强度**。

`figure_supplementation.py:222-269` 有三层防御:

```python
role = _choose_role(metadata_blob, code_blob, research_blob)
if role not in ALLOWED_AUTONOMOUS_ROLES:         # ← 角色白名单
    trace["status"] = "skipped"; return [], trace

target_type = ROLE_TO_TARGET_TYPE[role]
if target_type == "data_visualization":          # ← 显式硬阻断
    trace["status"] = "skipped"
    trace["rejected"].append({"reason": "autonomous_data_visualization_forbidden"})
    return [], trace
...
generation_prompt = (
    f"...Show concepts, components, or workflow relationships only. "
    "Do not show empirical result curves, benchmark bars, metrics, or ablation data."
)
```

= 经济学的 event study coef plot / RD plot / IRF / binned scatter 在 easypaper 内部**不仅没能力,在角色路由层直接被拒绝**。

**对 Tier 3 的意义**:
- 这些图必须来自**外部 econ_analysis_agent**(EvoScientist 主线),作为 `metadata.figures: List[FigureSpec]` 用户输入注入。
- `FigureSpec` 模型支持 `auto_generate=False` + 文件路径方式 — 这是合法的注入点。
- 5/31 推荐"新增 econ_analysis_agent 输出 artifacts 喂 writer"完全正确,**但理由不是'easypaper 缺画图能力',而是 easypaper 主动拒绝这条路径**。fork 后即使我们想从内部生成,也要先解锁这个角色白名单。

### C.4 Builtin venue 只有 7 个,清单如下

`src/skills/builtin/venues/`:
```
aaai.yaml  acl.yaml  colm.yaml  iclr.yaml  icml.yaml  nature.yaml  neurips.yaml
```

零经济学 / 金融 / 社科 venue。`aer.yaml / qje.yaml / jfe.yaml / restud.yaml` 全是新写,**没有可参考的 baseline YAML**。

`reviewing/` 和 `writing/` 子目录提供了 builtin checker / constraint,这些可被同名 user skill 覆盖。

### C.5 Venue 名称匹配是 token-tolerant 的(对 Tier 1 是利好)

`registry.py:139-161` `_venue_matches` 做了:
- 全字符串相等
- 子串包含(任一方向)
- 字母数字 token 化 + token overlap
- "venue mention 包含 profile key" 规则(例:`"nature portfolio"` 匹配 `"nature"`)

= 用户输入 `style_guide="American Economic Review"`,我们写的 `aer.yaml`(name="aer")**匹配不上**(token 不重叠);但写成 `name="american-economic-review"` 就能匹配,因为 token 化后能命中。

**Tier 1 操作建议**: venue yaml `name` 字段用全名 hyphenated(`american-economic-review`、`quarterly-journal-of-economics`),让 user 用任何形态都能路由对。

### C.6 `BODY_SECTION_SOURCES` 是 dispatch table

`section_generation.py:240` `from .models import BODY_SECTION_SOURCES`,然后 line 246 `value = getattr(metadata, source, "")`。

= **字段名同时是 dispatch key**。把 `experiments` 重命名为 `empirical_results`,`BODY_SECTION_SOURCES` 表里的字面值就必须同步改 — 这是 5/31 L2 估算的具体根因之一。

---

## D. GitHub repo 复核状态(无法在本次审查中确认)

5/31 audit §8 修正了用户最初的"没有可见 GitHub repo"假设,声称 `PinkGranite/EasyPaper` 公开存在(146 commits / 11 tags / 4 stars)。

v2 无法在本次离线审查中复核:
- 源码 `PKG-INFO / pyproject.toml / README.md / setup.cfg` 没有 GitHub URL
- `rg PinkGranite|github.com` 在 src 里**零命中**
- 5/31 当时是怎么确认的没写入 audit(可能用了 WebSearch/WebFetch)

**建议**: 在签 fork 决策前用 WebFetch 复查 `github.com/PinkGranite/EasyPaper` 是否仍存在、tag 是否与 PyPI 0.2.4 对齐,作为 upstream tracking 策略的前置条件。本次 audit 不替换 5/31 的结论,但标 "未独立复核"。

---

## E. 给 EvoScientist 主线的修订执行建议

5/31 audit §9 的 Tier 1.5 三件 PoC **仍是正确路径**。基于 v2 发现,具体动作有两处调整:

### E.1 章节约束接口 — 改路径

5/31 PoC #1 写: "让 `venue_config.required_sections` 进入 planner"。
v2 建议: **让 planner 读 `DocumentInput.constraints.required_sections`**,在 `PaperMetaData.to_document_input` 里把 venue_config 拷进 constraints。
理由: §C.2,接口设计原本就指向这里;减少 fork 长期发散。

### E.2 schema 扩展 — 改路径

5/31 PoC #2 写: "保留旧字段,新增 `research_question` 和 `identification_strategy` alias/derived properties"。
v2 建议: **把新字段直接放进 `content_brief: Dict[str, str]`**,沿用现有 `to_document_input()` 通道;PaperMetaData 那层旧五字段保留 backward compat。然后**让 section_generation 改吃 DocumentInput.content_brief.get(section_type)** 而不是 `getattr(metadata, source)`。
理由: §C.1 + §C.6,这条路撕掉 dispatch table 的字面字段绑定,是 L2 工时里"真正需要做的难活";现在做 vs 半年后做都一样难,提前对齐 upstream 设计。

### E.3 工时估算不动

Tier 1 ≈ 1 周,Tier 2 ≈ 3-5 周,Tier 3 ≈ 2-3 个月(走 EvoScientist `econ_analysis_agent` 外部 artifact 路径,不在 easypaper fork 内做)。

### E.4 Top 3 风险 — 重排序

5/31 列了 3 风险。v2 排序:

1. **`figure_supplementation` 角色白名单硬阻断 data visualization**(C.3)— 比"缺画图能力"更严,fork 后要么解锁要么完全走外部图注入。
2. **`required_sections` / planner 不消费 venue YAML 章节配置**(C.2)— 接入点在通用层,改一次受益所有 venue/profile。
3. **PaperMetaData 字段被 `BODY_SECTION_SOURCES` 当 dispatch key**(C.6)— alias 解决不了,必须改 planner/section 数据流。

---

## F. 给前一版 audit 的补丁建议(如果重写 `_AUDIT.md`)

若主线决定刷新 `_AUDIT.md` 主文,以下是最值得追加的段落:

- §2 Tier 1 段:新增 "venue 名 token-tolerant 匹配"(C.5),把"L1 1 周"细化为"venue yaml 命名约定"。
- §3 Tier 2 段:替换 alias 策略为 `DocumentInput.content_brief` 路径(C.1),保留旧 5 字段 backward compat 句。
- §4 Tier 3 段:补一句"easypaper figure 系统主动拒绝 data visualization"(C.3),从根本上把 Tier 3 排除在 easypaper fork 范围外。
- §6.1 tools 段:修正 7 条 `TOOL_FACTORY` 真实条目(B.1)。
- §7.2 测试段:把 46-48 改为"约 49 个无显式 skip 标记,但 `test_table_converter_enhanced.py` 真实可跑性未验证"(B.2)。

---

## G. 仍未触及/留待验证的开放问题

5/31 audit + v2 都没碰到:

- `langgraph_dev` 在 easypaper 里是否使用(EvoScientist 主线在用)— 没 grep,留待后续。
- ccproxy 对 easypaper 的兼容性 — easypaper 用的是 `openai>=2.7.2` 和 `anthropic>=0.18.0`(vlm extra),理论上可走 base_url 重定向,但**没有静态扫描验证**。
- `test_gemini.py` 实际是否需要 GEMINI_API_KEY — 没读文件,未确认 mock 程度。
- 中文 / GBK 支持现状 — easypaper 是否有显式 encoding 处理,本次未扫,但 EvoScientist 已经踩过 ccproxy/OAuth 那一坑,可能复用同一套 fix。
