# TODO_EasyPaper_EconFinance_Production_v2_HighConcurrency

版本：v2 / Production 高并发施工版  
日期：2026-06-10  
目标窗口：今晚到明早验收  
主原则：**复用 skill4econ 计量能力；EasyPaper 只消费/解释/审查产物，不重复实现计量算法。**

---

## 0. 任务背景与代码位置

### GitHub / PR

- skill4econ 整理分支：<https://github.com/randomcat4/skill4econ/tree/codex/organize-skill4econ-easypaper>
- EasyPaper econ/finance integration 子目录：<https://github.com/randomcat4/skill4econ/tree/codex/organize-skill4econ-easypaper/integrations/easypaper-econ-finance>
- PR 创建入口：<https://github.com/randomcat4/skill4econ/pull/new/codex/organize-skill4econ-easypaper>

### 本地路径与分支

```powershell
# EasyPaper fork
cd D:/myproject/EvoScientist/competitor_repos/easypaper-source
git checkout evo/econ-finance-tier1
git rev-parse --short HEAD   # 期望 latest: 63ba82c

# skill4econ repo
cd D:/myproject/skill4econ
git checkout codex/organize-skill4econ-easypaper
git rev-parse --short HEAD   # 期望 latest: 593f329
```

### 两个仓库的职责边界

| 仓库/目录 | 职责 | 禁止事项 |
|---|---|---|
| `D:/myproject/skill4econ` | 计量后端、wrapper、manifest/audit/model_table/reviewer risk/run status contract、backend discovery、validation reports | 不在这里写 EasyPaper 的生成流程；不把缺失依赖的 adapter 伪装成成功结果 |
| `D:/myproject/EvoScientist/competitor_repos/easypaper-source` | 多智能体论文生成、planner/writer/reviewer/typesetter、econ/finance metadata、file-backed artifacts、paper narrative bridge | 不实现 OLS/DID/IV/RDD/ML/空间/DEA 等计量算法；不自主生成经验结果图 |
| `D:/myproject/skill4econ/integrations/easypaper-econ-finance` | EasyPaper fork 的 integration snapshot，用于 skill4econ PR 展示和交付 | 不作为夜间多人直接主开发目录；最终从 EasyPaper fork 安全同步 |

---

## 1. 核心策略：从“造算法”改成“对接产物 + Claim Gate + 叙事桥”

### 1.1 Source of truth

1. **估计、诊断、稳健性、backend 状态**：以 `skill4econ` 输出的 `manifest.json`、`audit.json`、`model_table.csv/json`、`reviewer_risk.json`、`run_status.json`、`validation_report.json` 为准。
2. **论文中可陈述的实证结论**：必须经过 EasyPaper 侧 `claim_gate`，由 artifact 状态、claim level、估计器类型、依赖状态、diagnostics 共同决定。
3. **LaTeX 表格、图、caption、方法叙述**：只从 file-backed artifact 生成，不允许 LLM 自己编数值、显著性、图形、样本量、p 值或结论。
4. **缺口能力**：优先新增 `adapter contract`、`manifest parser`、`dependency gate`、`review checklist`，不要在 EasyPaper 里写估计算法。

### 1.2 v2 必须保持的红线

- `failed` / `missing_dependency` / `interface_only` / `parser_only` / `degraded` 不得写成论文“发现”。
- `spatial_panel_model_adapter` 如果只是 parser-only，不得写成已完成 SAR/SEM/SDM 估计。
- sklearn DML fallback 不得写成 DoubleML/EconML 包结果。
- 对 staggered DID，不得把 TWFE-only 写成完整成功；缺少 csdid/drdid 或 did_imputation 替代时最多 `not_paper_ready`。
- EasyPaper 禁止自主生成 empirical result figures；只能引用用户/skill4econ 写出的文件。
- 不自动安装包、不写入 API key、不依赖 live LLM 测试作为 release gate。

---

## 2. 现有 skill4econ 能力分层矩阵

### 2.1 可直接复用：只需 artifact contract / manifest adapter / narrative bridge

| 能力 | 当前状态 | EasyPaper v2 做法 | Claim 上限 |
|---|---|---|---|
| OLS clustered covariance | Python wrapper 已有 | 读取 `model_table`、cluster 维度、N、FE/controls、SE 类型 | `estimation_result`，若 audit pass 可写主表 |
| Panel FE/RE | Python wrapper 已有 | 映射到 Data/Empirical Strategy/Results；读取 Hausman/FE notes 若存在 | `estimation_result` |
| TWFE DID | Python/Stata wrappers 已有 | 只用于简单 DID 或作为补充；staggered 不能作为唯一主结果 | 简单 DID 可主结果；staggered 为 robustness/legacy |
| Event-study TWFE | Python wrapper 已有 | 读取 event-time coefficients、pretrend diagnostics | `event_study_descriptive_or_supporting` |
| Modern DID：`dr_did_2x2`、`cs_did_attgt`、`did_imputation_event` | Stata wrappers 已有，本地依赖 gate | 优先作为 DID 主通道；状态不成功则阻断强结论 | 成功时可主结果；缺依赖时不可 claim |
| Spatial DID / exposure DID / W audit / Moran preflight / LISA dependency gate | Python/R-gated wrappers 已有 | 明确写 reduced-form spillover；不写 structural spatial impact unless adapter has impact outputs | `reduced_form_spatial_claim` |
| IV 2SLS | Python/Stata wrappers 已有 | 强制 first-stage/weak-IV/over-ID artifact 读取；缺诊断时 reviewer risk | `iv_association_or_causal_limited` |
| Local-linear RDD / Stata rdrobust | 已有 | 读取 bandwidth、kernel、donut、covariate balance、McCrary 若有 | `local_identification_claim` |
| Quantile regression | Python/Stata 已有 | 作为 heterogeneity/distributional result；不替代 mean effect | `heterogeneity_result` |
| Threshold panel grid search | Python 已有 | 明确为 exploratory/threshold model；需要 validation | `exploratory_or_model_based` |
| Mediation | Python 已有 | 默认 mechanism suggestive；不要写 causal mediation unless design supports | `mechanism_suggestive` |
| Synthetic control | Python 已有 | 读取 fit/pre-period RMSPE/placebo 若有；否则 downgraded | `case_study_causal_limited` |
| PSM/IPW | Python/Stata teffects PSM 已有 | 只作为 balance/robustness 或 simple treatment design；不能包装为 staggered DID 主估计 | `robustness_or_adjustment` |
| Finance ML split audit | Python 已有 | 作为 leakage/temporal split audit，不写交易策略收益承诺 | `validation_audit` |
| Diagnostics | 已有 | 全部进入 reviewer attack 和 risk table | 不直接生成 causal claim |
| DEA/SBM/Malmquist adapter | vendored adapter 已有 | 读取效率结果与 backend status；缺依赖/失败不可写结论 | `efficiency_result_if_success` |

### 2.2 已有但必须验证/增强

| 能力 | 风险 | 今晚增强点 |
|---|---|---|
| Stata `csdid/drdid/did_imputation` | 本地依赖、日志解析、返回状态不稳定 | 增加 artifact schema 验证、dependency-gated 示例、not_paper_ready 映射 |
| SAR/SEM/SDM impact adapter | 可能 parser-only/interface-only | 强制 `backend_canonical_result.json` 含 direct/indirect/total 才允许 spatial impact claim |
| DML adapters | DoubleML/EconML 可能 missing_dependency；sklearn fallback 容易被误写为包结果 | `dml_backend_label` 和 `orthogonal_score_status` 必填 |
| IV | 弱工具变量/first stage/over-ID 诊断不完整时容易被写成强因果 | claim gate 要求 first-stage artifact 或 risk warning |
| RDD | 带宽、操纵检验、协变量平衡可能缺 | 缺项时 Reviewer Risk 自动写入 |
| Finance ML | leakage、look-ahead、cross-sectional/time split 混用 | 强制 split audit + embargo/purge 字段 |
| DEA | 效率解释容易被写成因果 | 只允许效率/生产率措辞，不允许政策因果 unless independent design |

### 2.3 顶级计量/金融缺口：新增 adapter，不在 EasyPaper 写算法

| 缺口 | 所属层 | 今晚做法 | 是否进 release gate |
|---|---|---|---|
| Fama-MacBeth cross-sectional regressions | Finance adapter gap | 定义 manifest contract + dependency-gated backend adapter spec；优先读外部结果 | Backlog unless already quick pass |
| Asset-pricing factor model / alpha table / GRS | Finance adapter gap | 定义 table schema：factor set、alpha、t、NW lag、test status | Backlog/spec，不能编结果 |
| Portfolio sorts / long-short tables | Finance adapter gap | 定义 artifact schema + leakage/date sort checklist | Backlog/spec |
| Event-study abnormal return / CAR/BHAR | Finance adapter gap | 定义 input/output schema；只 file-backed | Backlog/spec |
| Newey-West/HAC generic SE label | Existing regression enhancement | 若 skill4econ 已输出 SE type 直接读取；否则 docs gap | Manual signoff |
| Weak-IV robust inference / AR/CLR | IV enhancement | reviewer checklist + optional adapter gap | Backlog unless artifact exists |
| Multiple hypothesis correction / Romano-Wolf / BH q-values | Quality/stat enhancement | 先新增 reviewer checklist + manifest fields | Backlog |
| Oster/Altonji sensitivity | Robustness adapter gap | 只做 checklist/adapter spec | Backlog |
| Power/MDE | Design diagnostic gap | checklist + optional artifact fields | Backlog |
| Structural IO/DSGE/welfare | 不适合作为 v2 自动化 | 只做 paper checklist，强制人工签核 | Manual-only |

---

## 3. 高并发工作方式

### 3.1 双机协同

