# EasyPaper v3 Risk Drill: Figure Block + Test Triage

Scope: static/source inspection only. I did not install `easypaper`, did not run `pip install`, and did not run the test suite.

## Hard verdict

- Figure unblock recommendation: choose Path B, file-backed injection with `FigureSpec(auto_generate=False, file_path=...)`, using real figures produced by EvoScientist/skill4econ econ analysis artifacts. Do not unlock result/data figures through Dreamer as the primary path.
- Regression survivability is not below 20 direct tests. Static file-level triage finds 31 pure/source-level files plus 15 direct files with mocks or in-process ASGI clients already present. That gives about 46 direct fork-regression files before considering guarded TeX/fixture files.
- Tier 3 econ_analysis_agent is required for trustworthy econ/result figures if Path B is the plan. It should be the upstream artifact producer, not an EasyPaper-internal Dreamer replacement. The cost is moderate, but lower than accepting unreliable LLM-fabricated econ figures.

## Figure unblock path analysis

### Evidence

- `src/agents/metadata_agent/figure_supplementation.py:11-18` whitelists only non-result roles: `conceptual_framework`, `taxonomy`, `pipeline`, `architecture`, `protocol`, `info_figure`.
- `src/agents/metadata_agent/figure_supplementation.py:20-27` maps those roles only to `infograph`, `flowchart`, and `architecture_diagram`.
- `src/agents/metadata_agent/figure_supplementation.py:144-155` `_choose_role()` never returns a result/data role; fallback is `info_figure`.
- `src/agents/metadata_agent/figure_supplementation.py:166-170` states the policy intent: autonomous supplementation is conservative and no result/data visualization target is allowed.
- `src/agents/metadata_agent/figure_supplementation.py:222-231` skips unsupported roles and hard-blocks `target_type == "data_visualization"` with `autonomous_data_visualization_forbidden`.
- `src/agents/metadata_agent/figure_supplementation.py:249-259` creates an autonomous `FigureSpec` with `auto_generate=True`, and the prompt explicitly says not to show empirical result curves, benchmark bars, metrics, or ablation data.
- `src/agents/metadata_agent/figure_generation.py:293-304` dynamically imports `academic_dreamer`; if missing, generation fails with the images-extra install message.
- `src/agents/metadata_agent/figure_generation.py:375-398` first resolves any existing `file_path`, disables `auto_generate` if the file exists, and only loads Dreamer for remaining auto-generated figures.
- `src/agents/metadata_agent/figure_generation.py:433-434` turns a generated Dreamer output into an ordinary `file_path` and flips `auto_generate=False`.
- `src/agents/metadata_agent/models.py:104-116` already models the file-backed path: `file_path`, `derived_file_path`, `auto_generate`, `generation_prompt`, `target_type`, and `semantic_role`.
- `src/agents/metadata_agent/metadata_utils.py:95-101` validates non-auto-generated figure paths against `materials_root`.
- `src/agents/metadata_agent/latex_helpers.py:22-30` collects only non-auto-generated figure paths that resolve on disk.
- `src/agents/metadata_agent/metadata_agent.py:913-939` only runs supplementation/generation when `enable_figure_supplementation` is true, then validates and converts figure files.
- `src/agents/metadata_agent/metadata_agent.py:947-967` removes supplemental figures after generation failure, so Dreamer failure is already treated as non-fatal optional material.
- `skill4econ/workflows.py:131-174` writes a real event-study plot from numeric event rows via matplotlib to `event_study_plot.png`.
- `skill4econ/workflows.py:1885-1899` collects event rows, calls `_write_event_plot`, and warns if a requested event plot cannot be generated.
- `skill4econ/contracts/artifact_manifest.py:20-36` classifies `.png`, `.jpg`, `.jpeg`, `.svg`, and `.pdf` as figures.
- `skill4econ/contracts/artifact_manifest.py:71-83` records artifact path, type, role, existence, size, and producer.

