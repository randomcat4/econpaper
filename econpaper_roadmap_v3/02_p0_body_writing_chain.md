# 02. P0 Body Writing Chain

## Goal

Make the manuscript body useful, not merely safe. The output should feel like a strong empirical RA prepared a disciplined draft package: accurate numbers, readable magnitude interpretation, publication-grade tables, and a consolidated explanation of what the author still needs to do.

The implementation order still should not start with Introduction. Start with the sections where artifacts can actually constrain writing: Data, Empirical Strategy, Results, and tables. Abstract comes after claims exist, but it is a P0 writer.

## P0 module 1: `intake_interview`

Layer: content.

### Input

- optional author spec YAML;
- optional prior `research_context.md`;
- structured interview answers;
- optional target venue;
- optional preferred contribution sentence.

### Interview fields

- declared design type;
- treatment / exposure / shock definition;
- treatment timing, including staggered adoption and anticipation windows;
- estimand in author language;
- unit of observation and sample scope;
- institutional background timeline;
- policy / event details;
- research motivation;
- one-sentence contribution claim;
- outcome variable magnitude context: units, mean, standard deviation, meaningful benchmark changes;
- target venue and formatting family;
- author-provided literature notes, if available.

### Output

`intake_profile.json` containing:

- project metadata;
- declared design;
- timing profile;
- estimand statement;
- institutional context entries;
- contribution statement;
- outcome magnitude context;
- target venue;
- missing author inputs.

### Hard rules

- Hard rule (overridable: yes, by supplying author input): institutional, historical, regulatory, and contribution details not provided by the author become `[AUTHOR_INPUT_NEEDED]`; the LLM must not invent them.
- Hard rule (overridable: yes, by author assertion): if the author asks for a contribution or institutional claim not supported by intake, the claim may be written only as author-asserted and must be listed in `AUTHOR_REPORT.md`.
- Hard rule (overridable: no): the system must distinguish author-provided facts from LLM-suggested prose.

## P0 module 2: `run_validator`

Layer: safety.

### Input

- `skill4econ` run directory;
- `status.json`;
- `artifact_manifest.json`;
- `validation_report.json`;
- model tables and diagnostics.

### Output

`reports/internal/run_validation.json`.

### Hard rules

- Hard rule (overridable: no for automatic claims): unknown run status does not become success-with-warnings.
- Hard rule (overridable: no for automatic claims): unknown method does not become paper-ready.
- Hard rule (overridable: no for automatic claims): parser-only, missing-dependency, adapter-only, failed, or mock runs cannot generate verified empirical result claims.
- Hard rule (overridable: yes, by author assertion): the author may manually keep or add a statement after validation failure, but it is marked as author-asserted and not verified.

## P0 module 3: `design_profiler`

Layer: safety and content.

### Input

- `intake_profile.json`;
- run validation output;
- evidence ledger;
- model metadata;
- diagnostics;
- optional author amendments.

### Output

`design_profile.json` containing:

- `declared_by_author`;
- declared design type;
- checked design type;
- consistency checks;
- contradicted or missing artifacts;
- estimand scope;
- assumptions;
- diagnostics present and missing;
- three-tier claim levels;
- reviewer questions;
- next actions.

### Declare-and-confirm behavior

The profiler checks the author's declaration. It should say:

```text
You declared staggered DID. The artifacts contain TWFE and an event-study plot, but no modern staggered estimator. Causal DID language is flag-and-confirm, not automatically generated as fully supported.
```

It should not say:

```text
Design inference failed. Everything is blocked.
```

unless the author skipped intake and artifacts are insufficient.

### Hard rules

- Hard rule (overridable: yes, by author declaration or override): lack of machine inference alone is not a reason to erase the author's declared design.
- Hard rule (overridable: yes, with `author_asserts`): if declared design and artifacts conflict, the conflict is reported and claims are `flag-and-confirm`, not silently rewritten.
- Hard rule (overridable: no for automatic causal prose): when intake is absent and design cannot be inferred, the system must not automatically generate causal or identification language.

## P0 module 4: `evidence_ledger_builder`

Layer: safety.

### Input

- validated artifact manifest;
- structured model tables;
- figure metadata;
- diagnostic files;
- sample construction metadata;
- variable metadata.

### Output

`evidence_ledger.json` with cell-level and panel-level references.

### Required mapping

A numeric result claim must map to:

