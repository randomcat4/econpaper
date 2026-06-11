# TODO_EasyPaper_EconFinance_Production.md

> 施工起点：`D:/myproject/econpaper/EasyPaper`，branch `main`，latest known commit `63ba82c feat: require provenance hashes for empirical artifacts`。
> 相关整理分支：`D:/myproject/econpaper/skill4econ`，branch `codex/organize-skill4econ-easypaper`，latest known commit `5d08808`。
> 当前状态：EasyPaper econ/finance 第一阶段 demo 已可 mock 跑通，但 fast suite 仍有 6 个 baseline failures；live LLM、PDF/LaTeX、引用可靠性、provenance/replication、release gate 均未达到 production。

## 施工总原则

1. 不接 econpaper 主 agent 壳，不重写 EasyPaper agent 架构；只把 EasyPaper-derived layer 打磨成正式经济学/金融论文草稿引擎。
2. empirical results 只能来自 file-backed tables/figures/artifact manifests；禁止 Dreamer、AI image、autonomous visualization 生成实证结果图。
3. LLM 只能写作、组织、解释已给定证据；不得编造系数、样本量、p-value、显著性、数据来源、识别假设或参考文献。
4. 所有生产输出必须可复现：输入、模型配置、manifest、hash、命令、日志、LaTeX 编译状态、人工风险清单都要落盘。
5. fast CI 不访问外网、不需要 API key、不要求本地 LaTeX；live LLM 和 LaTeX 编译使用独立 manual/optional job。
6. 所有新增示例必须跨 Windows/Linux 可搬运；release artifact 不得含 API key、私有绝对路径、临时缓存路径。

## Definition of Production-Ready

Production-ready 表示一次正式生成至少产出：

- `main.tex`、`paper.pdf`、`references.bib`、`artifact_manifest.normalized.json`、`replication/README.md`、`replication/manifest.lock.json`、`evaluation_report.json`、`HANDOFF.md`。
- AER/QJE/JFE 至少各 2 个真实 live LLM run 通过人工审阅，且未退化成 AI/ML paper。
- LaTeX 可用 `latexmk` 或 `pdflatex+bibtex` 编译；无 undefined citation/reference、无 missing figure、无 raw prompt/TODO/placeholders。
- 每个结果图表都有 `data_hash`、`code_hash`、`command`、`created_at`、`source_files`、relative LaTeX path。
- release gate 按阈值阻断低质量草稿，不允许“生成了文件就算成功”。

## 禁止事项

- 禁止 `sha256:placeholder`、`TODO`、`TBD`、`need_citation`、raw prompt 泄漏进入正式 output。
- 禁止在 release artifact 中保存 `sk-*`、Moonshot/OpenAI key、私有绝对路径如 `D:/myproject/...`。
- 禁止把 failed/missing-dependency/interface-only 的 skill4econ 输出写成论文 empirical claim。
- 禁止让 Conclusion 简单复制 Results。
- 禁止把 venue constraints 只作为 metadata/hints；必须进入 prompt、plan、writer、typesetter、eval gate。

---

# A. 交接前必须先修的 Repo Hygiene / Packaging Blockers

## Phase A1. EasyPaper baseline 6 failures 清零 `[fast CI]`

### Task A1.1 补齐缺失 prompts/config/plugin skill/canonical skills tree

- 目标：让 `pytest -m "not live_llm and not latex and not slow" -q` 从 `6 failed` 变为全绿。
- 文件/模块：
  - 现有测试：`tests/test_dag_migration.py`、`tests/test_narrative_section_shape_guards.py`、`tests/test_plugin_config_template_sync.py`、`tests/test_skills_bootstrap.py`
  - 新增/修复建议：`src/prompts/metadata/generation_system.txt`、`src/prompts/planner/step1_structure.txt`、`configs/example.yaml`、`plugins/easypaper/skills/easypaper-setup-environment/SKILL.md`、`skills/`
- 具体改动：
  - 补最小但真实的 prompt 文件，不写空占位。
  - `configs/example.yaml` 与 `src/config/schema.py` 当前 schema 同步。
  - 建立 canonical `skills/` tree，或调整测试/打包逻辑，使 canonical tree 与 `src/skills/builtin/` 有明确同步规则。
  - README 中 `examples/config.example.yaml` 与 `configs/example.yaml` 指向必须真实存在，或统一改成一个 canonical example。
- 测试/命令：
  - `python -m pytest tests/test_dag_migration.py tests/test_narrative_section_shape_guards.py tests/test_plugin_config_template_sync.py tests/test_skills_bootstrap.py -q`
  - `python -m pytest -m "not live_llm and not latex and not slow" -q`
