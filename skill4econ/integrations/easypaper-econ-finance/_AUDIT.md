# easypaper 0.2.4 Source-Import Audit
日期: 2026-05-31

## 1. Executive Summary

Tier 1 可行性: **中**。黑盒配置版能做 demo: 沿用 `title / idea_hypothesis / method / data / experiments / references`,写经济学 venue/writing YAML,要求用户自带数据、表、图、回归结果。但 `venue.required_sections` 静态审查未发现被生成链路消费,AER/QJE 式章节不能靠 YAML 保证。

Tier 2 可行性: **中**。schema、planner、section prompt、ML/NLP 结果图表启发式都在 Python 里有语义硬编码;不是重写,但不是“改几个 YAML”。真实改造量约 3-5 周。

Tier 3 可行性: **低**。现有图路线是 AcademicDreamer AI 插画,没有 DiD/IV/RDD 执行层。端到端经济金融科研更适合在 econpaper 新增 `econ_analysis_agent`,把实证产物喂给 writer,而不是先在 easypaper 内硬塞。

Top 3 风险:
1. `required_sections` 基本是死配置: planner fallback 仍是 ML 论文骨架。
2. `idea_hypothesis` 等字段被 Python prompt/context 多处消费,Pydantic alias 只能兼容输入,不能完成语义迁移。
3. AcademicDreamer 生成概念图,不是 event-study/RD/IRF 真实数据图。

推荐路径: 先做 **Tier 1.5 PoC**: planner 消费 venue sections;旧 schema 保持兼容并加 `research_question/identification_strategy`;新增一个只读 econ checker。PoC 通过后再进入 Tier 2。Tier 3 留给 econpaper 主线 agent 编排。

## 2. Tier 1 详细分析

阻塞项:
- builtin venue 有 `required_sections`,如 `src/skills/builtin/venues/neurips.yaml:37`,但 `rg required_sections src tests` 只命中 `src/models/document_spec.py:81,90`,未命中 planner/metadata。
- `src/agents/planner_agent/prompt_contracts.py:53` 只写 “Choose sections appropriate for {style_guide}”,没有注入 YAML sections。
- fallback 章节在 `src/agents/planner_agent/models.py:545-553`: `abstract, introduction, related_work, method, experiment, result, conclusion`。
- 最终 assembly 顺序也硬编码在 `src/agents/metadata_agent/assembly_helper.py:50-63`。

估算工作量:
- 纯黑盒 YAML/demo: L1,约 1 周。
- 若要求 `aer.yaml` 的 `[Introduction, Data, Strategy, Results, Robustness, Conclusion]` 稳定生效: 还要 3-5 天改 planner 和 fallback,不再是纯配置版。

风险: 输出能被风格 prompt 影响,但章节不被配置强制;`econ-writing-skill` 是 prompt 素材,不是执行框架;AgentSociety 插件 workflow 也继续校验旧五字段非空。

## 3. Tier 2 详细分析

阻塞项:
- schema: `src/agents/metadata_agent/models.py:159-188` 定义 `PaperMetaData`;`models.py:271-275` 在 `PaperGenerationRequest` 重复字段;`models.py:318` 后逐字段映射。
- prompt: `src/agents/shared/prompt_compiler.py:912-964` 的 introduction 参数和标题写死为 `idea_hypothesis/method/data/experiments`。
- section: `src/agents/metadata_agent/section_generation.py:147-151` 直接喂旧字段;未知 body section 在 `section_generation.py:238-249` fallback 到 `metadata.method`。
- ML 规则: `plan_review_rules.py:34-60`, `planner_elements.py:131-142`, `code_context/builder.py:51-64`, `prompt_support.py:61-73` 使用 ablation/baseline/benchmark/metric 等词表。

估算工作量: L2,约 3-5 周。schema 兼容 3-5 天;planner/section prompt 1-2 周;tools/checker 3-7 天;ML 关键词和 placement 规则替换 1 周;测试修复 1 周。

风险: `research_question + identification_strategy` 不是 `idea_hypothesis` 的简单别名;`strategy/robustness` 新章节虽能被拼标题,但内容源、review、图表 placement 仍弱;citation grounding 不能自动变成经济学叙事引用。

## 4. Tier 3 详细分析

阻塞项:
- 现有 tools 是写作辅助,不是 econometrics runner。
- `src/agents/metadata_agent/figure_supplementation.py:228-230` 拒绝自主生成 data visualization;`figure_supplementation.py:258` 明确要求不要展示 empirical result curves、metrics、ablation data。
- DiD/IV/RDD 需要数据协议、变量识别、模型选择、稳健性、聚类 SE、图表/表格绑定,现有 metadata_agent 没有这些状态机。

