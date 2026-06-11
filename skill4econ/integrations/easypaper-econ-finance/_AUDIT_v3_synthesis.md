# EasyPaper Audit v3 Synthesis

Date: 2026-06-10
Scope: synthesis of `_AUDIT_v3_integration.md`, `_AUDIT_v3_patch_spec.md`, and `_AUDIT_v3_risks.md`. Static/source inspection only; no `pip install easypaper`.

## 0. Decision

**Fork + integrate is feasible.** The two hard preconditions from the brief do not block:

1. **GitHub upstream exists.** `https://github.com/PinkGranite/EasyPaper` is public. `master`, `HEAD`, and tag `v0.2.4` all resolve to `8797d4bf9cd8680f4da2d8b322533364d602b82d`. PyPI 0.2.4 was uploaded minutes after that tag and the local `competitor_repos/easypaper-source` tree matches the PyPI sdist shape.
2. **ccproxy is compatible for the main path.** EasyPaper centralizes OpenAI-compatible text model calls through `LLMClient -> AsyncOpenAI(**kwargs)`, and agents pass explicit `base_url` from `ModelConfig`. EvoScientist must inject an EasyPaper config with `base_url=http://127.0.0.1:<ccproxy_port>/codex/v1` and `api_key=ccproxy-oauth`; env-only routing is not enough.

**Recommended path:** fork upstream at `v0.2.4` / `8797d4bf...`, keep upstream remote for manual merges, and build a thin EvoScientist wrapper around `EasyPaper.generate_stream()` rather than merging EasyPaper's internal agents into EvoScientist YAML one by one.

## 1. Upstream Viability

Upstream tracking is viable but fragile.

- Repo exists, public, unarchived, default branch `master`.
- Tag `v0.2.4` exists and equals current `master`.
- No open issues and no open PRs.
- Six closed PRs, all by `PinkGranite`.
- Recent commits are effectively one-author (`Yuwei Yan` / `PinkGranite`).
- GitHub Releases are unused; version tracking should use tags, not releases.

Decision implication:

- **Do not downgrade to PyPI-only vendoring.**
- **Do not track floating `master`.**
- Use a hard fork baseline at `v0.2.4`, document upstream SHA, and treat upstream merges as manual review events because bus factor is low.

## 2. Integration Architecture

The integration should wrap EasyPaper as a subsystem.

Primary wrapper contract:

1. EvoScientist starts/ensures ccproxy with existing `maybe_start_ccproxy()`.
2. EvoScientist constructs an EasyPaper `AppConfig` in memory or writes a temporary config YAML.
3. Every EasyPaper OpenAI-compatible model gets:
   - `api_key: ccproxy-oauth`
   - `base_url: http://127.0.0.1:<ccproxy_port>/codex/v1`
4. The wrapper calls `EasyPaper(config=app_config).generate_stream(...)`.
5. Progress events are translated into EvoScientist channel/thinking events at the tool/subagent layer.

LangGraph nuance:

- EasyPaper does use LangGraph in several internal agents (`commander`, `parse`, `template`, `typesetter`, `vlm_review`).
- The main SDK path is still a clean boundary: `EasyPaper.generate()` -> `MetaDataAgent.generate_paper()` -> `prepare_plan()` -> `execute_generation()`.
- Therefore, do not deeply merge internal StateGraphs into EvoScientist's `langgraph_dev` manifest for Tier 1.5. Add a wrapper graph/subagent only if async execution is needed.

Known caveat:

- Optional Claude VLM is not `base_url`-injectable in EasyPaper source because `ClaudeVLM` constructs `anthropic.AsyncAnthropic(api_key=api_key)` without forwarding `base_url`.
- First integration should use OpenAI VLM through ccproxy or disable VLM review. Patch Claude VLM only if Anthropic VLM is required.

## 3. Tier 1.5 PoC Scope

Tier 1.5 is not just two tiny edits. Flow tracing found hidden dependencies that expand the patch scope.

Required patch areas:

1. `PaperMetaData.to_document_input(venue_config=...)`
   - Copy `venue_config.required_sections` into `GenerationConstraints.required_sections`.
   - Prefer `target_pages`; otherwise use venue page limit.
   - Expand `content_brief` with section-specific econ keys such as `empirical_strategy`, `results`, and `robustness`.

2. Planning request contract
   - `PlanRequest` currently carries legacy five-field metadata only.
   - Add `content_brief` and `constraints`.
   - `ReviewOrchestrator._create_paper_plan()` should build a `DocumentInput` and pass these fields to the planner.

3. Planner required-section enforcement
   - Add required-section prompt text.
   - Add deterministic post-LLM insertion/normalization for required sections.
   - Keep legacy ML defaults intact.
   - Add econ section ids/titles/sources/dependencies: `data`, `empirical_strategy`, `results`, `robustness`.

4. Section generation data source
   - Replace body-section `getattr(metadata, source)` with `DocumentInput.content_brief` lookup.
   - Keep `BODY_SECTION_SOURCES` as fallback dispatch, but read its keys from `content_brief`.

