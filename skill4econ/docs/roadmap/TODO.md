# TODO.md — skill4econ repo-local 能力包加固计划

> 目标：把 `D:/myproject/EvoScientist/skill4econ` 从“功能可跑 + smoke 通过”推进到“agent 可稳定调用、失败语义可信、论文审稿 artifact 可验证”的能力包。  
> 使用方式：本文件直接放到仓库根目录 `TODO.md`。Codex 按 Milestone / Phase 分 PR 执行。每个 Phase 都必须有输入、输出、验收标准和 Definition of Done。  
> 总原则：**先加固 contract / artifact / failure semantics，再扩展模型。不要为了通过 smoke 降低断言。**

---

## 0. Repo 假设和统一命令

### 0.1 仓库位置

```text
D:/myproject/EvoScientist/skill4econ
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

- [x] 不允许 silent fallback。
- [x] 不允许后端缺失时伪造成功结果。
- [x] 不允许 rank deficient / not identified / empty support 时悄悄换模型。
- [x] 不允许 parser 读取旧 artifact 后当作本轮结果。
- [x] 不允许生成看起来完整但语义是假的 `model_table`。
- [x] 不允许 workflow 顶层吞掉子模块 `failed` / `skipped`。
- [x] 不允许把 `W * treatment` 叫作 structural indirect effect。
- [x] 不允许把 spatial cutoff HAC sensitivity 当完整 Conley / 成熟空间面板推断。
- [x] 不允许把 SAR/SEM/SDM adapter-only 状态宣传成真实结构模型已完成。
- [x] 不允许把 TWFE-only staggered DID 标成 paper-ready 主估计。
- [x] 不允许 unregistered reviewer risk code。
- [x] 不允许为了过 smoke 删除 fixture、弱化断言、跳过核心测试。
- [x] 不允许把 notebook 作为能力包主入口。
- [x] 不允许新增依赖但不做 missing_dependency 测试。
- [x] 不允许要求联网才能跑本地 smoke。

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

- [x] Phase P0-0：建立 baseline 和 Codex runbook。
- [x] Phase P0-1：统一 schemas、claim level、paper readiness。
- [x] Phase P0-2：实现 `validate-run` / `validate-method` / `validate-workflow`。
- [x] Phase P0-3：实现 Windows-first smoke CLI。
- [x] Phase P0-4：给三条旗舰 workflow 做 golden-run 验收（代表性 golden 已完成；完整 3×3 workflow 矩阵见 `docs/KNOWN_BUGS.md`）。
- [x] Phase P0-5：补 dependency-gated / parser failure / no-fallback 测试矩阵（核心 adapter/parser 路径已覆盖；全后端环境矩阵见 `docs/KNOWN_BUGS.md`）。

### P1：做扎实，不扩面

- [x] Phase P1-1：DID 输出硬化：estimand、support、aggregation、TWFE role。
- [x] Phase P1-2：PSM/IPW 输出硬化：ESS、extreme weights、trimming、overlap 降级。
- [x] Phase P1-3：空间 reduced-form 输出硬化：claim boundary、W sensitivity、SE sensitivity。
- [x] Phase P1-4：文档边界机器化：KNOWN_BUGS 与 run artifact 一致。

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

- [x] 新增 `docs/CODEX_RUNBOOK.md`。
- [x] 记录当前官方命令。
- [x] 记录当前已知 smoke 基线：
  - `pytest tests -q`：本轮 `51 passed`。
  - `smoke --suite all --strict`：本轮 `{"status":"ok","suite":"all","checks":44,"failed":0,"skipped":0}`。
  - 原全量 CLI smoke runner 语义保留：内部 `checks=43`。
- [x] 记录 Windows 无 `make` 的事实：`make` 不是官方必需入口。
- [x] 记录 Codex 每轮 PR 必须运行的命令模板。

### 建议命令

```bash
cd /d D:\myproject\EvoScientist\skill4econ
conda run -n base python -m skill4econ.cli list
conda run -n base python -m pytest tests -q
```

如果现有 CLI smoke runner 命令已存在，把实际命令写入 `docs/CODEX_RUNBOOK.md`。

### 输出

```text
docs/CODEX_RUNBOOK.md
```

### Definition of Done

- [x] `docs/CODEX_RUNBOOK.md` 明确列出 baseline、官方入口、Windows 约束。
- [x] 没有新增模型功能。
- [x] 没有改动现有测试断言。
- [x] `python -m skill4econ.cli list` 可运行。

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

- [x] 所有 schema 可被测试加载。
- [x] 所有 enum 有测试。
- [x] 未注册 risk code 会失败。
- [x] `docs/ARTIFACT_CONTRACT.md` 解释 status、claim_level、paper_readiness。
- [x] 不要求所有方法一次性完全迁移，但新增 contract 必须向后兼容当前 smoke。

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

- [x] 必需文件存在。
- [x] JSON 可解析。
- [x] schema 合法。
- [x] `reviewer_risk.json` 中所有 code 已注册。
- [x] `artifact_manifest.json` 中声明的 `required=true` 文件真实存在。
- [x] `status.json` 的 `risk_codes` 和 `reviewer_risk.json` 一致。
- [x] `status=success` 时不得有 fatal risk。
- [x] `main_claim_available=true` 时不得是 `adapter_only` / `sensitivity_only` / `failed` / `skipped`。
- [x] `paper_readiness=paper_ready` 时不得含 claim_degradation 到 `not_for_claim` 的 risk。
- [x] `missing_dependencies` 非空时不得 `paper_readiness=paper_ready`。
- [ ] workflow 的子模块 failed/skipped 必须反映到 workflow 顶层 summary（顶层 contract 已验证；独立子 run 递归验证见 `docs/KNOWN_BUGS.md`）。
- [x] model_table 的 estimator/backend/spec 与 audit 中记录一致；无法比对时至少 warning。
- [x] `run_config_resolved.json` 必须包含可重跑所需 spec/config 信息。
- [x] `manifest.json` 或等价字段必须包含 rerun command。

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

- [x] valid fixture 通过。
- [x] missing artifact fixture 失败。
- [x] unregistered risk fixture 失败。
- [x] inconsistent status fixture 失败。
- [x] `validate-method` 和 `validate-workflow` 可从 CLI 调用。
- [x] `--strict` 行为有测试。
- [x] 不改变原有 `run` / `workflow` 的主接口。

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

- [x] 不需要 `make`。
- [x] smoke CLI 在 Windows shell 可运行。
- [x] strict 模式会调用 contract verifier。
- [x] 失败时返回非 0。
- [x] smoke report 记录每个 check 名称、命令、status、run_dir、validation result。
- [x] 保留或兼容当前 `{"status":"ok","checks":43}` 语义，不无故减少 check 数。

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

- [x] workflow status 是 `success` 或 `success_with_warnings`。
- [x] 有 DID design diagnostic。
- [x] 有 modern DID 路由结果或明确 backend status。
- [x] `twfe_role` 不是默认主估计，除非设计确实允许。
- [x] `model_table` 有主估计行。
- [x] `artifact_manifest` 所列 required 文件存在。
- [x] `validate-workflow` 通过。

#### Case DID-G2：TWFE-only staggered

预期：

- [x] 不得 `paper_readiness=paper_ready`。
- [x] 必须触发或等价标记 `TWFE_STAGGERED_NOT_MAIN`。
- [x] `main_claim_available=false` 或 `claim_level=sensitivity_only/comparison_only`。
- [x] audit 明确说明 TWFE 仅作 comparison。

#### Case DID-G3：rank deficient

预期：

- [x] status 是 `failed` 或 `skipped`，不能 success。
- [x] 必须有 `RANK_DEFICIENT_DESIGN` 或等价风险。
- [x] 不得生成主估计 model_table。
- [x] `validate-workflow --strict` 必须失败。

### PSM-DID golden cases

#### Case PSM-G1：good overlap

预期：

- [x] 有 overlap table。
- [x] 有 balance before/after table。
- [x] 有 weight diagnostics。
- [x] 有 DRDID 对照或明确 missing dependency。
- [x] `main_claim_available` 根据诊断结果合理设置。

#### Case PSM-G2：poor overlap

预期：

- [x] 必须触发 `PSM_OVERLAP_WEAK` 或等价风险。
- [x] 不得 `paper_readiness=paper_ready`。
- [x] 必须输出 retained sample / common support 信息。

#### Case PSM-G3：extreme weights

预期：

- [x] 必须触发 `IPW_EXTREME_WEIGHTS` 或等价风险。
- [x] 必须输出 max/p95/p99 weights。
- [x] 必须输出 ESS。
- [x] trimming sensitivity 缺失时必须 warning。

### Spatial golden cases

#### Case SP-G1：direct-only effect

预期：

- [x] `spatial_spillover_run` 路由到 `spatial_exposure_did`，不得回退老 `spatial_did_reduced_form`。
- [x] local treatment coefficient 写入 `did_common_output.json`。
- [x] spillover / exposure effect 分表。
- [x] 不把 exposure coefficient 写成 structural indirect effect。

#### Case SP-G2：indirect/exposure-only effect

预期：

- [x] 输出 reduced-form exposure estimate。
- [x] 必须触发 `INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION`，除非真实 structural impact decomposition 已完成。
- [x] `claim_level` 为 `exploratory_only` 或 `sensitivity_only`，不得 `main_estimate`。

#### Case SP-G3：W sign flip

预期：

- [x] `spatial_w_sensitivity` 输出 `tables/w_sensitivity_main_effects.csv`。
- [x] 输出 `figures/w_sensitivity_forest.png`。
- [x] 必须触发 `W_SENSITIVITY_SIGN_FLIP`。
- [x] workflow 顶层 claim strength 降级。

#### Case SP-G4：contaminated controls

预期：

- [x] 必须触发 `CONTROL_GROUP_CONTAMINATED`。
- [x] near/far controls 或 buffer deletion artifact 存在。
- [x] 控制组污染不得被吞掉。

### 验收命令

```bash
conda run -n base python -m pytest tests/golden -q
conda run -n base python -m skill4econ.cli smoke --suite all --strict
```

### Definition of Done

- [ ] 三条 workflow 至少各有 3 个 golden cases（本轮代表性 golden 已扩到 9 个；完整 workflow 矩阵见 `docs/KNOWN_BUGS.md`）。
- [x] 每个 golden case 检查 status、risk code、claim_level、paper_readiness、artifact existence。
- [x] 至少一个 case 验证 rank deficient / poor overlap / sign flip 这类负路径。
- [ ] 所有 golden run 都通过 `validate-workflow`（本轮 golden 逐 run `validate_run_dir`；慢 Stata workflow 矩阵见 known gap）。
- [x] 没有新增真实模型范围，只加固现有能力。

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

- [x] Rscript 不存在：`spatial_spdep_lisa` 必须 `missing_dependency` / `skipped`。
- [ ] Rscript 存在但 spdep 不存在：必须 `missing_dependency` / `skipped`。
- [ ] Stata 不存在：Stata wrapper 必须 `missing_dependency` / `skipped`。
- [ ] Stata 存在但包缺失：必须 `missing_dependency` / `skipped`。
- [ ] 后端进程非 0：必须 `failed`，不得读取旧 artifact。
- [ ] 后端 stdout 有成功字样但结果文件缺失：必须 `failed`。
- [ ] parser 输入为空：必须 `BACKEND_PARSE_FAILED`。
- [x] parser 输入 malformed：必须 `BACKEND_PARSE_FAILED`。
- [ ] ppmlhdfe 缺失：不得 fallback 到 local poisson。
- [x] SAR/SEM/SDM backend 缺失：只能 `adapter_only` / `missing_dependency`，不得宣称结构模型完成。

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

- [x] dependency missing 不假成功。
- [x] parser failure 不假成功。
- [x] no silent fallback 有测试。
- [ ] workflow 顶层能反映子模块 skipped/failed（顶层 contract 已覆盖；独立子 run 递归矩阵见 known gap）。
- [x] 所有 adapter failure 都写出合法 `status.json`、`reviewer_risk.json`、`run_log.txt`。

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

- [x] staggered adoption + TWFE-only：触发 `TWFE_STAGGERED_NOT_MAIN`。
- [x] cohort support 太弱：触发 `DID_INSUFFICIENT_COHORT_SUPPORT`。
- [x] event-time support 太弱：触发 `DID_EVENT_TIME_SUPPORT_WEAK`。
- [x] cluster 数过少：触发 cluster warning。
- [x] modern DID backend 缺失：`missing_dependency`，不得回退成 TWFE 主估计。
- [x] TWFE comparison 可以输出，但不得自动 `paper_ready`。

### 验收命令

```bash
conda run -n base python -m pytest tests/did -q
conda run -n base python -m pytest tests/golden/test_did_paper_run_golden.py -q
conda run -n base python -m skill4econ.cli smoke --suite did --strict
```

### Definition of Done

- [x] DID output 明确 estimand。
- [x] TWFE role 明确。
- [x] support diagnostics 可机器读取。
- [x] 现代 DID 缺后端不 fallback。
- [x] DID golden cases 全过。
- [x] docs 说明哪些结果可主张，哪些只能 comparison。

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

- [x] overlap fail：触发 `PSM_OVERLAP_WEAK` 或更强风险，`paper_readiness != paper_ready`。
- [x] SMD after 超阈值：触发 balance risk。
- [x] ESS 太低：触发 `IPW_LOW_EFFECTIVE_SAMPLE_SIZE`。
- [x] p99 或 max weight 极端：触发 `IPW_EXTREME_WEIGHTS`。
- [x] trimming sensitivity 未跑：触发 warning，不得静默缺失。
- [x] poor overlap 下不得输出强主结论。

### 验收命令

```bash
conda run -n base python -m pytest tests/psm -q
conda run -n base python -m pytest tests/golden/test_psm_did_policy_run_golden.py -q
conda run -n base python -m skill4econ.cli smoke --suite psm --strict
```

### Definition of Done

- [x] PSM/IPW output 有 ESS 和 weight diagnostics。
- [x] poor overlap 自动 claim 降级。
- [x] extreme weight 自动 risk。
- [x] trimming sensitivity 有 artifact 或 explicit warning。
- [x] PSM golden cases 全过。

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

- [x] 权重缺失：`SPATIAL_W_MISSING`，不得误报 `SPATIAL_W_HAS_ISLANDS`。
- [x] W 有 islands：`SPATIAL_W_HAS_ISLANDS`。
- [x] 无坐标不能跑 spatial SE：`SPATIAL_SE_NOT_USED`。
- [x] 无 impact decomposition 却出现 exposure/spillover 解释：`INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION`。
- [x] W sensitivity sign flip：`W_SENSITIVITY_SIGN_FLIP`，workflow claim 降级。
- [x] contaminated controls：`CONTROL_GROUP_CONTAMINATED`。
- [x] weak exposure/control definition：`EXPOSURE_CONTROL_DEFINITION_WEAK`。

### 验收命令

```bash
conda run -n base python -m pytest tests/spatial -q
conda run -n base python -m pytest tests/golden/test_spatial_spillover_run_golden.py -q
conda run -n base python -m skill4econ.cli smoke --suite spatial --strict
```

### Definition of Done

- [x] `spatial_spillover_run` 明确路由 `spatial_exposure_did`。
- [x] exposure DID 不宣称 structural effect。
- [x] SE comparison 明确 sensitivity-only。
- [x] W sensitivity sign flip 触发风险并降级。
- [x] 缺 W、W islands、contaminated controls 均有测试。
- [x] spatial golden cases 全过。

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

- [x] R spdep 依赖缺失时只 skipped，不假成功。
- [x] SAR/SEM/SDM 目前是 parser/contract，未真实跑 xsmle/splm 时 adapter-only。
- [x] spatial SE 是 Python cutoff HAC sensitivity，不是完整 Conley/fixest。
- [x] W grid 需要用户给 `weight_paths`；若尚未自动生成经济距离/kNN W，必须在 audit 中说明。
- [x] local ppmlhdfe only；不得 fallback 到 local poisson。

### 验收命令

```bash
conda run -n base python -m pytest tests/docs -q
conda run -n base python -m skill4econ.cli smoke --suite all --strict
```

### Definition of Done

- [x] docs 中每个 known gap 都有对应 artifact 字段或 risk code。
- [x] artifact 中每个 adapter-only / sensitivity-only 状态都在 docs 中解释。
- [x] `KNOWN_BUGS.md` 不再暗示 fallback。
- [x] docs 测试能防止边界说明和机器输出脱节。

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

1. [x] P0-1 schemas / claim_level / paper_readiness。
2. [x] P0-2 contract verifier。
3. [x] P0-3 Windows-first smoke CLI。
4. [x] P0-4 三条 workflow golden cases。
5. [x] P0-5 dependency/no-fallback/parser failure 测试矩阵。
6. [x] P1-1 DID claim boundary 的最小字段。
7. [x] P1-2 PSM/IPW ESS + extreme weights + overlap 降级。
8. [x] P1-3 spatial reduced-form claim boundary 机器化。

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

- [x] 每个 method/workflow 都有稳定 CLI。
- [x] 每个 run 都有 manifest/audit/model_table/reviewer_risk/artifact_manifest/rerun/status。
- [x] 每个 run 都能通过 `validate-run`。
- [x] 每个 workflow 都能通过 `validate-workflow`。
- [x] smoke 有 Windows-first CLI。
- [x] DID / PSM / spatial reduced-form 均有 golden success + failure cases。
- [x] 缺依赖、rank deficient、不可识别、parser failure 都不会假成功。
- [x] 所有风险码来自 registry。
- [x] 所有 known gaps 进入 run artifact，而不只是写在 docs。
- [x] spatial exposure DID 不被误读为 structural indirect effect。
- [x] SAR/SEM/SDM 无真实后端时始终 adapter-only。
- [x] TWFE-only staggered DID 不会 paper-ready。
- [x] poor overlap / extreme weights / W sign flip 会自动降级 claim。
- [x] `conda run -n base python -m skill4econ.cli smoke --suite all --strict` 通过。