- 验收标准：
  - fast suite 全绿；不再依赖缺失资产。
  - 新增 config/prompt/skill 文件不是空壳，能解释当前 econ/finance 独立项目的最小使用方式。
- 风险：
  - 复制旧 EasyPaper canonical tree 可能带回 AI/ML 默认假设；需审查 wording。
- 建议 commit 名：
  - `fix: restore packaged prompt config and skill assets`

## Phase A2. skill4econ 安装/路径阻断项 `[fast CI]`

### Task A2.1 修正 SKILL.md 运行目录和安装策略

- 目标：避免从 `D:/myproject/econpaper` 运行 `python -m skill4econ.cli` 时解析到旧副本或找不到 package。
- 文件/模块：
  - `D:/myproject/econpaper/skill4econ/SKILL.md`
  - `D:/myproject/econpaper/skill4econ/README.md`
  - 可新增：`D:/myproject/econpaper/skill4econ/docs/INSTALL.md`
- 具体改动：
  - 将 Required Workflow 改成优先在 `D:/myproject/econpaper/skill4econ` 根目录运行。
  - 明确两种合法模式：`python -m pip install -e D:/myproject/econpaper/skill4econ` 后任意目录运行；或在 repo 根目录用 `conda run -n base python -m skill4econ.cli ...`。
  - 加入 `python -c "import skill4econ; print(skill4econ.__file__)"` 验证步骤。
- 测试/命令：
  - `conda run -n base python -m pip install -e D:/myproject/econpaper/skill4econ`
  - `conda run -n base python -c "import skill4econ; print(skill4econ.__file__)"`
- 验收标准：
  - 文档不再要求从 econpaper 根目录裸跑。
  - import path 指向 `D:/myproject/econpaper/skill4econ/src/skill4econ`。
- 风险：
  - 用户机器上可能已有旧 editable install；文档需提供清理/验证步骤。
- 建议 commit 名：
  - `docs: clarify skill4econ editable install workflow`

### Task A2.2 修 smoke 子进程 import path

- 目标：`tests/smoke/run_smoke.py` 和 adapter 子进程测试在 src layout 后稳定找到 `skill4econ.cli`。
- 文件/模块：
  - `tests/smoke/run_smoke.py`
  - `tests/adapters/test_dependency_and_parser_failures.py`
  - `tests/conftest.py`
  - `pyproject.toml`
- 具体改动：
  - 子进程启动时显式设置 `PYTHONPATH=<repo>/src`，或在测试前检测 editable install。
  - 避免依赖 pytest `conftest.py` 对子进程隐式生效。
- 测试/命令：
  - `conda run -n base python tests/smoke/run_smoke.py`
  - `conda run -n base python -m pytest tests/smoke tests/adapters/test_dependency_and_parser_failures.py -q`
- 验收标准：
  - smoke 输出 `{"status": "ok"}`。
  - 不出现 `No module named skill4econ.cli`。
- 风险：
  - 强制 editable install 会污染全局环境；优先用 repo-local `PYTHONPATH`。
- 建议 commit 名：
  - `fix: make skill4econ smoke subprocesses src-layout aware`

### Task A2.3 修 `PACKAGE_ROOT.parents[1]` wheel 路径推断

- 目标：普通 wheel/非 editable 安装后 `DEFAULT_RUNS`、relative spec/data、vendor paths 不错位。
- 文件/模块：
  - `src/skill4econ/core.py`
  - `src/skill4econ/config.py`
  - tests 可新增：`tests/contracts/test_package_paths.py`
- 具体改动：
  - 不用 `PACKAGE_ROOT.parents[1]` 猜 repo root 作为运行资产根。
  - package data 用 `importlib.resources` 读取。
  - 示例/fixtures/vendor 源码若不打包，必须在错误信息中要求显式传路径。
- 测试/命令：
  - `conda run -n base python -m pytest tests/contracts/test_package_paths.py -q`
  - `python -m build` 后在临时 venv 安装 wheel 做 import smoke。
- 验收标准：
  - editable 和 wheel 安装均能定位 package data。
  - 缺少非打包资源时报 actionable error，不 silent fallback。
- 风险：
  - 现有测试可能默认 repo-relative fixtures；需区分 package assets 与 repo examples。
- 建议 commit 名：
  - `fix: resolve skill4econ resources without repo-root guessing`

## Phase A3. EasyPaper packaging 和 namespace 边界 `[fast CI]`

### Task A3.1 收敛 `src` 顶层 namespace 暴露

- 目标：降低 `pyproject.toml` 暴露顶层 `src` package 与外部项目冲突的风险。
- 文件/模块：
  - `pyproject.toml`
  - `easypaper/__init__.py`
  - 所有 `from src...` imports
  - 可新增迁移包：`easypaper_core/` 或 `easypaper/internal/`
