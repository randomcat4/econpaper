# Baseline Test Report

Date: 2026-06-10

## Scope

This report records the fast-suite baseline after adding pytest markers and
isolating live LLM, local PDF, and LaTeX-dependent tests.

## Environment Notes

- Python: 3.12.3
- pytest: 9.0.3
- pytest-asyncio: 1.4.0
- Editable install command used: `python -m pip install -e .`
- Dev install attempted: `python -m pip install -e ".[dev]"`

The first editable install upgraded `botocore` to `1.43.26`, which conflicts
with the installed `aiobotocore 2.12.3` constraint. The dev install also upgraded
IPython to `9.14.1`, which conflicts with installed Spyder packages expecting
IPython `<9.0.0`. These are environment-level risks and were not introduced by
the test marker changes.

## Commands

```bash
python -m pip install -e .
python -c "import easypaper; print(easypaper.__file__)"
pytest tests/test_parse_agent.py -q
pytest tests/test_table_visual_preview.py -q
pytest tests/test_core_ref_analyzer.py tests/test_table_converter_enhanced.py::TestEndToEndPipeline -q
pytest tests/test_minimal_econ_finance_fixtures.py -q
pytest tests/test_econ_venue_configs.py -q
pytest tests/test_metadata_econ_fields.py -q
pytest tests/test_document_input_econ_constraints.py -q
pytest tests/test_plan_request_econ_fields.py -q
pytest tests/test_effective_venue_config.py -q
pytest tests/test_orchestrator_passes_econ_constraints.py -q
pytest tests/test_econ_section_taxonomy.py -q
pytest tests/test_required_section_normalization.py -q
pytest tests/test_planner_prompt_includes_econ_constraints.py tests/test_planner_format.py -q
pytest tests/test_planner_required_sections.py -q
pytest tests/test_econ_section_generation_content_brief.py -q
pytest tests/test_econ_body_section_sources.py -q
pytest tests/test_econ_section_prompt_style.py -q
pytest tests/test_execute_generation_passes_content_brief.py -q
pytest tests/test_assembly_order_econ.py -q
pytest tests/test_venue_abstract_limits.py tests/test_jfe_anonymous_output.py tests/test_qje_word_count_placeholder.py -q
pytest tests/test_artifact_manifest_v1.py tests/test_artifact_path_validation.py tests/test_manifest_to_figure_specs.py tests/test_manifest_to_table_specs.py tests/test_no_autonomous_result_figures.py tests/test_file_backed_result_figure_does_not_use_dreamer.py tests/test_result_caption_locked.py tests/test_minimal_econ_finance_fixtures.py -q
pytest tests/test_table_direct_injection.py tests/test_figure_path_and_conclusion.py tests/test_table_visual_preview.py tests/test_smart_caption_writer.py tests/test_metadata_router_contracts.py tests/test_metadata_econ_fields.py tests/test_document_input_econ_constraints.py -q
pytest tests/test_easypaper_app_config_builder.py tests/test_run_econ_paper_script.py -q
pytest tests/test_easypaper_app_config_builder.py tests/test_run_econ_paper_script.py tests/test_manifest_to_figure_specs.py tests/test_artifact_manifest_v1.py tests/test_artifact_path_validation.py -q
pytest tests/test_document_input_econ_constraints.py tests/test_orchestrator_passes_econ_constraints.py tests/test_planner_required_sections.py tests/test_econ_section_generation_content_brief.py tests/test_assembly_order_econ.py tests/test_no_autonomous_result_figures.py -q
pytest tests/test_run_econ_paper_script.py tests/test_minimal_poc_runner_outputs.py -q
pytest tests/test_run_econ_paper_script.py tests/test_minimal_poc_runner_outputs.py tests/test_easypaper_app_config_builder.py tests/test_artifact_manifest_v1.py tests/test_no_autonomous_result_figures.py -q
pytest tests/test_artifact_manifest_v1.py tests/test_artifact_path_validation.py tests/test_manifest_to_figure_specs.py tests/test_manifest_to_table_specs.py tests/test_run_econ_paper_script.py tests/test_minimal_poc_runner_outputs.py -q
python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml --out outputs/aer_minimal_mock --mock-llm --no-pdf
python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml --out outputs/aer_minimal --mock-llm --no-pdf
python scripts/run_econ_paper.py examples/finance/jfe_minimal_request.yaml --out outputs/jfe_minimal --mock-llm --no-pdf
pytest -m "not live_llm and not latex and not slow" -q
```

## Passing Checks

