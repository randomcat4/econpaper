# skill4econ TODO.md — 给 Codex 分次执行版

> 目标：让 Codex / 小模型 agent 能按批次把 `skill4econ` 的环境经济、ESG、绿色金融、能源/碳排放 workflow 做深、做稳、做完。
> 原则：不要横向堆模型；优先补硬诊断、估计器选择、adapter、artifact contract、smoke test、reviewer risk。
> 兼容要求：不要破坏已有通过本地 smoke 的 workflow：`did_paper_run`、`psm_did_policy_run`、`spatial_spillover_run`、`mechanism_threshold_run`、`efficiency_frontier_run`。

---

## 0. Codex 执行规则

### 0.1 每次改动必须满足

- [ ] 保持现有 workflow 入口兼容，不删除原有函数名、CLI 名、配置字段。
- [ ] 新增功能默认 **可关闭**，不得让原有 smoke 因缺 Stata/R 包直接失败。
- [ ] 外部后端缺失时，输出 `backend_unavailable` warning，而不是硬崩。
- [ ] 每个 workflow 运行后必须生成：
  - [ ] `artifact_manifest.json`
  - [ ] `reviewer_risk.json`
  - [ ] `run_config_resolved.yaml`
  - [ ] `run_log.md`
- [ ] 每个新 adapter 至少有：
  - [ ] backend availability check
  - [ ] command/script renderer
  - [ ] result parser
  - [ ] graceful failure message
  - [ ] smoke test
- [ ] 所有图表、表格、诊断结果都要落盘，不能只打印到 stdout。
- [ ] 所有 reviewer risk 只能保守，不能替用户吹结果。

### 0.2 每个 PR 的 Definition of Done

每个 PR 必须附：

- [ ] 改了什么。
- [ ] 新增/更新哪些文件。
- [ ] 如何运行 smoke。
- [ ] 预期生成哪些 artifact。
- [ ] 缺失后端时如何降级。
- [ ] 已知限制。
- [ ] 是否修改 public API。
- [ ] 是否需要更新 docs。

### 0.3 建议目录结构

Codex 不必一次性全改；缺目录就逐步建。

```text
skill4econ/
  contracts/
    data_contract.py
    reviewer_risk.py
    artifact_manifest.py
    estimator_registry.py
  workflows/
    did_paper_run/
    psm_did_policy_run/
    adjusted_did_policy_run/        # 可作为兼容 alias/新入口，不强制删旧名
    spatial_spillover_run/
    mechanism_evidence_run/
    heterogeneity_nonlinearity_run/
    mechanism_threshold_run/         # 保留旧入口，内部调新模块
    efficiency_frontier_run/
    firm_green_finance_policy_run/
  adapters/
    stata/
      reghdfe.py
      csdid.py
      drdid.py
      eventstudyinteract.py
      did_imputation.py
      bacondecomp.py
      honestdid.py
      xsmle.py
      spxtregress.py
      xthreg.py
      xthenreg.py
      rifhdreg.py
      ppmlhdfe.py
      gtfpch.py
    r/
      did_att_gt.py
      drdid.py
      honestdid.py
      didimputation.py
      fixest.py
      spdep.py
      splm.py
      mediation.py
      dear.py
      benchmarking.py
      rdea.py
    python/
      balance.py
      spatial_weights.py
      moran.py
      conley.py
      green_patent.py
      policy_catalog.py
  diagnostics/
    did_design.py
    overlap_balance.py
    spatial_preflight.py
    mechanism_timing.py
    dea_checks.py
  reporting/
    tables.py
    plots.py
    paper_methods.py
    reviewer_risk_report.py
  data_catalogs/
    china_env_policy_catalog.json
    green_patent_classifiers.yaml
    spatial_weights_recipes.yaml
    china_env_data_sources.md
  examples/
    replication_zoo/
  docs/
  tests/
    smoke/
    unit/
    fixtures/
```

---

## 1. 全局基础设施：先做，所有 workflow 共用

### M0.1 `reviewer_risk.json` 全局 schema

**优先级：P0**
**依赖：无**
**目标：所有 workflow 都能输出审稿风险。**

#### TODO

- [x] 新建 `skill4econ/contracts/reviewer_risk.py`
- [x] 定义风险级别：
  - [x] `low`
  - [x] `medium`
  - [x] `high`
  - [x] `fatal`
- [x] 定义统一结构：

```json
{
  "workflow": "did_paper_run",
  "risk_level": "high",
  "risks": [
    {
      "code": "TWFE_STAGGERED_HETEROGENEITY",
      "severity": "high",
      "message": "Treatment timing is staggered; TWFE may use contaminated comparisons.",
      "required_fix": "Report CS/Sun-Abraham/BJS estimates.",
      "affected_artifacts": ["main_twfe_table.csv", "event_study_twfe.png"]
    }
  ],
  "safe_claims": [],
  "unsafe_claims": []
}
```

- [x] 新建 `ReviewerRiskCollector`
- [x] 支持：
  - [x] `add_warning(code, severity, message, required_fix, affected_artifacts=None)`
  - [x] `merge(other_collector)`
  - [x] `to_json(path)`
  - [x] `to_markdown(path)`
- [x] workflow 结束时统一写入 `reviewer_risk.json`
- [x] `fatal` 风险出现时允许 workflow 继续产出 artifact，但在 `run_log.md` 顶部标红。

#### 首批风险码

DID：

- [x] `TWFE_STAGGERED_HETEROGENEITY`
- [x] `NO_NEVER_TREATED`
- [x] `ONLY_NOT_YET_TREATED_CONTROLS`
- [x] `WEAK_PRETREND_PERIODS`
- [x] `FEW_TREATED_COHORTS`
- [x] `ANTICIPATION_RISK`
- [x] `POST_PERIOD_TOO_SHORT`
- [x] `UNBALANCED_PANEL_HIGH_LOSS`
- [x] `TWFE_MODERN_DID_DISAGREE`
- [x] `NEGATIVE_OR_BAD_TWFE_WEIGHTS`

PSM/IPW/DRDID：

- [x] `POOR_OVERLAP`
- [x] `OFF_SUPPORT_HIGH_SHARE`
- [x] `EXTREME_IPW_WEIGHTS`
- [x] `LOW_EFFECTIVE_SAMPLE_SIZE`
- [x] `BALANCE_STILL_POOR`
- [x] `PSM_SAMPLE_LOSS_HIGH`
- [x] `TRIM_SENSITIVITY_UNSTABLE`

Spatial：

- [x] `SPATIAL_W_HAS_ISLANDS`
- [x] `SPATIAL_W_NOT_ROW_STANDARDIZED`
- [x] `SPATIAL_TREATMENT_CLUSTERED`
- [x] `CONTROL_GROUP_CONTAMINATED`
- [x] `W_SENSITIVITY_SIGN_FLIP`
- [x] `INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION`
- [x] `SPATIAL_SE_NOT_USED`

Mechanism/threshold/quantile：

- [x] `MEDIATOR_TIMING_INVALID`
- [x] `MEDIATOR_SAME_PERIOD_AS_OUTCOME`
- [x] `MECHANISM_CLAIM_TOO_STRONG`
- [x] `MULTIPLE_MECHANISMS_NO_ADJUSTMENT`
- [x] `THRESHOLD_BOOTSTRAP_NOT_SIGNIFICANT`
- [x] `THRESHOLD_UNBALANCED_PANEL`
- [x] `QUANTILE_TYPE_AMBIGUOUS`

DEA/GTFP：

- [x] `DEA_DMU_TOO_FEW`
- [x] `DEA_BAD_OUTPUT_NEGATIVE`
- [x] `DEA_ZERO_OR_MISSING_BAD_OUTPUT`
- [x] `DEA_FRONTIER_CHOICE_UNREPORTED`
- [x] `DEA_VARIABLE_SENSITIVITY_UNCHECKED`
- [x] `DEA_SECOND_STAGE_NAIVE_TOBIT`
- [x] `MALMQUIST_INFEASIBLE`

#### 验收标准

- [x] 任意 workflow 可调用 collector。
- [x] `reviewer_risk.json` 和 `reviewer_risk.md` 都能生成。
- [x] smoke fixture 能触发至少 5 个风险码。
- [x] 没有风险时也生成空风险文件。

---

### M0.2 `artifact_manifest.json`

**优先级：P0**
**依赖：M0.1**

#### TODO

- [x] 新建 `skill4econ/contracts/artifact_manifest.py`
- [x] 每个 workflow 输出统一 manifest：

```json
{
  "workflow": "spatial_spillover_run",
  "run_id": "2026-06-05T120000",
  "input_contract": "data_contract.yaml",
  "artifacts": [
    {
      "path": "tables/main_effects.csv",
      "type": "table",
      "role": "main_result",
      "required_for_paper": true
    },
    {
      "path": "figures/event_study.png",
      "type": "figure",
      "role": "dynamic_effect",
      "required_for_paper": true
    }
  ],
  "backend_status": {
    "stata": "available",
    "r": "available"
  }
}
```

- [x] 所有表/图/日志/脚本/模型结果都登记。
- [x] 缺失必需 artifact 时，manifest 标记 `missing_required_artifacts`。

#### 验收标准

- [x] 现有 5 个 workflow 都能写 manifest。
- [x] smoke 后可自动检查 manifest 中的路径都存在。
- [x] artifact 缺失时测试失败。

---

### M0.3 `data_contract.yaml` 标准化

**优先级：P0**
**依赖：无**

#### TODO

- [x] 新建 `skill4econ/contracts/data_contract.py`
- [x] 支持读取/校验 YAML。
- [x] 最小字段：

```yaml
panel:
  unit_id: city_id
  time_id: year
  outcome: co2_intensity
  treatment: lowcarbon_pilot
  first_treat_year: first_treat_year
  covariates:
    - ln_gdp_pc
    - industrial_share
    - population_density
  fixed_effects:
    - unit
    - time
  cluster:
    - unit_id

spatial:
  longitude: lon
  latitude: lat
  weights:
    - name: inverse_distance_200km
      path: weights/inverse_distance_200km.csv
      row_standardized: true

policy:
  name: low_carbon_city_pilot
  level: city
  treatment_coding: staggered
  anticipation_periods: 0
```

- [x] 校验：
  - [x] 必需列是否存在。
  - [x] panel id/time 是否唯一。
  - [x] outcome/treatment 是否缺失。
  - [x] first_treat_year 是否与 treatment 序列一致。
  - [x] 坐标列是否在合法范围。
  - [x] spatial weights 路径是否存在。
- [x] 输出 `data_contract_validated.yaml`
- [x] 输出 `data_contract_errors.json`

#### 验收标准

- [x] DID、PSM、spatial、mechanism、DEA 都能复用。
- [x] 缺列时明确报错。
- [x] 非致命问题写 reviewer risk。

---

### M0.4 backend availability checker

**优先级：P0**
**依赖：无**

#### TODO

- [x] 新建 `skill4econ/adapters/backend_check.py`
- [x] 支持检查：
  - [x] Stata binary
  - [x] Rscript binary
  - [x] Python package
  - [x] Stata package command 是否可用
  - [x] R package 是否可用
- [x] 统一返回：

```json
{
  "backend": "stata",
  "available": true,
  "version": "18",
  "packages": {
    "reghdfe": "available",
    "csdid": "missing"
  }
}
```

- [x] adapter 缺后端时不崩，写：
  - [x] `backend_status.json`
  - [x] reviewer risk: `BACKEND_UNAVAILABLE`
  - [x] placeholder artifact explaining skipped estimator

#### 验收标准

- [x] 无 Stata 环境下 Python smoke 不失败。
- [x] 无 R 环境下 Python smoke 不失败。
- [x] 后端可用时能执行真实 adapter smoke。

---

## 2. `did_paper_run`：现代 DID 估计器矩阵

### M1.1 DID design detector

**优先级：P0**
**依赖：M0.3**

#### TODO

- [x] 新建 `skill4econ/diagnostics/did_design.py`
- [x] 输入 panel data + contract。
- [x] 输出 `did_design.json`：

```json
{
  "design_type": "staggered_adoption",
  "n_units": 287,
  "n_periods": 19,
  "n_treated_units": 81,
  "n_never_treated_units": 206,
  "n_treated_cohorts": 3,
  "first_treat_years": [2010, 2012, 2017],
  "has_never_treated": true,
  "has_not_yet_treated": true,
  "min_pre_periods_by_cohort": {
    "2010": 2,
    "2012": 4,
    "2017": 9
  },
  "min_post_periods_by_cohort": {
    "2010": 9,
    "2012": 7,
    "2017": 2
  },
  "recommended_estimators": ["csdid", "did_att_gt", "eventstudyinteract", "did_imputation"],
  "not_recommended_as_main": ["twfe"]
}
```

- [x] 自动判断：
  - [x] 2×2 DID
  - [x] 单一处理时点
  - [x] staggered adoption
  - [x] repeated cross-section
  - [x] no never-treated
  - [x] all treated
  - [x] continuous treatment，先只标记，不做主估计
- [x] 触发 reviewer risk：
  - [x] pre-period 少于 3 年
  - [x] no never-treated
  - [x] cohort 太少
  - [x] post-period 太短
  - [x] treatment reversal
  - [x] panel 严重不平衡

#### 验收标准

- [x] 7 个 synthetic fixtures 全部识别正确。
- [x] `did_design.json` 被 `did_paper_run` 写入 artifact manifest。
- [x] router 能读取 `recommended_estimators`。

---

### M1.2 estimator registry + router

**优先级：P0**
**依赖：M1.1、M0.4**

#### TODO

- [x] 新建 `skill4econ/contracts/estimator_registry.py`
- [x] 新建 `configs/estimator_registry.yaml`
- [ ] 内容示例：

```yaml
did:
  twfe:
    backend: stata_reghdfe
    role: benchmark
    allowed_designs: ["two_by_two", "single_timing", "staggered_adoption"]
    main_allowed: false

  csdid:
    backend: stata_csdid
    role: main_if_staggered
    allowed_designs: ["staggered_adoption"]
    main_allowed: true

  did_r_att_gt:
    backend: r_did
    role: main_if_staggered
    allowed_designs: ["staggered_adoption"]
    main_allowed: true

  eventstudyinteract:
    backend: stata_eventstudyinteract
    role: dynamic_effect
    allowed_designs: ["staggered_adoption"]
    main_allowed: true

  did_imputation:
    backend: stata_or_r_bjs
    role: robustness
    allowed_designs: ["staggered_adoption", "single_timing"]
    main_allowed: true

  drdid:
    backend: stata_or_r_drdid
    role: covariate_adjusted
    allowed_designs: ["two_by_two", "single_timing"]
    main_allowed: true

  honestdid:
    backend: r_or_stata_honestdid
    role: sensitivity
    allowed_designs: ["single_timing", "staggered_adoption"]
    main_allowed: false
```

- [x] Router 输入：
  - [x] `did_design.json`
  - [x] user config
  - [x] backend availability
- [x] Router 输出：
  - [x] `selected_estimators.json`
  - [x] `skipped_estimators.json`
- [x] 规则：
  - [x] staggered adoption 不允许 TWFE 作为唯一主结果。
  - [x] no never-treated 时优先 not-yet-treated 支持的估计器。
  - [x] 2×2 可用 DRDID / TWFE / standard DID。
  - [x] R/Stata 后端都缺时，输出指导脚本，不直接失败。
- [x] `did_paper_run` 调用 router，而不是硬编码估计器顺序。

#### 验收标准

- [x] staggered fixture 选择 CS/SA/BJS，TWFE 标记 benchmark。
- [x] 2×2 fixture 选择 DRDID/TWFE。
- [x] 无 Stata 时跳过 Stata adapter，不影响其他结果。

---

### M1.3 Stata/R modern DID adapters

**优先级：P0**
**依赖：M1.2、M0.4**