### Path A: unlock autonomous Dreamer data visualizations

Required edits:

- Add result/data roles to `ALLOWED_AUTONOMOUS_ROLES`.
- Add `ROLE_TO_TARGET_TYPE` entries such as `result_plot -> data_visualization`.
- Modify `_choose_role()` to select result/data roles.
- Remove or narrow the `autonomous_data_visualization_forbidden` block.
- Rewrite the supplementation prompt to allow empirical figures.
- Add tests covering allowed/blocked result figures, prompt constraints, Dreamer request payloads, and failure cleanup.

Estimated implementation cost: low to medium, about 0.5-1.5 engineering days for a minimal code change and tests.

Reliability risk: high. The current source deliberately forbids empirical result curves and metrics. Dreamer receives an idea/style/target payload, not a verified data table. For econometrics, this invites fabricated coefficients, synthetic confidence intervals, missing sample definitions, and visually plausible but non-auditable plots. This is exactly the kind of result figure a referee or reproduction check will reject.

Operational risk: medium. It adds dependency on `academic_dreamer` and the images extra for a path that currently degrades gracefully. It also increases prompt-policy surface area without solving data provenance.

### Path B: inject real external figures as file-backed FigureSpec

Required edits:

- Build a small adapter from EvoScientist/skill4econ output artifacts to EasyPaper metadata figures.
- Copy or reference figure files under `materials_root` and create `FigureSpec(id, caption, description, section, file_path, auto_generate=False, semantic_role, target_type)`.
- Prefer artifact-manifest discovery where available; otherwise use deterministic artifact naming such as `event_study_plot.png`.
- Add path-resolution and placement tests around `metadata_utils.validate_file_paths`, `preprocess_generated_figures`, and `latex_helpers.collect_figure_paths`.

Estimated implementation cost: medium, about 1-2 days if the econ artifact manifest is stable; 2-4 days if cross-repo orchestration, captions, and section placement need to be hardened.

Reliability risk: low to medium. The figure itself comes from econometric outputs, not an illustration model. Remaining risks are mostly integration risks: missing artifact paths, stale captions, wrong section assignment, and asset copy/relative-path handling.

Operational risk: medium. It introduces a cross-system contract, but EasyPaper already has the file-backed contract. The adapter can remain narrow and testable.

Recommendation: Path B. Path A is cheaper in code but expensive in scientific risk. Path B costs more integration work, but it preserves provenance and uses EasyPaper's existing path validation and LaTeX inclusion flow.

## Test suite triage

Found 50 `tests/test_*.py` files under `competitor_repos/easypaper-source/tests`.

### Pure/source-level or no real service/LLM

These are the safest direct fork-regression files by static inspection:

- `test_agent_discovery_contracts.py`
- `test_assign_references.py`
- `test_bugfix_body_section_generation.py`
- `test_canvas_translator.py`
- `test_dag_canvas_integration.py`
- `test_decomposed_generation.py`
- `test_docling_config.py`
- `test_execute_generation_exemplar.py`
- `test_exemplar_config.py`
- `test_exemplar_models.py`
- `test_exemplar_pipeline.py`
- `test_exemplar_prompt_injection.py`
- `test_figure_path_and_conclusion.py`
- `test_incremental_planning_models.py`
- `test_label_registry.py`
- `test_metadata_overflow_manager.py`
- `test_narrative_section_shape_guards.py`
- `test_plan_result_contract.py`
- `test_planner_format.py`
- `test_plugin_config_template_sync.py`
- `test_prepare_plan_pipeline.py`
- `test_research_context_models.py`
- `test_review_orchestrator_final_compile.py`
- `test_revision_executor_migration.py`
- `test_run_script.py`
- `test_sdk_without_fastapi.py`
- `test_table_direct_injection.py`
- `test_template_structure_profile.py`
- `test_tex_path_bootstrap.py`
- `test_usage_tracker.py`
- `test_writer_router_compat.py`

### Direct with mocks or in-process clients already present