- 具体改动：
  - 短期：记录为 packaging blocker，确保 CI 至少发现 namespace collision。
  - 中期：将内部 `src.*` 包迁移到 `easypaper_core.*` 或 `easypaper.internal.*`，并保留兼容 import shim。
  - 更新 setuptools package include，不再发布裸 `src`。
- 测试/命令：
  - `python -m pip install -e .`
  - `python -c "import easypaper; print(easypaper.__file__)"`
  - `python -m pytest tests/test_sdk_client.py tests/test_sdk_without_fastapi.py -q`
- 验收标准：
  - wheel/editable install 不向环境暴露通用顶层 `src`。
  - 旧测试通过，公共 `import easypaper` 不变。
- 风险：
  - 大范围 import 迁移风险高；必须单独分支或机械化脚本，并跑 full fast suite。
- 建议 commit 名：
  - `refactor: remove public top-level src package exposure`

### Task A3.2 明确 artifacts ignore 边界

- 目标：避免根 `.gitignore` 的 `artifacts/` 意外忽略 `integrations/easypaper-econ-finance/examples/.../artifacts`。
- 文件/模块：
  - `D:/myproject/econpaper/skill4econ/.gitignore`
  - `D:/myproject/econpaper/skill4econ/integrations/easypaper-econ-finance/.gitignore`
  - EasyPaper-derived layer `.gitignore`
- 具体改动：
  - 将泛化 `artifacts/` 改为明确运行产物目录，如 `/outputs/`、`/results/`、`/.artifacts/`。
  - 对需要 tracked 的 example artifacts 加反向 ignore。
- 测试/命令：
  - `git check-ignore -v integrations/easypaper-econ-finance/examples/econ/artifacts/manifest.json`
  - `git status --ignored --short`
- 验收标准：
  - 示例 manifest/fixtures 不被 ignore。
  - 生成产物仍被 ignore。
- 风险：
  - 可能把历史临时 artifact 暴露到 git status；需同步清理。
- 建议 commit 名：
  - `chore: tighten artifact ignore boundaries`

### Task A3.3 清理 whitespace 与 diff hygiene

- 目标：让未来 CI 可打开 `git diff --check`。
- 文件/模块：
  - 当前分支所有改动文件。
- 具体改动：
  - 修 trailing whitespace、mixed whitespace、EOF newline。
  - 不做无关格式化。
- 测试/命令：
  - `git diff --check main...HEAD`
  - `python -m pytest -m "not live_llm and not latex and not slow" -q`
- 验收标准：
  - `git diff --check` 无输出。
- 风险：
  - 大量文件 whitespace 变化会污染 review；拆独立 commit。
- 建议 commit 名：
  - `chore: clean whitespace in econ finance workspace`

---

# B. Production-Ready Paper Generation

## Phase B1. Manifest/provenance 产品化 `[fast CI]`

### Task B1.1 禁止 placeholder hash，补真实 example provenance

- 目标：示例和正式 manifest 不允许 `sha256:placeholder`。
- 文件/模块：
  - `examples/econ/artifacts/manifest.json`
  - `examples/finance/artifacts/manifest.json`
  - `src/agents/metadata_agent/artifact_manifest.py`
  - `tests/test_artifact_manifest_v1.py`
  - `tests/test_minimal_econ_finance_fixtures.py`
- 具体改动：
  - 对现有 PDF fixture 计算真实 sha256，写入 `data_hash` / `code_hash` 或改用 fixture source files 生成。
  - validator 拒绝 `sha256:placeholder`、空 hash、非 `sha256:<hex>` 格式。
  - manifest artifact 新增字段：`command`、`created_at`、`source_files`、`software`。
- 测试/命令：
  - `python -m pytest tests/test_artifact_manifest_v1.py tests/test_minimal_econ_finance_fixtures.py -q`
- 验收标准：
  - repo 内 `rg "sha256:placeholder" examples src tests` 无正式示例命中。
  - result figure/table 缺任何 provenance 字段时 fast test fail。
- 风险：
  - 旧测试用 `sha256:data` 这类假 hash；需改成格式有效 fixture hash。
- 建议 commit 名：
  - `feat: enforce real provenance hashes for empirical artifacts`

### Task B1.2 normalized manifest 使用可搬运相对路径

- 目标：release artifact 不泄漏 `D:/myproject/...` 绝对路径，LaTeX figure paths relative。
- 文件/模块：
  - `scripts/run_econ_paper.py`
  - `src/agents/metadata_agent/artifact_manifest.py`
  - `src/agents/metadata_agent/metadata_utils.py`
  - `tests/test_run_econ_paper_script.py`
  - `tests/test_artifact_path_validation.py`