#### TODO：Stata adapters

- [x] `adapters/stata/reghdfe.py`
  - [x] TWFE main table
  - [x] event-study TWFE
  - [x] multi-way cluster
  - [x] fixed-effect absorption
- [x] `adapters/stata/csdid.py`
  - [x] render `.do`
  - [x] support never-treated / not-yet-treated options
  - [x] parse overall ATT
  - [x] parse dynamic effects
  - [x] parse group-time ATT if available
- [x] `adapters/stata/drdid.py`
  - [x] panel 2×2
  - [x] repeated cross-section if contract says so
  - [x] covariates
- [x] `adapters/stata/eventstudyinteract.py`
  - [ ] cohort variable
  - [ ] relative-time indicators
  - [ ] omitted baseline
  - [ ] dynamic effect CSV
- [x] `adapters/stata/did_imputation.py`
  - [x] treatment date variable
  - [x] pretrend test
  - [x] event-study output
- [x] `adapters/stata/bacondecomp.py`
  - [ ] parse weights
  - [ ] output `bacon_decomposition.csv`
  - [ ] output weight scatter if possible
- [x] `adapters/stata/honestdid.py`
  - [ ] sensitivity grid
  - [ ] robust CI table
  - [ ] skip gracefully if input event-study not compatible

#### TODO：R adapters

- [x] `adapters/r/did_att_gt.py`
  - [ ] call `did::att_gt()`
  - [ ] call `did::aggte()`
  - [ ] dynamic/calendar/group/simple aggregation
  - [ ] parse output to common schema
- [x] `adapters/r/drdid.py`
  - [ ] call `DRDID`
  - [ ] ATT + SE + CI
- [x] `adapters/r/didimputation.py`
  - [ ] imputation estimator
  - [ ] dynamic effects
- [x] `adapters/r/honestdid.py`
  - [ ] sensitivity intervals
- [x] `adapters/r/fixest.py`
  - [ ] TWFE fallback via `feols`
  - [ ] `fepois` for count outcomes later
  - [ ] Conley vcov support later

#### Common output schema

每个 adapter 都输出：

```json
{
  "estimator": "csdid",
  "estimand": "ATT",
  "design_type": "staggered_adoption",
  "n_obs": 5453,
  "n_units": 287,
  "n_periods": 19,
  "control_group": "never_treated",
  "main_effect": {
    "estimate": -0.043,
    "std_error": 0.012,
    "p_value": 0.001,
    "ci_low": -0.066,
    "ci_high": -0.020
  },
  "dynamic_effects_path": "tables/csdid_dynamic.csv",
  "raw_output_path": "raw/csdid.log",
  "status": "success"
}
```

#### 验收标准

- [x] 每个 adapter 有单独 smoke。
- [x] 缺后端时 status = `skipped_backend_unavailable`。
- [x] 结果能被 `estimator_comparison_table` 读取。

#### 材料入口

- R `did` package / `att_gt`: https://bcallaway11.github.io/did/reference/att_gt.html
- Stata `csdid` / `drdid`: https://friosavila.github.io/playingwithstata/main_drdid.html
- Stata `eventstudyinteract`: https://github.com/lsun20/EventStudyInteract
- Stata `did_imputation`: https://github.com/borusyak/did_imputation
- R `didimputation`: https://cran.r-project.org/web/packages/didimputation/didimputation.pdf
- R/Stata `HonestDiD`: https://github.com/asheshrambachan/HonestDiD and https://github.com/mcaceresb/stata-honestdid
- Bacon decomposition: https://ideas.repec.org/c/boc/bocode/s458676.html and https://github.com/tgoldring/ddtiming
- Modern DiD resource index: https://jonathandroth.github.io/did-resources/

---

### M1.4 DID estimator comparison table

**优先级：P0**
**依赖：M1.3**

#### TODO

- [x] 新建 `reporting/did_comparison.py`
- [x] 读取所有 adapter common output。
- [x] 输出：
  - [x] `tables/did_estimator_comparison.csv`
  - [x] `tables/did_estimator_comparison.md`
  - [x] `figures/did_estimator_forest.png`
- [x] 表字段：
  - [x] estimator
  - [x] estimand
  - [x] control group
  - [x] estimate
  - [x] SE
  - [x] CI
  - [x] p-value
  - [x] N
  - [x] FE
  - [x] cluster
  - [x] backend
  - [x] status
  - [x] recommended role
- [x] 若 TWFE 与任一 modern DID 方向相反，触发 `TWFE_MODERN_DID_DISAGREE`。
- [x] 若 TWFE 是唯一成功估计器且 design 是 staggered，触发 `TWFE_STAGGERED_HETEROGENEITY` high risk。

#### 验收标准

- [x] staggered fixture 下生成 comparison table。
- [x] 缺部分 estimator 不影响表生成。
- [x] direction flip fixture 触发风险。

---

### M1.5 DID smoke fixtures

**优先级：P0**
**依赖：M1.1-M1.4**

#### TODO

在 `tests/fixtures/did/` 下建 synthetic data：

- [x] `two_by_two_clean.csv`
- [x] `single_timing_never_treated.csv`
- [x] `staggered_with_never_treated.csv`
- [x] `staggered_no_never_treated.csv`
- [x] `weak_pretrend_only_two_pre.csv`
- [x] `few_cohorts.csv`
- [x] `twfe_modern_did_flip.csv`
- [x] `unbalanced_panel_high_loss.csv`
- [x] `anticipation_effect.csv`

每个 fixture 配：

- [x] `data_contract.yaml`
- [x] `expected_design.json`
- [x] `expected_risks.json`

#### 验收标准

- [x] `pytest tests/smoke/test_did_paper_run.py` 通过。
- [ ] `make smoke-did` 通过。（Makefile target 已添加；本机未安装 make，已用 `conda run -n base python skill4econ/tests/smoke/smoke_did.py` 验证同等命令通过。）
- [x] smoke 不依赖 Stata/R 必装；有后端时多跑真实 adapter。

---

## 3. `psm_did_policy_run`：匹配/加权/DRDID 诊断补强

> 保留 `psm_did_policy_run` 入口。可以新增 `adjusted_did_policy_run` 作为 alias 或新入口，但不要强制用户迁移。重点不是多做 matching 算法，而是 overlap、balance、weights、trim、DRDID。

### M2.1 propensity score overlap diagnostics

**优先级：P0**
**依赖：M0.3、M0.1**

#### TODO

- [x] 新建 `diagnostics/overlap_balance.py`
- [x] 支持 PS 模型：
  - [x] logit
  - [x] probit optional
  - [x] user-supplied propensity score
- [x] 输出：
  - [x] `tables/propensity_summary.csv`
  - [x] `figures/propensity_overlap_density.png`
  - [x] `figures/propensity_overlap_hist.png`
  - [x] `tables/off_support_units.csv`
- [x] 诊断：
  - [x] treated/control PS min/max
  - [x] common support interval
  - [x] off-support share
  - [x] p1/p5/p50/p95/p99
- [x] 触发风险：
  - [x] off-support share > 10%: `OFF_SUPPORT_HIGH_SHARE`
  - [x] overlap visually/quantitatively poor: `POOR_OVERLAP`

#### 验收标准

- [x] overlap 好/差两个 fixtures 能正确触发/不触发风险。
- [x] 图片和表都进入 artifact manifest。

---

### M2.2 balance table + Love plot

**优先级：P0**
**依赖：M2.1**

#### TODO

- [x] 支持 matching 前后、IPW 前后、trim 前后 balance。
- [x] 指标：
  - [x] Standardized Mean Difference, SMD
  - [x] variance ratio
  - [x] treated mean
  - [x] control mean
  - [x] weighted treated/control mean
  - [x] missing rate
- [x] 输出：
  - [x] `tables/balance_table_before.csv`
  - [x] `tables/balance_table_after_matching.csv`
  - [x] `tables/balance_table_after_ipw.csv`
  - [x] `figures/love_plot.png`
- [x] 阈值：
  - [x] abs(SMD) > 0.1 标黄
  - [x] abs(SMD) > 0.25 标红
- [x] 触发 `BALANCE_STILL_POOR`

#### 验收标准

- [x] poor balance fixture 能触发风险。
- [x] Love plot 变量排序按 before SMD 从大到小。

---

### M2.3 weight diagnostics

**优先级：P0**
**依赖：M2.1**

#### TODO

- [x] 支持：
  - [x] IPW
  - [x] stabilized IPW
  - [x] trimmed IPW
- [x] 输出：
  - [x] `tables/weight_summary.csv`
  - [x] `figures/weight_histogram.png`
  - [x] `tables/extreme_weight_units.csv`
- [x] 计算：
  - [x] max weight
  - [x] p95/p99 weight
  - [x] effective sample size
  - [x] share of total weight held by top 1%
- [x] 风险：
  - [x] `EXTREME_IPW_WEIGHTS`
  - [x] `LOW_EFFECTIVE_SAMPLE_SIZE`

#### 验收标准

- [x] extreme weight fixture 触发风险。
- [x] trim 后风险下降时记录在 `run_log.md`。

---

### M2.4 PSM sensitivity grid

**优先级：P1**
**依赖：M2.1、M2.2**

#### TODO

- [ ] 实现参数网格：
  - [x] nearest neighbor = 1, 2, 3, 5
  - [x] caliper = 0.01, 0.03, 0.05
  - [x] with/without replacement
  - [ ] kernel/radius optional
- [x] 输出：
  - [x] `tables/psm_grid_results.csv`
  - [x] `figures/psm_grid_forest.png`
- [x] 记录每个规格：
  - [x] matched N
  - [x] sample loss
  - [x] max SMD after matching
  - [x] ATT
  - [x] SE/CI if available
- [x] 风险：
  - [x] sample loss > 30%: `PSM_SAMPLE_LOSS_HIGH`
  - [x] sign/significance unstable: `TRIM_SENSITIVITY_UNSTABLE`

#### 验收标准

- [x] sample loss fixture 触发风险。
- [x] PSM grid 不作为默认主估计，只作为诊断/稳健性。

---

### M2.5 DRDID integration as core adjusted DID

**优先级：P0**
**依赖：M1.3、M2.1-M2.3**

#### TODO

- [x] 在 `psm_did_policy_run` 中接入 Stata/R DRDID adapter。（当前 workflow 用 Stata `dr_did_2x2`，R adapter 保持 backend-gated interface。）
- [x] 输出：
  - [x] `tables/drdid_main.csv`
  - [x] `raw/drdid.log`
- [x] 报告说明：
  - [x] PS/匹配只解决可观测协变量分布问题。
  - [x] DID 识别仍依赖条件平行趋势。
  - [x] DRDID 是协变量调整 DID 估计，不等同于“匹配后回归自动因果”。
- [x] 与 TWFE、PSM-DID、IPW-DID 放到同一 comparison table。

#### 验收标准

- [x] `tables/adjusted_did_comparison.csv` 生成。
- [x] DRDID 成功时优先展示在报告主表。
- [x] DRDID 与 PSM-DID 方向相反时触发 reviewer risk。

#### 材料入口

- R `DRDID`: https://psantanna.com/DRDID/
- CRAN `DRDID`: https://cran.r-project.org/package=DRDID
- Stata `drdid`: https://ideas.repec.org/c/boc/bocode/s458977.html
- Stata `csdid` / `drdid` usage: https://friosavila.github.io/playingwithstata/main_drdid.html

---

### M2.6 PSM/IPW smoke fixtures

**优先级：P0**
**依赖：M2.1-M2.5**

#### TODO

在 `tests/fixtures/psm_did/` 建：

- [x] `overlap_good.csv`
- [x] `overlap_poor.csv`
- [x] `extreme_weights.csv`
- [x] `psm_sample_loss_high.csv`
- [x] `balance_still_poor.csv`
- [x] `drdid_psm_disagree.csv`
- [x] `trim_sensitivity_unstable.csv`

#### 验收标准

- [ ] `make smoke-psm-did` 通过。（Makefile target 已添加；本机未安装 make，已用 `conda run -n base python skill4econ/tests/smoke/smoke_psm_did.py` 验证同等命令通过。）
- [x] 每个 fixture 有 expected risk。
- [x] 缺 R/Stata 时仍可跑 Python diagnostics。

---

## 4. `spatial_spillover_run`：W 矩阵、空间诊断、spillover DID、SDM adapter

### M3.1 spatial weights factory

**优先级：P0**
**依赖：M0.3**

#### TODO

- [x] 新建 `adapters/python/spatial_weights.py`
- [ ] 支持 W 类型：
  - [x] contiguity from shapefile/adjacency list
  - [x] inverse distance
  - [x] distance band
  - [x] k-nearest neighbors
  - [ ] economic distance
  - [ ] industry similarity
  - [ ] transport network
  - [ ] wind/downwind
  - [ ] river upstream/downstream
  - [ ] patent citation / knowledge network
- [x] 每种 W 输出：
  - [x] dense CSV optional
  - [x] sparse edge list CSV
  - [x] metadata JSON
- [ ] metadata 格式：

```json
{
  "matrix_name": "inverse_distance_200km",
  "unit": "city",
  "row_standardized": true,
  "zero_diagonal": true,
  "density": 0.042,
  "isolated_units": [],
  "min_neighbors": 1,
  "max_neighbors": 19,
  "n_components": 1,
  "source_columns": ["lon", "lat"],
  "parameters": {
    "cutoff_km": 200,
    "power": 1
  }
}
```

- [x] 统一设置：
  - [x] diagonal = 0
  - [x] row-standardization optional but default true
  - [x] isolated units policy: keep/drop/error configurable

#### 验收标准

- [x] 至少 inverse distance、distance band、kNN 三种先落地。
- [x] W metadata 进入 manifest。
- [x] 孤岛节点触发 `SPATIAL_W_HAS_ISLANDS`。
- [x] 未 row-normalize 触发 `SPATIAL_W_NOT_ROW_STANDARDIZED`。

#### 材料入口

- R `spdep` neighbors/weights: https://r-spatial.github.io/spdep/articles/nb.html
- Stata spatial manual W matrix sections: https://www.stata-press.com/manuals/spatial-autoregressive-models-reference-manual/

---

### M3.2 W audit report

**优先级：P0**
**依赖：M3.1**

#### TODO

- [x] 新建 `diagnostics/spatial_preflight.py`
- [x] 输入 W + panel data。
- [x] 输出：
  - [x] `tables/spatial_w_audit.csv`
  - [x] `figures/spatial_degree_distribution.png`
  - [x] `tables/spatial_isolates.csv`
  - [x] `tables/spatial_components.csv`
- [x] 检查：
  - [x] density
  - [x] row sums
  - [x] diagonal
  - [x] degree distribution
  - [x] isolated nodes
  - [x] connected components
  - [x] max/min neighbor count
- [x] 多个 W 时输出 comparison：
  - [x] `tables/spatial_w_comparison.csv`

#### 验收标准

- [x] W 有孤岛 fixture 能识别。
- [x] W comparison 表能比较多个 W。
- [x] 所有 W audit 结果进入 manifest。

---

### M3.3 Moran / LISA spatial preflight

**优先级：P0**
**依赖：M3.1、M3.2**

#### TODO

- [x] Python 实现基础 Moran’s I 或调用 R `spdep`。
- [x] 输出：
  - [x] outcome Moran by year
  - [x] treatment Moran by year
  - [x] residual Moran after baseline TWFE
  - [ ] optional local Moran/LISA
- [x] 文件：
  - [x] `tables/moran_outcome_by_year.csv`
  - [x] `tables/moran_treatment_by_year.csv`
  - [x] `tables/moran_residual_by_year.csv`
  - [x] `figures/moran_outcome_trend.png`
  - [x] `figures/moran_residual_trend.png`
- [x] 如果 treatment spatial clustering 明显，触发 `SPATIAL_TREATMENT_CLUSTERED`。