```text
artifact_id
artifact_type
panel / row / column / statistic
model_id
sample_id
estimator
coefficient / effect / statistic
standard error / confidence interval / p-value if available
diagnostic status
variable_semantics reference
provenance hash
```

### Hard rules

- Hard rule (overridable: no): a table path, figure path, or PDF page is not enough evidence for a numeric result sentence.
- Hard rule (overridable: no): all ledger numeric values must preserve machine precision; display rounding happens only in the numeric renderer.
- Hard rule (overridable: yes, by author assertion): if a result exists only in an unparsed table, the author may describe it manually, but it is listed as author-asserted and not verified.

## P0 module 5: `economic_magnitude_interpreter`

Layer: content.

### Input

- `evidence_ledger.json`;
- `intake_profile.json`;
- summary statistics artifacts;
- variable semantics;
- outcome means, standard deviations, units, transformations, and standardization rules.

### Output

- `reports/internal/magnitude_interpretations.json`;
- magnitude slots inside `claim_ledger.json`.

### Required output examples

```text
0.03 units equals 0.40 outcome standard deviations.
0.03 units equals 12% of the control-group mean.
A 10 percentage point treatment increase corresponds to a 1.2 percentage point outcome change.
```

### Hard rules

- Hard rule (overridable: no for automatic claims): Results paragraphs with main estimates are incomplete without economic magnitude interpretation.
- Hard rule (overridable: yes, by intake update): if unit, mean, standard deviation, or scale is missing, request author input or mark `[AUTHOR_INPUT_NEEDED]`; do not invent magnitude context.
- Hard rule (overridable: no): percentage points and percent changes must be represented as distinct slot types.

## P0 module 6: `claim_ledger_builder`

Layer: safety.

### Input

- evidence ledger;
- design profile;
- citation index;
- magnitude interpretations;
- intake profile;
- section plan.

### Output

`claim_ledger.json` containing:

- claim ids;
- claim type;
- prose template with placeholders;
- numeric slot ids;
- evidence refs;
- citation refs;
- gate tier;
- suggested rewrite;
- reviewer questions;
- author override object.

### Hard rules

- Hard rule (overridable: no): a claim with numeric values is generated as a template with placeholders, not raw digits.
- Hard rule (overridable: no): fabricated numbers, fabricated citations, and mock-as-real outputs are non-overridable hard-blocks.
- Hard rule (overridable: yes): identification, mechanism, contribution, and external-validity language outside available diagnostics becomes `flag-and-confirm` with author override path.

## P0 module 7: `deterministic_numeric_renderer`

Layer: content and safety.

### Input

- claim ledger templates;
- evidence ledger numeric slots;
- rounding policy;
- percentage vs percentage-point slot metadata;
- venue formatting rules.

### Output

- rendered section text;
- rendered table notes;
- numeric-rendering audit in `reports/internal/numeric_rendering.json`.

### Process

LLM-generated prose may contain placeholders such as:

```text
{{coef:claim_main_001}}
{{se:claim_main_001}}
{{pvalue:claim_main_001}}
{{magnitude:claim_main_001}}
{{n:sample_primary}}
```

The renderer fills the placeholders after the prose is accepted.

### Hard rules

- Hard rule (overridable: no): the LLM must not directly write coefficients, standard errors, p-values, sample sizes, percentages, or percentage points.
- Hard rule (overridable: no): Test 4, invented coefficient blocked, is a fallback check only; it must not be the primary numeric safety mechanism.
- Hard rule (overridable: no): if a numeric placeholder cannot be resolved, the sentence is not rendered as a numeric claim.

## P0 module 8: `publication_table_generator`

Layer: content.

### Input

- `model_table.json`;
- evidence ledger;
- variable label mapping;
- panel definitions;
- star policy;
- venue template;
- table-note policy.

### Output

- `tables/table_*.tex` using booktabs;
- `tables/table_*.md` for markdown fallback;
- table metadata in `reports/internal/table_generation.json`.

### Table capabilities

- panels and model groups;
- variable-name beautification;
- coefficient and standard error formatting;
- p-value / t-stat / confidence interval policy;
- star policy including a no-star option;
- sample size rows;
- fixed-effect rows;
- clustering and inference notes;
- provenance notes.

### Hard rules

- Hard rule (overridable: no): publication tables are generated from structured model data; arbitrary table artifacts are not assumed to be publication-ready.
- Hard rule (overridable: yes, by author style setting): star policies are configurable and must be disclosed in table notes.
- Hard rule (overridable: no): every displayed table number must map back to the evidence ledger.

