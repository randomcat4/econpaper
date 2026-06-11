# 08. Implementation Order

## Build sequence

### Step 1: fail-closed status and method handling

Keep the v2 safety foundation.

- Unknown status -> no automatic verified claims.
- Unknown method -> no automatic paper-ready claims.
- Missing validation report -> no automatic Results section.
- Missing artifact manifest -> no claimable result writing.
- Mock output -> visible smoke-test watermark.

### Step 2: linter MVP first

Build the wedge product before full prose generation.

- Implement `econpaper lint`.
- Extract numbers, cite commands, causal/mechanism/external-validity phrases.
- Compare numbers to evidence ledger.
- Validate citekeys.
- Emit `AUTHOR_REPORT.md` and annotated draft.

### Step 3: intake interview

- Implement `econpaper intake`.
- Collect declared design, timing, estimand, institutional context, contribution statement, motivation, outcome magnitude context, and venue.
- Produce `intake_profile.json`.
- Add `[AUTHOR_INPUT_NEEDED]` handling.

### Step 4: evidence ledger plus magnitude semantics

- Parse native `skill4econ` model tables.
- Build cell-level evidence ledger.
- Add `variable_semantics`.
- Connect summary statistics to model-table claims.

### Step 5: deterministic numeric renderer

- Convert claim prose to placeholder templates.
- Render all coefficients, SEs, p-values, N, percentages, percentage points, and magnitude calculations from ledger slots.
- Audit rendered numbers.

### Step 6: publication table generator

- Generate booktabs tables from `model_table.json`.
- Support panels, notes, star/no-star policy, fixed effects, clustering notes, sample rows, and variable labels.
- Produce markdown fallback tables.

### Step 7: claim ledger with three-tier gates and override

- Implement `hard_block`, `flag_and_confirm`, `style_advice`, `safe`, and `author_asserted` statuses.
- Add author override fields.
- Convert design gates to declare-and-confirm mode.
- Add reviewer questions and suggested rewrites.

### Step 8: section writers including abstract

Implement in this order:

1. Data.
2. Empirical Strategy.
3. Main Results.
4. Robustness.
5. Limitations.
6. Mechanisms.
7. Heterogeneity.
8. Conclusion.
9. Abstract and title candidates.
10. Introduction skeleton.
11. Related Literature skeleton.

Do not start with Introduction.

### Step 9: global coherence and AUTHOR_REPORT

- Check abstract / intro / results / conclusion numeric consistency.
- Check promises vs delivered sections.
- Check dangling references.
- Check terminology consistency.
- Check hedging density.
- Consolidate all user-facing reports into `AUTHOR_REPORT.md`.

### Step 10: incremental rerun

- Detect changed artifacts.
- Rebuild evidence and claim ledgers.
- Emit claim status diff.
- Protect human-edited regions using markers and hashes.

### Step 11: quality tests and human release gate

- Keep all fifteen false-confidence fixtures.
- Add Q-series quality tests.
- Run at least five real scholar evaluations.
- Require median generated-text retention >= 50%.

## First 10 PRs

1. `run_status_fail_closed_and_mock_watermark`
2. `lint_mode_claim_extractor_mvp`
3. `citation_safety_refs_bib_and_cite_needed`
4. `intake_profile_schema_and_cli`
5. `evidence_ledger_model_table_cells`
6. `variable_semantics_and_magnitude_slots`
7. `deterministic_numeric_renderer_placeholders`
8. `publication_table_generator_booktabs`
9. `claim_ledger_three_tier_override`
10. `author_report_consolidation_and_lint_pack`

## Second 10 PRs

11. `design_profiler_declare_and_confirm`
12. `did_iv_rdd_finance_gate_conversion`
13. `section_writer_data_strategy_results`
14. `abstract_title_writer`
15. `global_coherence_pass`
16. `incremental_rerun_claim_diff`
17. `human_edit_region_protection`
18. `latex_compile_loop_templates`
19. `quality_tests_q_series`
20. `five_scholar_release_trial_harness`

## Release blockers

- Any non-overridable hard-block not caught.
- Any generated numeric value not rendered from the ledger.
- Any missing citekey emitted as a citation command.
- Any mock output not watermarked.
- Any main Results paragraph without economic magnitude explanation.
- Any run without consolidated `AUTHOR_REPORT.md`.
- Human evaluation median generated-text retention below 50%.