#### 验收标准

- [x] spatial clustering fixture 触发风险。
- [x] 无 R 后端时 Python basic Moran 可跑。
- [ ] 有 R `spdep` 时可输出 local Moran。

#### 材料入口

- R `spdep` package: https://r-spatial.r-universe.dev/spdep
- `localmoran` docs: https://r-spatial.github.io/spdep/reference/localmoran.html
- `moran.test` docs: https://github.com/r-spatial/spdep/blob/master/man/moran.test.Rd

---

### M3.4 spatial exposure DID

**优先级：P0**
**依赖：M3.1-M3.3、M1.1**

#### TODO

- [x] 实现 exposure 构造：
  - [x] `exposure_it = W * treatment_it`
  - [x] lagged exposure
  - [x] cumulative exposure
  - [x] distance-ring exposure
  - [x] near-control vs far-control indicators
  - [x] buffer-zone deletion
- [x] 输出：
  - [x] `tables/spatial_exposure_summary.csv`
  - [x] `figures/spatial_exposure_distribution.png`
  - [x] `tables/contaminated_controls.csv`
- [ ] 模型：
  - [x] local treatment + exposure TWFE
  - [x] event-study local treatment
  - [x] event-study exposure
  - [x] modern DID common-schema bridge for local treatment where feasible
- [x] 风险：
  - [x] 控制组 exposure 高：`CONTROL_GROUP_CONTAMINATED`
  - [x] exposure/control definition weak: medium risk

#### 验收标准

- [x] `W*treat` exposure 正确。
- [x] ring exposure fixture 正确。
- [x] contaminated controls fixture 触发风险。
- [x] 输出 local effect 和 spillover effect 分开表。

#### 当前实现记录

- [x] `diagnostics/spatial_exposure.py` + `python_wrappers.spatial_exposure_did`
      已实现 reduced-form exposure DID。
- [x] `tests/smoke/test_spatial_weights.py` 覆盖 W*treat、ring exposure、
      contaminated controls、wrapper manifest/reviewer risk。
- [x] modern DID bridge 已接入 `did_paper_run` common schema for local treatment only.

#### 材料入口

- Spatial spillover DID: https://www.kylebutts.com/papers/spatial-spillovers/
- GitHub replication/material: https://github.com/kylebutts/Spatial-Spillover

---

### M3.5 SDM/SAR/SEM spatial panel adapters

**优先级：P1**
**依赖：M3.1-M3.3、M0.4**

#### TODO

Stata:

- [ ] `adapters/stata/xsmle.py`
  - [ ] SAR
  - [ ] SEM
  - [ ] SDM
  - [ ] SAC optional
  - [ ] FE/RE options
  - [ ] parse direct/indirect/total effects
- [ ] `adapters/stata/spxtregress.py`
  - [ ] SAR panel where appropriate
  - [ ] parse main coefficients
  - [ ] parse spatial autoregressive parameter

R:

- [ ] `adapters/r/splm.py`
  - [ ] ML/GM spatial panel
  - [ ] parse coefficients
- [ ] `adapters/r/spdep.py`
  - [ ] spatial lag construction
  - [ ] Moran diagnostics

Common output:

```json
{
  "estimator": "xsmle_sdm_fe",
  "spatial_model": "SDM",
  "weights": "inverse_distance_200km",
  "effects": {
    "direct": {"estimate": -0.031, "se": 0.010},
    "indirect": {"estimate": -0.018, "se": 0.007},
    "total": {"estimate": -0.049, "se": 0.015}
  },
  "raw_coefficients_path": "tables/xsmle_coefficients.csv",
  "status": "success"
}
```

- [x] `spatial_panel_model_adapter` 已有 adapter contract 和
      `backend_canonical_result.json`，不会把缺失后端伪装成估计成功。
- [x] direct/indirect/total impact parser 有固定 fixture 测试。
- [x] fake backend contract matrix 已接入
      `smoke --suite backend-contract --strict`，覆盖 nonzero exit、
      timeout、stdout success but missing output、R 包缺失、empty/malformed
      impacts。
- [ ] SDM 输出必须解释 direct/indirect/total，不允许只报告原始 `Wx` 系数。
- [ ] 如果用户报告 SDM 原始系数为 spillover effect，触发 `INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION`。

#### 验收标准

- [ ] 有 Stata/R 后端时至少一个 SDM adapter smoke 成功。
- [ ] 缺后端时生成 skipped artifact。
- [ ] direct/indirect/total parser 有 fixture 测试。

#### 材料入口

- Stata `xsmle` article: https://journals.sagepub.com/doi/pdf/10.1177/1536867X1701700109
- Stata `spxtregress` manual: https://www.stata.com/manuals/spspxtregress.pdf
- R `splm` CRAN: https://cran.r-project.org/package=splm
- R `splm` JSS: https://www.jstatsoft.org/v47/i01/

---

### M3.6 spatial standard errors / Conley adapter

**优先级：P1**
**依赖：M3.1、M0.4**

#### TODO

- [ ] R `fixest` Conley adapter:
  - [ ] detect lon/lat
  - [ ] cutoff grid
  - [ ] output SE comparison table
- [ ] Stata options:
  - [ ] `acreg` adapter optional
  - [ ] `reg2hdfespatial` adapter optional
  - [ ] Eric Lewis spatial regression code optional external script
- [ ] 输出：
  - [x] `tables/spatial_se_comparison.csv`
  - [ ] `figures/spatial_se_cutoff_sensitivity.png`
- [ ] 风险：
  - [ ] spatial evidence but no spatial SE: `SPATIAL_SE_NOT_USED`

#### 验收标准

- [ ] fixest Conley smoke 可跑。
- [ ] cutoff grid 结果进 manifest。
- [ ] 无坐标时清晰跳过。

#### 材料入口

- `fixest` Conley vcov: https://lrberge.github.io/fixest/reference/vcov_conley.html
- `fixest` SE vignette: https://lrberge.github.io/fixest/articles/standard_errors.html
- Stata `acreg`: https://people.unil.ch/mathiasthoenig/files/2023/04/stata_journal.pdf
- Stata `reg2hdfespatial`: https://github.com/Ramin001/reg2hdfespatial
- Eric Lewis Conley Stata code: https://github.com/erikylewis/spatial_regression

---

### M3.7 W sensitivity grid

**优先级：P0**
**依赖：M3.1-M3.5**

#### TODO

- [ ] 多 W 跑同一主模型。
- [ ] 支持：
  - [ ] contiguity
  - [ ] inverse distance 100/200/300km
  - [ ] kNN k=3/5/8
  - [ ] economic distance optional
- [ ] 输出：
  - [x] `tables/w_sensitivity_main_effects.csv`
  - [ ] `figures/w_sensitivity_forest.png`
- [ ] 检测：
  - [ ] local effect sign flip
  - [ ] spillover effect sign flip
  - [ ] significance unstable
- [ ] 触发 `W_SENSITIVITY_SIGN_FLIP`

#### 验收标准

- [ ] sign flip fixture 触发风险。
- [ ] 至少 3 个 W 的 sensitivity 可自动生成。
- [ ] 报告默认展示 W sensitivity summary。

---

### M3.8 spatial smoke fixtures

**优先级：P0**
**依赖：M3.1-M3.7**

#### TODO

在 `tests/fixtures/spatial/` 建：

- [x] `w_has_islands/`
- [x] `w_not_row_standardized/`
- [x] `treatment_spatially_clustered/`
- [x] `contaminated_controls/`
- [x] `direct_only_effect/`
- [x] `indirect_only_effect/`
- [x] `w_sign_flip/`

#### 验收标准

- [x] `make smoke-spatial` equivalent pytest passes; `make` is missing on this Windows PATH.
- [ ] 每个 fixture 有 expected risk。
- [ ] 没有 Stata/R 时 Python preflight 和 exposure DID 仍通过。

---

## 5. 绿色创新、企业 ESG、绿色金融材料包

### M4.1 中国环境政策试点库

**优先级：P0**
**依赖：M0.3**

#### TODO

- [ ] 新建 `data_catalogs/china_env_policy_catalog.json`
- [ ] 每条政策字段：

```json
{
  "policy_id": "low_carbon_city_pilot",
  "name_zh": "低碳城市试点",
  "policy_level": "city",
  "treatment_type": "staggered",
  "recommended_workflows": ["did_paper_run", "spatial_spillover_run"],
  "required_columns": ["city_id", "year", "first_treat_year"],
  "common_outcomes": ["co2", "co2_intensity", "gtfp", "green_patents"],
  "reviewer_risks": ["policy batch coding must be verified against official list"],
  "source_urls": []
}
```

- [ ] 先录入：
  - [ ] 低碳城市试点
  - [ ] 碳交易试点
  - [ ] 绿色金融改革创新试验区
  - [ ] 创新型城市试点
  - [ ] 智慧城市试点
  - [ ] 宽带中国
  - [ ] 环保约谈
  - [ ] 中央生态环境保护督察
  - [ ] 大气污染防治重点区域
  - [ ] 排污权交易
  - [ ] 绿色信贷政策
  - [ ] 环境保护税
- [ ] 为每条政策提供：
  - [ ] treatment coding notes
  - [ ] common unit level
  - [ ] common start year
  - [ ] pitfalls
  - [ ] recommended DID design
  - [ ] source links
- [ ] 新建 helper：
  - [ ] `list_policies()`
  - [ ] `get_policy(policy_id)`
  - [ ] `render_policy_coding_template(policy_id)`

#### 验收标准

- [ ] 可以由 policy_id 生成 data_contract 草稿。
- [ ] policy catalog smoke 能读取并校验 JSON schema。
- [ ] 每条政策至少有 1 个材料入口 URL。

#### 材料入口

- 低碳试点/碳交易试点官方材料：
  - https://www.ndrc.gov.cn/xwdt/ztzl/2021qgjnxcz/bmjncx/202108/t20210827_1294892.html
  - https://www.ndrc.gov.cn/xxgk/zcfb/tz/201201/t20120113_964370.html
- 绿色金融改革创新试验区官方材料：
  - https://wzdt.pbc.gov.cn/rmyh/2025-07/21/article_2025072110012382105.html
- 中央生态环境保护督察官方材料：
  - https://www.mee.gov.cn/ywgz/zysthjbhdc/dcjl/202302/t20230220_1016786.shtml
  - https://www.mee.gov.cn/ywgz/zysthjbhdc/dczg/202310/t20231010_1042707.shtml

---

### M4.2 green patent outcome pipeline

**优先级：P0**
**依赖：M0.3**

#### TODO

- [ ] 新建 `adapters/python/green_patent.py`
- [ ] 新建 `data_catalogs/green_patent_classifiers.yaml`
- [ ] 支持三套分类：
  - [ ] WIPO IPC Green Inventory
  - [ ] OECD ENV-TECH
  - [ ] EPO Y02/Y04S
- [ ] 输入：
  - [ ] patent id
  - [ ] applicant / firm id
  - [ ] city/province
  - [ ] application year
  - [ ] grant year optional
  - [ ] IPC/CPC codes
  - [ ] patent type
  - [ ] citations optional
- [ ] 输出：
  - [ ] `green_patent_application_count`
  - [ ] `green_patent_grant_count`
  - [ ] `green_invention_application_count`
  - [ ] `green_utility_model_application_count`
  - [ ] `green_patent_citations`
  - [ ] `log1p_*`
- [ ] 支持聚合：
  - [ ] firm-year
  - [ ] city-year
  - [ ] province-year
  - [ ] industry-year
- [ ] 零值处理：
  - [ ] `log(1+x)`
  - [ ] PPML-ready count outcome
  - [ ] missing vs true zero 区分
- [ ] 输出：
  - [ ] `tables/green_patent_constructed_panel.csv`
  - [ ] `tables/green_patent_summary.csv`
  - [ ] `figures/green_patent_zero_share_by_year.png`
  - [ ] `figures/green_patent_trend.png`

#### 验收标准

- [ ] 能用小 fixture 把 IPC/CPC codes 分类成 green/non-green。
- [ ] 能按 firm-year/city-year 聚合。
- [ ] 输出可直接作为 `did_paper_run` outcome。
- [ ] 零值占比高时建议 PPML/fepois/ppmlhdfe。

#### 材料入口

- WIPO IPC Green Inventory: https://www.wipo.int/classifications/ipc/green-inventory/home
- OECD environment-related patents: https://www.oecd.org/en/data/indicators/patents-on-environment-technologies.html
- EPO Y02/Y04S: https://www.epo.org/en/news-events/in-focus/classification/classification/updatesYO2andY04S
- CNIPA green/low-carbon patent reports: https://english.cnipa.gov.cn/col/col3262/index.html

---

### M4.3 firm green finance / ESG panel template

**优先级：P1**
**依赖：M1、M2、M4.1、M4.2**

#### TODO

- [ ] 新增 workflow/template：`firm_green_finance_policy_run`
- [ ] 或者在 `did_paper_run` 下新增 `template=firm_green_finance`
- [ ] 输入 contract 扩展：

```yaml
firm_panel:
  firm_id: stkcd
  year: year
  industry: industry_code
  province: province_code
  city: city_code
  listed_status_filters:
    drop_st: true
    drop_financial_industry: true
  winsor:
    columns: ["size", "lev", "roa", "cashflow"]
    limits: [0.01, 0.99]
```

- [ ] 固定效应模板：
  - [ ] firm FE
  - [ ] year FE
  - [ ] industry × year FE
  - [ ] province × year FE
  - [ ] city × year FE optional
- [ ] 聚类模板：
  - [ ] firm cluster
  - [ ] city cluster
  - [ ] province cluster
  - [ ] two-way cluster
- [ ] 常见 outcomes：
  - [ ] ESG score
  - [ ] green patent count
  - [ ] financing constraint
  - [ ] debt cost
  - [ ] environmental investment
  - [ ] pollution penalty
  - [ ] carbon performance
- [ ] 常见 mechanisms：
  - [ ] financing constraint
  - [ ] green credit
  - [ ] R&D
  - [ ] analyst attention
  - [ ] media attention
  - [ ] environmental investment
- [ ] heterogeneity：
  - [ ] SOE vs non-SOE
  - [ ] heavy polluting vs non-heavy
  - [ ] high vs low financing constraint
  - [ ] east/central/west
  - [ ] high vs low marketization
- [ ] adapters:
  - [ ] `reghdfe`
  - [ ] `ppmlhdfe`
  - [ ] R `fixest::feols`
  - [ ] R `fixest::fepois`

#### 验收标准

- [ ] firm panel fixture 可生成主表。
- [ ] green patent count outcome 默认推荐 PPML 作为稳健性。
- [ ] artifact 包含 firm panel cleaning log。
- [ ] 不强制依赖商业数据库，只提供 schema 和模板。

#### 材料入口

- CSMAR: https://www.csmar.com/en/
- CNRDS patent data reference: https://ceibs.libguides.com/news/newresources/home/CNRDS-Patent-Data-Recommendation
- SynTao Green Finance ESG rating: https://en.syntaogf.com/
- `reghdfe`: https://scorreia.com/help/reghdfe.html
- `ppmlhdfe`: https://scorreia.com/software/ppmlhdfe/
- R `fixest`: https://cran.r-project.org/package=fixest/vignettes/fixest_walkthrough.html

---

### M4.4 China environment data source guide

**优先级：P1**
**依赖：无**

#### TODO

- [ ] 新建 `data_catalogs/china_env_data_sources.md`
- [ ] 覆盖：
  - [ ] CEADs
  - [ ] 国家统计局/统计年鉴
  - [ ] 中国城市统计年鉴
  - [ ] EPS/CNKI 年鉴
  - [ ] CNEMC
  - [ ] ACAG satellite PM2.5
  - [ ] CIED
  - [ ] CIESD
  - [ ] CSMAR
  - [ ] CNRDS
