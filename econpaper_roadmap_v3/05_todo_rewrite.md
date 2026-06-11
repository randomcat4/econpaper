# 05. TODO Rewrite

## Priority principle

P0 is no longer only "safe generation." P0 is two product forms sharing the same ledgers and gates:

```text
Shape A: claim linter for human drafts
Shape B: generation pipeline for artifact-backed draft packages
```

Both forms must serve the three layers:

```text
safety -> content -> iteration
```

## P0: shared foundation

### Run validation and provenance

- [ ] Unknown run status fails closed for automatic claims.
- [ ] Unknown method fails closed for automatic claims.
- [ ] Parser-only, adapter-only, missing-dependency, failed, and mock runs cannot produce verified claims.
- [ ] Public paths are portable and relative.
- [ ] Internal provenance is redacted outside `reports/internal/`.

### Evidence ledger

- [ ] Parse native `skill4econ` model tables to cell-level evidence.
- [ ] Store model id, sample id, estimator, row, column, statistic, coefficient, standard error, p-value, confidence interval, and provenance hash.
- [ ] Add `variable_semantics` with unit, scale, mean, standard deviation, standardization, transformation, and winsorization.
- [ ] Treat arbitrary unparsed external tables as non-claimable unless imported through the P1+ importer track.

### Claim ledger

- [ ] Generate placeholder-based claim templates.
- [ ] Add numeric slot ids for every number.
- [ ] Store tier decisions: `hard_block`, `flag_and_confirm`, `style_advice`, `safe`, `author_asserted`.
- [ ] Add `author_override` with `asserted`, `reason`, and `original_status`.
- [ ] Record reviewer questions and next actions per claim.

### Citation safety

- [ ] Parse `refs.bib`.
- [ ] Validate citekeys.
- [ ] Emit `CITE_NEEDED` instead of fake references.
- [ ] Accept structured external literature notes.
- [ ] Reject external generated prose as direct manuscript input.

## P0 Shape A: claim linter TODO

### CLI

- [ ] Implement `econpaper lint draft.tex --run-dir ... --refs refs.bib --out lint_pack`.
- [ ] Accept `draft.md` in addition to `draft.tex`.
- [ ] Extract numeric claims, citation commands, table/figure references, and causal/mechanism/external-validity language.
- [ ] Map draft claims to claim ledger or create candidate claim ids.
- [ ] Produce an annotated draft with inline comments.
- [ ] Produce `AUTHOR_REPORT.md` with safe, flagged, author-asserted, and hard-blocked claims.

### Linter rules

- [ ] Hard-block invented numbers.
- [ ] Hard-block nonexistent citekeys.
- [ ] Hard-block mock-as-real output.
- [ ] Flag-and-confirm identification and contribution risks.
- [ ] Style-advice only for wording preferences.
- [ ] Allow author override with reason.

### Why this is the wedge

- [ ] Does not require the generated prose to be good.
- [ ] Demonstrates value on the author's existing draft.
- [ ] Forces ledger and gate quality early.
- [ ] Builds trust before full generation.

## P0 Shape B: generation pipeline TODO

### Intake

- [ ] Implement `econpaper intake --out intake_profile.json`.
- [ ] Collect declared design, treatment timing, estimand, institutional timeline, contribution sentence, motivation, outcome magnitude context, target venue.
- [ ] Mark missing author inputs explicitly.
- [ ] Ensure LLM does not invent missing institutional or contribution details.

### Design profiler

- [ ] Change from inference-first to declare-and-confirm.
- [ ] Compare author-declared design to artifacts.
- [ ] Report contradictions rather than erasing the declaration.
- [ ] Use conservative inference only when intake is absent.

### Economic magnitude interpreter

- [ ] Compute unit changes, standard-deviation changes, and mean-relative changes.
- [ ] Separate percent from percentage points.
- [ ] Ask intake for missing scale information.
- [ ] Require each main Results paragraph to include magnitude interpretation.

### Deterministic numeric renderer

- [ ] Require placeholders in LLM prose.
- [ ] Fill coefficients, SEs, p-values, N, percentages, and magnitude calculations after prose generation.
- [ ] Audit every rendered number.

### Publication table generator

- [ ] Generate booktabs LaTeX tables from `model_table.json`.
- [ ] Support panels, variable labels, sample rows, fixed-effect rows, star/no-star policies, and notes.
- [ ] Generate markdown fallback tables.

### Section writers

- [ ] Write Data, Empirical Strategy, Results, Robustness, Mechanisms, Heterogeneity, Limitations, Conclusion, Abstract, Introduction skeleton, and Related Literature skeleton.
- [ ] Add `sections/00_abstract.md`.
- [ ] Do not start implementation with Introduction.

### Global coherence

- [ ] Check abstract / intro / results / conclusion numeric consistency.
- [ ] Check promises vs delivered sections.
- [ ] Check dangling table and figure references.
- [ ] Check terminology consistency.
- [ ] Check hedging density.

### AUTHOR_REPORT

- [ ] Merge all scholar-facing reports into `AUTHOR_REPORT.md`.
- [ ] Move JSON ledgers and reports into `reports/internal/`.
- [ ] Include Author-asserted claims section.
- [ ] Include claim status diff after reruns.

## P0 iteration layer TODO

### Incremental rerun

- [ ] Implement `econpaper rerun manuscript_pack --run-dir updated_run --out updated_pack`.
- [ ] Detect new artifacts and changed evidence.
- [ ] Recompute gate decisions.
- [ ] Emit claim status diff.
- [ ] Preserve human-edited regions using markers and paragraph hashes.
- [ ] Suggest updates beside protected regions rather than overwriting them.

## P1 TODO

### LaTeX compile loop

- [ ] Implement compile, common-error repair, retry, and markdown fallback.
- [ ] Generate `main.pdf` when possible.
- [ ] If PDF fails, produce human-readable compile memo in `AUTHOR_REPORT.md`.
- [ ] Add AEA and JF/JFE-style templates.
- [ ] Make `--venue` control template and formatting only.

### External output importer track

- [ ] Design importer contract for Stata / R / Python outputs.
- [ ] Parse external tables into cell-level evidence.
- [ ] Preserve model/sample ids and inference notes.
- [ ] Keep unparsed tables as appendix artifacts only.

### Bibliography adapters

- [ ] Better BibTeX exported `.bib` support.
- [ ] Optional Zotero local/web adapter.
- [ ] Metadata enrichment via Crossref/OpenAlex/Semantic Scholar.

## P2 TODO

- [ ] Literature discovery suggestions.
- [ ] PDF folder RAG that emits structured notes only.
- [ ] Contribution gap memo from structured notes.
- [ ] Venue-specific prose style adaptation.
- [ ] Advanced journal template packs.
- [ ] Broader field-specific gate packs for accounting, management, political economy, IO, health, labor, and development.

## Low-leverage work to avoid in P0

- [ ] Do not build web search.
- [ ] Do not build a reference manager.
- [ ] Do not build citation graph UI.
- [ ] Do not build arbitrary regression-table parser before native `skill4econ` path works.
- [ ] Do not add more independent reports instead of improving `AUTHOR_REPORT.md`.