估算工作量: L3,至少 2-3 个月。更优路径是 econpaper 新增 `econ_analysis_agent`,输出标准化 regression/table/figure artifacts,再由 easypaper-derived layer 写作。

## 5. P0 问题逐条回答

### 5.1 PaperMetaData 字段硬编码深度

静态 grep 结果:

| 字段 | Python 全词出现 | 直接属性引用 | YAML 出现 |
| --- | ---: | ---: | ---: |
| title | 590 | 53 | 1 |
| idea_hypothesis | 84 | 18 | 0 |
| method | 263 | 18 | 5 |
| data | 346 | 12 | 0 |
| experiments | 82 | 13 | 1 |
| references | 332 | 9 | 11 |

关键消费点:
- 模型/API: `src/agents/metadata_agent/models.py:159-188`, `models.py:271-275`, `models.py:318`;`metadata_agent/router.py:452-516`。
- planner: `planner_agent/router.py:91-96`, `planner_agent.py:1444-1448`, `metadata_agent/orchestrator.py:1470-1475`。
- writer/context: `section_generation.py:147-151`, `section_generation.py:238-249`, `shared/core_ref_analyzer.py:179-181`, `shared/research_context_builder.py:141-142`, `metadata_agent/prompt_support.py:61-73`。
- figures: `figure_generation.py:212-215`, `figure_supplementation.py:186-190`。

结论: alias 可以让新输入映射到旧字段,但下游仍按 “Idea/Hypothesis” 语义写作。**改 schema 是 L2(约一个月);只做兼容 alias 是 L1**。

### 5.2 prompt 模板化程度

`src/prompts/` 只有 `__init__.py` PromptLoader,未随 sdist 提供 `.txt` 模板。真实 prompt 多在 Python:
- `shared/prompt_compiler.py:227-291` 定义 `_SECTION_PROMPTS_DEFAULTS/SECTION_PROMPTS`。
- `prompt_compiler.py:912-964` 拼 introduction;`prompt_compiler.py:1120-1330` 拼 body。
- `shared/section_prompt_builder.py:15-100` 另一套 Python `SYSTEM_PROMPTS`。
- 抽样 router: `writer_agent/router.py:523-535,681-689`;`metadata_agent/router.py:447-520`。

结论: **改 prompt = 改 Python + 可选补模板;YAML skill 主要只能 append 约束**。

### 5.3 venue.required_sections 是否被消费

未发现有效消费。`src/skills/models.py:50` 保存 `venue_config`;`src/skills/registry.py:72-104` 只按 venue 名和 target_sections 找 skill,不读 `required_sections`。兜底在 `planner_agent/models.py:545-553`, `planner_build.py:308`, `planner_agent.py:1490`, `assembly_helper.py:50-63`。

结论: **写 `aer.yaml` 并设置 required_sections 不会被稳定 honor**。除非改 planner 或把章节写入 `system_prompt_append` 交给 LLM 软遵守。

## 6. P1 问题逐条回答

### 6.1 tools 扩展性

框架半插件化。`shared/tools/base.py` 有 `WriterTool`;`registry.py` 有 `ToolRegistry`;实际装配靠 `src/agents/shared/tools/__init__.py:136-144` 的 `TOOL_FACTORY` 硬编码。`src/config/schema.py:106` 默认 `available_tools`;`react_base.py:58-66` 按名字从 factory 实例化。加 `check_pre_trends` 至少改 3-4 处: 新 tool、factory/import、config/default、agent 上下文。若要读数据/模型结果,还要扩 request/state。

### 6.2 ML 硬编码地图

grep: Python 中 `ablation=21, benchmark=32, baseline=24, hyperparameter=4, sota=1`。风险点:
- prompt: `prompt_compiler.py:259-271`, `writer_agent/router.py:530-532`, `section_prompt_builder.py:27-30`。
- plan review: `plan_review_rules.py:34-60,78-90,394-404`。
- placement: `planner_elements.py:131-142,205-212`。
- evidence/code context: `prompt_support.py:61-73`, `code_context/builder.py:51-64`。

结论: 控制流不完全 ML-only,但图表/证据 placement 明显按 ML/NLP 训练。经济学要替换为 identification、treatment/control、pre-trends、clustered SE、first stage、bandwidth、IRF 等词表。

### 6.3 figure_generation 路线