- [ ] 每个数据源写：
  - [ ] 适合什么 outcome/control
  - [ ] 常见时间范围
  - [ ] 地理层级
  - [ ] 是否公开/商业
  - [ ] 常见清洗坑
  - [ ] 推荐 workflow
  - [ ] URL
- [ ] 新建 `docs/data_source_to_workflow_map.md`

#### 验收标准

- [ ] 文档存在且链接可点击。
- [ ] 至少 10 个数据源。
- [ ] 每个数据源都有 workflow mapping。

#### 材料入口

- CEADs: https://www.ceads.net/
- CEADs city CO2 inventories: https://www.ceads.net/publications/inventory_compilation/
- 国家统计局年鉴入口: https://www.stats.gov.cn/english/Statisticaldata/
- CNEMC: https://www.cnemc.cn/en/
- CNEMC responsibilities: https://www.cnemc.cn/en/main_responsibilities/
- ACAG PM2.5 archive: https://sites.wustl.edu/acag/satellites/surface-pm2-5-archive/
- CIED: https://figshare.com/collections/Chinese_Industrial_Emissions_Database_CIED_/6269295
- CIESD: https://www.nature.com/articles/s41597-022-01362-x

---

## 6. `efficiency_frontier_run`：DEA/GTFP adapter 和变量协议

> 不重写 DEA 核心。只做 schema、检查、adapter、结果解析、敏感性、与 DID/spatial 串联。

### M5.1 DEA/GTFP data schema

**优先级：P0**
**依赖：M0.3、M0.1**

#### TODO

- [ ] 扩展 data contract：

```yaml
frontier:
  dmu_id: city_id
  time_id: year
  inputs:
    - capital_stock
    - labor
    - energy_consumption
  desirable_outputs:
    - gdp
  undesirable_outputs:
    - co2
    - so2
  orientation: non_oriented
  returns_to_scale: vrs
  frontier_type: global
  model_family: super_sbm_undesirable
```

- [ ] 新建 `diagnostics/dea_checks.py`
- [ ] 检查：
  - [ ] DMU 数是否足够
  - [ ] input/output 是否非负
  - [ ] undesirable output 是否有负值
  - [ ] 零值/缺失值比例
  - [ ] 同一年 DMU 数
  - [ ] balanced/unbalanced panel
  - [ ] CRS/VRS/frontier_type 是否声明
- [ ] 风险：
  - [ ] `DEA_DMU_TOO_FEW`
  - [ ] `DEA_BAD_OUTPUT_NEGATIVE`
  - [ ] `DEA_ZERO_OR_MISSING_BAD_OUTPUT`
  - [ ] `DEA_FRONTIER_CHOICE_UNREPORTED`

#### 验收标准

- [ ] DEA fixture 能通过 schema。
- [ ] bad output 负值 fixture 触发 fatal。
- [ ] DMU 太少 fixture 触发 high risk。

---

### M5.2 DEA/R adapters

**优先级：P1**
**依赖：M5.1、M0.4**

#### TODO

- [ ] `adapters/r/dear.py`
  - [ ] conventional DEA
  - [ ] SBM/super-efficiency where supported
  - [ ] Malmquist where supported
  - [ ] bootstrapping where supported
- [ ] `adapters/r/benchmarking.py`
  - [ ] DEA
  - [ ] Malmquist
  - [ ] super/directional if applicable
- [ ] `adapters/r/rdea.py`
  - [ ] robust DEA
  - [ ] returns-to-scale tests
  - [ ] Simar-Wilson style second-stage support where feasible
- [ ] Common output:
  - [ ] `tables/frontier_efficiency_scores.csv`
  - [ ] `tables/frontier_peer_slacks.csv`
  - [ ] `tables/malmquist_decomposition.csv`
  - [ ] `raw/frontier_backend.log`

#### 验收标准

- [ ] 至少一个 R adapter 真实 smoke 可跑。
- [ ] 缺 R 时可生成 backend skipped artifact。
- [ ] 结果 schema 可被 DID workflow 当 outcome 读入。

#### 材料入口

- R `deaR` paper: https://www.sciencedirect.com/science/article/pii/S235271102500233X
- R `deaR` manual: https://cran.r-project.org/web/packages/deaR/deaR.pdf
- R `Benchmarking`: https://cran.r-project.org/package=Benchmarking
- R `rDEA`: https://cran.r-project.org/web/packages/rDEA/refman/rDEA.html

---

### M5.3 Stata GTFP / undesirable output adapters

**优先级：P1**
**依赖：M5.1、M0.4**

#### TODO

- [ ] `adapters/stata/gtfpch.py`
  - [ ] Malmquist–Luenberger
  - [ ] Luenberger indicator
  - [ ] undesirable outputs
  - [ ] parse productivity change
- [ ] optional:
  - [ ] `teddf`
  - [ ] `dea`
  - [ ] `malmq`
- [ ] 输出：
  - [ ] `tables/gtfpch_index.csv`
  - [ ] `tables/gtfpch_decomposition.csv`
  - [ ] `raw/gtfpch.log`

#### 验收标准

- [ ] Stata 后端可用时 smoke 成功。
- [ ] infeasible case 触发 `MALMQUIST_INFEASIBLE`。
- [ ] 输出 index 可作为 DID/spatial outcome。

#### 材料入口

- Stata `gtfpch` Stata Journal: https://ideas.repec.org/a/tsj/stataj/y22y2022i1p103-124.html
- Stata presentation: https://www.stata.com/meeting/china20-Uone-Tech/slides/China20_Wang_D.pdf

---

### M5.4 variable sensitivity grid

**优先级：P0**
**依赖：M5.1-M5.3**

#### TODO

- [ ] 支持变量口径敏感性：
  - [ ] bad output: CO2 / SO2 / PM / COD / combined
  - [ ] energy input: electricity / total energy / coal
  - [ ] capital stock: perpetual inventory variants
  - [ ] desirable output: GDP / industrial output
- [ ] 输出：
  - [ ] `tables/frontier_variable_sensitivity.csv`
  - [ ] `figures/frontier_rank_correlation_heatmap.png`
  - [ ] `figures/frontier_sensitivity_forest.png`
- [ ] 计算：
  - [ ] efficiency score rank correlation
  - [ ] GTFP rank correlation
  - [ ] sign stability when used in DID
- [ ] 风险：
  - [ ] `DEA_VARIABLE_SENSITIVITY_UNCHECKED`
  - [ ] sensitivity rank correlation too low -> high risk

#### 验收标准

- [ ] 至少两个 bad output 口径可跑。
- [ ] sensitivity 输出进入 manifest。
- [ ] 敏感性大时 reviewer risk 触发。

---

### M5.5 DEA second-stage warning and bridge to DID/spatial

**优先级：P0**
**依赖：M5.1-M5.4、M1、M3**

#### TODO

- [ ] 检测用户是否把 DEA score 直接进 OLS/Tobit 二阶段。
- [ ] 若 naive second-stage：
  - [ ] 触发 `DEA_SECOND_STAGE_NAIVE_TOBIT`
  - [ ] 报告中提示 bootstrap/Simar-Wilson 或将 score 作为构造指标进入政策评估并谨慎解释
- [ ] 提供 bridge：
  - [ ] `frontier_to_did_contract()`
  - [ ] `frontier_to_spatial_contract()`
- [ ] 输出：
  - [ ] `derived_outcomes/gtfp_panel.csv`
  - [ ] `derived_outcomes/ecological_efficiency_panel.csv`

#### 验收标准

- [ ] `efficiency_frontier_run` 产出的 panel 能直接喂给 `did_paper_run`。
- [ ] 能直接喂给 `spatial_spillover_run`。
- [ ] naive Tobit fixture 触发风险。

---

### M5.6 DEA smoke fixtures

**优先级：P0**
**依赖：M5.1-M5.5**

#### TODO

在 `tests/fixtures/frontier/` 建：

- [ ] `basic_dea_valid.csv`
- [ ] `bad_output_zero.csv`
- [ ] `bad_output_negative.csv`
- [ ] `low_dmu_ratio.csv`
- [ ] `crs_vrs_diverge.csv`
- [ ] `variable_sensitivity_unstable.csv`
- [ ] `malmquist_infeasible.csv`
- [ ] `naive_second_stage_tobit.csv`

#### 验收标准

- [ ] `make smoke-frontier` 通过。
- [ ] 每个 fixture 有 expected risk。

---

## 7. `mechanism_threshold_run`：拆成机制证据和异质性/非线性

> 保留旧入口 `mechanism_threshold_run`，内部调两个新模块：`mechanism_evidence_run`、`heterogeneity_nonlinearity_run`。不要默认写“机制成立”；默认写“机制证据”。

### M6.1 mechanism timing validator

**优先级：P0**
**依赖：M0.3、M0.1**

#### TODO

- [ ] 新建 `diagnostics/mechanism_timing.py`
- [ ] 支持 contract：

```yaml
mechanism:
  mediators:
    - name: green_innovation
      variable: green_patent_count
      expected_timing: post_policy_pre_outcome
      lags: [1, 2]
  outcome_lags: [1, 2]
```

- [ ] 检查：
  - [ ] mediator 是否晚于 policy
  - [ ] mediator 是否早于 outcome
  - [ ] mediator 是否与 outcome 同期
  - [ ] mediator 是否实际发生在 outcome 之后
- [ ] 输出：
  - [ ] `tables/mechanism_timing_check.csv`
- [ ] 风险：
  - [ ] outcome 后出现的 mediator: `MEDIATOR_TIMING_INVALID`
  - [ ] mediator/outcome 同期: `MEDIATOR_SAME_PERIOD_AS_OUTCOME`

#### 验收标准

- [ ] timing valid/invalid fixtures 正确触发风险。
- [ ] 所有 mechanism 报告先跑 timing validator。

---

### M6.2 mechanism evidence workflow

**优先级：P1**
**依赖：M6.1、M1**

#### TODO

- [ ] 新建 `workflows/mechanism_evidence_run/`
- [ ] 默认流程：
  - [ ] policy -> mediator DID
  - [ ] policy -> outcome DID
  - [ ] mediator association with outcome, with lag options
  - [ ] optional causal mediation adapter
- [ ] 多机制：
  - [ ] green innovation
  - [ ] industrial structure
  - [ ] energy structure
  - [ ] financing constraints
  - [ ] environmental regulation
  - [ ] factor misallocation
  - [ ] fiscal pressure
- [ ] 多重检验：
  - [ ] FDR correction optional
  - [ ] `MULTIPLE_MECHANISMS_NO_ADJUSTMENT` warning
- [ ] 输出：
  - [ ] `tables/mechanism_policy_to_mediator.csv`
  - [ ] `tables/mechanism_mediator_to_outcome.csv`
  - [ ] `tables/mechanism_summary.csv`
  - [ ] `paper_methods/mechanism_evidence_language.md`
- [ ] 语言 guardrails：
  - [ ] 禁止默认输出“证明机制成立”
  - [ ] 默认输出“结果支持某机制渠道的证据”
  - [ ] causal mediation assumptions 不满足时强制降级表述

#### 验收标准

- [ ] 旧 `mechanism_threshold_run` 可调用该 workflow。
- [ ] 报告语言通过 snapshot test。
- [ ] invalid timing 不阻断运行，但标 high/fatal risk。

#### 材料入口

- R `mediation` vignette: https://cran.r-project.org/web/packages/mediation/vignettes/mediation.pdf
- R `mediation` JSS: https://www.jstatsoft.org/v59/i05/
- Stata `mediate`: https://www.stata.com/manuals/causalmediate.pdf
- Stata `mediate intro`: https://www.stata.com/manuals/causalmediateintro.pdf

---

### M6.3 causal mediation adapters

**优先级：P2**
**依赖：M6.2、M0.4**

#### TODO

- [ ] R `mediation` adapter:
  - [ ] mediator model
  - [ ] outcome model
  - [ ] ACME/ADE/total/proportion mediated
  - [ ] sensitivity if applicable
- [ ] Stata `mediate` adapter:
  - [ ] continuous/binary/count outcome/mediator where supported
  - [ ] parse direct/indirect/total effects
- [ ] 输出：
  - [ ] `tables/causal_mediation_effects.csv`
  - [ ] `tables/causal_mediation_sensitivity.csv`
  - [ ] `raw/mediation_backend.log`
- [ ] 强制写 assumptions：
  - [ ] no unmeasured treatment-outcome confounding
  - [ ] no unmeasured treatment-mediator confounding
  - [ ] no unmeasured mediator-outcome confounding
  - [ ] correct timing

#### 验收标准

- [ ] 缺 assumptions config 时 reviewer risk。
- [ ] causal mediation output 不覆盖机制证据主表，只作为 optional supplement。

---

### M6.4 threshold panel adapter

**优先级：P1**
**依赖：M0.4**

#### TODO

- [ ] 新建 `workflows/heterogeneity_nonlinearity_run/`
- [ ] Stata `xthreg` adapter:
  - [ ] static fixed-effect panel threshold
  - [ ] balanced panel check
  - [ ] single/double/triple threshold
  - [ ] bootstrap p-value
  - [ ] threshold CI
- [ ] Stata `xthenreg` adapter:
  - [ ] dynamic panel threshold GMM
  - [ ] instrument settings
  - [ ] bootstrap
- [ ] 输出：
  - [ ] `tables/threshold_results.csv`
  - [ ] `tables/threshold_bootstrap_tests.csv`
  - [ ] `figures/threshold_lr_plot.png`
- [ ] 风险：
  - [ ] unbalanced panel with `xthreg`: `THRESHOLD_UNBALANCED_PANEL`
  - [ ] bootstrap not significant: `THRESHOLD_BOOTSTRAP_NOT_SIGNIFICANT`

#### 验收标准

- [ ] threshold insignificant fixture 触发风险。
- [ ] dynamic/static threshold 分开，不混用解释。
- [ ] 旧 `mechanism_threshold_run` 可调用该模块。

#### 材料入口

- Stata `xthreg`: https://journals.sagepub.com/doi/pdf/10.1177/1536867X1501500108
- Stata `xthenreg`: https://journals.sagepub.com/doi/pdf/10.1177/1536867X19874243
- RePEc `xthreg`: https://ideas.repec.org/a/tsj/stataj/v15y2015i1p121-134.html
- RePEc `xthenreg`: https://ideas.repec.org/a/tsj/stataj/v19y2019i3p685-697.html

---

### M6.5 quantile heterogeneity adapters

**优先级：P1**
**依赖：M0.4**

#### TODO

- [ ] 区分：
  - [ ] conditional quantile
  - [ ] unconditional quantile / RIF
- [ ] Stata `rifhdreg` adapter：
  - [ ] q10/q25/q50/q75/q90
  - [ ] high-dimensional FE
  - [ ] parse RIF estimates
- [ ] R optional:
  - [ ] RIF implementation / existing packages if selected later
  - [ ] `fixest` for FE on RIF-transformed outcome
- [ ] 输出：
  - [ ] `tables/quantile_heterogeneity.csv`
  - [ ] `figures/quantile_effect_curve.png`
- [ ] 风险：
  - [ ] user does not specify conditional/unconditional: `QUANTILE_TYPE_AMBIGUOUS`
  - [ ] quantile results conflict with mean effect: medium risk requiring explanation

#### 验收标准

- [ ] RIF q-grid smoke 通过或后端缺失时 graceful skip。
- [ ] 报告明确写 conditional vs unconditional。
- [ ] 不默认把 quantile 当主识别。

#### 材料入口

- Stata RIF / `rifhdreg`: https://ideas.repec.org/c/boc/bocode/s458577.html
- Rios-Avila RIF slides: https://www.stata.com/meeting/chicago19/slides/chicago19_Rios-Avila.pdf

---

### M6.6 mechanism/threshold smoke fixtures

**优先级：P0**
**依赖：M6.1-M6.5**