These are direct-run candidates, but not pure: they use mocked LLM/http behavior, mocked imports, subprocess probes, or in-process ASGI/FastAPI clients.

- `test_compilation_pipeline.py`
- `test_core_ref_analyzer.py`
- `test_dag_migration.py`
- `test_docling_analyzer.py`
- `test_docling_enricher.py`
- `test_exemplar_analyzer.py`
- `test_exemplar_external_search.py`
- `test_exemplar_selector.py`
- `test_metadata_router_contracts.py`
- `test_research_context_builder.py`
- `test_sdk_client.py`
- `test_sdk_metadata_gen.py`
- `test_skills_bootstrap.py`
- `test_smart_caption_writer.py`
- `test_writer_router_endpoints.py`

Evidence:

- `tests/test_sdk_client.py:1-6` explicitly says all internal agents are mocked and no LLM calls are made.
- `tests/test_docling_analyzer.py:51-58` patches `httpx.AsyncClient` for downloader success.
- `tests/test_docling_analyzer.py:224-238` mocks the entire Docling import chain with `patch.dict("sys.modules", ...)`.
- `tests/test_docling_enricher.py:71-83` patches `_download_pdf` and `_parse_pdf`.
- `tests/test_exemplar_external_search.py:291-300` patches `PaperSearchTool` and uses an async mock result.
- `tests/test_metadata_router_contracts.py:12-22` uses an in-process FastAPI app and `httpx.ASGITransport`, not network.
- `tests/test_sdk_metadata_gen.py:56-69` injects a mocked `chat.completions.create`.
- `tests/test_smart_caption_writer.py:729-735` uses a fake API key and overrides `_llm_json_call` with `AsyncMock`.
- `tests/test_compilation_pipeline.py:390-418` uses a fake typesetter and stub model config for compile-pdf plumbing.
- `tests/test_sdk_without_fastapi.py:42-47` spawns a Python subprocess to verify SDK import without FastAPI; no network, but it is still a subprocess regression.

### Gated local external tool or real fixture

- `test_table_converter_enhanced.py`: mostly unit tests, but the fixture `blip2_track_meta` skips if the real metadata file is absent (`tests/test_table_converter_enhanced.py:25-30`), and `test_pdflatex_compiles_each_table_preview` performs a real pdflatex compile if pdflatex exists (`tests/test_table_converter_enhanced.py:1644-1685`). It has no decorator skip marker on that test, but it does have an inline `shutil.which("pdflatex")` guard at `tests/test_table_converter_enhanced.py:1650-1651`.
- `test_table_visual_preview.py`: has one inline pdflatex skip (`tests/test_table_visual_preview.py:98-99`), several mocked subprocess tests (`tests/test_table_visual_preview.py:256-265`, `tests/test_table_visual_preview.py:292-309`), and one decorator skipif for a real TeX compile (`tests/test_table_visual_preview.py:433-472`).

### Needs LLM API key, real PDF, or rewrite before fork regression

- `test_gemini.py`: no pytest test functions by inspection; it is a scratch script. Network calls are guarded under `__main__` (`tests/test_gemini.py:4-5`, `tests/test_gemini.py:58-59`). If run as a script, it requires `OPENROUTER_API_KEY` (`tests/test_gemini.py:15-23`) and calls `google/gemini-3-pro-preview` twice (`tests/test_gemini.py:26-35`, `tests/test_gemini.py:50-55`). Actual mock depth: zero.
- `test_parse_agent.py`: initializes with a hard-coded OpenRouter-style key and base URL (`tests/test_parse_agent.py:20-24`), and the parse test uses a hard-coded local PDF path (`tests/test_parse_agent.py:36-42`). If that file exists, it calls `agent.run(file_path=pdf_path)` (`tests/test_parse_agent.py:43-48`), which should be treated as live integration unless mocked.

### External service summary