| 角色 | 做什么 | 不做什么 | 交付 |
|---|---|---|---|
| Local code fork agents | 改代码、写测试、跑 pytest、提交 commits | 不做 live web 文献判断；不凭直觉写顶刊规则 | 小粒度 commits + test logs |
| skill4econ agents | 对接/导出 manifest、补 docs/contracts、跑 smoke | 不改 EasyPaper 生成核心 | contract + adapter + fixture |
| ChatGPT 网页版 / live-web 老哥 | 顶层计量判断、论文质量、reviewer attack、top-journal risk、术语降级 | 不直接改代码；不声称读过本地未提供文件 | review memo + red-flag list |
| Merge captain | 串联分支、解决冲突、跑 release gate、同步 integration snapshot | 不抢各 Agent 写入边界 | final branch + PR notes |

### 3.2 必备状态文件

在两个仓库根目录都维护一个轻量 handoff 目录，避免多 Agent 互相踩文件：

```text
_handoff/
  agent_A_contracts.md
  agent_B_easypaper_ingest.md
  agent_C_claim_gate.md
  agent_D_narrative.md
  agent_E_quality_eval.md
  agent_F_skill4econ_export.md
  agent_G_finance_gaps.md
  merge_log.md
  release_gate.md
```

每个 Agent 完成一个 commit 前必须更新自己的 handoff：

```markdown
## Agent X status
- Branch:
- Files touched:
- Tests run:
- Passing:
- Known failures:
- Needs from others:
- Safe to merge after:
```

### 3.3 推荐 worktree

```powershell
# EasyPaper fork worktrees
cd D:/myproject/EvoScientist/competitor_repos/easypaper-source
git status --short
git worktree add -b agent/A-contracts D:/myproject/worktrees/easypaper-A evo/econ-finance-tier1
git worktree add -b agent/B-ingest    D:/myproject/worktrees/easypaper-B evo/econ-finance-tier1
git worktree add -b agent/C-claim     D:/myproject/worktrees/easypaper-C evo/econ-finance-tier1
git worktree add -b agent/D-narrative D:/myproject/worktrees/easypaper-D evo/econ-finance-tier1
git worktree add -b agent/E-quality   D:/myproject/worktrees/easypaper-E evo/econ-finance-tier1

# skill4econ worktrees
cd D:/myproject/skill4econ
git status --short
git worktree add -b agent/F-skill4econ-export D:/myproject/worktrees/skill4econ-F codex/organize-skill4econ-easypaper
git worktree add -b agent/G-finance-gaps      D:/myproject/worktrees/skill4econ-G codex/organize-skill4econ-easypaper
```

---

## 4. Phase 总览

| Phase | 名称 | Owner | 可并发 | 依赖 |
|---:|---|---|---|---|
| P0 | Baseline freeze / safety rails | Merge captain + all | 否 | 无 |
| P1 | Artifact Contract v2 | Agent A + F | A/F 可并发 | P0 |
| P2 | skill4econ Manifest Export Adapter | Agent F | 可与 P3/P4 开始并行 | P1 skeleton |
| P3 | EasyPaper Manifest Ingest Adapter | Agent B | 可与 P2 并行，最终对齐 | P1 |
| P4 | Capability Registry + Gap Matrix | Agent A + G + live-web | 可并发 | P1 |
| P5 | Claim Gate v2 | Agent C | 可与 P6 并行 | P1/P3 |
| P6 | Table/Figure/Caption Locked Bridge | Agent B + C | 可并发 | P3/P5 skeleton |
| P7 | Paper Narrative Bridge | Agent D | 可与 P8/P9 并行 | P4/P5 |
| P8 | Planner/Section Routing for Econ/Finance | Agent D | 可与 P7 并行 | P4 |
| P9 | Quality Eval + Reviewer Attack Pack | Agent E + live-web | 可并发 | P4/P5 |
| P10 | DID/Panel Production Route | Agent C + F | 可并发 | P2/P5 |
| P11 | IV/RDD/SCM/PSM/Quantile/Threshold Route | Agent C + F | 可并发 | P2/P5 |
| P12 | Spatial/DML/DEA Risk Route | Agent C + F | 可并发 | P2/P5 |
| P13 | Finance Tier-1 Gap Adapter Specs | Agent G + live-web | 可并发 | P4 |
| P14 | Runner/CLI/Config Bridge | Agent B + H | 可并发 | P3/P5/P7 |
| P15 | End-to-End Fixtures + Regression Matrix | Agent E + Merge captain | 部分并发 | P6-P14 |
| P16 | PR Packaging + Integration Snapshot Sync | Merge captain | 否 | P15 |
| P17 | Morning Release Signoff | Merge captain + live-web + all | 否 | P16 |

---

## 5. Phase 任务卡

### P0 — Baseline freeze / safety rails

**目标**  
冻结两个 repo 当前状态、确认分支/commit、跑 baseline，不让后续 Agent 在未知失败上叠改。

**Owner / Agent role**  
Merge captain 主导；所有 Agent 只读参与。

**文件/模块**  
- `D:/myproject/EvoScientist/competitor_repos/easypaper-source`
- `D:/myproject/skill4econ`
- 新增/更新：`_handoff/merge_log.md`、`_handoff/release_gate.md`

**具体改动**  
1. 记录 `git rev-parse --short HEAD`、`git status --short`。
2. 跑当前 baseline。
3. 将已知失败、缺依赖、跳过项写入 `_handoff/release_gate.md`。
4. 确认 `.env`、API key、outputs、大文件不被 git 跟踪。
5. 明确 integration snapshot 不作为多人主开发目录。

**测试/命令**

```powershell
# EasyPaper
cd D:/myproject/EvoScientist/competitor_repos/easypaper-source
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
git rev-parse --short HEAD
git status --short
python -m pytest -m "not live_llm and not latex and not slow" -q
python -m pytest `
  tests/test_document_input_econ_constraints.py `
  tests/test_orchestrator_passes_econ_constraints.py `
  tests/test_planner_required_sections.py `
  tests/test_econ_section_generation_content_brief.py `
  tests/test_assembly_order_econ.py `
  tests/test_no_autonomous_result_figures.py `
  -q
python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml --out outputs/aer_minimal_baseline --mock-llm --no-pdf

# skill4econ
cd D:/myproject/skill4econ
git rev-parse --short HEAD
git status --short
conda run -n base python -m skill4econ.cli list
conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict
```

**验收标准**  
- 两个 repo 的 starting commit 写入 handoff。
- baseline pass/fail 明确，不把既有失败算作新回归。
- 每个 Agent 已拿到独立 worktree 或明确写入边界。

**风险**  
- baseline 原本有失败；处理方式是记录而不是盲修所有。
- Windows path / encoding 导致测试输出乱码；必须设 `PYTHONUTF8` 和 `PYTHONIOENCODING`。

**commit 名**  
`chore: record econ finance production v2 baseline`

**可并发/依赖**  
不可并发。所有后续 phase 依赖 P0。

---

### P1 — Artifact Contract v2

**目标**  
定义 EasyPaper 能消费的统一 artifact contract v2，覆盖 skill4econ 的 manifest/audit/model_table/reviewer_risk/run_status/validation reports，并把 status/claim level 写死为机器可验证字段。

**Owner / Agent role**  
Agent A：EasyPaper contract/model。  
Agent F：skill4econ contract/docs 对齐。

**文件/模块**  
EasyPaper:
- `src/models/econ_artifact_contract.py`（新建或等价位置）
- `src/models/document_spec.py`
- `src/generation/artifact_manifest.py` 或现有 manifest 模块
- `tests/test_artifact_manifest_v2_contract.py`
- `tests/test_artifact_claim_level_schema.py`

skill4econ:
- `docs/contracts/easypaper_artifact_contract_v2.md`
- `src/skill4econ/contracts/easypaper.py`（如已有 contracts 模块则扩展）
- `tests/test_easypaper_contract_v2.py`

**具体改动**  
1. 新增 `EconArtifactBundleV2`：
   - `bundle_id`
   - `created_at`
   - `producer`: `skill4econ`
   - `producer_version`
   - `method_family`
   - `method_name`
   - `engine`: `python|stata|r|external|manual_file`
   - `backend_label`
   - `run_status`: `success|degraded|not_paper_ready|failed|missing_dependency|interface_only|parser_only`
   - `claim_level`
   - `files`: manifest/audit/model_table/figures/tables/logs/validation/reviewer_risk
   - `sample`: N/entities/time range/filters if available
   - `estimation_metadata`: FE, controls, SE, cluster, weights, bandwidth, treatment timing, W matrix, etc.
   - `diagnostics`: list of typed diagnostics with `status`, `severity`, `paper_action`
   - `allowed_paper_uses`
   - `forbidden_claims`
2. claim levels 只允许枚举：
   - `no_result`
   - `descriptive_only`
   - `estimation_result`
   - `robustness_result`
   - `causal_design_supported`
   - `mechanism_suggestive`
   - `prediction_validation`
   - `efficiency_result`
   - `manual_signoff_required`
3. status 到 claim 的默认映射：
   - `success` 才可进入主结果候选。
   - `degraded` 只能 robustness/supporting，且必须明示 limitation。
   - `not_paper_ready` 只能写方法限制/appendix，不可写主结论。
   - `failed|missing_dependency|interface_only|parser_only` 默认 `no_result`。
4. contract 中必须支持 “read-only artifact bundle”：EasyPaper 不运行估计，只读取文件。
5. 加 schema roundtrip 测试；缺字段默认 fail loud。

**测试/命令**

```powershell
# EasyPaper
python -m pytest tests/test_artifact_manifest_v1.py tests/test_artifact_manifest_v2_contract.py tests/test_artifact_claim_level_schema.py -q