#### TODO

在 `tests/fixtures/mechanism_threshold/` 建：

- [ ] `mediator_valid_timing.csv`
- [ ] `mediator_same_period_as_outcome.csv`
- [ ] `mediator_after_outcome.csv`
- [ ] `multiple_mechanisms_conflict.csv`
- [ ] `threshold_not_significant.csv`
- [ ] `threshold_unbalanced_panel.csv`
- [ ] `conditional_unconditional_quantile_conflict.csv`

#### 验收标准

- [ ] `make smoke-mechanism-threshold` 通过。
- [ ] 每个 fixture 有 expected risk。

---

## 8. replication zoo：10 个可复现 demo

### M7.1 replication zoo scaffold

**优先级：P1**
**依赖：M1-M6 可逐步接入**

#### TODO

在 `examples/replication_zoo/` 建 10 个 demo skeleton：

```text
examples/replication_zoo/
  01_low_carbon_city_co2/
  02_carbon_trading_carbon_intensity/
  03_green_finance_green_innovation/
  04_environmental_inspection_air_pollution/
  05_green_credit_heavy_polluting_firms/
  06_smart_city_green_innovation/
  07_broadband_china_carbon_efficiency/
  08_emission_trading_industrial_pollution/
  09_low_carbon_city_gtfp/
  10_carbon_trading_neighbor_pollution/
```

每个 demo 固定文件：

```text
README.md
01_data_contract.yaml
02_policy_coding.do
02_policy_coding.R
03_main_did.do
03_main_did.R
04_modern_did_estimators.do
04_modern_did_estimators.R
05_spatial_or_mechanism.do
05_spatial_or_mechanism.R
expected_artifacts.md
expected_reviewer_risk.json
```

#### 10 个 demo 对应 workflow

- [ ] 低碳城市试点 -> CO2 排放：DID + spatial spillover
- [ ] 碳交易试点 -> 碳强度：DID + event-study
- [ ] 绿色金融试验区 -> 企业绿色创新：firm DID + PPML
- [ ] 中央环保督察 -> 空气污染：staggered DID + spatial SE
- [ ] 绿色信贷政策 -> 重污染企业融资约束：firm DID / DDD
- [ ] 智慧城市 -> 绿色创新：DID + mechanism
- [ ] 宽带中国 -> 碳排放效率：DID + GTFP
- [ ] 排污权交易 -> 工业污染：DID + spatial spillover
- [ ] 低碳城市 -> GTFP：DEA/GML + DID
- [ ] 碳交易试点 -> 邻地污染：spatial exposure DID

#### 验收标准

- [ ] 每个 demo README 说明数据需求、政策编码、主 workflow。
- [ ] 不要求真实商业数据入库。
- [ ] 每个 demo 能用 synthetic/minimal fixture 跑通。
- [ ] 每个 demo 都有 expected reviewer risks。

---

### M7.2 paper artifact generator

**优先级：P1**
**依赖：M0.2、M1-M6**

#### TODO

- [ ] 新建 `reporting/paper_methods.py`
- [ ] 每个 workflow 输出：
  - [ ] `paper_methods/main_identification.md`
  - [ ] `paper_methods/diagnostics_summary.md`
  - [ ] `paper_methods/robustness_summary.md`
  - [ ] `paper_methods/reviewer_risks.md`
- [ ] 注意：
  - [ ] 不自动夸大 causal claim。
  - [ ] 机制只写 evidence。
  - [ ] TWFE 在 staggered 时只写 benchmark。
  - [ ] spatial SDM 只解释 impact decomposition。
  - [ ] DEA 结果写清楚模型设定。
- [ ] 支持中英文模板：
  - [ ] `language: zh`
  - [ ] `language: en`

#### 验收标准

- [ ] DID、spatial、DEA、mechanism 都有 methods text。
- [ ] snapshot test 防止 unsafe claims。
- [ ] reviewer risk 高时 methods text 自动降调。

---

## 9. docs：Codex 每轮要补的文档

### M8.1 必写 docs 文件

**优先级：P0-P1**
**依赖：对应模块**

创建以下文档：

- [ ] `docs/did_estimator_router.md`
- [ ] `docs/did_failure_modes.md`
- [x] `docs/psm_ipw_balance_diagnostics.md`
- [ ] `docs/spatial_weights_cookbook.md`
- [ ] `docs/spatial_spillover_identification.md`
- [ ] `docs/green_patent_outcome_construction.md`
- [ ] `docs/china_env_policy_catalog.md`
- [ ] `docs/dea_gtfp_variable_protocol.md`
- [ ] `docs/mechanism_evidence_language_guardrails.md`
- [ ] `docs/reviewer_risk_schema.md`
- [ ] `docs/backend_adapters.md`
- [ ] `docs/replication_zoo.md`

每个文档固定 5 段，不要写成长论文：

```text
1. When to use
2. Required columns
3. Estimators/adapters called
4. Mandatory diagnostics
5. Reviewer risks
```

#### 验收标准

- [ ] 每个新增模块有对应 docs。
- [ ] docs 中命令能复制运行。
- [ ] docs 中列出 artifact 输出路径。

---

## 10. CI / smoke / release hardening

### M9.1 Makefile / task runner

**优先级：P0**
**依赖：所有模块逐步接入**

#### TODO

- [ ] 新增或更新 `Makefile`：

```makefile
smoke:
	pytest tests/smoke

smoke-did:
	pytest tests/smoke/test_did_paper_run.py

smoke-psm-did:
	pytest tests/smoke/test_psm_did_policy_run.py

smoke-spatial:
	pytest tests/smoke/test_spatial_spillover_run.py

smoke-frontier:
	pytest tests/smoke/test_efficiency_frontier_run.py

smoke-mechanism-threshold:
	pytest tests/smoke/test_mechanism_threshold_run.py

lint:
	ruff check skill4econ tests

format:
	ruff format skill4econ tests
```

- [ ] 后端可用时增加：
  - [ ] `make smoke-stata`
  - [ ] `make smoke-r`
- [ ] 后端不可用时跳过，不失败。

#### 验收标准

- [ ] `make smoke` 一条命令可跑。
- [ ] CI 无 Stata/R 时仍能过 Python smoke。
- [ ] 有后端的本地机器可跑 integration smoke。

---

### M9.2 run reproducibility log

**优先级：P0**
**依赖：M0.2**

#### TODO

每次 workflow 输出 `run_log.md`：

```md
# Run log

- workflow:
- run_id:
- timestamp:
- input data hash:
- config hash:
- git commit:
- python version:
- stata status:
- r status:
- selected estimators:
- skipped estimators:
- reviewer risk level:
```

- [ ] 数据 hash 可选但推荐。
- [ ] config hash 必须有。
- [ ] adapter command/script 必须存档到 `scripts/`。

#### 验收标准

- [ ] 任意 smoke run 都有 `run_log.md`。
- [ ] scripts 可复跑。
- [ ] artifact manifest 指向 run_log。

---

### M9.3 safe degradation

**优先级：P0**
**依赖：M0.4**

#### TODO

- [ ] 对所有 adapter 实现统一状态：
  - [ ] `success`
  - [ ] `failed`
  - [ ] `skipped_backend_unavailable`
  - [ ] `skipped_incompatible_design`
  - [ ] `skipped_missing_required_columns`
- [ ] 失败时输出：
  - [ ] raw error
  - [ ] clean error
  - [ ] suggested fix
- [ ] 不允许裸 exception 直接抛给用户，除非是 data contract fatal。

#### 验收标准

- [ ] 每个 adapter 有 failure fixture。
- [ ] 失败进入 manifest。
- [ ] reviewer risk 能合并失败原因。

---

## 11. 不要做 / 只做 adapter

这些不是 todo，是明确避免 Codex 浪费时间。

### 不要多做 PSM 算法动物园

- [ ] 不要优先堆 Genetic Matching、CBPS、复杂机器学习 PS。
- [ ] 先把 overlap、balance、weight、trim、DRDID 做硬。

### 不要重写 DEA/SBM/Malmquist 核心

- [ ] 不写 LP solver。
- [ ] 不自己实现复杂 GML/Super-SBM。
- [ ] 用 R/Stata 后端，自己做 schema、检查、解析、报告。

### 不要把复杂空间模型全家桶做成默认入口

- [ ] SDM/SAR/SEM/SAC 够用。
- [ ] GNS/Manski/social interaction 不做默认按钮。
- [ ] 如要支持，只能 hidden advanced adapter。

### 不要默认输出强 causal mediation claim

- [ ] 默认写“机制证据”。
- [ ] 只有 causal mediation assumptions 明确时才写 causal mediation。
- [ ] 不允许自动写“证明机制成立”。

### 不要做通用 CGE/IAM/ABM workflow

- [ ] 这类模型只做 external adapter/report assembler。
- [ ] 不进入 P0/P1。

---

## 12. 推荐执行顺序

### Batch 0：基础设施

- [ ] M0.1 reviewer risk
- [ ] M0.2 artifact manifest
- [ ] M0.3 data contract
- [ ] M0.4 backend checker
- [ ] M9.1 Makefile smoke
- [ ] M9.2 run log
- [ ] M9.3 safe degradation

完成标准：

- [ ] 现有 5 个 workflow 都仍能 smoke。
- [ ] 每个 workflow 都产出 manifest/risk/log。
- [ ] 无 Stata/R 环境也不硬崩。

---

### Batch 1：DID 可信度补强

- [x] M1.1 DID design detector
- [x] M1.2 estimator router
- [ ] M1.3 modern DID adapters
- [x] M1.4 comparison table
- [ ] M1.5 DID fixtures
- [ ] `docs/did_estimator_router.md`
- [ ] `docs/did_failure_modes.md`

完成标准：

- [ ] staggered DID 不再默认只跑 TWFE。
- [ ] CS/SA/BJS/DRDID/HonestDiD/Bacon 可按后端 availability 自动选择/跳过。
- [ ] reviewer risk 能识别 TWFE 问题。

---

### Batch 2：PSM/IPW/DRDID 诊断补强

- [x] M2.1 overlap
- [x] M2.2 balance
- [x] M2.3 weights
- [x] M2.4 PSM grid
- [x] M2.5 DRDID integration
- [x] M2.6 fixtures
- [x] `docs/psm_ipw_balance_diagnostics.md`

完成标准：

- [x] PSM/IPW 结果不再只是“能跑回归”。
- [x] overlap/balance/weights/trim 都有硬 artifact。
- [x] DRDID 能作为 adjusted DID 主结果之一。

---

### Batch 3：空间溢出论文级化

- [x] M3.1 W factory
- [x] M3.2 W audit
- [ ] M3.3 Moran/LISA
- [x] M3.4 spatial exposure DID（reduced-form core done；local DID common-schema bridge done）
- [x] M3.5 SDM/SAR/SEM adapter contract/parser
- [ ] M3.5-live 真实 xsmle/spxtregress/splm/spatialreg 后端认证（P2/nightly/manual certification）
- [x] M3.6 spatial SE
- [x] M3.7 W sensitivity
- [x] M3.8 fixtures
- [ ] `docs/spatial_weights_cookbook.md`
- [ ] `docs/spatial_spillover_identification.md`

完成标准：

- [ ] 不同 W 可自动生成、审计、跑敏感性。
- [x] control contamination 能被检测。
- [ ] SDM 输出 direct/indirect/total effects。
- [ ] spatial workflow 能作为环境经济 P0 主流程。

---

### Batch 4：绿色创新 / 企业绿色金融模板

- [ ] M4.1 policy catalog
- [ ] M4.2 green patent pipeline
- [ ] M4.3 firm green finance template
- [ ] M4.4 data source guide
- [ ] `docs/green_patent_outcome_construction.md`
- [ ] `docs/china_env_policy_catalog.md`

完成标准：

- [ ] 能从 policy catalog 生成 data_contract 草稿。
- [ ] green patent 可按 WIPO/OECD/EPO 口径构造。
- [ ] firm panel ESG/绿色金融 DID 模板可 smoke。
- [ ] count outcome 有 PPML/fepois adapter 路径。

---

### Batch 5：DEA/GTFP adapter 补强

- [ ] M5.1 DEA/GTFP schema
- [ ] M5.2 R adapters
- [ ] M5.3 Stata gtfpch adapter
- [ ] M5.4 variable sensitivity
- [ ] M5.5 bridge to DID/spatial
- [ ] M5.6 fixtures
- [ ] `docs/dea_gtfp_variable_protocol.md`

完成标准：

- [ ] 不重写 DEA 核心。
- [ ] bad output、frontier choice、DMU ratio 都能诊断。
- [ ] GTFP/效率 score 能进入 DID/spatial。
- [ ] 二阶段 naive Tobit 有 reviewer risk。

---

### Batch 6：机制、门槛、分位数防误用

- [ ] M6.1 mechanism timing
- [ ] M6.2 mechanism evidence workflow
- [ ] M6.3 causal mediation adapters
- [ ] M6.4 threshold panel
- [ ] M6.5 quantile adapters
- [ ] M6.6 fixtures
- [ ] `docs/mechanism_evidence_language_guardrails.md`

完成标准：

- [ ] 旧 `mechanism_threshold_run` 仍可用。
- [ ] 新机制 workflow 不再默认写“机制成立”。
- [ ] threshold/quantile 明确作为 heterogeneity/nonlinearity。
- [ ] timing invalid 能触发风险。

---

### Batch 7：replication zoo 和报告生成器

- [ ] M7.1 replication zoo scaffold
- [ ] M7.2 paper artifact generator
- [ ] 所有 docs 补齐
- [ ] examples smoke

完成标准：

- [ ] 10 个 demo skeleton 都在。
- [ ] 每个 demo 有 data contract、policy coding、expected risk。
- [ ] 每个 workflow 能生成 paper methods markdown。
- [ ] snapshot test 防止 unsafe claims。

---

## 13. 最终验收总表

项目做完后，必须全部满足：

### Workflow 层

- [ ] `did_paper_run` 支持 DID design detection + estimator router + modern DID comparison。
- [ ] `psm_did_policy_run` 支持 overlap/balance/weights/trim/DRDID。
- [ ] `spatial_spillover_run` 支持 W factory/audit/Moran/exposure DID/SDM adapter/W sensitivity。
- [ ] `mechanism_threshold_run` 保持兼容，并内部拆到 mechanism evidence + heterogeneity/nonlinearity。
- [ ] `efficiency_frontier_run` 保持 adapter 路线，支持 DEA/GTFP schema/checks/sensitivity/bridge。
- [ ] `firm_green_finance_policy_run` 或对应模板可跑。

### Artifact 层

- [ ] 每次 run 都有 `artifact_manifest.json`。
- [ ] 每次 run 都有 `reviewer_risk.json`。
- [ ] 每次 run 都有 `run_log.md`。
- [ ] 每个主要估计器都有 raw output。
- [ ] 每个 workflow 都有主表、诊断表、关键图、方法说明。

### Test 层

- [ ] `make smoke` 通过。
- [ ] `make smoke-did` 通过。
- [ ] `make smoke-psm-did` 通过。
- [ ] `make smoke-spatial` 通过。
- [ ] `make smoke-frontier` 通过。
- [ ] `make smoke-mechanism-threshold` 通过。
- [ ] 无 Stata/R 环境下 Python smoke 仍通过。
- [ ] 有 Stata/R 环境下 integration smoke 可跑。

### Docs 层

- [ ] 所有 docs 文件存在。
- [ ] 每个 docs 都有 When to use / Required columns / Estimators / Diagnostics / Reviewer risks。
- [ ] 材料入口 URL 都集中在 docs 或 data_catalogs 里。
- [ ] 小模型 agent 读 docs 后不会把 TWFE、PSM、机制、DEA、SDM 结果乱吹。

---

## 14. 维护备注