- 具体改动：
  - `manifest.normalized.json` 同时保留 internal resolved path 和 redacted/relative artifact path；release copy 只用 relative。
  - `latex_path` 必须相对 output root 或 `replication/materials/`。
  - 增加 export step，把 referenced figures/tables 复制到 output bundle。
- 测试/命令：
  - `python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml --out outputs/aer_minimal_mock --mock-llm --no-pdf`
  - `python -m pytest tests/test_run_econ_paper_script.py tests/test_artifact_path_validation.py -q`
- 验收标准：
  - output 中 `rg "D:/|C:/|/Users/|/home/" outputs/aer_minimal_mock` 无命中，debug-only 文件除外且不进 release。
  - `main.tex` 中 includegraphics 路径可在 output bundle 内解析。
- 风险：
  - 内部 validator 仍需要绝对 path 做安全检查；注意 internal/release 两份表示。
- 建议 commit 名：
  - `feat: export portable empirical artifact bundles`

## Phase B2. Replication package `[fast CI]`

### Task B2.1 自动生成 `replication/README.md` 和 `manifest.lock.json`

- 目标：每次正式生成都有可读、可机器校验的复现包。
- 文件/模块：
  - 新增建议：`src/agents/metadata_agent/replication_package.py`
  - `scripts/run_econ_paper.py`
  - `tests/test_replication_package.py`
- 具体改动：
  - 从 request、manifest、runner config、events、output files 生成 lockfile。
  - `replication/README.md` 包含数据来源、代码来源、生成命令、hash 校验、不可复现项、人工补充项。
  - lockfile 记录 `created_at`、model/base_url redacted、venue、method preset、input request hash、artifact hashes。
- 测试/命令：
  - `python -m pytest tests/test_replication_package.py -q`
- 验收标准：
  - mock run 后存在 `replication/README.md`、`replication/manifest.lock.json`。
  - lockfile hash 与实际文件一致。
- 风险：
  - hash source 选择不一致会导致 nondeterminism；固定排序和 path normalization。
- 建议 commit 名：
  - `feat: generate replication package for econ finance runs`

### Task B2.2 生成 data/code availability statement

- 目标：论文正文或附录自动含合规 availability statement。
- 文件/模块：
  - `src/agents/metadata_agent/assembly_helper.py`
  - `src/agents/typesetter_agent/typesetter_template.py`
  - venue YAML：`src/skills/builtin/venues/aer.yaml`、`qje.yaml`、`jfe.yaml`
  - tests 新增：`tests/test_availability_statement.py`
- 具体改动：
  - 从 manifest/replication lock 生成 “Data and Code Availability” section 或 footnote。
  - venue-specific：AER/QJE/JFE 按投稿规则放置。
- 测试/命令：
  - `python -m pytest tests/test_availability_statement.py -q`
- 验收标准：
  - statement 不声称公开不可公开的数据。
  - 无 manifest 时正式模式阻断，mock/dev 模式可写明 “not provided”。
- 风险：
  - 真实 journal 规则会变化；venue YAML 中保留日期和人工复核提示。
- 建议 commit 名：
  - `feat: add data and code availability statements`

## Phase B3. Venue LaTeX templates `[latex CI + fast structural tests]`

### Task B3.1 AER/QJE/JFE 专用模板

- 目标：不再裸 `article`；输出符合各 venue 基本格式。
- 文件/模块：
  - 新增建议：`src/templates/venues/aer.tex.j2`、`qje.tex.j2`、`jfe.tex.j2`
  - `src/agents/typesetter_agent/typesetter_template.py`
  - `src/skills/builtin/venues/*.yaml`
  - tests：`tests/test_template_structure_profile.py`、新增 `tests/test_econ_venue_templates.py`
- 具体改动：
  - AER：abstract 限 100 words，JEL/keywords slots，AER-like title page。
  - QJE：title page、word count placeholder、section order、appendix handling。
  - JFE：anonymous mode、12pt、double spacing、submission-safe author handling。
  - 所有模板统一 relative figures、BibTeX、appendix tables。
- 测试/命令：
  - fast：`python -m pytest tests/test_econ_venue_templates.py tests/test_venue_abstract_limits.py tests/test_jfe_anonymous_output.py tests/test_qje_word_count_placeholder.py -q`
  - latex/manual：`python -m pytest -m latex -q`
- 验收标准：
  - mock AER/JFE/QJE 均生成 venue-specific class/options，不再是裸 article。
  - LaTeX compile 无 missing figure、undefined citation。
- 风险：
  - journal 官方 class 可能不可用；优先用 repo-contained fallback 模板，不依赖外部 `.cls`。