## P0 module 9: `section_planner_and_writers`

Layer: content.

### Input

- intake profile;
- design profile;
- claim ledger;
- citation index;
- publication tables;
- magnitude interpretations.

### Output sections

```text
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
```

### Writing order

1. Data.
2. Empirical Strategy.
3. Results.
4. Robustness.
5. Mechanisms.
6. Heterogeneity.
7. Limitations / External Validity.
8. Conclusion.
9. Abstract and title candidates.
10. Introduction skeleton.
11. Related Literature skeleton.

### Hard rules

- Hard rule (overridable: no): section writers write from claim ledger templates and author-provided context, not directly from raw artifacts.
- Hard rule (overridable: yes, by author override): flagged language can be written when the author asserts it, but the author assertion is recorded.
- Hard rule (overridable: yes, by adding notes): literature positioning and institutional context require author notes or structured external notes; otherwise use `[AUTHOR_INPUT_NEEDED]` or `CITE_NEEDED`.

## P0 module 10: `abstract_title_writer`

Layer: content.

### Input

- final or current claim ledger;
- intake contribution statement;
- design profile;
- rendered main result claims;
- target venue abstract-length policy.

### Output

- `sections/00_abstract.md`;
- two to three candidate titles;
- abstract consistency checks in `AUTHOR_REPORT.md`.

### Hard rules

- Hard rule (overridable: no): abstract numbers must be rendered from the same ledger slots used in Results.
- Hard rule (overridable: yes, by author assertion): contribution language not supported by intake or structured literature notes becomes `flag-and-confirm`.
- Hard rule (overridable: no): the abstract cannot claim results, samples, or designs absent from the claim ledger.

## P0 module 11: `global_coherence_pass`

Layer: content and safety.

### Input

- all rendered sections;
- claim ledger;
- publication tables;
- citation index;
- figure/table numbering map;
- design profile.

### Output

Coherence section inside `AUTHOR_REPORT.md` and machine-readable output in `reports/internal/global_coherence.json`.

### Checks

- abstract, introduction, results, and conclusion use the same main numbers;
- intro promises are delivered in results or marked as planned;
- result claims point to existing tables or figures;
- table and figure references are not dangling;
- terminology is consistent across sections;
- hedging density stays below the threshold;
- limitations match design scope.

### Hard rules

- Hard rule (overridable: no): contradictory numeric claims across sections are non-overridable if the contradiction is ledger-based.
- Hard rule (overridable: yes, by author override): contribution and scope disagreements become flagged author-decision items.
- Hard rule (overridable: no): unresolved table / figure references must be fixed or listed before the package is marked complete.

## P0 module 12: `AUTHOR_REPORT_packager`

Layer: safety, content, and iteration.

### Input

- run validation;
- claim ledger;
- citation safety output;
- design gate output;
- magnitude output;
- coherence output;
- rerun diff.

### Output

`AUTHOR_REPORT.md` with this structure:

```text
1. Status overview
2. Safe claims
3. Flagged and downgraded claims
4. Author-asserted claims
5. Non-overridable hard-blocks
6. Missing diagnostics and citations
7. Economic magnitude gaps
8. Global coherence findings
9. Next best actions
10. Expected referee questions
```

### Hard rules

- Hard rule (overridable: no): scholar-facing reports are consolidated; no pile of independent log-like markdown reports.
- Hard rule (overridable: no): author-asserted claims must preserve original system status and author reason.
- Hard rule (overridable: no): machine-readable JSON lives under `reports/internal/`.

## P0 module 13: `incremental_rerun`

Layer: iteration.

### Input

- previous manuscript pack;
- previous claim ledger;
- previous evidence ledger;
- paragraph hashes;
- author edit markers;
- updated run directory or added artifacts.

### Output

- updated pack;
- claim status diff in `AUTHOR_REPORT.md`;
- updated internal ledgers;
- protected human-edited regions with side comments or suggestions.

### Required behavior

```text
Before: claim_007 = flag_and_confirm because modern staggered DID missing.
After:  claim_007 = safe because Callaway-Sant'Anna artifact added.
Report: upgraded; suggested replacement paragraph available; author-edited paragraph preserved.
```

### Hard rules

- Hard rule (overridable: no): rerun must not overwrite human-edited regions without explicit author permission.
- Hard rule (overridable: no): claim status changes must be diffed and explained.
- Hard rule (overridable: yes, with explicit CLI flag): author may choose to regenerate protected sections, but the action is logged.