- 优先让结果“少但稳”，不要让模型“多但虚”。
- 后端 adapter 不可用不是失败；无诊断、无风险提示、无 artifact 才是失败。
- 对科研教师最有价值的是：主识别稳、诊断全、表图规范、风险诚实。
- 对小模型 agent 最有价值的是：明确 contract、明确禁止乱吹、明确何时跳过、明确下一步修复。
# TODO.md — skill4econ repo-local 能力包加固计划

> 目标：把 `D:/myproject/econpaper/skill4econ` 从“功能可跑 + smoke 通过”推进到“agent 可稳定调用、失败语义可信、论文审稿 artifact 可验证”的能力包。
> 使用方式：本文件直接放到仓库根目录 `TODO.md`。Codex 按 Milestone / Phase 分 PR 执行。每个 Phase 都必须有输入、输出、验收标准和 Definition of Done。
> 总原则：**先加固 contract / artifact / failure semantics，再扩展模型。不要为了通过 smoke 降低断言。**

---

## 0. Repo 假设和统一命令

### 0.1 仓库位置

```text
D:/myproject/econpaper/skill4econ
```

所有路径默认相对仓库根目录。

### 0.2 官方调用入口

```bash
conda run -n base python -m skill4econ.cli run --engine python --method METHOD --spec SPEC --run
conda run -n base python -m skill4econ.cli workflow --name WORKFLOW --spec SPEC --run
conda run -n base python -m skill4econ.cli list
```

### 0.3 Windows-first 约束

- 不允许把 `make` 作为唯一官方入口。
- 可以保留 `Makefile`，但所有 smoke / validation 必须有 Python CLI 等价入口。
- 所有新增 smoke 命令必须可在 Windows `conda run -n base python ...` 下执行。

### 0.4 当前材料入口

Codex 每轮 PR 开始前先读这些材料：

```text
docs/KNOWN_BUGS.md
README.md
skill4econ/cli.py 或 skill4econ/cli/__init__.py
skill4econ/core/
skill4econ/contracts/
skill4econ/diagnostics/
skill4econ/workflows/
tests/
tests/fixtures/
tests/fixtures/spatial/
```

若实际文件名和上面不同，先用下面命令定位，不要创建平行重复实现：

```bash
rg "RunContext|reviewer_risk|artifact_manifest|run_config_resolved|run_log" .
rg "did_paper_run|psm_did_policy_run|spatial_spillover_run" .
rg "spatial_exposure_did|spatial_w_sensitivity|spatial_se_comparison" .
rg "SPATIAL_W_MISSING|SPATIAL_SE_NOT_USED|W_SENSITIVITY_SIGN_FLIP" .
```

---

## 1. 不可违反的硬规则

### 1.1 禁止事项

- [ ] 不允许 silent fallback。
- [ ] 不允许后端缺失时伪造成功结果。
- [ ] 不允许 rank deficient / not identified / empty support 时悄悄换模型。
- [ ] 不允许 parser 读取旧 artifact 后当作本轮结果。
- [ ] 不允许生成看起来完整但语义是假的 `model_table`。
- [ ] 不允许 workflow 顶层吞掉子模块 `failed` / `skipped`。
- [ ] 不允许把 `W * treatment` 叫作 structural indirect effect。
- [ ] 不允许把 spatial cutoff HAC sensitivity 当完整 Conley / 成熟空间面板推断。
- [ ] 不允许把 SAR/SEM/SDM adapter-only 状态宣传成真实结构模型已完成。
- [ ] 不允许把 TWFE-only staggered DID 标成 paper-ready 主估计。
- [ ] 不允许 unregistered reviewer risk code。
- [ ] 不允许为了过 smoke 删除 fixture、弱化断言、跳过核心测试。
- [ ] 不允许把 notebook 作为能力包主入口。
- [ ] 不允许新增依赖但不做 missing_dependency 测试。
- [ ] 不允许要求联网才能跑本地 smoke。

### 1.2 统一输出硬约束

每个 `run` 和 `workflow` 成功写出 run 目录后，至少必须包含：

```text
RUN_DIR/
  manifest.json
  audit.json
  reviewer_risk.json
  artifact_manifest.json
  run_config_resolved.json
  run_log.txt
  model_table.json 或 model_table.csv
  status.json
```

如果某方法本身不产生模型表，必须仍然输出空表或诊断表，并在 `artifact_manifest.json` 标明 `role=diagnostic` 或 `role=adapter_only`，不得缺省消失。

### 1.3 统一状态语义

建议统一枚举：

```text
success
success_with_warnings
partial_success
skipped
failed
```

最低字段：

```json
{
  "status": "success_with_warnings",
  "method_or_workflow": "spatial_spillover_run",
  "run_id": "...",
  "main_claim_available": false,
  "claim_level": "sensitivity_only",
  "paper_readiness": "supplementary_only",
  "primary_failure_reason": null,
  "skipped_reason": null,
  "missing_dependencies": [],
  "risk_codes": ["SPATIAL_SE_NOT_USED"],
  "run_dir": "..."
}
```

### 1.4 Claim level 统一枚举

新增或固化：

```text
main_estimate
diagnostic
sensitivity_only
adapter_only
exploratory_only
failed
skipped
```

### 1.5 Paper readiness 统一枚举

新增或固化：

```text
paper_ready
supplementary_only
exploratory_only
not_for_claim
not_available
```

### 1.6 Process exit code 建议

不要让 artifact 写不出来。建议规则：

- 默认 `run/workflow --run`：只要 CLI 成功处理并写出完整 contract，即使 analytic status 是 `skipped` / `failed`，进程也可以返回 0。
- `--strict`：analytic status 为 `failed`、主 claim 不可用、contract 不合法时返回非 0。
- `validate-run` / `validate-method` / `validate-workflow`：contract 不合法必须返回非 0。
- CLI 参数错误、spec 缺失、内部异常、artifact 写入失败：必须返回非 0。

如果现有项目已有明确 exit code 约定，不要无测试地改；先把约定写进 `docs/ARTIFACT_CONTRACT.md`。

---

## 2. 推荐 PR 顺序总览

### P0：必须先做

- [ ] Phase P0-0：建立 baseline 和 Codex runbook。
- [ ] Phase P0-1：统一 schemas、claim level、paper readiness。
- [ ] Phase P0-2：实现 `validate-run` / `validate-method` / `validate-workflow`。
- [ ] Phase P0-3：实现 Windows-first smoke CLI。
- [ ] Phase P0-4：给三条旗舰 workflow 做 golden-run 验收。
- [ ] Phase P0-5：补 dependency-gated / parser failure / no-fallback 测试矩阵。

### P1：做扎实，不扩面

- [ ] Phase P1-1：DID 输出硬化：estimand、support、aggregation、TWFE role。
- [ ] Phase P1-2：PSM/IPW 输出硬化：ESS、extreme weights、trimming、overlap 降级。
- [ ] Phase P1-3：空间 reduced-form 输出硬化：claim boundary、W sensitivity、SE sensitivity。
- [ ] Phase P1-4：文档边界机器化：KNOWN_BUGS 与 run artifact 一致。

### P2：后续扩展

- [ ] Phase P2-1：真实 SAR/SEM/SDM 后端接入。
- [ ] Phase P2-2：自动 W grid 生成：distance cutoff、kNN、ring、row-standardized variants。
- [ ] Phase P2-3：更多 workflow / 图表 / 自动 appendix。

---

# Milestone P0：可信 contract / 可信失败 / 可信 artifact

---

## Phase P0-0：Baseline 快照和 Codex runbook

### 目标

在任何重构前固定当前状态，避免 Codex 后续 PR 误删能力或降低测试标准。

### 输入

```text
当前仓库
已有 docs/KNOWN_BUGS.md
已有 smoke tests
已有 spatial fixtures
```

### 需要修改或新增的文件

```text
TODO.md
README.md                         # 只补入口，不大改
scripts/ 或 skill4econ/devtools/    # 如已有 smoke runner，优先复用
docs/CODEX_RUNBOOK.md              # 新增
```

### 任务

- [ ] 新增 `docs/CODEX_RUNBOOK.md`。
- [ ] 记录当前官方命令。
- [ ] 记录当前已知 smoke 基线：
  - `spatial` 专项 pytest：预期 15 passed。
  - 全量 smoke pytest：预期 32 passed。
  - 全量 CLI smoke runner：预期 `{"status":"ok","checks":43}`。
- [ ] 记录 Windows 无 `make` 的事实：`make` 不是官方必需入口。
- [ ] 记录 Codex 每轮 PR 必须运行的命令模板。

### 建议命令

```bash
cd /d D:\myproject\econpaper\skill4econ
conda run -n base python -m skill4econ.cli list
conda run -n base python -m pytest tests -q
```

如果现有 CLI smoke runner 命令已存在，把实际命令写入 `docs/CODEX_RUNBOOK.md`。

### 输出

```text
docs/CODEX_RUNBOOK.md
```

### Definition of Done

- [ ] `docs/CODEX_RUNBOOK.md` 明确列出 baseline、官方入口、Windows 约束。
- [ ] 没有新增模型功能。
- [ ] 没有改动现有测试断言。
- [ ] `python -m skill4econ.cli list` 可运行。

---

## Phase P0-1：统一 schemas、claim_level、paper_readiness

### 目标

让所有 method/workflow 的输出语义可机器验证。先定义 contract，再改实现。

### 输入

```text
现有 manifest/audit/reviewer_risk/artifact_manifest/model_table 输出
现有 reviewer_risk code registry
现有 docs/KNOWN_BUGS.md
```

### 需要修改或新增的文件

优先使用现有同职责文件；若不存在，再新增：

```text
skill4econ/contracts/__init__.py
skill4econ/contracts/risk_registry.py
skill4econ/contracts/claim_levels.py
skill4econ/contracts/run_status.py
skill4econ/contracts/schemas/run_contract.schema.json
skill4econ/contracts/schemas/status.schema.json
skill4econ/contracts/schemas/manifest.schema.json
skill4econ/contracts/schemas/audit.schema.json
skill4econ/contracts/schemas/reviewer_risk.schema.json
skill4econ/contracts/schemas/artifact_manifest.schema.json
skill4econ/contracts/schemas/model_table.schema.json
skill4econ/core/context.py
skill4econ/core/manifest.py
skill4econ/core/artifacts.py
tests/contracts/test_claim_levels.py
tests/contracts/test_risk_registry.py
tests/contracts/test_schemas.py
docs/ARTIFACT_CONTRACT.md
```

### 接口要求

新增 Python-level API：

```python
from skill4econ.contracts.claim_levels import ClaimLevel, PaperReadiness
from skill4econ.contracts.run_status import RunStatus
from skill4econ.contracts.risk_registry import validate_risk_codes
```

最低行为：

```python
validate_risk_codes(["SPATIAL_W_MISSING"])  # pass
validate_risk_codes(["FAKE_NEW_CODE"])      # raise / return invalid
```

### schema 最低字段

`status.json` 必须包含：

```json
{
  "status": "success_with_warnings",
  "method_or_workflow": "...",
  "run_id": "...",
  "engine": "python|stata|r|mixed",
  "claim_level": "diagnostic",
  "paper_readiness": "supplementary_only",
  "main_claim_available": false,
  "primary_failure_reason": null,
  "skipped_reason": null,
  "missing_dependencies": [],
  "risk_codes": []
}
```

`artifact_manifest.json` 中每个 artifact 至少包含：

```json
{
  "path": "tables/example.csv",
  "type": "table|figure|json|log|model_table|diagnostic|other",
  "role": "main_result|diagnostic|sensitivity|audit|adapter_only|log",
  "required": true,
  "producer": "method_or_workflow_name",
  "exists": true
}
```

`reviewer_risk.json` 每个风险至少包含：

```json
{
  "code": "SPATIAL_SE_NOT_USED",
  "severity": "info|warning|high|fatal",
  "scope": "did|psm|spatial|workflow|adapter|inference",
  "message": "...",
  "claim_degradation": "none|supplementary_only|not_for_claim|failed"
}
```

### 必须固化的风险码

以下 code 不得丢失，必须在 registry 中可验证：

```text
CONTROL_GROUP_CONTAMINATED
EXPOSURE_CONTROL_DEFINITION_WEAK
SPATIAL_W_MISSING
SPATIAL_W_HAS_ISLANDS
SPATIAL_SE_NOT_USED
INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION
W_SENSITIVITY_SIGN_FLIP
```

建议同时补充但不强制一次完成：

```text
TWFE_STAGGERED_NOT_MAIN
DID_INSUFFICIENT_COHORT_SUPPORT
DID_EVENT_TIME_SUPPORT_WEAK
PSM_OVERLAP_WEAK
IPW_EXTREME_WEIGHTS
IPW_LOW_EFFECTIVE_SAMPLE_SIZE
BACKEND_MISSING_DEPENDENCY
BACKEND_PARSE_FAILED
RANK_DEFICIENT_DESIGN
MODEL_NOT_IDENTIFIED
```

### 验收命令

```bash
conda run -n base python -m pytest tests/contracts -q
```

### Definition of Done

- [ ] 所有 schema 可被测试加载。
- [ ] 所有 enum 有测试。
- [ ] 未注册 risk code 会失败。
- [ ] `docs/ARTIFACT_CONTRACT.md` 解释 status、claim_level、paper_readiness。
- [ ] 不要求所有方法一次性完全迁移，但新增 contract 必须向后兼容当前 smoke。

---

## Phase P0-2：实现全局 contract verifier CLI

### 目标

新增机器可执行验收器，任何 run/workflow 输出都能被独立判定是否合法。

### 输入

```text
Phase P0-1 schemas
已有 run output directories
已有 manifest/audit/reviewer_risk/artifact_manifest/model_table
```

### 需要修改或新增的文件

```text
skill4econ/cli.py 或 skill4econ/cli/__init__.py
skill4econ/validation/__init__.py
skill4econ/validation/contract_verifier.py
skill4econ/validation/schema_loader.py
skill4econ/validation/report.py
tests/validation/test_contract_verifier.py
tests/fixtures/runs/valid_minimal/
tests/fixtures/runs/invalid_missing_artifact/
tests/fixtures/runs/invalid_unregistered_risk/
tests/fixtures/runs/invalid_inconsistent_status/
docs/ARTIFACT_CONTRACT.md
```

### 新增 CLI 接口

```bash
conda run -n base python -m skill4econ.cli validate-run --run-dir RUN_DIR
conda run -n base python -m skill4econ.cli validate-run --run-dir RUN_DIR --strict
conda run -n base python -m skill4econ.cli validate-method --engine python --method METHOD --spec SPEC --run
conda run -n base python -m skill4econ.cli validate-workflow --name WORKFLOW --spec SPEC --run
```

### `validate-run` 输入输出

输入：

```text
--run-dir RUN_DIR
--strict optional
```

输出：

```text
stdout: concise validation summary
RUN_DIR/validation_report.json
exit code 0/1
```

`validation_report.json` 最低格式：

```json
{
  "status": "passed|failed",
  "strict": true,
  "run_dir": "...",
  "errors": [],
  "warnings": [],
  "checked_files": [
    "manifest.json",
    "audit.json",
    "reviewer_risk.json",
    "artifact_manifest.json",
    "run_config_resolved.json",
    "run_log.txt",
    "status.json"
  ]
}
```

### verifier 必须检查