- 建议 commit 名：
  - `feat: add venue-specific econ finance latex templates`

## Phase B4. Paper-ready 内容结构 `[fast CI]`

### Task B4.1 强制 production section contract

- 目标：正文具备 abstract、贡献、文献定位、识别假设、方程/模型、结果解释、稳健性、局限、结论。
- 文件/模块：
  - `src/agents/planner_agent/*`
  - `src/agents/metadata_agent/section_generation.py`
  - `src/agents/shared/section_prompt_builder.py`
  - `tests/test_planner_required_sections.py`
  - 新增：`tests/test_paper_ready_section_contract.py`
- 具体改动：
  - Plan schema 增加 required rhetorical roles：`contribution_claims`、`literature_positioning`、`identification_assumptions`、`model_equations`、`limitations`。
  - writer prompt 明确不得把 Results 当 Conclusion。
  - section guard 拒绝 raw prompt、TODO、placeholder、ML-specific “experiments”。
- 测试/命令：
  - `python -m pytest tests/test_paper_ready_section_contract.py tests/test_figure_path_and_conclusion.py tests/test_narrative_section_shape_guards.py -q`
- 验收标准：
  - mock output 含经济学/金融论文必要结构。
  - Conclusion 与 Results 文本相似度低于阈值。
- 风险：
  - 过硬规则可能压制短稿；区分 `draft` 与 `production` 模式。
- 建议 commit 名：
  - `feat: enforce paper-ready econ narrative contract`

### Task B4.2 方程和模型表达安全层

- 目标：有方程但不编造估计结果。
- 文件/模块：
  - 新增建议：`src/agents/shared/econ_equation_builder.py`
  - method preset 文件见 B5
  - `tests/test_econ_equation_builder.py`
- 具体改动：
  - 方程只由 method preset + user inputs 生成。
  - 方程变量必须来自 request/data dictionary；未定义变量进入 risk note。
  - Results 只能解释 manifest/table 中存在的统计量。
- 测试/命令：
  - `python -m pytest tests/test_econ_equation_builder.py -q`
- 验收标准：
  - 无数据/无结果时，只能写 design/proposed specification，不能写 findings。
- 风险：
  - LLM 仍可能扩写过度；后续 eval gate 必须扫描 claims。
- 建议 commit 名：
  - `feat: ground equations in method presets and inputs`

## Phase B5. Method presets `[fast CI]`

### Task B5.1 建立 method preset registry

- 目标：支持 DiD/event study/RD/IV/RCT/panel FE/asset pricing/corporate finance/banking。
- 文件/模块：
  - 新增建议：`src/econ_methods/presets/*.yaml`
  - 新增：`src/econ_methods/registry.py`
  - `src/agents/metadata_agent/models.py`
  - `tests/test_econ_method_presets.py`
- 具体改动：
  - 每个 preset 包含 `inputs`、`equation`、`identification_checklist`、`robustness`、`expected_tables`、`expected_figures`、`claim_limits`。
  - request 增加 `method_preset`，缺失时 planner 可建议但不能假定。
- 测试/命令：
  - `python -m pytest tests/test_econ_method_presets.py -q`
- 验收标准：
  - 8 类 preset 均可 load/validate。
  - 每个 preset 至少有 3 条 identification checks 和 3 条 robustness checks。
- 风险：
  - finance 方法差异大；asset pricing 与 corporate/banking 分开写 claim limits。
- 建议 commit 名：
  - `feat: add econ finance method preset registry`

### Task B5.2 skill4econ artifact contract 对接

- 目标：EasyPaper 能消费 skill4econ 输出，但不依赖 econpaper agent。
- 文件/模块：
  - `D:/myproject/econpaper/skill4econ/src/skill4econ/contracts/artifact_manifest.py`
  - EasyPaper：`src/agents/metadata_agent/artifact_manifest.py`
  - 新增 cross repo docs：`integrations/easypaper-econ-finance/README_SKILL4ECON_INTEGRATION.md`
- 具体改动：
  - 定义最小共同 manifest schema：status、claim_level、tables、figures、warnings、not_paper_ready。
  - EasyPaper 读取 `not_paper_ready` 时只能写风险/局限，不能写结论性 empirical claim。
- 测试/命令：
  - skill4econ：`conda run -n base python -m pytest tests/contracts tests/validation -q`
  - EasyPaper：`python -m pytest tests/test_artifact_manifest_v1.py tests/test_econ_method_presets.py -q`
- 验收标准：
  - failed/missing_dependency/interface_only artifact 被阻断或降级为 handoff risk。
- 风险：
  - 两 repo schema 容易漂移；锁定 contract version。