5. Assembly artifact order
   - `_compile_pdf` already uses `paper_plan.get_compile_section_order()`.
   - Saved root `main.tex` still uses `assembly_helper`'s hard-coded ML-ish order.
   - Patch assembly to accept plan order/titles so exported artifacts match the PDF path.

Acceptance criterion:

- With venue required sections `[Introduction, Data, Empirical Strategy, Results, Robustness, Conclusion]`, planner output and saved artifacts preserve that order, and no new section id requires a matching `PaperMetaData` attribute.

## 4. Econ Venue YAMLs

Draft venue specs should be created only during implementation, not in this audit pass.

Use hyphenated full names:

- `american-economic-review`
- `quarterly-journal-of-economics`
- `journal-of-financial-economics`

Required sections for all three:

```yaml
required_sections: [Introduction, Data, Empirical Strategy, Results, Robustness, Conclusion]
```

Limits from public guides:

- AER: 40 pages at 11pt / 1.5 spacing / 1-inch margins, or 45 pages at 12pt; abstract 100 words.
- QJE: abstract 250 words; first page includes total word count; no hard full-manuscript page limit found in public instructions.
- JFE: anonymous PDF, abstract 100 words, double-spaced, 12pt or larger, at least 1-inch margins; no hard full-manuscript page limit found in public instructions.

## 5. Figure Decision

Use **Path B: injected real figures**.

Do not unlock EasyPaper's autonomous Dreamer path for empirical/result plots as the primary route.

Why:

- EasyPaper intentionally whitelists only non-result roles for autonomous supplementation.
- It hard-blocks `target_type == "data_visualization"` with `autonomous_data_visualization_forbidden`.
- The autonomous prompt explicitly forbids empirical result curves, benchmark bars, metrics, and ablation data.
- Dreamer-style generated econ figures would be scientifically risky: fabricated coefficients, CIs, magnitudes, or sample definitions are unacceptable.

Path B contract:

- EvoScientist/skill4econ/econ analysis produces real figure artifacts.
- Adapter creates `FigureSpec(..., file_path=..., auto_generate=False, semantic_role=..., target_type=...)`.
- EasyPaper validates paths, converts/stages figures, and includes them through its existing LaTeX path.

Decision implication:

- Tier 3 `econ_analysis_agent` is not a fork-decision blocker, but it is the right provenance path for trustworthy econ figures.
- Tier 1.5 can proceed without building Tier 3, as long as it supports file-backed `FigureSpec` injection.

## 6. Regression Cost

Regression survivability is better than feared.

Static triage found:

- 50 `tests/test_*.py` files.
- About 46 files are plausible direct fork-regression candidates, including pure/source-level tests and tests that already mock LLM/http/Docling behavior.
- Regression survivability is **not below 20**.

Needs cleanup before being treated as reliable regression:

- `test_gemini.py`: not a pytest regression; no mocks; only avoids network because calls sit under `if __name__ == "__main__"`.
- `test_parse_agent.py`: hard-coded OpenRouter-style key and local PDF path; treat as live integration unless mocked.
- `test_table_converter_enhanced.py`: mostly unit tests, but includes guarded real `pdflatex`; add marker/split for clean triage.
- `test_table_visual_preview.py`: already guarded/skipped in places, but should be marked consistently.

Encoding note:

- EasyPaper generally uses explicit UTF-8 and some `errors="replace"`/`ignore` for subprocess/log paths.
- There is no GBK/chardet/cp936 fallback. Chinese/Windows robustness is not solved by EasyPaper itself.

## 7. Work Estimate

Rough engineering estimate after this audit:

- Fork baseline + upstream remote + pin documentation: **0.5 day**
- ccproxy-backed EasyPaper wrapper with streaming event translation: **1-2 days**
- Tier 1.5 required-section/content-brief patch and focused tests: **2-4 days**
- Econ venue YAMLs and skill registry wiring: **0.5-1 day**
- Figure Path B adapter for existing econ artifacts: **1-3 days**, depending on artifact manifest stability
- Test triage cleanup and smoke regression list: **1 day**

Practical Tier 1.5 PoC budget: **5-8 engineering days**.

Not included:

- Full Tier 2 schema migration.
- Full Tier 3 econ analysis agent design/build.
- Claude VLM base-url patch unless needed.
- End-to-end live LLM/PDF production hardening.

## 8. Final Recommendation

Proceed.

The fork decision should not be blocked by missing upstream or ccproxy incompatibility; both are manageable. The fork should be conservative: pin `v0.2.4`, wrap the SDK boundary, inject ccproxy config explicitly, and keep EasyPaper's internal LangGraph machinery boxed behind `generate_stream()`.

The real Tier 1.5 risk is schema/dataflow: required sections must travel through `DocumentInput.constraints`, planner must honor them deterministically, and section generation must stop assuming every source key is a `PaperMetaData` attribute. The real Tier 3 risk is figure provenance: use injected real econ figures, not autonomous illustrative generation.