- [ ] 必需文件存在。
- [ ] JSON 可解析。
- [ ] schema 合法。
- [ ] `reviewer_risk.json` 中所有 code 已注册。
- [ ] `artifact_manifest.json` 中声明的 `required=true` 文件真实存在。
- [ ] `status.json` 的 `risk_codes` 和 `reviewer_risk.json` 一致。
- [ ] `status=success` 时不得有 fatal risk。
- [ ] `main_claim_available=true` 时不得是 `adapter_only` / `sensitivity_only` / `failed` / `skipped`。
- [ ] `paper_readiness=paper_ready` 时不得含 claim_degradation 到 `not_for_claim` 的 risk。
- [ ] `missing_dependencies` 非空时不得 `paper_readiness=paper_ready`。
- [ ] workflow 的子模块 failed/skipped 必须反映到 workflow 顶层 summary。
- [ ] model_table 的 estimator/backend/spec 与 audit 中记录一致；无法比对时至少 warning。
- [ ] `run_config_resolved.json` 必须包含可重跑所需 spec/config 信息。
- [ ] `manifest.json` 或等价字段必须包含 rerun command。

### `validate-method` 行为

- 调用 method。
- 拿到本轮 run_dir。
- 自动执行 `validate-run`。
- 输出 validation summary。

### `validate-workflow` 行为

- 调用 workflow。
- 拿到本轮 run_dir。
- 自动执行 `validate-run`。
- workflow 中每个子 run 若有独立 run_dir，也必须递归验证。

### 验收命令

```bash
conda run -n base python -m pytest tests/validation -q
conda run -n base python -m skill4econ.cli validate-run --run-dir tests/fixtures/runs/valid_minimal
conda run -n base python -m skill4econ.cli validate-run --run-dir tests/fixtures/runs/invalid_missing_artifact --strict
```

### Definition of Done

- [ ] valid fixture 通过。
- [ ] missing artifact fixture 失败。
- [ ] unregistered risk fixture 失败。
- [ ] inconsistent status fixture 失败。
- [ ] `validate-method` 和 `validate-workflow` 可从 CLI 调用。
- [ ] `--strict` 行为有测试。
- [ ] 不改变原有 `run` / `workflow` 的主接口。

---

## Phase P0-3：Windows-first smoke CLI

### 目标

把 smoke 从 make/零散 pytest 变成 agent 可调用的 Python CLI。

### 输入

```text
现有 pytest smoke
现有 CLI smoke runner
Phase P0-2 validate-run
```

### 需要修改或新增的文件

```text
skill4econ/cli.py 或 skill4econ/cli/__init__.py
skill4econ/devtools/__init__.py
skill4econ/devtools/smoke.py
tests/devtools/test_smoke_cli.py
docs/CODEX_RUNBOOK.md
```

### 新增 CLI 接口

```bash
conda run -n base python -m skill4econ.cli smoke --suite all
conda run -n base python -m skill4econ.cli smoke --suite all --strict
conda run -n base python -m skill4econ.cli smoke --suite spatial --strict
conda run -n base python -m skill4econ.cli smoke --suite did --strict
conda run -n base python -m skill4econ.cli smoke --suite psm --strict
```

### suite 定义

```text
all       = 当前全部 CLI smoke + contract verifier
spatial   = spatial weights / audit / Moran / exposure DID / SE comparison / W sensitivity
DID       = did_paper_run + DID methods smoke
psm       = psm_overlap_balance + psm_ipw_match + psm_did_policy_run
contracts = schema + validation-only smoke
```

### 输出

stdout 必须最终打印一行 JSON summary：

```json
{"status":"ok","suite":"all","checks":43,"failed":0,"skipped":0}
```

同时写出：

```text
artifacts/smoke/latest_smoke_report.json
```

或写入临时 run output，但路径必须稳定可被 docs 引用。

### 验收命令

```bash
conda run -n base python -m pytest tests/devtools -q
conda run -n base python -m skill4econ.cli smoke --suite spatial --strict
conda run -n base python -m skill4econ.cli smoke --suite all --strict
```

### Definition of Done

- [ ] 不需要 `make`。
- [ ] smoke CLI 在 Windows shell 可运行。
- [ ] strict 模式会调用 contract verifier。
- [ ] 失败时返回非 0。
- [ ] smoke report 记录每个 check 名称、命令、status、run_dir、validation result。
- [ ] 保留或兼容当前 `{"status":"ok","checks":43}` 语义，不无故减少 check 数。

---

## Phase P0-4：三条旗舰 workflow 的 golden-run 验收

### 目标

从“不会炸”升级为“关键计量语义和 artifact 可验证”。只做三条主线：DID、PSM-DID、空间 reduced-form。

### 输入

```text
现有 did_paper_run
现有 psm_did_policy_run
现有 spatial_spillover_run
现有 fixture generators
现有 spatial fixtures
Phase P0-2 validate-workflow
```

### 需要修改或新增的文件

```text
tests/golden/test_did_paper_run_golden.py
tests/golden/test_psm_did_policy_run_golden.py
tests/golden/test_spatial_spillover_run_golden.py
tests/golden/expected/did_paper_run/*.json
tests/golden/expected/psm_did_policy_run/*.json
tests/golden/expected/spatial_spillover_run/*.json
tests/fixtures/specs/did_paper_run_clean.json
tests/fixtures/specs/did_paper_run_twfe_only_staggered.json
tests/fixtures/specs/did_paper_run_rank_deficient.json
tests/fixtures/specs/psm_did_policy_run_good_overlap.json
tests/fixtures/specs/psm_did_policy_run_poor_overlap.json
tests/fixtures/specs/psm_did_policy_run_extreme_weights.json
tests/fixtures/specs/spatial_spillover_direct_only.json
tests/fixtures/specs/spatial_spillover_indirect_only.json
tests/fixtures/specs/spatial_spillover_w_sign_flip.json
tests/fixtures/specs/spatial_spillover_contaminated_controls.json
```

如已有同类 fixtures，不要重复造；改用已有 fixture 并补 expected contract。

### DID golden cases

#### Case DID-G1：clean modern DID

输入：

```text
tests/fixtures/specs/did_paper_run_clean.json
```

预期：

- [ ] workflow status 是 `success` 或 `success_with_warnings`。
- [ ] 有 DID design diagnostic。
- [ ] 有 modern DID 路由结果或明确 backend status。
- [ ] `twfe_role` 不是默认主估计，除非设计确实允许。
- [ ] `model_table` 有主估计行。
- [ ] `artifact_manifest` 所列 required 文件存在。
- [ ] `validate-workflow` 通过。

#### Case DID-G2：TWFE-only staggered

预期：

- [ ] 不得 `paper_readiness=paper_ready`。
- [ ] 必须触发或等价标记 `TWFE_STAGGERED_NOT_MAIN`。
- [ ] `main_claim_available=false` 或 `claim_level=sensitivity_only/comparison_only`。
- [ ] audit 明确说明 TWFE 仅作 comparison。

#### Case DID-G3：rank deficient

预期：

- [ ] status 是 `failed` 或 `skipped`，不能 success。
- [ ] 必须有 `RANK_DEFICIENT_DESIGN` 或等价风险。
- [ ] 不得生成主估计 model_table。
- [ ] `validate-workflow --strict` 必须失败。

### PSM-DID golden cases

#### Case PSM-G1：good overlap

预期：

- [ ] 有 overlap table。
- [ ] 有 balance before/after table。
- [ ] 有 weight diagnostics。
- [ ] 有 DRDID 对照或明确 missing dependency。
- [ ] `main_claim_available` 根据诊断结果合理设置。

#### Case PSM-G2：poor overlap

预期：

- [ ] 必须触发 `PSM_OVERLAP_WEAK` 或等价风险。
- [ ] 不得 `paper_readiness=paper_ready`。
- [ ] 必须输出 retained sample / common support 信息。

#### Case PSM-G3：extreme weights

预期：

- [ ] 必须触发 `IPW_EXTREME_WEIGHTS` 或等价风险。
- [ ] 必须输出 max/p95/p99 weights。
- [ ] 必须输出 ESS。
- [ ] trimming sensitivity 缺失时必须 warning。

### Spatial golden cases

#### Case SP-G1：direct-only effect

预期：

- [ ] `spatial_spillover_run` 路由到 `spatial_exposure_did`，不得回退老 `spatial_did_reduced_form`。
- [ ] local treatment coefficient 写入 `did_common_output.json`。
- [ ] spillover / exposure effect 分表。
- [ ] 不把 exposure coefficient 写成 structural indirect effect。

#### Case SP-G2：indirect/exposure-only effect

预期：

- [ ] 输出 reduced-form exposure estimate。
- [ ] 必须触发 `INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION`，除非真实 structural impact decomposition 已完成。
- [ ] `claim_level` 为 `exploratory_only` 或 `sensitivity_only`，不得 `main_estimate`。

#### Case SP-G3：W sign flip

预期：

- [ ] `spatial_w_sensitivity` 输出 `tables/w_sensitivity_main_effects.csv`。
- [ ] 输出 `figures/w_sensitivity_forest.png`。
- [ ] 必须触发 `W_SENSITIVITY_SIGN_FLIP`。
- [ ] workflow 顶层 claim strength 降级。

#### Case SP-G4：contaminated controls

预期：

- [ ] 必须触发 `CONTROL_GROUP_CONTAMINATED`。
- [ ] near/far controls 或 buffer deletion artifact 存在。
- [ ] 控制组污染不得被吞掉。

### 验收命令

```bash
conda run -n base python -m pytest tests/golden -q
conda run -n base python -m skill4econ.cli smoke --suite all --strict
```

### Definition of Done

- [ ] 三条 workflow 至少各有 3 个 golden cases。
- [ ] 每个 golden case 检查 status、risk code、claim_level、paper_readiness、artifact existence。
- [ ] 至少一个 case 验证 rank deficient / poor overlap / sign flip 这类负路径。
- [ ] 所有 golden run 都通过 `validate-workflow`。
- [ ] 没有新增真实模型范围，只加固现有能力。

---

## Phase P0-5：dependency-gated / parser failure / no-fallback 测试矩阵

### 目标

证明 wrapper 和 adapter 不会假成功，不会 silent fallback，不会 parse 旧结果。

### 输入

```text
现有 Python/Stata/R wrappers
现有 dependency-gated adapters
Phase P0-2 contract verifier
```

### 需要修改或新增的文件

```text
tests/adapters/test_dependency_gates.py
tests/adapters/test_parser_failure.py
tests/adapters/test_no_silent_fallback.py
tests/fixtures/adapters/fake_backend_success/
tests/fixtures/adapters/fake_backend_nonzero_exit/
tests/fixtures/adapters/fake_backend_empty_output/
tests/fixtures/adapters/fake_backend_malformed_output/
skill4econ/adapters/ 或 skill4econ/wrappers/  # 复用现有路径
skill4econ/contracts/risk_registry.py
```

### 必测场景

- [ ] Rscript 不存在：`spatial_spdep_lisa` 必须 `missing_dependency` / `skipped`。
- [ ] Rscript 存在但 spdep 不存在：必须 `missing_dependency` / `skipped`。
- [ ] Stata 不存在：Stata wrapper 必须 `missing_dependency` / `skipped`。
- [ ] Stata 存在但包缺失：必须 `missing_dependency` / `skipped`。
- [ ] 后端进程非 0：必须 `failed`，不得读取旧 artifact。
- [ ] 后端 stdout 有成功字样但结果文件缺失：必须 `failed`。
- [ ] parser 输入为空：必须 `BACKEND_PARSE_FAILED`。
- [ ] parser 输入 malformed：必须 `BACKEND_PARSE_FAILED`。
- [ ] ppmlhdfe 缺失：不得 fallback 到 local poisson。
- [ ] SAR/SEM/SDM backend 缺失：只能 `adapter_only` / `missing_dependency`，不得宣称结构模型完成。

### 实现建议

- 使用 monkeypatch / fake executable / temporary PATH 模拟依赖存在与缺失。
- 每个 adapter 本轮运行前清空或隔离 run_dir。
- parser 必须只读取本轮 run_dir 内 artifact。
- artifact 文件名尽量含 run_id 或写入 manifest provenance，防止读旧文件。

### 验收命令

```bash
conda run -n base python -m pytest tests/adapters -q
conda run -n base python -m skill4econ.cli smoke --suite all --strict
```

### Definition of Done

- [ ] dependency missing 不假成功。
- [ ] parser failure 不假成功。
- [ ] no silent fallback 有测试。
- [ ] workflow 顶层能反映子模块 skipped/failed。
- [ ] 所有 adapter failure 都写出合法 `status.json`、`reviewer_risk.json`、`run_log.txt`。

---

# Milestone P1：把现有 DID / PSM / 空间 reduced-form 做成真实科研最小可用

---

## Phase P1-1：DID 输出硬化

### 目标

DID 结果必须讲清楚估计对象、control group、support、aggregation 和 TWFE 角色。不要只输出系数。

### 输入

```text
现有 did_paper_run
现有 DID design diagnostics
现有 TWFE / event study / modern DID routing
现有 common DID schema
```

### 需要修改或新增的文件

```text
skill4econ/workflows/did_paper_run.py
skill4econ/diagnostics/did_design.py
skill4econ/methods/did_*.py 或现有 DID wrappers
skill4econ/contracts/did_schema.py
skill4econ/contracts/risk_registry.py
tests/did/test_did_claim_contract.py
tests/did/test_did_support_diagnostics.py
tests/golden/test_did_paper_run_golden.py
docs/DID_CONTRACT.md
```

### 必须输出字段

在 DID common output 或 `status.json` / `audit.json` 中加入：

```json
{
  "estimand_scope": "ATT(g,t)|event_time_ATT|simple_ATT|TWFE_comparison|unknown",
  "control_group": "never_treated|not_yet_treated|mixed|unknown",
  "cohort_support": {},
  "event_time_support": {},
  "anticipation_periods": 0,
  "aggregation_method": "cohort_time|event_time|calendar_time|simple|none",
  "twfe_role": "main|comparison_only|forbidden_for_main|not_used",
  "cluster_variable": "...",
  "cluster_count": 0,
  "pretrend_test_role": "diagnostic_only|not_used"
}
```

### 风险规则

- [ ] staggered adoption + TWFE-only：触发 `TWFE_STAGGERED_NOT_MAIN`。
- [ ] cohort support 太弱：触发 `DID_INSUFFICIENT_COHORT_SUPPORT`。
- [ ] event-time support 太弱：触发 `DID_EVENT_TIME_SUPPORT_WEAK`。
- [ ] cluster 数过少：触发 cluster warning。
- [ ] modern DID backend 缺失：`missing_dependency`，不得回退成 TWFE 主估计。
- [ ] TWFE comparison 可以输出，但不得自动 `paper_ready`。

### 验收命令

```bash
conda run -n base python -m pytest tests/did -q
conda run -n base python -m pytest tests/golden/test_did_paper_run_golden.py -q
conda run -n base python -m skill4econ.cli smoke --suite did --strict
```

### Definition of Done

- [ ] DID output 明确 estimand。
- [ ] TWFE role 明确。
- [ ] support diagnostics 可机器读取。
- [ ] 现代 DID 缺后端不 fallback。
- [ ] DID golden cases 全过。
- [ ] docs 说明哪些结果可主张，哪些只能 comparison。

---

## Phase P1-2：PSM/IPW 输出硬化

### 目标

PSM/IPW 不能只给匹配结果；必须输出 overlap、balance、ESS、extreme weight 和 trimming sensitivity。

### 输入

```text
现有 psm_overlap_balance
现有 psm_ipw_match
现有 psm_did_policy_run
现有 DRDID 对照接入
```

### 需要修改或新增的文件

```text
skill4econ/diagnostics/psm_overlap_balance.py
skill4econ/methods/psm_ipw_match.py
skill4econ/workflows/psm_did_policy_run.py
skill4econ/contracts/psm_schema.py
skill4econ/contracts/risk_registry.py
tests/psm/test_overlap_balance_contract.py
tests/psm/test_ipw_weight_diagnostics.py
tests/psm/test_psm_claim_degradation.py
tests/golden/test_psm_did_policy_run_golden.py
docs/PSM_IPW_CONTRACT.md
```

### 必须输出 artifacts