- 建议 commit 名：
  - `feat: align easypaper with skill4econ artifact contracts`

## Phase B6. Citation/reference 可靠性 `[fast CI + optional external]`

### Task B6.1 所有 cite 必须来自 reference pool / `.bib`

- 目标：杜绝 hallucinated references 和 undefined citations。
- 文件/模块：
  - `src/agents/shared/reference_pool.py`
  - `src/agents/shared/reference_assignment.py`
  - `src/agents/metadata_agent/citation_grounding.py`
  - `tests/test_assign_references.py`
  - 新增：`tests/test_citation_validity_gate.py`
- 具体改动：
  - writer 只能使用 pool 中 key。
  - 输出后扫描 `\cite{}`，全部 key 必须存在于 `references.bib`。
  - citation claims 附近没有引用时打 risk 或 fail。
- 测试/命令：
  - `python -m pytest tests/test_assign_references.py tests/test_citation_validity_gate.py -q`
- 验收标准：
  - undefined citation 在 fast CI fail。
  - `need_citation`、假 DOI、空 BibTeX fail。
- 风险：
  - reference pool 太小会导致 draft 被阻断；handoff 应要求作者补 bib。
- 建议 commit 名：
  - `feat: gate citations against reference pool and bibtex`

### Task B6.2 venue-specific bibliography style

- 目标：AER/QJE/JFE bib style 与 template 一致。
- 文件/模块：
  - `src/templates/venues/*.tex.j2`
  - `src/skills/builtin/venues/*.yaml`
  - `tests/test_bibliography_style.py`
- 具体改动：
  - venue YAML 增加 `bibliography_style`、`citation_style`。
  - fallback 使用 repo-contained style 或 standard style。
- 测试/命令：
  - `python -m pytest tests/test_bibliography_style.py -q`
  - latex/manual compile。
- 验收标准：
  - `main.tex` 不硬编码单一 style。
- 风险：
  - 官方 bst 不一定存在；fallback 需记录为 compliance risk。
- 建议 commit 名：
  - `feat: configure venue-specific bibliography styles`

---

# C. Live Quality Eval

## Phase C1. Live LLM run harness `[manual-live]`

### Task C1.1 建立 live eval 目录和 JSONL schema

- 目标：真实 LLM run 有可追踪评审记录，不混入 fast CI。
- 文件/模块：
  - 新增建议：`live_eval/README.md`
  - 新增：`scripts/run_live_eval.py`
  - 新增：`tests/test_live_eval_schema.py`
- 具体改动：
  - schema 字段：venue、case_id、model、base_url_host、request_hash、output_dir、status、fail_reasons、manual_reviewer、created_at。
  - 失败样例保存到 `live_eval/*.jsonl`，不保存 API key。
- 测试/命令：
  - fast schema：`python -m pytest tests/test_live_eval_schema.py -q`
  - manual：`python scripts/run_live_eval.py --venue aer --case examples/econ/aer_minimal_request.yaml --out outputs/live/aer_001`
- 验收标准：
  - live eval 文件可 append、可 validate、可汇总。
- 风险：
  - live output 可能含私有路径；写入前 redaction。
- 建议 commit 名：
  - `feat: add manual live eval harness`

### Task C1.2 AER/JFE/QJE 各至少 2 个真实 live run

- 目标：证明 live LLM 不退化成 ML paper，且不编造 empirical facts。
- 文件/模块：
  - `examples/econ/*.yaml`
  - `examples/finance/*.yaml`
  - `live_eval/*.jsonl`
  - `outputs/live/...` 不入 git，release 只收摘要。
- 具体改动：
  - 准备 6 个 case：AER 2、QJE 2、JFE 2；至少包含 DiD/event study、IV/RD、asset pricing/corporate finance/banking 中多类。
  - 每个 case 有真实 reference pool 和 artifact manifest。
- 测试/命令：
  - manual only：
    - `python scripts/run_econ_paper.py <case.yaml> --out outputs/live/<case> --model <model> --base-url <url> --compile-pdf`
    - `python scripts/evaluate_econ_paper.py outputs/live/<case>`
- 验收标准：
  - 6 个 run 生成 `main.tex`、`paper.pdf`、`evaluation_report.json`、`HANDOFF.md`。
  - 无编造系数/样本量/显著性；无 ML “Experiment/Benchmark/SOTA”退化。
- 风险：
  - LLM 质量波动；失败必须记录，不要改分数掩盖。
- 建议 commit 名：
  - `eval: record venue live runs for econ finance production gate`

## Phase C2. Evaluation rubric `[fast CI + manual-live]`

### Task C2.1 生成 `evaluation_report.json`