# skill4econ
conda run -n base python -m pytest tests/test_easypaper_contract_v2.py -q
conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict
```

**验收标准**  
- v2 schema 能读 v1 manifest 或提供清晰 migration error。
- 所有非成功状态默认不能产生 empirical claim。
- schema docs 与 Pydantic/dataclass 字段一致。
- EasyPaper 与 skill4econ 对 claim/status 枚举完全一致。

**风险**  
- 两边 enum 不一致导致后续 adapter 混乱；用 shared docs + tests 固定。
- 过早大改 `document_spec.py` 影响 planner；新增模型优先，少改已有模型。

**commit 名**  
`contracts: define easypaper skill4econ artifact contract v2`

**可并发/依赖**  
P1 依赖 P0。Agent A/F 可并发，但 enum 必须在同一 handoff 中锁定。

---

### P2 — skill4econ Manifest Export Adapter

**目标**  
让 skill4econ 现有 wrappers 的输出可以被 EasyPaper 统一消费；只做 export/normalize，不改估计算法。

**Owner / Agent role**  
Agent F：skill4econ backend/export owner。

**文件/模块**  
- `src/skill4econ/adapters/easypaper_manifest.py`（新建或复用 adapters 目录）
- `src/skill4econ/cli.py` 或 workflow CLI 注册点
- `examples/easypaper_bridge/`
- `tests/test_easypaper_manifest_export.py`
- `docs/contracts/easypaper_artifact_contract_v2.md`

**具体改动**  
1. 新增 `export_easypaper_bundle(run_dir, out_dir=None)`：
   - 读取 `manifest.json`、`audit.json`、`model_table.*`、`reviewer_risk.*`、`validation_report.*`。
   - 生成 `easypaper_bundle.json`。
   - 不对估计值做再计算。
2. 方法映射：
   - `did_paper_run` → DID bundle，含 design type、treatment timing、event-study files。
   - OLS/panel/IV/RDD/qreg/SCM/PSM/spatial/DML/DEA → method_family。
3. 对 dependency-gated 结果：
   - `missing_dependency` 必须保留 discovery chain。
   - `interface_only/parser_only` 必须 `claim_level=no_result`。
4. CLI：
   - `python -m skill4econ.cli export-easypaper --run-dir <dir> --out <dir>`
   - 若 CLI 不宜动，先提供 script `scripts/export_easypaper_bundle.py`。
5. fixtures：
   - success bundle
   - missing_dependency bundle
   - degraded bundle
   - parser_only spatial bundle
   - DID not_paper_ready bundle

**测试/命令**

```powershell
cd D:/myproject/skill4econ
conda run -n base python -m pytest tests/test_easypaper_manifest_export.py -q
conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict

# 若实现 CLI
conda run -n base python -m skill4econ.cli export-easypaper `
  --run-dir examples/mini_panel/example_run_dir `
  --out outputs/easypaper_bundle_smoke
```

**验收标准**  
- 不同 status fixture 都能导出 v2 bundle。
- 缺失文件时 fail loud，除非 contract 明确 optional。
- `failed/missing_dependency/interface_only/parser_only` 绝不被导出为可 claim。
- 不修改任何估计算法实现。

**风险**  
- run_dir 结构在不同 wrapper 中不一致；adapter 用容错读取，但缺关键字段必须报错。
- CLI 改动影响全局；优先薄封装。

**commit 名**  
`adapters: export skill4econ runs as easypaper artifact bundles`

**可并发/依赖**  
依赖 P1 skeleton。可与 P3/P4 并行，最终对齐 schema。

---

### P3 — EasyPaper Manifest Ingest Adapter

**目标**  
EasyPaper 可以读取 skill4econ bundle，将其转成 paper planning/writing 可用的 table specs、figure specs、content brief 和 risk signals。

**Owner / Agent role**  
Agent B：EasyPaper ingest owner。

**文件/模块**  
- `src/generation/econ_artifact_ingest.py`（新建）
- `src/generation/manifest_to_table_specs.py` 或现有等价模块
- `src/generation/manifest_to_figure_specs.py` 或现有等价模块
- `src/models/document_spec.py`
- `tests/test_easypaper_ingests_skill4econ_bundle.py`
- `tests/test_manifest_to_table_specs.py`
- `tests/test_manifest_to_figure_specs.py`

**具体改动**  
1. 在 metadata/request 层新增 `empirical_artifact_bundles`：
   ```yaml
   empirical_artifact_bundles:
     - path: ../skill4econ_run/easypaper_bundle.json
       role: main_results
       required: true
   ```
2. loader 必须：
   - 使用 `materials_root` 解析相对路径。
   - 拒绝越权路径、目录遍历、非 JSON bundle。
   - 读取 bundle 后进行 schema validation。
3. 转换输出：
   - `TableSpec`: model table, summary stats, balance, robustness, appendix。
   - `FigureSpec`: event-study, coefficient plot, RDD plot, SCM fit, spatial diagnostics；但必须 file-backed。
   - `ContentBrief`: method narrative facts, allowed claims, limitations, reviewer risks。
4. `required: true` 的 bundle 如果 invalid/missing，runner 必须 fail，不得静默生成空论文。
5. `required: false` 的 bundle invalid 时写入 risk，不生成结果 claim。

**测试/命令**

```powershell
cd D:/myproject/EvoScientist/competitor_repos/easypaper-source
python -m pytest `
  tests/test_artifact_path_validation.py `
  tests/test_easypaper_ingests_skill4econ_bundle.py `
  tests/test_manifest_to_table_specs.py `
  tests/test_manifest_to_figure_specs.py `
  -q
```

**验收标准**  
- 能读 P2 fixture bundle。
- 无效路径/缺少核心字段被拒绝。
- ingest 输出明确区分 `allowed_paper_uses` 与 `forbidden_claims`。
- 不触发任何估计算法运行。

**风险**  
- 现有 `DocumentInput`/metadata 字段过载；优先新增 optional 字段，不破坏旧 examples。
- bundle 相对路径在 scripts/SDK/server 三种模式中解析不一致；必须测 runner 和 SDK。

**commit 名**  
`ingest: read skill4econ artifact bundles in easypaper`

**可并发/依赖**  
依赖 P1。可与 P2 并行，但最终需要用 P2 fixture 做 contract test。

---

### P4 — Capability Registry + Gap Matrix

**目标**  
把“已有可直接用 / 已有但需验证增强 / 缺口需新增 adapter / 只做论文 checklist”做成机器可读 registry，供 planner、claim gate、reviewer 使用。

**Owner / Agent role**  
Agent A：EasyPaper registry。  
Agent G：finance/econometrics gap taxonomy。  
live-web 老哥：顶层方法判断审查。

**文件/模块**  
- EasyPaper: `src/generation/econ_capability_registry.py`
- EasyPaper: `src/prompts/econ_method_boundaries.py` 或现有 prompts
- skill4econ docs: `docs/roadmaps/easypaper_capability_gap_matrix.md`
- tests:
  - `tests/test_econ_capability_registry.py`
  - `tests/test_gap_matrix_claim_defaults.py`

**具体改动**  
1. registry 字段：
   - `method_family`
   - `skill4econ_methods`
   - `default_claim_level`
   - `required_artifacts`
   - `required_diagnostics`
   - `paper_sections_allowed`
   - `paper_sections_forbidden`
   - `top_journal_risks`
   - `manual_signoff_triggers`
2. 写入直接复用能力清单：
   - OLS, panel FE/RE, DID core, event-study, spatial DID, IV, RDD, qreg, threshold, mediation, SCM, PSM/IPW, finance ML audit, diagnostics, DEA。
3. 写入增强/验证能力：
   - dependency-gated Stata DID
   - DML package adapters
   - spatial impact decomposition
   - weak IV diagnostics
   - RDD manipulation/balance
   - finance ML leakage audit
4. 写入 finance gaps：
   - Fama-MacBeth
   - portfolio sorts
   - factor alpha/GRS
   - CAR/BHAR event study
   - HAC/Newey-West labels
   - multiple testing
5. registry 不调估计器，只给 claim gate 和 prompts 提供约束。

**测试/命令**

```powershell
python -m pytest tests/test_econ_capability_registry.py tests/test_gap_matrix_claim_defaults.py -q
```

**验收标准**  
- 每个 method_family 都有默认 claim 和 forbidden claims。
- finance gaps 不会被误标为可直接运行。
- live-web review memo 对每个高风险方法给出 “可写/不可写/需人工签核” 建议。
- registry 覆盖所有 P2 fixture 方法。

**风险**  
- 把 checklist 当成能力；必须有 `implementation_status` 字段。
- registry 与 skill4econ README 漂移；文档中注明更新时间和验证命令。

**commit 名**  
`registry: classify skill4econ capabilities for paper claims`

**可并发/依赖**  
依赖 P1。可与 P2/P3 并行。

---

### P5 — Claim Gate v2

**目标**  
建立硬门禁：任何论文句子、表格 caption、abstract/conclusion claim 都必须被 artifact status + claim level 允许。

**Owner / Agent role**  
Agent C：claim gate owner。

**文件/模块**  
- `src/generation/econ_claim_gate.py`（新建）
- `src/agents/metadata_agent/decomposed_runner.py`
- `src/agents/metadata_agent/section_generation.py`
- `src/agents/writer_agent/*` 或 writer router 相关文件
- tests:
  - `tests/test_claim_gate_blocks_failed_artifacts.py`
  - `tests/test_claim_gate_downgrades_degraded.py`
  - `tests/test_no_autonomous_empirical_claims.py`
  - `tests/test_result_caption_locked.py`

**具体改动**  
1. 新增 `ClaimGateDecision`：
   - `allow`
   - `max_claim_level`
   - `required_qualifiers`
   - `forbidden_phrases`
   - `must_include_limitations`
   - `manual_signoff_required`