- Real LLM/API risk: `test_gemini.py` if invoked as a script; `test_parse_agent.py::test_parse_pdf_output_format` if the hard-coded PDF path exists.
- Real pdflatex risk: `test_table_converter_enhanced.py` and `test_table_visual_preview.py`, both guarded, but the former needs an explicit marker for cleaner suite triage.
- Real Docling service risk: none in tests by static inspection. `src/agents/shared/docling_analyzer.py:201-209` lazily imports Docling and raises an install message, while tests mock the import chain.
- S3/AWS risk: no test file references were found in the static risk scan. `pyproject.toml:19` includes `boto3`, but there is no matching test-level S3 usage in this suite.

## Can run directly as fork regression

Recommended direct list:

- All files in "Pure/source-level or no real service/LLM".
- All files in "Direct with mocks or in-process clients already present".

That is about 46 files. Add `test_table_visual_preview.py` only if local pdflatex skips/runs are acceptable for the fork. Add the non-pdflatex portions of `test_table_converter_enhanced.py` with `-k "not pdflatex"` or after marking the real TeX test as integration.

## Needs mocks first

- `test_gemini.py`: convert to a real pytest test with mocked OpenAI client, or rename/mark as manual integration.
- `test_parse_agent.py`: remove the hard-coded key, parameterize the PDF fixture, and mock the LLM path or mark the parse test as integration.
- `test_table_converter_enhanced.py`: split or mark the real pdflatex preview test; keep the deterministic converter tests in the direct fork set.
- Optional cleanup: mark `test_table_visual_preview.py` real TeX tests consistently even though it already has runtime/decorator skips.

## v2 G open questions

### `test_gemini.py` actual mock depth

Verdict: no mocks. It is not a normal pytest regression. It only avoids network during pytest collection because all API calls are inside `main()` and `main()` is guarded by `if __name__ == "__main__"`.

Line evidence:

- `tests/test_gemini.py:4-5` says CI should not hit the API because calls are under `__main__`.
- `tests/test_gemini.py:12` imports `OpenAI` directly.
- `tests/test_gemini.py:15-23` reads `OPENROUTER_API_KEY` and constructs the real client.
- `tests/test_gemini.py:26-35` and `tests/test_gemini.py:50-55` call the model.
- `tests/test_gemini.py:58-59` invokes `main()` only as a script.

### Chinese/GBK encoding handling

Verdict: UTF-8 is explicit in many file reads/writes and subprocess decodes, but there is no GBK/chardet/cp936 fallback in EasyPaper. Current handling is "UTF-8 plus ignore/replace in selected paths", not robust Chinese/GBK autodetection.

Line evidence:

- `src/config/loader.py:38` reads config with `encoding="utf-8"`.
- `src/agents/typesetter_agent/typesetter_agent.py:963-964` decodes pdflatex output with UTF-8 and `errors="replace"`.
- `src/agents/shared/table_converter.py:2031-2043` runs pdflatex with `encoding="utf-8"` and `errors="replace"`.
- `src/agents/shared/table_converter.py:2051-2053` reads TeX logs as UTF-8 with `errors="ignore"`.
- `src/agents/shared/code_context/builder.py:173` decodes raw bytes as UTF-8 with `errors="ignore"`.
- `src/agents/shared/table_converter.py:2163-2165` reads table files as UTF-8 only.
- Exact grep for `gbk|GBK|gb18030|GB18030|chardet|charset_normalizer|cp936|cp950` across `src`, `tests`, `README.md`, `pyproject.toml`, and `setup.cfg` returned no matches.

## Final risk call

- Path A is a fast code unlock with high scientific and reviewer risk.
- Path B is the right unblock: consume true econ artifacts as ordinary figure files, keep EasyPaper's current non-result Dreamer policy, and make captions/placement/path handling the integration contract.
- Regression survivability is comfortably above 20 direct files. The high-risk test debt is concentrated in `test_gemini.py`, `test_parse_agent.py`, and the two pdflatex/fixture-heavy table preview files.