- Local import succeeds from `D:/myproject/econpaper/EasyPaper/easypaper/__init__.py`.
- `tests/test_parse_agent.py`: `2 passed, 1 deselected`
- `tests/test_table_visual_preview.py`: `10 passed, 2 deselected`
- `tests/test_core_ref_analyzer.py tests/test_table_converter_enhanced.py::TestEndToEndPipeline`: `14 passed`
- `tests/test_minimal_econ_finance_fixtures.py`: `3 passed`
- `tests/test_econ_venue_configs.py`: `4 passed`
- `tests/test_metadata_econ_fields.py`: `3 passed`
- `tests/test_document_input_econ_constraints.py`: `5 passed`
- `tests/test_plan_request_econ_fields.py`: `4 passed`
- `tests/test_effective_venue_config.py`: `5 passed`
- `tests/test_orchestrator_passes_econ_constraints.py`: `2 passed`
- `tests/test_econ_section_taxonomy.py`: `5 passed`
- `tests/test_required_section_normalization.py`: `5 passed`
- `tests/test_planner_prompt_includes_econ_constraints.py tests/test_planner_format.py`: `14 passed`
- `tests/test_planner_required_sections.py`: `6 passed`
- `tests/test_econ_section_generation_content_brief.py`: `5 passed`
- `tests/test_econ_body_section_sources.py`: `4 passed`
- `tests/test_econ_section_prompt_style.py`: `5 passed`
- `tests/test_execute_generation_passes_content_brief.py`: `3 passed`
- `tests/test_assembly_order_econ.py`: `4 passed`
- `tests/test_venue_abstract_limits.py tests/test_jfe_anonymous_output.py tests/test_qje_word_count_placeholder.py`: `5 passed`
- `tests/test_artifact_manifest_v1.py tests/test_artifact_path_validation.py tests/test_manifest_to_figure_specs.py tests/test_manifest_to_table_specs.py tests/test_no_autonomous_result_figures.py tests/test_file_backed_result_figure_does_not_use_dreamer.py tests/test_result_caption_locked.py tests/test_minimal_econ_finance_fixtures.py`: `20 passed`
- `tests/test_table_direct_injection.py tests/test_figure_path_and_conclusion.py tests/test_table_visual_preview.py tests/test_smart_caption_writer.py tests/test_metadata_router_contracts.py tests/test_metadata_econ_fields.py tests/test_document_input_econ_constraints.py`: `136 passed, 2 deselected`
- `tests/test_easypaper_app_config_builder.py tests/test_run_econ_paper_script.py`: `7 passed`
- `tests/test_easypaper_app_config_builder.py tests/test_run_econ_paper_script.py tests/test_manifest_to_figure_specs.py tests/test_artifact_manifest_v1.py tests/test_artifact_path_validation.py`: `19 passed`
- Core econ invariant suite (`test_document_input_econ_constraints.py`,
  `test_orchestrator_passes_econ_constraints.py`,
  `test_planner_required_sections.py`,
  `test_econ_section_generation_content_brief.py`,
  `test_assembly_order_econ.py`, `test_no_autonomous_result_figures.py`):
  `24 passed`
- `tests/test_run_econ_paper_script.py tests/test_minimal_poc_runner_outputs.py`: `5 passed`
- `tests/test_run_econ_paper_script.py tests/test_minimal_poc_runner_outputs.py tests/test_easypaper_app_config_builder.py tests/test_artifact_manifest_v1.py tests/test_no_autonomous_result_figures.py`: `15 passed`
- `tests/test_artifact_manifest_v1.py tests/test_artifact_path_validation.py tests/test_manifest_to_figure_specs.py tests/test_manifest_to_table_specs.py tests/test_run_econ_paper_script.py tests/test_minimal_poc_runner_outputs.py`: `20 passed`
- Mock runner smoke wrote `outputs/aer_minimal_mock/main.tex` plus
  `events.jsonl`, `request.normalized.json`, `manifest.normalized.json`,
  `config.redacted.yaml`, and `runner.summary.json`.
- AER/JFE PoC mock runner smoke wrote `outputs/aer_minimal/main.tex` and
  `outputs/jfe_minimal/main.tex`; checks confirmed required sections,
  file-backed result figure placement, JFE venue hints, and no `sk-*` pattern
  in outputs.
- Full fast suite now runs to completion without collection errors.

## Full Fast Suite Baseline

Command:

```bash
pytest -m "not live_llm and not latex and not slow" -q
```

Result:

```text
6 failed, 780 passed, 6 skipped, 4 deselected
```