2. 对每个 bundle 生成 `claim_context` 注入 section writer：
   - 可写 facts：方法、数据范围、估计器、表/图引用、诊断结果。
   - 不可写 facts：未运行的 robustness、没有 artifact 的机制、显著性方向、政策含义。
3. 在 decomposed paragraph generation 后做本地规则审查：
   - 禁止 “we find significant/large/robust/causal” 等词出现在没有对应 claim level 的段落。
   - 禁止 abstract/conclusion 超过主结果 claim level。
4. `failed/missing_dependency/interface_only/parser_only`：
   - 只允许写入 appendix “not run / dependency missing / planned analysis”。
   - 不允许写 results。
5. `degraded/not_paper_ready`：
   - 必须带 limitation 句。
   - 不允许出现在 abstract 作为主发现。
6. 生成 `claim_gate_report.json`。

**测试/命令**

```powershell
python -m pytest `
  tests/test_claim_gate_blocks_failed_artifacts.py `
  tests/test_claim_gate_downgrades_degraded.py `
  tests/test_no_autonomous_empirical_claims.py `
  tests/test_result_caption_locked.py `
  tests/test_econ_section_generation_content_brief.py `
  -q
```

**验收标准**  
- 无 artifact 的 mock paper 不会出现经验结论。
- failed/missing_dependency bundle 只生成 limitation，不生成结果。
- degraded bundle 自动降级措辞。
- claim gate report 能指出每个被拦截/降级的 claim。

**风险**  
- LLM 输出多样，纯字符串规则漏检；先做 conservative forbidden phrases + content brief 约束，后续再加 LLM judge。
- 过严导致空 results；这是可接受的，宁可少写，不可伪科学。

**commit 名**  
`guard: enforce artifact-backed empirical claim gates`

**可并发/依赖**  
依赖 P1/P3。可与 P6/P7 并行，但最终必须在 P15 统一测。

---

### P6 — Table/Figure/Caption Locked Bridge

**目标**  
把 skill4econ 的表/图资产安全注入 EasyPaper；caption 只允许读取 artifact metadata，不允许 LLM 编造。

**Owner / Agent role**  
Agent B + Agent C。

**文件/模块**  
- `src/generation/manifest_to_table_specs.py`
- `src/generation/manifest_to_figure_specs.py`
- `src/generation/table_renderer.py` 或现有 table converter
- `src/generation/figure_renderer.py` 或现有 figure path injection
- `tests/test_table_direct_injection.py`
- `tests/test_file_backed_result_figure_does_not_use_dreamer.py`
- `tests/test_result_caption_locked.py`
- `tests/test_table_visual_preview.py`

**具体改动**  
1. `TableSpec` 必须含：
   - `source_bundle_id`
   - `source_file`
   - `columns`
   - `notes`
   - `se_type`
   - `cluster`
   - `sample`
   - `claim_level`
   - `status`
2. `FigureSpec` 必须含：
   - `source_bundle_id`
   - `source_file`
   - `figure_type`
   - `caption_locked: true`
   - `caption_source_fields`
   - `alt_text`
3. caption 生成规则：
   - 如果 `caption_locked=true`，LLM 不能改数值或结论，只能转换格式。
   - 对 event-study caption 强制写明 pre-trend status if available。
   - 对 spatial caption 强制写明 reduced-form / W exposure。
4. 没有 file-backed figure 时，不调用 Dreamer/图像生成。
5. LaTeX 注入必须可复现，并写 `artifact_usage_report.json`。

**测试/命令**

```powershell
python -m pytest `
  tests/test_manifest_to_table_specs.py `
  tests/test_manifest_to_figure_specs.py `
  tests/test_table_direct_injection.py `
  tests/test_file_backed_result_figure_does_not_use_dreamer.py `
  tests/test_result_caption_locked.py `
  -q
```

**验收标准**  
- 表格数字来自文件，测试可追踪。
- 缺图时不会生成假图。
- caption 中不得出现 source metadata 不存在的显著性/效应方向。
- 生成 artifact usage report。

**风险**  
- 表格格式多样；先支持 canonical `model_table.csv/json`，其他格式放 backlog。
- LaTeX 转义/路径在 Windows 下出错；路径测试必须覆盖空格和反斜杠。

**commit 名**  
`render: inject artifact-backed tables figures and locked captions`

**可并发/依赖**  
依赖 P3/P5 skeleton。可与 P7/P8 并行。

---

### P7 — Paper Narrative Bridge

**目标**  
让论文叙事使用 skill4econ artifact facts：Data、Empirical Strategy、Results、Robustness、Conclusion 各段都有可写事实和限制，不让 LLM 自由发挥。

**Owner / Agent role**  
Agent D：narrative/prompt owner。

**文件/模块**  
- `src/generation/econ_content_brief.py`
- `src/agents/metadata_agent/section_generation.py`
- `src/agents/metadata_agent/decomposed_runner.py`
- `src/prompts/econ_sections.py` 或现有 prompts
- `tests/test_econ_section_generation_content_brief.py`
- `tests/test_narrative_section_shape_guards.py`
- `tests/test_econ_body_section_sources.py`

**具体改动**  
1. 新增 `EconContentBrief`：
   - `design_summary`
   - `data_summary`
   - `estimation_summary`
   - `identification_assumptions`
   - `diagnostics_summary`
   - `allowed_results_sentences`
   - `limitations_sentences`
   - `reviewer_attack_points`
   - `must_cite_tables`
   - `must_not_claim`
2. 每个 section 的输入：
   - Introduction：只允许写 motivating claim，不允许没有 artifact 的 result claim。
   - Data：样本、时间、单位、处理组、变量构造来自 bundle/sample metadata。
   - Empirical Strategy：估计式、FE/controls/SE、identification assumptions 来自 method registry + artifact。
   - Results：只写 `success` 且 allowed 的表/图。
   - Robustness：只写已成功运行的 robustness bundle；没跑就写 planned/backlog，不写 “robust”。
   - Conclusion：不得超出 Results 的最高 claim level。
3. 将 reviewer risk 自动加入 Results/Limitations。
4. 若没有 artifact，生成 “empirical plan” 版本，而不是 fake results paper。

**测试/命令**

```powershell
python -m pytest `
  tests/test_econ_section_generation_content_brief.py `
  tests/test_narrative_section_shape_guards.py `
  tests/test_econ_body_section_sources.py `
  tests/test_no_autonomous_empirical_claims.py `
  -q