```text
tables/psm_overlap_summary.csv
tables/psm_balance_before_after.csv
tables/ipw_weight_diagnostics.csv
tables/ipw_trimming_sensitivity.csv      # 若未实现，必须有 explicit warning artifact
figures/ps_overlap_density.png 或等价图
reviewer_risk.json
```

### 必须输出字段

```json
{
  "overlap_status": "pass|weak|fail|not_checked",
  "balance_status": "pass|weak|fail|not_checked",
  "max_standardized_mean_difference_before": 0.0,
  "max_standardized_mean_difference_after": 0.0,
  "effective_sample_size_treated": 0.0,
  "effective_sample_size_control": 0.0,
  "max_weight": 0.0,
  "p95_weight": 0.0,
  "p99_weight": 0.0,
  "trim_rules_evaluated": [],
  "retained_share_treated": 0.0,
  "retained_share_control": 0.0
}
```

### 风险规则

- [ ] overlap fail：触发 `PSM_OVERLAP_WEAK` 或更强风险，`paper_readiness != paper_ready`。
- [ ] SMD after 超阈值：触发 balance risk。
- [ ] ESS 太低：触发 `IPW_LOW_EFFECTIVE_SAMPLE_SIZE`。
- [ ] p99 或 max weight 极端：触发 `IPW_EXTREME_WEIGHTS`。
- [ ] trimming sensitivity 未跑：触发 warning，不得静默缺失。
- [ ] poor overlap 下不得输出强主结论。

### 验收命令

```bash
conda run -n base python -m pytest tests/psm -q
conda run -n base python -m pytest tests/golden/test_psm_did_policy_run_golden.py -q
conda run -n base python -m skill4econ.cli smoke --suite psm --strict
```

### Definition of Done

- [ ] PSM/IPW output 有 ESS 和 weight diagnostics。
- [ ] poor overlap 自动 claim 降级。
- [ ] extreme weight 自动 risk。
- [ ] trimming sensitivity 有 artifact 或 explicit warning。
- [ ] PSM golden cases 全过。

---

## Phase P1-3：空间 reduced-form 输出硬化

### 目标

空间 reduced-form 可以作为诊断/敏感性/探索性结果，但必须严禁被误读为结构溢出分解。

### 输入

```text
spatial_weights_factory
spatial_w_audit
spatial_moran_preflight
spatial_spdep_lisa
spatial_exposure_did
spatial_se_comparison
spatial_w_sensitivity
spatial_spillover_run
```

### 需要修改或新增的文件

```text
skill4econ/diagnostics/spatial_weights_factory.py
skill4econ/diagnostics/spatial_w_audit.py
skill4econ/diagnostics/spatial_moran_preflight.py
skill4econ/diagnostics/spatial_spdep_lisa.py
skill4econ/methods/spatial_exposure_did.py
skill4econ/methods/spatial_se_comparison.py
skill4econ/methods/spatial_w_sensitivity.py
skill4econ/workflows/spatial_spillover_run.py
skill4econ/contracts/spatial_schema.py
skill4econ/contracts/risk_registry.py
tests/spatial/test_spatial_claim_boundaries.py
tests/spatial/test_spatial_w_missing.py
tests/spatial/test_spatial_se_sensitivity.py
tests/spatial/test_spatial_w_sensitivity.py
tests/golden/test_spatial_spillover_run_golden.py
docs/SPATIAL_REDUCED_FORM_CONTRACT.md
```

### 必须输出 claim boundary

`spatial_exposure_did` 输出必须包含：

```json
{
  "estimand_scope": "reduced_form_spatial_exposure",
  "is_structural_spillover_model": false,
  "has_impact_decomposition": false,
  "allowed_claim": "association between spatial exposure and outcome under specified W and controls",
  "forbidden_claims": [
    "structural indirect effect",
    "SAR/SEM/SDM impact decomposition",
    "policy spillover mechanism proven"
  ]
}
```

`spatial_panel_model_adapter` 在无真实后端时必须包含：

```json
{
  "claim_level": "adapter_only",
  "paper_readiness": "not_available",
  "main_claim_available": false,
  "backend_status": "missing_dependency|not_configured|not_run"
}
```

`spatial_se_comparison` 必须包含：

```json
{
  "claim_level": "sensitivity_only",
  "is_full_conley": false,
  "is_full_spatial_panel_inference": false
}
```

### 必须保持的输出文件

```text
tables/spatial_se_comparison.csv
figures/spatial_se_cutoff_sensitivity.png
tables/w_sensitivity_main_effects.csv
figures/w_sensitivity_forest.png
did_common_output.json
```

### 风险规则

- [ ] 权重缺失：`SPATIAL_W_MISSING`，不得误报 `SPATIAL_W_HAS_ISLANDS`。
- [ ] W 有 islands：`SPATIAL_W_HAS_ISLANDS`。
- [ ] 无坐标不能跑 spatial SE：`SPATIAL_SE_NOT_USED`。
- [ ] 无 impact decomposition 却出现 exposure/spillover 解释：`INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION`。
- [ ] W sensitivity sign flip：`W_SENSITIVITY_SIGN_FLIP`，workflow claim 降级。
- [ ] contaminated controls：`CONTROL_GROUP_CONTAMINATED`。
- [ ] weak exposure/control definition：`EXPOSURE_CONTROL_DEFINITION_WEAK`。

### 验收命令

```bash
conda run -n base python -m pytest tests/spatial -q
conda run -n base python -m pytest tests/golden/test_spatial_spillover_run_golden.py -q
conda run -n base python -m skill4econ.cli smoke --suite spatial --strict
```

### Definition of Done

- [ ] `spatial_spillover_run` 明确路由 `spatial_exposure_did`。
- [ ] exposure DID 不宣称 structural effect。
- [ ] SE comparison 明确 sensitivity-only。
- [ ] W sensitivity sign flip 触发风险并降级。
- [ ] 缺 W、W islands、contaminated controls 均有测试。
- [ ] spatial golden cases 全过。

---

## Phase P1-4：文档边界机器化

### 目标

`docs/KNOWN_BUGS.md` 中的限制必须同步进入 run artifact，不能只写给人看。

### 输入

```text
docs/KNOWN_BUGS.md
Phase P0/P1 新增 contract 字段
```

### 需要修改或新增的文件

```text
docs/KNOWN_BUGS.md
docs/ARTIFACT_CONTRACT.md
docs/DID_CONTRACT.md
docs/PSM_IPW_CONTRACT.md
docs/SPATIAL_REDUCED_FORM_CONTRACT.md
tests/docs/test_known_bugs_contract_alignment.py
skill4econ/contracts/known_gaps.py
```

### 必须覆盖的 known gaps

- [ ] R spdep 依赖缺失时只 skipped，不假成功。
- [ ] SAR/SEM/SDM 目前是 parser/contract，未真实跑 xsmle/splm 时 adapter-only。
- [ ] spatial SE 是 Python cutoff HAC sensitivity，不是完整 Conley/fixest。
- [ ] W grid 需要用户给 `weight_paths`；若尚未自动生成经济距离/kNN W，必须在 audit 中说明。
- [ ] local ppmlhdfe only；不得 fallback 到 local poisson。

### 验收命令

```bash
conda run -n base python -m pytest tests/docs -q
conda run -n base python -m skill4econ.cli smoke --suite all --strict
```

### Definition of Done

- [ ] docs 中每个 known gap 都有对应 artifact 字段或 risk code。
- [ ] artifact 中每个 adapter-only / sensitivity-only 状态都在 docs 中解释。
- [ ] `KNOWN_BUGS.md` 不再暗示 fallback。
- [ ] docs 测试能防止边界说明和机器输出脱节。

---

# Milestone P2：后续扩展，不得抢 P0/P1 之前做

---

## Phase P2-1：真实 SAR/SEM/SDM 后端接入

### 目标

把 `spatial_panel_model_adapter` 从 adapter contract 推进到真实可运行后端。未完成前不得宣传为空间结构模型完成。

### 输入

```text
spatial_panel_model_adapter
impact decomposition parser
Stata xsmle/spxtregress 或 R splm/spatialreg 后端设计
```

### 需要修改或新增的文件

```text
skill4econ/methods/spatial_panel_model_adapter.py
skill4econ/adapters/stata_spatial.py
skill4econ/adapters/r_spatial.py
skill4econ/contracts/spatial_structural_schema.py
tests/spatial_structural/test_backend_dependency.py
tests/spatial_structural/test_impact_decomposition_parser.py
tests/spatial_structural/test_structural_claim_readiness.py
docs/SPATIAL_STRUCTURAL_MODELS.md
```

### 必须实现

- [ ] 至少一个真实后端可运行。
- [ ] backend version/package audit。
- [ ] direct / indirect / total effects parser。
- [ ] impact decomposition artifact。
- [ ] backend missing 时仍然 `missing_dependency`。
- [ ] parser failure 时 `BACKEND_PARSE_FAILED`。
- [ ] 无 impact decomposition 时不得称 indirect effect。

### 验收命令

```bash
conda run -n base python -m pytest tests/spatial_structural -q
conda run -n base python -m skill4econ.cli smoke --suite spatial --strict
```

### Definition of Done

- [ ] 真实后端成功 case 通过。
- [ ] 缺后端 case 通过。
- [ ] parser malformed case 通过。
- [ ] claim_level 可从 `adapter_only` 升级为 `main_estimate` 只在真实后端 + impact decomposition 成功时发生。

---

## Phase P2-2：自动 W grid 生成

### 目标

减少用户手工提供 `weight_paths` 的负担，并把 W 选择变成默认审稿 artifact。

### 输入

```text
spatial_weights_factory
spatial_w_audit
spatial_w_sensitivity
已有 coordinate / distance / ring fixtures
```

### 需要修改或新增的文件

```text
skill4econ/diagnostics/spatial_weights_factory.py
skill4econ/methods/spatial_w_sensitivity.py
skill4econ/workflows/spatial_spillover_run.py
tests/spatial/test_auto_w_grid.py
tests/fixtures/spatial/w_grid_*.csv
docs/SPATIAL_W_GRID.md
```

### 新增 spec 字段建议

```json
{
  "w_grid": {
    "auto_generate": true,
    "methods": ["distance_cutoff", "knn", "ring"],
    "distance_cutoffs": [10, 25, 50],
    "knn_values": [4, 8, 12],
    "row_standardize": [true, false],
    "primary_w": "distance_cutoff_25_rowstd"
  }
}
```

### 必须输出

```text
tables/w_grid_audit.csv
tables/w_sensitivity_main_effects.csv
figures/w_sensitivity_forest.png
```

### 验收命令

```bash
conda run -n base python -m pytest tests/spatial/test_auto_w_grid.py -q
conda run -n base python -m skill4econ.cli smoke --suite spatial --strict
```

### Definition of Done

- [ ] 自动生成至少 distance cutoff 和 kNN W。
- [ ] 每个 W 都跑 audit。
- [ ] 每个 W 的 exposure summary 可追踪。
- [ ] primary W 和 robustness W 明确区分。
- [ ] sign/significance/effect magnitude instability 进入 reviewer_risk。

---

## Phase P2-3：更多 workflow / 图表 / appendix 自动化

### 目标

只有 P0/P1 全部完成后，才允许继续扩机制、门槛、效率前沿、自动 appendix。

### 禁止前置条件

以下未完成时不要做本 phase：

- [ ] contract verifier 未完成。
- [ ] golden workflow 未完成。
- [ ] dependency-gated 测试矩阵未完成。
- [ ] DID / PSM / spatial reduced-form claim boundary 未机器化。

### 可做方向

```text
mechanism_threshold_run hardening
efficiency_frontier_run hardening
auto appendix artifacts
auto reviewer response table
more publication-quality plots
```

### Definition of Done

- [ ] 新 workflow 必须从第一天就接入 status/claim_level/paper_readiness。
- [ ] 新 workflow 必须有 golden cases。
- [ ] 新 workflow 必须有 failure cases。
- [ ] 新 workflow 必须被 `smoke --suite all --strict` 覆盖。

---

# 3. 每个 PR 的固定交付格式

每个 Codex PR 必须在 PR 描述中填写：

```text
PR Phase: P0-2 / P1-1 / ...
Scope:
  - 修改了哪些路径
  - 没有做哪些超范围事项
Inputs:
  - 使用了哪些 fixtures/specs
Outputs:
  - 新增/修改了哪些 artifacts/contracts/docs
Commands Run:
  - conda run -n base python -m pytest ...
  - conda run -n base python -m skill4econ.cli smoke ...
Definition of Done:
  - [ ] 对应 phase 的 DoD 全部满足
Known Limitations:
  - ...
```

---

# 4. 每轮 Codex 执行检查清单

## 开工前

- [ ] 读 `TODO.md` 当前 phase。
- [ ] 读 `docs/CODEX_RUNBOOK.md`。
- [ ] 读 `docs/KNOWN_BUGS.md`。
- [ ] 用 `rg` 定位现有实现，避免平行造轮子。
- [ ] 跑或确认 baseline smoke。

## 开发中

- [ ] 优先改现有同职责文件。
- [ ] 新增字段必须有 schema。
- [ ] 新增 risk code 必须进 registry。
- [ ] 新增 CLI 必须有测试。
- [ ] 新增 artifact 必须进 `artifact_manifest.json`。
- [ ] 新增 known gap 必须进 docs 和 artifact。

## 收尾前

- [ ] 跑目标 phase 的 pytest。
- [ ] 跑相关 suite 的 smoke。
- [ ] strict 模式能过。
- [ ] 检查 run_dir 下 artifact 是否齐全。
- [ ] 检查 failed/skipped/warning 是否没有被 workflow 吞掉。
- [ ] 更新 docs。
- [ ] 不做无关格式化。

---

# 5. 一周内推荐锁定范围

如果只允许再做一周，按下面顺序做，不要扩展新模型：

1. [ ] P0-1 schemas / claim_level / paper_readiness。
2. [ ] P0-2 contract verifier。
3. [ ] P0-3 Windows-first smoke CLI。
4. [ ] P0-4 三条 workflow golden cases。
5. [ ] P0-5 dependency/no-fallback/parser failure 测试矩阵。
6. [ ] P1-1 DID claim boundary 的最小字段。
7. [ ] P1-2 PSM/IPW ESS + extreme weights + overlap 降级。
8. [ ] P1-3 spatial reduced-form claim boundary 机器化。

不建议这一周做：

- [ ] 新机制模型。
- [ ] 新门槛模型。
- [ ] 新效率前沿模型。
- [ ] 自动 appendix 大扩展。
- [ ] 真实 SAR/SEM/SDM 后端，除非 P0 已全部完成。
- [ ] 大规模重构目录结构。

---

# 6. 最终完成判定

当以下全部满足时，skill4econ 才能从“严肃原型”升级为“可托管论文主流程的 agent-callable 科研能力包”：

- [ ] 每个 method/workflow 都有稳定 CLI。
- [ ] 每个 run 都有 manifest/audit/model_table/reviewer_risk/artifact_manifest/rerun/status。
- [ ] 每个 run 都能通过 `validate-run`。
- [ ] 每个 workflow 都能通过 `validate-workflow`。
- [ ] smoke 有 Windows-first CLI。
- [ ] DID / PSM / spatial reduced-form 均有 golden success + failure cases。
- [ ] 缺依赖、rank deficient、不可识别、parser failure 都不会假成功。
- [ ] 所有风险码来自 registry。
- [ ] 所有 known gaps 进入 run artifact，而不只是写在 docs。
- [ ] spatial exposure DID 不被误读为 structural indirect effect。
- [ ] SAR/SEM/SDM 无真实后端时始终 adapter-only。
- [ ] TWFE-only staggered DID 不会 paper-ready。
- [ ] poor overlap / extreme weights / W sign flip 会自动降级 claim。
- [ ] `conda run -n base python -m skill4econ.cli smoke --suite all --strict` 通过。