- 目标：每次正式生成用统一 rubric 自动评分。
- 文件/模块：
  - 新增建议：`src/evaluation/econ_paper_rubric.py`
  - 新增：`scripts/evaluate_econ_paper.py`
  - 新增：`tests/test_evaluation_report.py`
- 具体改动：
  - rubric 维度：structure、econ identification、evidence grounding、artifact provenance、citation validity、LaTeX compile、venue compliance、hallucination risk。
  - 每维 `score`、`threshold`、`status`、`findings`、`blocking`。
- 测试/命令：
  - `python -m pytest tests/test_evaluation_report.py -q`
  - `python scripts/evaluate_econ_paper.py outputs/aer_minimal_mock`
- 验收标准：
  - 低于阈值时 release gate fail。
  - 报告是机器可读 JSON，另可生成 markdown summary。
- 风险：
  - 自动检测无法完全判断 hallucination；manual-live 仍需人工签字。
- 建议 commit 名：
  - `feat: add econ finance evaluation report gate`

### Task C2.2 hallucination and claim scanner

- 目标：阻断无证据 empirical claims。
- 文件/模块：
  - 新增建议：`src/evaluation/claim_scanner.py`
  - `src/generation/claim_verifier.py`
  - tests：`tests/test_claim_scanner.py`
- 具体改动：
  - 扫描显著性词汇、数字系数、样本量、p-value、“we find”等 claim。
  - claim 附近必须有 manifest-backed table/figure 或 reference citation。
  - 无 evidence 的 claim 标为 blocking。
- 测试/命令：
  - `python -m pytest tests/test_claim_scanner.py -q`
- 验收标准：
  - 人工构造的 hallucinated coefficient fixture 被 fail。
- 风险：
  - false positive 较多；先宁可阻断 production。
- 建议 commit 名：
  - `feat: block unsupported empirical claims`

---

# D. Release Gate

## Phase D1. CI matrix `[fast CI + optional latex/manual-live]`

### Task D1.1 新增 GitHub Actions

- 目标：repo 有正式 CI，不靠本地口头检查。
- 文件/模块：
  - 新增：`.github/workflows/fast.yml`
  - 新增：`.github/workflows/latex.yml`
  - 新增：`.github/workflows/manual-live.yml`
  - `CODEX_TASKS.md`
- 具体改动：
  - fast：Windows + Linux，Python 3.11/3.12，跑 fast suite、diff check、secret scan、portable path scan。
  - latex：可手动/PR label 触发，安装 minimal tex，跑 latex marked tests。
  - manual-live：只 workflow_dispatch，不存 key，不自动跑 PR。
- 测试/命令：
  - 本地近似：`python -m pytest -m "not live_llm and not latex and not slow" -q`
  - `git diff --check`
- 验收标准：
  - PR 上 fast 必须绿。
  - live job 永不默认执行。
- 风险：
  - LaTeX 安装耗时；可先 optional，不阻断 fast。
- 建议 commit 名：
  - `ci: add fast latex and manual live workflows`

## Phase D2. Release artifact builder `[fast CI + latex optional]`

### Task D2.1 打包正式 release bundle

- 目标：一条命令产出可交给作者/审稿前人工修订的 bundle。
- 文件/模块：
  - 新增建议：`scripts/build_release_bundle.py`
  - 新增：`tests/test_release_bundle.py`
- 具体改动：
  - bundle 内容：`main.tex`、`paper.pdf`、`references.bib`、`replication/*`、`evaluation_report.json`、`HANDOFF.md`、`logs/events.jsonl`、`config.redacted.yaml`。
  - 排除：API key、绝对私有路径、cache、临时输出、raw provider responses。
- 测试/命令：
  - `python scripts/build_release_bundle.py outputs/aer_minimal_mock --out results/release/aer_minimal_mock`
  - `python -m pytest tests/test_release_bundle.py -q`
- 验收标准：
  - bundle 可 zip。
  - portable scan 和 secret scan 通过。
- 风险：
  - PDF 不存在时 production 应 fail，draft/mock 可降级。
- 建议 commit 名：
  - `feat: build portable release bundles`

### Task D2.2 最终 release gate 命令

- 目标：把所有 gate 合成一个明确出口。
- 文件/模块：
  - 新增建议：`scripts/release_gate.py`
  - `CODEX_TASKS.md`
  - tests：`tests/test_release_gate.py`
- 具体改动：
  - gate 检查：fast suite status、eval thresholds、manifest provenance、citation validity、LaTeX compile、venue compliance、secret/path scan、handoff exists。
  - 返回码：pass=0，blocking fail=2，manual required=3。