```

**验收标准**  
- 每个 section 都能追溯到 bundle/content brief。
- Abstract/Conclusion 不会写超过 Results 的 claim。
- 缺 artifact 时仍能生成非伪造的 proposal-style draft。
- reviewer risks 出现在 paper 或 summary。

**风险**  
- prompt 太长导致 writer 忽略；用短 structured brief + hard local gate。
- 结果段过干；可以让 LLM润色，但不能新增事实。

**commit 名**  
`narrative: bridge skill4econ artifacts into econ paper sections`

**可并发/依赖**  
依赖 P4/P5。可与 P8/P9 并行。

---

### P8 — Planner/Section Routing for Econ/Finance

**目标**  
强化 AER/QJE/JFE 等 venue-aware section routing，但不让 planner 自行发明结果或方法。

**Owner / Agent role**  
Agent D。

**文件/模块**  
- `src/agents/planner_agent/models.py`
- `src/agents/planner_agent/planner_agent.py`
- `src/agents/metadata_agent/orchestrator.py`
- `src/config/*venue*` 或 `skills/` venue configs
- tests:
  - `tests/test_planner_required_sections.py`
  - `tests/test_plan_request_econ_fields.py`
  - `tests/test_planner_prompt_includes_econ_constraints.py`
  - `tests/test_econ_venue_configs.py`
  - `tests/test_jfe_anonymous_output.py`

**具体改动**  
1. `PlanRequest` 必须带：
   - `discipline`
   - `venue`
   - `empirical_artifact_summary`
   - `claim_constraints`
   - `required_sections`
   - `forbidden_sections_or_claims`
2. section taxonomy：
   - Econ default：Introduction, Data, Empirical Strategy, Results, Robustness, Conclusion。
   - Finance default：Introduction, Data, Empirical Design, Main Results, Asset Pricing/Portfolio Tests or Prediction Validation as applicable, Robustness, Conclusion。
3. JFE：
   - 匿名输出、data/portfolio/identification 结构、appendix risk。
4. QJE/AER：
   - identification clarity、mechanism/robustness 不能超 claim。
5. planner 输出中记录 `section_source_requirements`，writer 不满足则 fail/skip。

**测试/命令**

```powershell
python -m pytest `
  tests/test_plan_request_econ_fields.py `
  tests/test_planner_required_sections.py `
  tests/test_planner_prompt_includes_econ_constraints.py `
  tests/test_econ_venue_configs.py `
  tests/test_jfe_anonymous_output.py `
  -q
```

**验收标准**  
- planner 不会省略 Data/Empirical Strategy/Results/Robustness。
- finance venue 不会误用纯 econ DID 模板。
- section requirements 能传到 section generation。
- legacy metadata examples 仍通过。

**风险**  
- 改 planner 容易影响全局写作；只在 `discipline in {economics, finance}` 时启用。
- venue 规则不要伪装成官方格式，命名为 internal style profile。

**commit 名**  
`planner: route econ finance sections with artifact constraints`

**可并发/依赖**  
依赖 P4。可与 P7 并行，但要协调 section brief 字段名。

---

### P9 — Quality Eval + Reviewer Attack Pack

**目标**  
给生成论文加质量评估：审稿人会攻击什么、哪些 top-journal 风险必须手动签核、哪些 claim 要降级。

**Owner / Agent role**  
Agent E + live-web 老哥。

**文件/模块**  
- `src/generation/econ_quality_eval.py`
- `src/generation/reviewer_attack_pack.py`
- `tests/test_econ_quality_eval.py`
- `tests/test_reviewer_attack_pack.py`
- 输出：`reviewer_attack_pack.md/json`、`top_journal_risk_report.md/json`

**具体改动**  
1. 质量维度：
   - data/source transparency
   - identification assumptions
   - estimator appropriateness
   - standard error/clustering
   - pre-trends / treatment timing
   - robustness coverage
   - mechanism overclaim
   - external validity
   - finance leakage/look-ahead
   - multiple testing
2. 对每个 artifact bundle 生成 risk points：
   - severity: `info|minor|major|blocker`
   - section: Data/Empirical Strategy/Results/Robustness
   - action: `write_limitation|downgrade_claim|manual_signoff|block_release`
3. reviewer attack 输出同时给 writer 和 release gate。
4. live-web 老哥审查：
   - DID 是否使用正确现代 estimator。
   - Spatial 是否 reduced-form 表述。
   - Finance asset-pricing/ML 是否有 leakage。
   - JFE/AER/QJE 风险是否需要手动降级。

**测试/命令**

```powershell
python -m pytest tests/test_econ_quality_eval.py tests/test_reviewer_attack_pack.py -q
```

**验收标准**  
- 任何 `major/blocker` risk 都出现在 release report。
- risk 能反向约束 narrative，不只是日志。
- live-web memo 被保存到 `_handoff/live_web_review.md` 或 `docs/reviews/`.

**风险**  
- 质量评估变成空泛 checklist；必须绑定具体 bundle/method/status。
- live-web 观点不能自动覆盖 artifact truth；只作为 manual signoff 输入。

**commit 名**  
`quality: add reviewer attack and top journal risk reports`

**可并发/依赖**  
依赖 P4/P5。可与 P7/P8 并行。

---

### P10 — DID/Panel Production Route

**目标**  
把 skill4econ 已有 DID/panel 能力接入 EasyPaper production route，尤其避免 staggered DID 的 TWFE 误用。

**Owner / Agent role**  
Agent C + Agent F。

**文件/模块**  
- EasyPaper registry/claim gate/content brief
- skill4econ export fixture: `examples/easypaper_bridge/did_*`
- tests:
  - `tests/test_did_bundle_claim_gate.py`
  - `tests/test_staggered_did_twfe_not_full_success.py`
  - `tests/test_event_study_pretrend_narrative.py`

**具体改动**  
1. DID method routing：
   - `simple_2x2` → `dr_did_2x2` 优先；TWFE 可补充。
   - `staggered_adoption` → `cs_did_attgt` 或 `did_imputation_event` 优先。
   - TWFE-only staggered → `not_paper_ready`，只能 appendix/diagnostic。
2. event-study：
   - 读取 event_time coefficients。
   - pre-trend fail/unknown 时 conclusion 降级。
3. panel FE/RE：
   - 读取 FE dimension、cluster、N、entity/time counts。
   - 不写 causal unless design bundle 支持。
4. `did_common_output.json` bridge：
   - 只对 local treatment coefficient 使用。
   - spillover W*D coefficient 保持 reduced-form。

**测试/命令**

```powershell
python -m pytest `
  tests/test_did_bundle_claim_gate.py `
  tests/test_staggered_did_twfe_not_full_success.py `
  tests/test_event_study_pretrend_narrative.py `
  tests/test_planner_required_sections.py `
  -q
```

**验收标准**  
- staggered TWFE-only 不能成为 abstract main finding。
- csdid/drdid 成功时能生成主 DID table narrative。
- pretrend risk 进入 reviewer attack。
- panel-only result 不被包装成 causal policy effect。

**风险**  
- fixture 不代表所有 DID outputs；先覆盖 canonical outputs，其他格式 backlog。
- 论文措辞容易过强；claim gate 优先。

**commit 名**  
`did: route panel and modern did artifacts safely`

**可并发/依赖**  
依赖 P2/P5。可与 P11/P12 并行。

---

### P11 — IV/RDD/SCM/PSM/Quantile/Threshold Route

**目标**  
把已存在的非 DID 主流计量方法接入 paper route，并设置各自的诊断和措辞限制。

**Owner / Agent role**  
Agent C + Agent F。

**文件/模块**  
- `src/generation/econ_capability_registry.py`
- `src/generation/econ_claim_gate.py`
- `src/generation/econ_content_brief.py`
- fixtures:
  - `examples/easypaper_bridge/iv_2sls_success`
  - `examples/easypaper_bridge/rdd_success_or_missing_diag`
  - `examples/easypaper_bridge/scm_success`
  - `examples/easypaper_bridge/psm_balance`
  - `examples/easypaper_bridge/qreg_threshold`
- tests:
  - `tests/test_iv_rdd_claim_gate.py`
  - `tests/test_scm_psm_quantile_narrative.py`

**具体改动**  
1. IV：
   - 必填 first-stage/weak IV status；缺失则 `major risk`。
   - over-ID/under-ID 有则读取；无则 limitation。
2. RDD：
   - 必填 running variable、cutoff、bandwidth、kernel、polynomial order。
   - manipulation/balance 缺失则 reviewer risk。
3. SCM：
   - pre-fit/RMSPE/placebo 缺失则降级。
4. PSM/IPW：
   - 必填 balance diagnostics；未通过不能写 adjusted causal claim。
5. Quantile/Threshold：
   - 写 heterogeneity/model-based，不写主平均因果。
6. Mediation：
   - 默认 mechanism suggestive；强因果中介需 manual signoff。

**测试/命令**

```powershell
python -m pytest tests/test_iv_rdd_claim_gate.py tests/test_scm_psm_quantile_narrative.py -q
```

**验收标准**  
- 缺 first-stage 的 IV 不产生强 causal claim。
- RDD 缺 manipulation/balance 被标为 major risk。
- PSM 不被写成 staggered DID 主结果。
- Quantile/threshold 进入 heterogeneity/appendix 叙事。

**风险**  
- 诊断文件命名不统一；adapter 需要 method-specific normalizer。
- 过度阻断旧论文；允许 manual override，但 release gate 要显示 override。

**commit 名**  
`methods: bridge iv rdd scm psm quantile threshold artifacts`

**可并发/依赖**  
依赖 P2/P5。可与 P10/P12 并行。

---

### P12 — Spatial/DML/DEA Risk Route

**目标**  
接入高风险/高级方法时强制正确表述：空间 reduced-form、DML backend truth、DEA 效率非因果。

**Owner / Agent role**  
Agent C + Agent F。

**文件/模块**  
- `src/generation/econ_capability_registry.py`
- `src/generation/econ_claim_gate.py`
- `src/generation/econ_content_brief.py`
- `tests/test_spatial_dml_dea_claim_boundaries.py`
- skill4econ fixtures:
  - spatial exposure DID success
  - spatial panel parser_only
  - DML sklearn fallback
  - DoubleML missing_dependency
  - DEA success

**具体改动**  
1. Spatial：
   - `spatial_exposure_did` → reduced-form local/spillover wording。
   - `W*D` 不能写成 structural indirect effect。
   - `SAR/SEM/SDM impact` 只有 direct/indirect/total effects backend output 才允许。
   - Moran/LISA preflight 只是 diagnostic，不是 causal result。
2. DML：
   - `sklearn_fallback` 明确写 fallback/cross-fitting，不写 DoubleML/EconML。
   - `missing_dependency` 不产生 result。
   - 需要 nuisance diagnostics / folds / seed / sample split 字段。
3. DEA：
   - 只写 efficiency/productivity。
   - 政策因果和 welfare claim 默认 forbidden。
4. finance ML split audit：
   - 若 split audit fail，prediction result 不进入主结果。
   - look-ahead/leakage 风险写入 reviewer attack。

**测试/命令**

```powershell
python -m pytest tests/test_spatial_dml_dea_claim_boundaries.py tests/test_no_autonomous_empirical_claims.py -q
```

**验收标准**  
- parser-only spatial impact 不产生 impact claim。
- DML fallback 不被误标为 DoubleML/EconML。
- DEA 不写 causal/policy effect。
- finance ML leakage fail 阻断 prediction claim。

**风险**  
- 高级方法名称容易被 LLM“升格”；forbidden phrases 需要 method-specific。
- 用户可能希望强叙事；manual signoff 但不自动通过 release gate。

**commit 名**  
`guard: enforce spatial dml dea claim boundaries`

**可并发/依赖**  
依赖 P2/P5。可与 P10/P11 并行。

---

### P13 — Finance Tier-1 Gap Adapter Specs

**目标**  
补顶级金融论文常见能力缺口，但严格分层：今晚优先 contract/spec/checklist；只有可快速复用后端时才做 dependency-gated adapter。

**Owner / Agent role**  
Agent G + live-web 老哥。

**文件/模块**  
skill4econ:
- `docs/roadmaps/finance_tier1_adapter_gaps.md`
- `docs/contracts/finance_artifact_contract_v2.md`
- 可选：`src/skill4econ/adapters/finance/` skeleton
- `tests/test_finance_gap_contracts.py`

EasyPaper:
- `src/generation/econ_capability_registry.py`
- `src/generation/finance_claim_gate.py` 或并入 claim gate
- `tests/test_finance_gap_claim_defaults.py`

**具体改动**  
1. 定义但不硬实现的 adapter contracts：
   - Fama-MacBeth：
     - input: panel returns/factors/characteristics IDs, time index。
     - output: coefficient time series, average premia, t-stats, NW lag, N_time, N_assets。
   - Factor alpha / GRS：
     - output: alpha table, factor set, time-series regression status, GRS status。
   - Portfolio sorts：
     - output: sort variable, rebalance frequency, value/equal weighted, long-short, t-stats, sample filters。
   - Event-study CAR/BHAR：
     - output: estimation window, event window, benchmark, abnormal return metric。
2. Claim defaults：
   - 所有 finance gap 在没有 success artifact 前 `no_result`。
   - 有 external manual_file bundle 时 `manual_signoff_required`。
3. Checklist：
   - look-ahead
   - survivorship bias
   - delisting returns
   - factor construction
   - multiple testing
   - transaction costs 如涉及交易策略
4. live-web 老哥输出：
   - 哪些 finance gaps 明早必须 backlog。
   - 哪些必须 manual signoff。
   - 哪些可以直接表述为 “future adapter”。

**测试/命令**

```powershell
# EasyPaper
python -m pytest tests/test_finance_gap_claim_defaults.py -q

# skill4econ
conda run -n base python -m pytest tests/test_finance_gap_contracts.py -q
```

**验收标准**  
- 缺口不会被 registry 标成可运行。
- finance examples 若没有 success bundle，不会生成资产定价/组合排序实证结果。
- docs 清晰列出 adapter backlog，不误导 PR reviewer。

**风险**  
- “不要寒酸 MVP” 可能诱导今晚写半吊子 Fama-MacBeth；不要。宁可 contract + gate + checklist 完整，也不写未验证算法。
- 若已有外部结果文件，作为 `manual_file` bundle 读取，但必须 manual signoff。

**commit 名**  
`finance: specify tier1 adapter gaps and claim defaults`

**可并发/依赖**  
依赖 P4。可与 P10-P12 并行。

---

### P14 — Runner/CLI/Config Bridge

**目标**  
让本地 runner 能接收 skill4econ artifact bundle 路径，生成可复现输出：events、normalized request、manifest、config.redacted、claim_gate_report、paper tex。

**Owner / Agent role**  
Agent B + Agent H。

**文件/模块**  
- `scripts/run_econ_paper.py`
- `examples/econ/*.yaml`
- `examples/finance/*.yaml`
- `src/config/*`
- `tests/test_run_econ_paper_script.py`
- `tests/test_easypaper_app_config_builder.py`
- `tests/test_minimal_poc_runner_outputs.py`

**具体改动**  
1. CLI 参数：
   - `--artifact-bundle <path>` 可重复。
   - `--strict-artifacts`：required bundle invalid 则 fail。
   - `--claim-gate-strict`：任何 blocker claim violation fail。
   - `--emit-quality-report`。
2. 输出目录必须包含：
   - `events.jsonl`
   - `request.normalized.json`
   - `manifest.normalized.json`
   - `artifact_usage_report.json`
   - `claim_gate_report.json`
   - `reviewer_attack_pack.json/md`
   - `top_journal_risk_report.json/md`
   - `config.redacted.yaml`
   - `runner.summary.json`
   - `main.tex`
3. config redaction：
   - API key/base url secrets 不落盘。
4. mock LLM mode：
   - 能用 fixture bundle 完整生成 mock paper，不调用 live LLM。
5. server mode 如要接入，只加 schema，不作为明早硬门槛。

**测试/命令**

```powershell
python -m pytest tests/test_run_econ_paper_script.py tests/test_easypaper_app_config_builder.py tests/test_minimal_poc_runner_outputs.py -q

python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml `
  --out outputs/aer_minimal_v2 `
  --mock-llm `
  --no-pdf `
  --strict-artifacts `
  --claim-gate-strict
```

**验收标准**  
- runner 输出所有 v2 报告。
- redacted config 不含 key。
- strict mode 能阻断 invalid bundle。
- mock runner 不发 live LLM 请求。

**风险**  
- CLI 兼容旧 examples；新增参数默认不破坏旧行为。
- 输出目录中可能有旧文件；测试使用临时目录。

**commit 名**  
`runner: add artifact bundle and claim gate reporting`

**可并发/依赖**  
依赖 P3/P5/P7。可与 P15 准备 fixtures 并行。

---

### P15 — End-to-End Fixtures + Regression Matrix

**目标**  
建立从 skill4econ fixture bundle 到 EasyPaper mock paper 的端到端测试矩阵，确保 release gate 不是只测零散单元。

**Owner / Agent role**  
Agent E + Merge captain。

**文件/模块**  
EasyPaper:
- `examples/econ/skill4econ_did_request.yaml`
- `examples/econ/skill4econ_iv_rdd_request.yaml`
- `examples/finance/finance_gap_no_result_request.yaml`
- `tests/test_e2e_skill4econ_bundle_to_paper.py`
- `tests/test_release_gate_econ_finance.py`

skill4econ:
- `examples/easypaper_bridge/*`
- `tests/test_easypaper_bridge_fixtures.py`

**具体改动**  
1. E2E cases：
   - success OLS/panel bundle → Results with table.
   - DID staggered success → main DID result.
   - DID TWFE-only staggered → not paper ready / no main claim.
   - missing_dependency DML → no result claim.
   - spatial parser_only → no impact claim.
   - finance gap no artifact → proposal/checklist only.
2. 每个 E2E 输出检查：
   - `main.tex`
   - `claim_gate_report.json`
   - `artifact_usage_report.json`
   - `reviewer_attack_pack.md`
3. 负向测试：
   - 伪造 bundle status success 但缺 model table → fail。
   - result caption 试图新增显著性 → fail。
4. 记录 baseline runtime，标记 slow 测试但 release gate 至少跑 lightweight E2E。

**测试/命令**

```powershell
# EasyPaper focused E2E
python -m pytest tests/test_e2e_skill4econ_bundle_to_paper.py tests/test_release_gate_econ_finance.py -q

# Full non-live regression
python -m pytest -m "not live_llm and not latex and not slow" -q

# skill4econ
conda run -n base python -m pytest tests/test_easypaper_bridge_fixtures.py tests/test_easypaper_manifest_export.py -q
conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict
```

**验收标准**  
- 所有 v2 negative gates 通过。
- E2E mock paper 不含伪造 empirical findings。
- skill4econ fixture 与 EasyPaper ingest schema 对齐。
- release gate 文档更新为 pass/fail。

**风险**  
- Full regression 时间长；先跑 focused，最后跑 full。
- 两 repo fixture 同步失配；用 version field 和 fixture hash。

**commit 名**  
`tests: add end to end skill4econ artifact paper matrix`

**可并发/依赖**  
依赖 P6-P14。部分 fixture 准备可提前。

---

### P16 — PR Packaging + Integration Snapshot Sync

**目标**  
把 EasyPaper fork 的最终代码安全同步到 skill4econ integration 子目录，准备 PR，避免 `.git`、outputs、secrets、cache 进入 snapshot。

**Owner / Agent role**  
Merge captain。

**文件/模块**  
- `D:/myproject/EvoScientist/competitor_repos/easypaper-source`
- `D:/myproject/skill4econ/integrations/easypaper-econ-finance`
- `D:/myproject/skill4econ/README.md`
- `D:/myproject/skill4econ/docs/REPO_STRUCTURE.md`
- `D:/myproject/skill4econ/integrations/easypaper-econ-finance/README_SKILL4ECON_INTEGRATION.md`
- `D:/myproject/skill4econ/integrations/easypaper-econ-finance/CODEX_TASKS.md`

**具体改动**  
1. 在 EasyPaper fork 完成 merge 后打 tag/记录 commit。
2. 用 dry-run 比较 snapshot：
   ```powershell
   robocopy D:/myproject/EvoScientist/competitor_repos/easypaper-source `
     D:/myproject/skill4econ/integrations/easypaper-econ-finance `
     /MIR /L `
     /XD .git .venv venv env outputs .pytest_cache __pycache__ .mypy_cache .ruff_cache `
     /XF .env *.pyc *.pyo
   ```
3. 人工确认 dry-run 后再执行无 `/L`。
4. 同步后在 skill4econ 根目录跑：
   ```powershell
   cd D:/myproject/skill4econ
   git status --short
   conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict
   cd integrations/easypaper-econ-finance
   python -m pytest -m "not live_llm and not latex and not slow" -q
   ```
5. 更新 integration README：
   - v2 artifact contract
   - claim gate
   - no algorithm duplication
   - commands
   - known gaps/backlog
6. 准备 PR summary：
   - What changed
   - Why no duplicate econometrics
   - Test evidence
   - Risk and manual signoff
   - Backlog

**测试/命令**

```powershell
cd D:/myproject/skill4econ
git diff --stat
git diff --check
conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict

cd D:/myproject/skill4econ/integrations/easypaper-econ-finance
python -m pytest -m "not live_llm and not latex and not slow" -q
python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml --out outputs/aer_minimal_snapshot --mock-llm --no-pdf
```

**验收标准**  
- integration snapshot 无 secrets/cache/outputs 大文件。
- skill4econ root smoke pass。
- EasyPaper integration tests pass。
- PR notes 包含 release gate 和 backlog。

**风险**  
- `robocopy /MIR` 可能删除目标文件；必须先 `/L` dry-run 并检查。
- snapshot 中有路径引用回 EasyPaper fork；必须保持 portable relative paths。

**commit 名**  
`integrations: sync easypaper econ finance production v2 snapshot`

**可并发/依赖**  
依赖 P15。不可并发。

---

### P17 — Morning Release Signoff

**目标**  
明早做最终验收：机器 gate + 人工 signoff + live-web 计量/论文风险审查。

**Owner / Agent role**  
Merge captain + live-web 老哥 + all Agent 签字。

**文件/模块**  
- `_handoff/release_gate.md`
- `_handoff/live_web_review.md`
- `docs/reviews/top_journal_risk_report.md`
- PR body

**具体改动**  
1. 机器 gate 全部贴结果。
2. manual signoff：
   - DID/staggered 表述
   - spatial/DML/DEA 表述
   - finance gap/backlog 表述
   - generated mock paper 抽样审查
3. live-web 老哥：
   - 给 top-journal reviewer attack 10 条最强批评。
   - 标明哪些是 blocker、哪些是 backlog。
4. PR body 加：
   - “failed/missing_dependency/interface_only 不产生论文结果”
   - “EasyPaper 不重复实现计量算法”
   - “finance tier1 gaps are contract/checklist unless backend artifact exists”

**测试/命令**

```powershell
# EasyPaper final
cd D:/myproject/EvoScientist/competitor_repos/easypaper-source
python -m pytest -m "not live_llm and not latex and not slow" -q
python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml --out outputs/final_aer --mock-llm --no-pdf --strict-artifacts --claim-gate-strict

# skill4econ final
cd D:/myproject/skill4econ
conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict
git diff --check
```

**验收标准**  
- release gate 100% pass 项全部通过。
- manual signoff 项有人名/时间/结论。
- backlog 明确，不混入 release promise。
- PR 可打开。

**风险**  
- 明早发现生成论文质量差；如果 claim gates 可靠，可以先作为 production-safe v2，论文风格优化列 backlog。
- live-web 发现重大方法风险；相应 method route 降级，不硬撑。

**commit 名**  
`release: document econ finance v2 gates and signoff`

**可并发/依赖**  
依赖 P16。不可并发。

---

## 6. 今晚到明早高并发施工排程

### 0–2h：冻结、分工、contract skeleton、负向门禁先行

**目标**：先让所有人不踩线，确保后面并行不是乱改。

| 时间 | Agent | 工作 |
|---|---|---|
| 0:00–0:20 | Merge captain | 跑 P0 baseline，建 worktree，写 `_handoff/merge_log.md` |
| 0:20–0:40 | Agent A/F | 锁定 P1 enum/status/claim_level 字段 |
| 0:40–1:30 | Agent A | EasyPaper contract skeleton + schema tests |
| 0:40–1:30 | Agent F | skill4econ contract docs + export skeleton |
| 0:40–1:30 | Agent C | claim gate negative tests 先写：failed/missing_dependency 不得生成 result |
| 0:40–1:30 | Agent B | ingest loader path validation tests |
| 1:30–2:00 | Merge captain | 合并 P1 skeleton；跑 targeted tests；解决 enum 冲突 |

**0–2h 必须产出**  
- v2 enum/status/claim docs。
- 至少 3 个负向测试：missing_dependency、parser_only、no artifact。
- baseline 和 known failures 文档。

### 2–6h：主干能力接入、Claim Gate、Narrative Bridge、Quality Eval 并发

| 时间 | Agent | 工作 |
|---|---|---|
| 2–4h | Agent F | P2 export adapter + fixtures |
| 2–4h | Agent B | P3 ingest adapter + table/figure spec bridge |
| 2–5h | Agent C | P5 claim gate + P10/P11/P12 method-specific gates |
| 2–5h | Agent D | P7/P8 content brief + planner routing |
| 2–5h | Agent E | P9 reviewer attack + quality eval |
| 2–5h | Agent G | P13 finance gap contracts/checklists |
| 3–5h | live-web 老哥 | 审 DID/spatial/DML/finance gap matrix，输出 red flags |
| 5–6h | Merge captain | 第一轮 merge：P1→P3→P5→P7/P8→P9；跑 focused tests |

**2–6h 必须产出**  
- EasyPaper 能读至少一个 skill4econ-style bundle。
- failed/missing_dependency/interface_only/parser_only 不产生 result claim。
- Results/Data/Empirical Strategy 能从 ContentBrief 取 facts。
- reviewer_attack_pack 初版。

### 6–12h：E2E、方法路由、finance backlog、runner 和 snapshot 前准备

| 时间 | Agent | 工作 |
|---|---|---|
| 6–8h | Agent C/F | P10/P11/P12 method route fixtures 完成 |
| 6–8h | Agent B/H | P14 runner/config/output reports |
| 6–9h | Agent E | P15 E2E matrix + negative tests |
| 6–9h | Agent D | 修 prompt/narrative 失败，确保 abstract/conclusion 不越权 |
| 6–9h | Agent G/live-web | finance gaps + top-journal risk review 完成 |
| 9–10h | Merge captain | 第二轮 merge，跑 full non-live regression |
| 10–11h | 全体 | 修 release blockers |
| 11–12h | Merge captain | 准备 P16 snapshot dry-run，不执行危险 sync 直到 tests 绿 |

**6–12h 必须产出**  
- mock runner 生成 `main.tex + claim_gate_report + artifact_usage_report + reviewer_attack_pack`。
- E2E 至少覆盖 success、missing_dependency、parser_only、finance gap no result。
- full non-live regression 绿或 known failures 明确。

### 明早验收：机器 gate + 人工 signoff + PR

| 顺序 | Owner | 动作 |
|---|---|---|
| 1 | Merge captain | 跑 EasyPaper final non-live regression |
| 2 | Merge captain | 跑 skill4econ backend-contract smoke |
| 3 | live-web 老哥 | 审 PR summary、top-journal risk、method wording |
| 4 | Agent C/D/E | 抽查 2–3 篇 mock 输出：abstract/conclusion/results |
| 5 | Merge captain | `robocopy /L` dry-run，确认后 sync integration snapshot |
| 6 | Merge captain | PR body + release gate + backlog |
| 7 | 全体 | 签 release_gate.md |

---

## 7. Agent 切分表：写入边界与合并顺序

| Agent | 工作目录 | 允许写入 | 不能碰 | 交付物 | 合并顺序 |
|---|---|---|---|---|---|
| A Contracts | `D:/myproject/worktrees/easypaper-A` | `src/models/*artifact*`, `src/generation/econ_capability_registry.py`, contract tests, `_handoff/agent_A_contracts.md` | writer/planner core runtime、runner、skill4econ wrappers | P1/P4 EasyPaper schema/registry | 1 |
| B Ingest/Render | `D:/myproject/worktrees/easypaper-B` | ingest adapter, manifest-to-table/figure, artifact path validation, runner input parser | claim gate rules、planner prompts、skill4econ code | P3/P6/P14 ingest/render | 3 |
| C Claim Gate | `D:/myproject/worktrees/easypaper-C` | `econ_claim_gate.py`, claim tests, method-specific negative gates | table renderer internals、venue configs、skill4econ wrappers | P5/P10-P12 gate logic | 2 after A, before D |
| D Narrative/Planner | `D:/myproject/worktrees/easypaper-D` | planner econ fields, section prompts, content brief injection | artifact loader internals、export adapter、release scripts | P7/P8 narrative bridge | 4 after C skeleton |
| E Quality/Test | `D:/myproject/worktrees/easypaper-E` | quality eval, reviewer attack, E2E tests, release test matrix | core models unless adding test-only fixtures | P9/P15 quality/e2e | 5 |
| F skill4econ Export | `D:/myproject/worktrees/skill4econ-F` | skill4econ contracts, export adapter, bridge fixtures, tests | core estimator algorithms except metadata fields needed for export | P2 export + fixtures | parallel; merge into skill4econ before snapshot |
| G Finance Gaps | `D:/myproject/worktrees/skill4econ-G` and small EasyPaper registry patch via A | docs/contracts for finance gaps, checklist tests | implementing finance estimators from scratch、EasyPaper writer core | P13 finance gap docs/tests | parallel; merge before release docs |
| H Runner/Packaging | main EasyPaper after A/B/C merge | runner CLI, config redaction, outputs list, docs | estimator code、claim semantics | P14 runner | after B/C |
| Merge captain | main repos only | conflict resolution, version bump, integration snapshot, PR body | unreviewed method semantics | P16/P17 | final |
| live-web 老哥 | no local write | `_handoff/live_web_review.md`, `docs/reviews/*.md` via pasted memo | code edits, test edits | top-journal risk/reviewer attack | before P17 |

### 合并命令模板

```powershell
# EasyPaper main merge
cd D:/myproject/EvoScientist/competitor_repos/easypaper-source
git checkout evo/econ-finance-tier1
git pull --ff-only  # 如有 remote
git merge --no-ff agent/A-contracts
python -m pytest tests/test_artifact_manifest_v2_contract.py tests/test_econ_capability_registry.py -q

git merge --no-ff agent/C-claim
python -m pytest tests/test_claim_gate_blocks_failed_artifacts.py tests/test_no_autonomous_empirical_claims.py -q

git merge --no-ff agent/B-ingest
python -m pytest tests/test_easypaper_ingests_skill4econ_bundle.py tests/test_manifest_to_table_specs.py tests/test_manifest_to_figure_specs.py -q

git merge --no-ff agent/D-narrative
python -m pytest tests/test_econ_section_generation_content_brief.py tests/test_planner_required_sections.py -q

git merge --no-ff agent/E-quality
python -m pytest tests/test_e2e_skill4econ_bundle_to_paper.py tests/test_release_gate_econ_finance.py -q
```

---

## 8. live-web 老哥介入点

### 8.1 第一次介入：P4 后，方法分类审查

**输入**  
- `econ_capability_registry.py`
- `docs/roadmaps/easypaper_capability_gap_matrix.md`
- skill4econ 当前能力摘要

**问题清单**  
1. 哪些方法可作为主结果，哪些只能 robustness/appendix？
2. DID/staggered DID 的主通道是否正确？
3. spatial DID / SAR/SDM impact 表述是否过界？
4. sklearn DML fallback 是否可能被误读？
5. finance tier-1 缺口有哪些必须降为 backlog？

**输出**  
`_handoff/live_web_review.md` 第一节：method classification red flags。

### 8.2 第二次介入：P7/P8 后，论文叙事审查

**输入**  
- 生成的 content brief
- mock paper 的 Data/Empirical Strategy/Results/Conclusion
- claim gate report

**问题清单**  
1. Abstract/Conclusion 是否超出 Results？
2. Identification assumptions 是否明确？
3. 结果语言是否把 association 写成 causality？
4. finance/ML 是否写了收益承诺或交易策略暗示？
5. 哪些句子会被 AER/QJE/JFE reviewer 直接打？

**输出**  
`docs/reviews/narrative_risk_review.md`

### 8.3 第三次介入：P13 后，finance gap 审查

**输入**  
- `finance_tier1_adapter_gaps.md`
- finance example mock outputs

**问题清单**  
1. Fama-MacBeth / factor alpha / portfolio sorts / event study 哪些不可进入 v2 release？
2. 若读取 external manual results，哪些字段必须 manual signoff？
3. JFE 风格下哪些 claim 必须删？
4. 是否有 look-ahead/survivorship/multiple testing 未覆盖？

**输出**  
`docs/reviews/finance_top_journal_gap_review.md`

### 8.4 第四次介入：P17 release signoff

**输入**  
- PR body draft
- release gate
- E2E mock outputs
- top_journal_risk_report

**问题清单**  
1. PR 是否清楚说明“不重复造计量算法”？
2. release 是否诚实说明 gaps/backlog？
3. 有没有把 missing_dependency/parser_only 写成成果？
4. 还有哪些 blocker 必须先降级/删除？

**输出**  
`_handoff/live_web_release_signoff.md`

---

## 9. Release Gate

### 9.1 必须 100% pass

| Gate | 命令/检查 | Owner |
|---|---|---|
| EasyPaper non-live regression | `python -m pytest -m "not live_llm and not latex and not slow" -q` | Merge captain |
| Core econ invariant suite | `python -m pytest tests/test_document_input_econ_constraints.py tests/test_orchestrator_passes_econ_constraints.py tests/test_planner_required_sections.py tests/test_econ_section_generation_content_brief.py tests/test_assembly_order_econ.py tests/test_no_autonomous_result_figures.py -q` | Agent D/C |
| Artifact contract v2 | `tests/test_artifact_manifest_v2_contract.py`, schema roundtrip, invalid bundle fail | Agent A |
| Manifest ingest path safety | artifact path validation, required bundle invalid fail | Agent B |
| Claim gate negative tests | failed/missing_dependency/interface_only/parser_only/no artifact 不生成 result claim | Agent C |
| Caption/result guard | no autonomous empirical figures; caption locked; no LLM numbers | Agent B/C |
| Runner mock output | `scripts/run_econ_paper.py ... --mock-llm --no-pdf --strict-artifacts --claim-gate-strict` | Agent H |
| skill4econ backend contract | `conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict` | Agent F |
| Export/ingest fixture compatibility | skill4econ fixture bundle can be read by EasyPaper | Agent F/B |
| Secret scan / diff check | `git diff --check`; no `.env`, keys, outputs/cache | Merge captain |
| Integration snapshot dry-run | `robocopy /L` reviewed before actual sync | Merge captain |

### 9.2 必须 manual signoff

| Item | 谁签 | 标准 |
|---|---|---|
| DID/staggered DID route | live-web + Agent C | TWFE-only staggered 没有被写成 full success |
| Spatial route | live-web + Agent C | reduced-form 与 SAR/SDM impact 边界清楚 |
| DML route | live-web + Agent C | sklearn fallback 未被误写成 DoubleML/EconML |
| Finance gaps | live-web + Agent G | Fama-MacBeth/factor/portfolio/event-study 缺口不伪装为 v2 功能 |
| Mock paper sample | Agent D/E + live-web | Abstract/Results/Conclusion 不越权 |
| PR body | Merge captain + live-web | 清楚写出 capabilities/gaps/tests/risks |
| Any manual_file artifact | 人工 reviewer | source、status、claim level、files 全部可追溯 |

### 9.3 可进入 backlog

| Backlog | 原因 |
|---|---|
| Live LLM quality eval | 不是安全 release gate；需要 API key 和成本 |
| Full LaTeX/PDF visual review | latex/poppler 依赖可能不稳定；明早可 manual run |
| Fama-MacBeth 实估计 adapter | 需要后端验证和金融数据 fixture，不要今晚手写半成品 |
| Factor alpha/GRS adapter | 同上 |
| Portfolio sorts/CAR/BHAR adapter | 同上 |
| Multiple testing/ROMANO-Wolf/Oster/MDE | 可先 checklist，后续 adapter |
| Server mode full integration | SDK/runner 先 production-safe |
| VLM review | optional，不作为 non-live gate |
| Structural/welfare/DSGE/IO claims | 需要人工模型审查，不做自动化 |

---

## 10. 不要做清单

1. **不要在 EasyPaper 中实现 OLS、FE、DID、IV、RDD、DML、空间、DEA、Fama-MacBeth 等估计算法。** EasyPaper 只读 skill4econ 或 external file-backed artifact。
2. **不要把 PSM-DID 作为 staggered DID 主估计。** 简单 2x2 走 `dr_did_2x2`；staggered 走 `cs_did_attgt` / `did_imputation_event`。
3. **不要把 TWFE-only staggered DID 写成 full success。**
4. **不要把 `missing_dependency`、`failed`、`interface_only`、`parser_only` 写成论文结果。**
5. **不要把 spatial reduced-form spillover 写成 structural SAR/SDM indirect effect。**
6. **不要把 sklearn DML fallback 写成 DoubleML/EconML 包结果。**
7. **不要让 LLM 编造表格数字、标准误、显著性、p 值、N、样本期、图。**
8. **不要自动生成 empirical result figures。** 结果图必须 file-backed。
9. **不要自动安装 Stata/R/Python 包。** 缺依赖就 dependency-gated。
10. **不要提交 API keys、`.env`、config 未脱敏版本、outputs/cache。**
11. **不要在 `skill4econ` core 中为了 EasyPaper 改估计算法语义。** 只补导出 metadata 或 docs/tests。
12. **不要大规模重构 planner/writer。** 只在 econ/finance discipline 下加约束路径。
13. **不要让 live-web review 替代 artifact truth。** 它只能作为人工风险判断。
14. **不要为了“顶刊感”自动夸大 causality、robustness、mechanism、policy implication。**
15. **不要在 PR 中暗示 v2 已覆盖所有金融顶刊实证方法。** 要明确哪些是 adapter gap/backlog。
16. **不要直接运行 `robocopy /MIR`。** 必须先 `/L` dry-run 并人工确认。
17. **不要把 docs checklist 当成已实现能力。** registry 必须区分 `direct|needs_validation|adapter_gap|checklist_only`。
18. **不要吞掉错误继续生成“看似完整”的论文。** required artifact invalid 必须 fail loud。
19. **不要把 reviewer_risk 当装饰。** major/blocker risk 必须影响 claim gate 或 release gate。
20. **不要在明早 release 前引入 live-only hard dependency。**

---

## 11. 推荐 PR Body 模板

```markdown
## Summary

This PR adds a production-safe v2 plan and implementation path for EasyPaper econ/finance manuscript generation backed by skill4econ artifacts.

Key design:
- skill4econ remains the econometrics execution layer.
- EasyPaper consumes file-backed artifact bundles and does not reimplement estimators.
- Manifest/audit/model_table/reviewer_risk/run_status drive claim gates.
- failed/missing_dependency/interface_only/parser_only artifacts cannot become paper results.
- Empirical tables/figures/captions are file-backed and locked.

## What changed

- Artifact contract v2 for skill4econ → EasyPaper bundles.
- EasyPaper ingest adapter for skill4econ manifests.
- Capability registry and finance gap matrix.
- Claim gate v2 and reviewer attack reports.
- Paper narrative bridge for Data / Empirical Strategy / Results / Robustness.
- Runner outputs for claim reports and artifact usage.
- E2E mock fixture matrix.

## Tests

Paste commands and pass/fail results:

```powershell
python -m pytest -m "not live_llm and not latex and not slow" -q
python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml --out outputs/final_aer --mock-llm --no-pdf --strict-artifacts --claim-gate-strict
conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict
```

## Safety / scientific integrity

- No autonomous empirical result figures.
- No fabricated significance, p-values, N, sample period, or conclusions.
- DID, spatial, DML, DEA, and finance methods have claim-specific gates.
- Known adapter gaps are documented and not advertised as implemented.

## Backlog

- Finance Fama-MacBeth / factor alpha / portfolio sorts / CAR-BHAR adapters.
- Multiple testing, sensitivity, MDE.
- Live LLM and PDF visual review.
```

---

## 12. 最小成功定义与理想成功定义

### 最小成功，但不是寒酸 MVP

明早前至少必须做到：

1. v2 artifact contract 双边一致。
2. EasyPaper 能读取 skill4econ-style bundle。
3. claim gate 能阻断所有失败/缺依赖/parser-only/interface-only 输出。
4. runner 能输出 `main.tex + claim_gate_report + artifact_usage_report + reviewer_attack_pack`。
5. DID/spatial/DML/DEA/finance gap 有明确降级规则。
6. non-live tests 和 backend-contract smoke 通过。
7. PR 文档诚实列出 gaps/backlog。

### 理想成功

在最小成功基础上：

1. P10/P11/P12 方法路由 fixture 全覆盖。
2. AER/QJE/JFE mock examples 都能生成非伪造草稿。
3. reviewer_attack_pack 可直接给作者当 checklist。
4. integration snapshot 与 EasyPaper fork 完全同步且可复现。
5. live-web 老哥签过 top-journal risk，无 blocker。

---

## 13. 最后提醒

这版 v2 的竞争力不在于“又写了多少计量函数”，而在于：

- 已有 skill4econ 计量能力被系统性接入；
- 每个论文 claim 都能追溯到 artifact；
- 缺依赖/半成品/接口-only 不会变成论文结论；
- 顶刊 reviewer 会攻击的地方提前暴露；
- 多 Agent 并行时不会互相踩核心文件；
- 明早能给 PR 一个诚实、可验证、可继续扩展的 production-safe 基线。