The 4 deselected tests are marker-excluded live/LaTeX/slow tests.

## Remaining Baseline Failures

1. `tests/test_dag_migration.py::TestPromptLoader::test_load_existing_prompt`
   - Cause: `src/prompts/metadata/generation_system.txt` is missing, so
     `PromptLoader.load(...)` returns the fallback value.

2. `tests/test_narrative_section_shape_guards.py::test_planner_prompt_policy_requires_dedicated_conclusion`
   - Cause: `src/prompts/planner/step1_structure.txt` is missing.

3. `tests/test_plugin_config_template_sync.py::test_plugin_setup_skill_config_template_matches_example_config`
   - Cause: `configs/example.yaml` is missing.

4. `tests/test_plugin_config_template_sync.py::test_example_config_matches_current_schema_shape`
   - Cause: `configs/example.yaml` is missing.

5. `tests/test_plugin_config_template_sync.py::test_setup_skill_mentions_synchronized_config_template`
   - Cause: `plugins/easypaper/skills/easypaper-setup-environment/SKILL.md`
     is missing.

6. `tests/test_skills_bootstrap.py::test_builtin_packaged_tree_matches_canonical_skills_tree`
   - Cause: the canonical `skills/` tree is missing while packaged builtin
     skills exist under `src/skills/builtin/`.

## P0.2 Changes Applied

- Added pytest markers for `unit`, `mock`, `integration`, `live_llm`, `latex`,
  and `slow`.
- Set default pytest fast-suite marker expression to exclude live LLM, LaTeX,
  and slow tests.
- Removed a hardcoded OpenRouter API key from `tests/test_parse_agent.py`.
- Replaced the hardcoded local PDF path with `EASYPAPER_PARSE_TEST_PDF`.
- Marked live ParseAgent PDF parsing as `live_llm` and `slow`.
- Marked real pdflatex preview tests as `latex`.
- Added lightweight test import helpers and shared core-reference fixtures so
  the fast suite can collect and run.
- Updated Python 3.12/pytest 9-sensitive table converter tests to use
  `asyncio.run(...)`.

## P0.2 Acceptance

- Fast suite does not require a real API key.
- Fast suite does not depend on a hardcoded local PDF path.
- Fast suite excludes tests that require pdflatex.
- Remaining failures are recorded and attributable to missing repository assets,
  not to live LLM, LaTeX, or local PDF access.

## P5 Artifact Manifest Changes Applied

- Added econ/finance artifact manifest v1 validation and normalization.
- Manifest artifacts are resolved under `materials_root`, checked for path
  traversal, extension whitelist, missing files, and POSIX-like LaTeX paths.
- Added file-backed manifest adapters for `FigureSpec` and `TableSpec`.
- Added `figures_manifest` / `artifact_manifest_path` request support.
- For empirical result figures, `data_visualization` / `result_figure`
  artifacts must be file-backed; autonomous Dreamer generation is rejected.
- Added locked caption/provenance fields on figures and tables.

## P6 Standalone Runner Changes Applied

- Added explicit OpenAI-compatible `AppConfig` builder for local runs.
- All local runner agents receive the same explicit `model`, `base_url`, and
  `api_key`; no implicit OpenAI official base URL fallback is used.
- Added redacted config export so API keys never appear in saved audit config.
- Added `scripts/run_econ_paper.py` with request YAML loading, manifest
  validation, normalized request/manifest exports, `events.jsonl`, and mock
  no-LLM execution.
- Added `CODEX_TASKS.md` with common commands and construction rules.
- Added `outputs/` to `.gitignore` for generated local runner artifacts.

## P7 Test and CI Checks Applied

- Confirmed all Phase 7 econ/finance test files exist.
- Added the core econ invariant suite command to `CODEX_TASKS.md`.
- Core econ invariant suite passes locally.
- Fast suite remains at the recorded baseline failure set only.

## P8 Minimal PoC Changes Applied

- Mock runner now emits a structure-correct economics/finance draft using
  venue required sections.
- Mock output includes file-backed figures in their manifest sections.
- Runner writes `venue.normalized.json` for venue metadata checks.
- Added AER/JFE minimal PoC tests covering required sections, no legacy
  Experiment section, result figure placement, JFE anonymous/double-spacing/
  minimum-font hints, and output secret-pattern checks.

## P9 Backlog Hardening Applied

- Empirical result artifacts now require both `data_hash` and `code_hash`.
- Non-result conceptual artifacts remain allowed without provenance hashes.
- Added manifest tests for missing provenance rejection and non-result
  backwards compatibility.
