# 07. User Experience Pack

## UX target

A non-programmer economics / finance / accounting / management scholar should be able to understand the output without reading logs or JSON first.

The v3 journey is:

```text
intake -> one command -> manuscript or lint pack -> AUTHOR_REPORT -> rerun loop
```

## Main commands

### Intake

```bash
econpaper intake \
  --run-dir path/to/skill4econ_run \
  --out intake_profile.json
```

This is a 15-30 minute structured author interview. It asks for design declaration, treatment timing, estimand, institutional context, contribution, outcome magnitude context, and venue.

### Lint

```bash
econpaper lint draft.tex \
  --run-dir path/to/skill4econ_run \
  --refs refs.bib \
  --out lint_pack
```

Checks a human-written draft against evidence, citations, and design gates.

### Write

```bash
econpaper write \
  --run-dir path/to/skill4econ_run \
  --intake intake_profile.json \
  --refs refs.bib \
  --venue aea \
  --out manuscript_pack
```

Generates a draft package.

### Rerun

```bash
econpaper rerun manuscript_pack \
  --run-dir path/to/updated_skill4econ_run \
  --out manuscript_pack_v2
```

Updates evidence, gates, claim statuses, and suggestions while preserving human-edited regions.

### Compile

```bash
econpaper compile manuscript_pack --venue aea
```

Runs the LaTeX compile loop. In v3, `--venue` controls formatting and templates, not journal-specific prose promises.

## Output directory: generation mode

```text
manuscript_pack/
  AUTHOR_REPORT.md
  main.pdf                 # produced when compile succeeds
  main.tex
  main.md
  sections/
    00_abstract.md
    01_introduction.md
    02_data.md
    03_empirical_strategy.md
    04_results.md
    05_robustness.md
    06_mechanisms.md
    07_heterogeneity.md
    08_limitations.md
    09_conclusion.md
    10_related_literature_skeleton.md
  tables/
    table_*.tex
    table_*.md
  figures/
  bibliography/
    refs.bib
  reports/
    internal/
      run_validation.json
      intake_profile.json
      design_profile.json
      evidence_ledger.json
      claim_ledger.json
      citation_index.json
      citation_safety_report.json
      magnitude_interpretations.json
      table_generation.json
      global_coherence.json
      rerun_diff.json
      reproduction_manifest.json
```

User-readable reports under `reports/` are capped at two: `AUTHOR_REPORT.md` at package root and optional `main.pdf`. JSON is internal.

## Output directory: lint mode

```text
lint_pack/
  AUTHOR_REPORT.md
  annotated_draft.tex
  annotated_draft.md
  reports/
    internal/
      extracted_claims.json
      evidence_ledger.json
      claim_ledger.json
      citation_safety_report.json
      design_profile.json
      lint_findings.json
```

## `AUTHOR_REPORT.md` structure

```text
# AUTHOR_REPORT

## 1. Status overview
- Draft status
- Compile status
- Data/artifact status
- Intake completeness
- Main risks

## 2. Safe claims
- Claims that are evidence-backed and design-compatible

## 3. Flagged and downgraded claims
- Serious reviewer risks
- Suggested rewrites
- Override instructions

## 4. Author-asserted claims
- Claim text
- Original system status
- Author reason
- Evidence gap or design concern

## 5. Non-overridable hard-blocks
- Fabricated number mismatches
- Missing citekeys used as citations
- Mock-as-real output

## 6. Missing diagnostics and citations
- DID/IV/RDD/finance diagnostics
- CITE_NEEDED items
- AUTHOR_INPUT_NEEDED items

## 7. Economic magnitude gaps
- Missing units, means, SDs, scale, benchmarks

## 8. Global coherence findings
- Cross-section numeric consistency
- Dangling references
- Promises vs delivered results
- Hedging density

## 9. Next best actions
- Ordered list of highest-leverage author or estimation tasks

## 10. Expected referee questions
- Design-specific questions emitted by gates
```

## Scholar-facing status language

Use decisive language:

```text
Status: Draft generated with three flagged claims and one missing diagnostic.
```

Do not use log-like language:

```text
Pipeline completed with warnings; see claim_gate_report.json.
```

## Failure-as-memo behavior

If the run fails, the output should still be useful.

Example:

```text
Status: No verified Results section generated.

Why:
- status.json contains unknown status `weird_completed_state`.
- model_table.json is present but cannot be treated as verified evidence.

What you can do next:
1. Re-run skill4econ and produce validation_report.json.
2. If this is a custom estimator, register the method or add an author assertion.
3. You may still use lint mode to check citations and nonnumeric prose.
```

## Incremental rerun UX

After rerun, `AUTHOR_REPORT.md` should say:

```text
Claim status changes since previous pack:
- claim_007 upgraded from flag_and_confirm to safe after Callaway-Sant'Anna output was added.
- claim_012 unchanged: mechanism proxy still suggestive_only.
- claim_018 newly flagged: abstract now makes an external-validity claim not present in limitations.

Protected author edits:
- sections/04_results.md paragraph 3 was edited by the author; econpaper did not overwrite it.
- Suggested replacement is shown below the protected paragraph.
```

## LaTeX compile loop UX

`main.pdf` is no longer "optional if LaTeX succeeds" without explanation.

Behavior:

1. compile;
2. auto-fix common errors: escaping, missing packages, dangling refs, bibliography path;
3. retry;
4. if still failing, produce markdown fallback and write a human-readable compile memo in `AUTHOR_REPORT.md`.

## Venue semantics

In v3:

```text
--venue aea
--venue jf-jfe
--venue generic-field-journal
```

controls:

- LaTeX template;
- abstract length target;
- table note conventions;
- citation package;
- appendix naming;
- star/no-star default.

It does not claim to tailor intellectual framing to AER, JFE, QJE, or any specific ABS journal in P0.

## What makes users trust the product

- Linter finds real draft problems quickly.
- Generated numbers are deterministic.
- Main results have economic magnitude, not just significance.
- Tables look publishable.
- The report explains next actions in scholar language.
- Rerun preserves human edits.