- 测试/命令：
  - `python scripts/release_gate.py outputs/aer_minimal_mock --mode draft`
  - `python scripts/release_gate.py outputs/live/aer_001 --mode production`
- 验收标准：
  - production mode 缺 PDF/live/manual review 时阻断。
  - draft mode 清楚标记不可 release。
- 风险：
  - gate 太宽会被绕过；默认 production 严格。
- 建议 commit 名：
  - `feat: add final production release gate`

## Phase D3. Human handoff `[fast CI]`

### Task D3.1 每次正式生成 `HANDOFF.md`

- 目标：让作者明早接手时知道输入、模型、检查、风险、复现命令和必须人工补充项。
- 文件/模块：
  - 新增建议：`src/agents/metadata_agent/handoff.py`
  - `scripts/run_econ_paper.py`
  - tests：`tests/test_handoff_generation.py`
- 具体改动：
  - 自动生成 handoff，包含下面模板。
  - handoff 中列出作者必须补充/确认的 empirical claims，不允许全自动盖章。
- 测试/命令：
  - `python -m pytest tests/test_handoff_generation.py -q`
- 验收标准：
  - mock 和 live output 均有 `HANDOFF.md`。
  - 缺 evaluation/manifest/replication 时 handoff 明确标红。
- 风险：
  - handoff 可能变成流水账；保持结构固定、重点风险优先。
- 建议 commit 名：
  - `feat: write human handoff for each econ finance run`

---

# 多智能体并行施工建议

## 必须串行

1. A1 baseline 6 failures 清零先做，否则后续 fast CI 噪声太大。
2. A2 skill4econ 安装/路径策略先做，否则 integration/handoff 文档会继续误导。
3. B1 provenance/path 产品化先做，再做 B2 replication、D2 release bundle。
4. B3 templates 先于 latex release gate。
5. C2 evaluation rubric 先于 D2/D3 release gate。

## 可并行

- Agent 1：A1、A3 EasyPaper repo hygiene。
- Agent 2：A2 skill4econ packaging/path/smoke。
- Agent 3：B1/B2 provenance + replication。
- Agent 4：B3 venue templates + LaTeX compile。
- Agent 5：B5 method presets + skill4econ contract。
- Agent 6：B6 citation/reference + C2 claim scanner。
- Agent 7：C1 live eval cases，等 B1/B3/C2 最小接口稳定后执行。
- Agent 8：D1/D2/D3 CI/release/handoff，等 upstream modules 输出稳定后接线。

---

# 最终 Release Gate

Production release 必须全部满足：

1. `python -m pytest -m "not live_llm and not latex and not slow" -q` 全绿。
2. `git diff --check main...HEAD` 无 whitespace error。
3. `python -m pytest -m latex -q` 通过，或在 release report 中明确 latex job 环境失败且本地 compile log 通过。
4. `scripts/release_gate.py <output> --mode production` 返回 0。
5. AER/JFE/QJE live eval 各至少 2 个 case 通过人工 reviewer 签字。
6. `evaluation_report.json` 所有 blocking dimensions pass。
7. bundle scan 无 API key、无私有绝对路径、无 placeholder hash、无 undefined citations。
8. `HANDOFF.md` 存在并列出人工必看风险。

---

# HANDOFF.md 模板

```markdown
# HANDOFF

## 输入摘要

- Request file:
- Venue:
- Method preset:
- Artifact manifest:
- Reference pool / BibTeX:
- Output directory:

## 模型与配置

- Model:
- Base URL host:
- Config file:
- API key redacted: yes/no
- Runner command:

## 生成产物索引

- main.tex:
- paper.pdf:
- references.bib:
- replication/README.md:
- replication/manifest.lock.json:
- evaluation_report.json:
- events.jsonl:

## 自动检查结果

| Check | Status | Notes |
| --- | --- | --- |
| Structure |  |  |
| Econ identification |  |  |
| Evidence grounding |  |  |
| Artifact provenance |  |  |
| Citation validity |  |  |
| LaTeX compile |  |  |
| Venue compliance |  |  |
| Hallucination risk |  |  |

## 人工必看风险

-
-
-

## 作者必须补充或确认

- Empirical claim needing author confirmation:
- Data/code availability language:
- Confidential/proprietary data restrictions:
- Journal-specific formatting caveats:

## 复现命令

```powershell
python scripts/run_econ_paper.py <request.yaml> --out <output> --model <model> --base-url <base-url> --compile-pdf
python scripts/evaluate_econ_paper.py <output>
python scripts/release_gate.py <output> --mode production
```

## 不可自动声称事项

- 未由 manifest-backed table/figure 支持的结果。
- failed/missing-dependency/interface-only skill4econ 输出。
- 作者未确认的数据清洗、样本限制、识别假设。
```