`figure_generation.py:293-304` 动态 import `academic_dreamer.generate_academic_illustration`;`pyproject.toml:42` 把它放在 images extra。PyPI [`academic-dreamer`](https://pypi.org/project/academic-dreamer/) 描述为 multi-agent academic illustrations,用 visual schema、style compilation、OpenRouter image generation、quality review 生成插图。结论: 这是 AI 概念图工具,不是 matplotlib/真实数据作图。event study/RD/IRF 图应由 `econ_analysis_agent` 生成文件后写入 `metadata.figures`。

### 6.4 citation_grounding.py 风格假设

`citation_grounding.py` 是 deterministic audit,不是风格 prompt。`citation_grounding.py:18` 解析 `\cite*`;`citation_grounding.py:257-295` 用 title/abstract token overlap 判断 claim support;`citation_grounding.py:315-319` 查 citation key 是否 section-authorized。未发现 ML compare-against 风格硬编码,也没有 econ narrative 配置。它能做最低限度 grounding,不能保证经济学 introduction 的引用编织质量。

## 7. P2 问题逐条回答

### 7.1 metadata_agent 高层流程图

`prepare_plan()` (`metadata_agent.py:529-1244`) 解析 metadata/template/refs/figures/tables/code context/docling/exemplar,调用 planner,做 core ref、research context、补图、reference discovery、EvidenceDAG、table conversion,输出 `PlanResult`。`execute_generation()` 之后分三阶段: introduction (`metadata_agent.py:1388-1426`), body (`metadata_agent.py:1438-1485`), abstract/conclusion (`metadata_agent.py:1486-1530`)。随后 `orchestrator.py` review/typeset/VLM/revision,再做 figure/table contract、citation audit、final compile。段落级生成在 `decomposed_runner.py`: core content -> citation injection -> edit -> float refs -> mini-review -> claim verifier -> retry/fallback。

### 7.2 测试套件分类

`tests/` 有 50 个 `test_*.py`。静态判断大多是纯单元或 mock LLM/httpx。`test_docling_*`, `test_exemplar_external_search.py`, `test_writer_router_endpoints.py` 有外部接口形态但使用 patch/mock;`test_table_visual_preview.py` 和 `test_table_converter_enhanced.py` 对 `pdflatex`/真实 fixture 有 skip;`test_gemini.py` 可能 env/API 敏感,需 PoC。结论: 约 46-48 个文件可作为离线 regression 起点,未运行测试,数字未确认。

### 7.3 Skill 注入优先级和冲突

`bootstrap.py:80-103` 先注册 builtin,再加载 user skills;同名覆盖。`registry.py:33-48` register 按 name overwrite。`prompt_compiler.py:195-220` 按 target_sections 过滤,再按 priority 升序 append。结论: **同名用户 skill 可干净覆盖;不同名约束会 stack,冲突只靠 priority/文本顺序**。

## 8. 隐性信息发现

academic_dreamer: 见 6.3。它是 original maintainer 维护的 AI 学术插图包,不是数据可视化分析库。

easypaper GitHub: PyPI metadata/本地 `pyproject.toml` 未填 Project-URL,但公开仓库存在: [`the original EasyPaper source project`](the original EasyPaper source repository)。页面显示 public、146 commits、11 tags、4 stars、4 source-repo forks。用户给定“没有可见 GitHub 仓库”的前提已过期/不完整;仍需确认 sdist 0.2.4 与 GitHub tag 完全一致。PyPI 0.2.4 上传日期为 2026-05-24,release history 0.1.1 到 0.2.4 共 11 版: [`easypaper` PyPI](https://pypi.org/project/easypaper/)。

boto3: 不是 Bedrock。`src/utils/storage_client.py:21` import boto3;`storage_client.py:34` 说明 wraps boto3 S3 client for OSS uploads;`storage_client.py:49-63` 读取 `STORAGE_TYPE/OSS_*`;`storage_client.py:70` 创建 `boto3.client("s3")`。调用点 `artifact_exporter.py:78-80`,用于上传 artifact。`STORAGE_TYPE != "oss"` 时 no-op。可考虑移到 server/oss extra。

其它: AgentSociety 插件提供 config template 和交互式 metadata workflow,但仍要求旧五字段;`econ-writing-skill` 价值高,但只是 1245 行 prompt 素材,不是执行系统。

## 9. 给 econpaper 团队的执行建议

建议走 **Tier 1.5 -> Tier 2**。第一周只做三件 PoC:
1. 让 `venue_config.required_sections` 进入 planner,验证 `aer.yaml` 能稳定生成 Introduction/Data/Strategy/Results/Robustness/Conclusion。
2. 保留旧字段,新增 `research_question` 和 `identification_strategy` alias/derived properties,验证 schema endpoint、planner、section prompts 不崩。
3. 新增最小 econ tool,例如 `check_economic_significance`,只读已有回归表 JSON/CSV,验证 tool factory 和 writer feedback 闭环。

长期 upstream 策略: 以 GitHub `the original EasyPaper source project` tag 为准,不要只盯 PyPI sdist。经济学写作知识先进入 econpaper YAML subagents 和 easypaper writing_constraint;实证执行能力留在 econpaper `data_analysis/econ_analysis_agent`。独立项目化后先跑离线 regression,再补 LaTeX/PDF smoke。
