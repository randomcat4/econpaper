# econpaper Roadmap v3 — Combined Document

This combined file mirrors the segmented roadmap package.


---

# econpaper Roadmap v3

## One-line change from v2

v3 builds on the v2 safety layer, adds a content layer and an iteration layer, and changes the product role from **arbiter** to **advisor**.

v2 asked: "How do we stop the system from saying false things?"

v3 asks: "How do we help a scholar produce a submission-grade draft package while making every risk, override, missing input, and next action explicit?"

Safety is the foundation. It is not the selling point by itself. Scholars will pay for content quality, iteration speed, and trust after revision.

## v3 product definition

The product should produce:

> A roughly 70% complete economics / finance manuscript package plus a precise author task list, not a fully automatic submission-ready paper.

The final 30% is not an engineering bug. Institutional background, research motivation, contribution judgment, and field positioning contain information that is often absent from a run directory. The `intake_interview` reduces this gap, but it cannot eliminate it.

## Three-layer architecture

```text
Safety layer
  - fail-closed run status and unknown method handling
  - evidence ledger and claim ledger
  - citation safety and CITE_NEEDED placeholders
  - design-specific gates

Content layer
  - intake interview
  - economic magnitude interpretation
  - deterministic numeric rendering
  - publication table generation
  - global coherence pass
  - abstract and title writer

Iteration layer
  - incremental rerun
  - claim status diff
  - human-edited region protection
  - LaTeX compile loop with graceful markdown fallback
```

Every module must be clear about which layer it serves. A module that only prevents errors belongs to the safety layer. A module that improves what the paper says belongs to the content layer. A module that protects author work across revisions belongs to the iteration layer.

## Two P0 product shapes

v3 defines two parallel P0 forms. They share the same ledgers and gates, but enter the pipeline differently.

### Shape A: claim linter

```bash
econpaper lint draft.tex \
  --run-dir path/to/skill4econ_run \
  --refs refs.bib \
  --out lint_pack
```

The linter checks a human-written draft. It verifies that every numeric value matches the evidence ledger, every citation key exists, and every causal / mechanism / external-validity phrase is compatible with the design gate or explicitly author-asserted.

This is the best wedge product because it does not depend on generated prose quality. The value proposition is one sentence: "Upload your draft and run directory; econpaper finds unsupported empirical and citation claims before referees do."

### Shape B: generation pipeline

```bash
econpaper write \
  --run-dir path/to/skill4econ_run \
  --intake intake_profile.json \
  --refs refs.bib \
  --venue aea \
  --out manuscript_pack
```

The generator creates a manuscript pack from validated artifacts, an intake profile, a bibliography, and conservative section writers. It should not pretend to be fully automatic. It should produce a strong first draft and a clear author action list.

## Advisor, not arbiter

Except for the three non-overridable hard-block classes, econpaper should advise, flag, downgrade, and explain rather than silently refuse.

The three non-overridable hard-block classes are:

1. fabricated numeric values that disagree with the evidence ledger;
2. fabricated citations where a citekey is absent from `refs.bib` and no `CITE_NEEDED` marker is present;
3. mock output masquerading as a real manuscript.

All other design, identification, contribution, mechanism, and external-validity risks are `flag-and-confirm`. The author may override them by setting `author_asserts: true` with a reason in the claim ledger or by using the CLI override workflow. The final `AUTHOR_REPORT.md` must preserve the system's original judgment and the author's reason.

## Literature policy

v3 keeps the v2 decision: do not build literature search, citation graph discovery, PDF crawling, or literature RAG in P0.

P0 does citation safety. P1/P2 can integrate Zotero, Better BibTeX, OpenAlex, Crossref, Semantic Scholar, NBER metadata, RePEc, PaperQA-style PDF workflows, or other tools through structured notes. External prose is not accepted directly into the manuscript.

## Input scope honesty

P0 supports native structured `skill4econ` output. External Stata / R / Python outputs and manually supplied regression tables are an important P1+ track, not a hidden P0 assumption. Parsing arbitrary LaTeX or text regression tables into cell-level evidence is a research-sized problem, and this track directly affects the size of the addressable user base.

## Package contents

- `00_v3_executive_changes.md` — v2 to v3 changes and positioning corrections.
- `01_product_architecture.md` — three-layer product architecture and object model.
- `02_p0_body_writing_chain.md` — P0 module contracts for safety, content, and iteration.
- `03_citation_safety_not_search.md` — citation policy and external literature notes contract.
- `04_design_specific_claim_gates.md` — three-tier language gates by design.
- `05_todo_rewrite.md` — rewritten P0 / P1 / P2 TODO plan.
- `06_quality_and_false_confidence_tests.md` — release-blocking safety and quality tests.
- `07_user_experience_pack.md` — scholar-facing UX, CLI, output pack, and reporting.
- `08_implementation_order.md` — recommended build order and first PR sequence.
- `schemas/` — draft JSON schemas.
- `examples/` — minimal example ledgers and intake profile.
- `checklists/` — release and lint-mode checklists.
- `DELIVERY_SELF_CHECK.md` — v3 package compliance self-check.

## Most important P0 rule

The manuscript is a view over the claim ledger, not free prose cleaned up after the fact. LLMs may propose wording, but numeric values, citations, design permissions, and author overrides must come from structured objects.


---

# 00. v3 Executive Changes

## Verdict

v3 is a product reset, not a patch. v2 correctly built a safety layer, but it over-centered "do not say false things" and under-specified why scholars would keep using the product after the first run. v3 defines econpaper as a system for producing a roughly 70% complete submission-oriented draft package, with safety as infrastructure, content quality as the product, and iteration as the retention mechanism.

## Change 1: two P0 product shapes

v3 has two P0 forms.

### Shape A: claim linter

```bash
econpaper lint draft.tex --run-dir path/to/run --refs refs.bib --out lint_pack
```

The linter checks human-written drafts. It produces an annotated manuscript and an `AUTHOR_REPORT.md` with numeric mismatches, missing citations, unsupported causal language, author-asserted claims, and next actions.

Why it is P0:

- It does not require generated prose to be good.
- It establishes trust quickly.
- The value proposition is easy to explain.
- It uses the same evidence ledger, claim ledger, citation safety, and design gates as generation.

### Shape B: generation pipeline

```bash
econpaper write --run-dir path/to/run --intake intake_profile.json --refs refs.bib --out manuscript_pack
```

The generator creates the draft package. It uses the same ledgers and gates, plus the content-layer modules added in v3.

## Change 2: advisor, not arbiter

v2 treated many disputed methodological statements as blocked. v3 keeps strict safety for fabricated numbers, fabricated citations, and mock outputs, but moves most scholarly judgment to `flag-and-confirm`.

### Non-overridable hard-blocks

- fabricated numeric value inconsistent with ledger; overridable: no;
- fabricated citation key not present in `refs.bib` and not marked `CITE_NEEDED`; overridable: no;
- mock output presented as a real manuscript; overridable: no.

### Author override

For every other downgraded or flagged claim, the author can override with:

```json
{
  "author_asserts": true,
  "author_override": {
    "asserted": true,
    "reason": "The institutional design section explains the quasi-random timing; keep the stronger wording for now.",
    "original_status": "flag_and_confirm"
  }
}
```

The system then writes or preserves the author's language, but records the item in `AUTHOR_REPORT.md` under **Author-asserted claims**.

## Change 3: declare-and-confirm intake replaces design guessing

The author usually knows the design. v3 should not frustrate users by forcing the system to infer what the author can declare in seconds.

New flow:

```text
intake_interview
  -> author declares design, treatment timing, estimand, contribution, and context
  -> design_profiler checks consistency against artifacts
  -> contradictions are reported, not silently converted into unknown-design blocks
```

Only when the author skips intake entirely does the system fall back to conservative inference. In that fallback mode, causal writing is not generated automatically, but the author can still assert claims with traceable override records.

## Change 4: three-tier gates replace oversized forbidden-language lists

Every design gate must classify language into exactly three operational tiers.

```text
hard-block        non-overridable; only fabricated numbers, fabricated citations, or mock-as-real
flag-and-confirm  serious reviewer risk; author can override with reason
style-advice      wording preference; never blocks, never enters blocked report
```

Examples:

- TWFE-only staggered DID causal language: `flag-and-confirm`, not non-overridable hard-block.
- IV causal wording without first-stage diagnostics: `flag-and-confirm`.
- RDD causal wording without manipulation tests: `flag-and-confirm`.
- "This is the first paper to ...": `flag-and-confirm`.
- "effect of" in an OLS paper: `style-advice`, because scholars use this phrase in real titles and abstracts.

## Change 5: AUTHOR_REPORT replaces the log pile

The scholar-facing output should not be a folder of reports that must be interpreted like CI logs.

v3 user-readable reporting is:

```text
AUTHOR_REPORT.md
main.pdf                 # if compile succeeds; otherwise markdown fallback with explanation
```

Machine-readable JSON moves to:

```text
reports/internal/
```

`claim_gate_report.md`, `blocked_claims.md`, `cite_needed_report.md`, and `reviewer_risk_memo.md` become sections inside `AUTHOR_REPORT.md`. The standalone reviewer simulator is removed; reviewer questions are fields emitted by design gates and summarized in the report.

## Change 6: success criteria now include quality

A v3 run is not successful merely because it avoids hallucinations. A P0 release must pass negative safety tests and positive quality tests.

### Safety success criteria

1. Unknown run status does not become success-with-warnings.
2. Unknown method does not become paper-ready automatically.
3. Numeric claims map to ledger cells.
4. Citation keys exist or are marked `CITE_NEEDED`.
5. Mock output is visibly watermarked.
6. Reports are consolidated into `AUTHOR_REPORT.md`.

### Content success criteria

1. Each main Results paragraph contains an economic magnitude interpretation.
2. The LLM never writes raw numeric values; numbers are rendered deterministically from placeholders.
3. Publication tables are generated from structured model tables, not treated as arbitrary copied artifacts.
4. Abstract, introduction, results, and conclusion reference the same main numbers.
5. Hedging density is bounded so safety does not become timid writing.
6. At least five real economics / finance scholars run real projects through the system before release; median generated-text retention must be at least 50%, and median self-reported time saved must be meaningfully positive.

## What stays from v2

The following v2 choices remain correct and must not be weakened:

- fail-closed run status and unknown method handling;
- `CITE_NEEDED` instead of hallucinated references;
- failure-as-memo UX;
- do not start implementation with Introduction;
- manuscript as a view over claim ledger;
- no P0 literature search;
- all fifteen false-confidence fixtures, with v3 tier semantics applied.

## Honest endpoint

The endpoint is not "one click to a publishable paper." The endpoint is:

```text
A 70% draft package + deterministic numbers + publication-grade tables + consolidated author report + claim diff across reruns.
```

That is already a product a serious scholar can value. Pretending the remaining 30% can be solved from a run directory alone would be dishonest.


---

# 01. Product Architecture

## Target architecture

```text
Shape A: Linter entry
  draft.tex / draft.md
  refs.bib
  skill4econ run_dir
        |
        v
Shared safety and content objects

Shape B: Generation entry
  intake_profile.json
  refs.bib
  skill4econ run_dir
        |
        v
Shared safety and content objects
```

```text
Safety layer
  Run Validator
    - fail-closed status and method handling
    - parser-only / missing-dependency / adapter-only detection

  Evidence Ledger
    - artifact, table cell, figure panel, diagnostic, provenance mapping
    - variable semantics for economic magnitude

  Claim Ledger
    - claim templates, numeric slots, evidence refs, tier decisions
    - author override records

  Citation Safety
    - refs.bib index
    - citekey validation
    - CITE_NEEDED markers

  Design Gates
    - declare-and-confirm design profile
    - three-tier language decisions
    - reviewer questions and next actions

Content layer
  Intake Interview
    - design declaration, context, contribution, variable magnitude, venue

  Economic Magnitude Interpreter
    - converts coefficients into units, standard deviations, percentage changes, and comparable quantities

  Deterministic Numeric Renderer
    - renders all numbers from ledger slots after prose generation

  Publication Table Generator
    - produces booktabs tables, panels, labels, notes, star policy, and venue templates

  Section Writers
    - write from claim ledger templates and author-provided context
    - include abstract and title candidates

  Global Coherence Pass
    - checks cross-section consistency, table references, terminology, promises vs delivered sections

Iteration layer
  Incremental Rerun
    - detects new artifacts
    - recomputes gate status
    - emits claim status diff
    - protects human-edited regions

  LaTeX Compile Loop
    - compile, auto-fix common errors, retry
    - if still failing, produce markdown package plus human-readable compile memo
```

## Product object model

### `RunStatus`

Fail-closed. Unknown status is not success-with-warnings. The system may allow an author to assert claims after a failed validation, but such claims are recorded as author-asserted and are not verified empirical claims.

### `IntakeProfile`

Author-provided structured context. It is the source of truth for declared design, treatment timing, estimand, institutional details, motivation, contribution statement, target venue, and variable magnitude context.

### `DesignProfile`

A checked profile, not an oracle. It compares the author's declared design with artifacts. It stores:

- `declared_by_author: true|false`;
- declared design and estimand;
- consistency checks;
- missing diagnostics;
- gate outputs;
- reviewer questions;
- next actions.

When intake is skipped, the profiler may infer conservatively. That fallback is labeled as such.

### `EvidenceLedger`

The cell-level evidence layer. It maps artifacts to:

- model ids;
- sample ids;
- row / column / statistic locations;
- coefficients, standard errors, confidence intervals, p-values, t-statistics;
- diagnostic statuses;
- variable semantics: unit, scale, mean, standard deviation, standardization, winsorization, and transformation.

### `ClaimLedger`

The manuscript source of truth. It stores claim templates, numeric placeholders, evidence references, citation references, gate decisions, suggested rewrites, and author overrides.

The ledger is used by both linter and generation modes.

### `CitationIndex`

A parsed index from `refs.bib` and structured literature notes. It is not a search engine.

### `ExternalLiteratureNotes`

Structured notes from Zotero, OpenAlex, Elicit, PaperQA, a human RA, or another external tool. econpaper accepts structured notes, not externally generated literature-review paragraphs.

### `AuthorReport`

The single scholar-facing report. It merges claim gate report, blocked / flagged items, cite-needed items, missing diagnostics, author-asserted claims, next actions, and reviewer questions.

### `RerunState`

A state object that records prior claim ids, paragraph hashes, author edits, previous gate decisions, and artifact hashes. It powers incremental reruns and human-edited region protection.

### `VenueTemplate`

In v3, `--venue` controls formatting and template behavior: table notes, citation style, title page, abstract length, appendix conventions, and PDF template. It does not promise journal-specific prose voice in P0.

## Why EasyPaper remains downstream

EasyPaper can still provide writer harnesses, typesetting helpers, and orchestration. It should not be the conceptual product center. The source of truth is:

```text
intake_profile
  + validated skill4econ artifacts
  + evidence ledger
  + claim ledger
  + citation index
  + design gate decisions
```

## External table importer track

P0 assumes native structured `skill4econ` outputs. External Stata / R / Python outputs and manually supplied tables are a separate P1+ track.

The importer must solve:

- table-to-cell parsing;
- row/column/statistic recognition;
- model and sample ids;
- standard error and p-value conventions;
- notes and clustering extraction;
- provenance reconstruction.

Until that track exists, arbitrary external tables can be included as appendix artifacts but not treated as verified claim evidence.

Hard rule (overridable: no): A table image, arbitrary LaTeX table, or pasted regression output is not claimable evidence until parsed into the evidence ledger.


---

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


---

# 03. Citation Safety, Not Literature Search

## Principle

Do not build a literature search engine in P0. Build citation safety and structured literature-note ingestion.

The product should not compete with mature systems for search, discovery, citation graphs, PDF management, or bibliography management. econpaper's P0 duty is narrower and more important: do not hallucinate references, do not cite absent keys, and do not let unsupported literature claims masquerade as field positioning.

## P0: required citation safety

### Inputs

```text
refs.bib                         # required for citation-safe draft
literature_notes.md              # optional, author-provided notes
external_literature_notes.json   # optional, structured external notes
research_context.md              # optional, author-provided framing
```

### Outputs

```text
reports/internal/citation_index.json
reports/internal/citation_safety_report.json
AUTHOR_REPORT.md                 # citation section only; no separate cite_needed_report.md
```

### Hard rules

1. Hard rule (overridable: no): a manuscript citation key must exist in `refs.bib`, unless the manuscript uses an explicit `[CITE_NEEDED: ...]` marker instead of a cite command.
2. Hard rule (overridable: no): fake citations are non-overridable hard-blocks.
3. Hard rule (overridable: no): fake paper summaries are not accepted as literature notes.
4. Hard rule (overridable: yes, by author note or structured external note): a literature claim must have either a citation, an author-provided note, or a structured external note.
5. Hard rule (overridable: yes, by author assertion): unsupported literature or novelty claims become `flag-and-confirm`, not permanent blocks, except when they cite nonexistent keys.
6. Hard rule (overridable: no): missing literature support becomes `[CITE_NEEDED: ...]`, `[AUTHOR_INPUT_NEEDED]`, or an author-asserted claim; it never becomes a hallucinated citation.

## What the P0 writer may say

Allowed without literature search:

> This paper contributes to the literature on `[TOPIC]`. The precise positioning should be finalized after the author supplies preferred references.

Allowed with `refs.bib` but no notes:

> Prior work has examined related questions in `[AREA]`; the final version should cite and discuss the most relevant studies from the supplied bibliography.

Allowed with author notes:

> As summarized in the author's literature notes, `[paper_key]` studies `[topic]`, while this paper differs by focusing on `[difference]`.

Allowed with structured external notes:

> Structured notes identify `[paper_key]` as studying `[what_it_did]`; this paper differs by `[relation_to_this_paper]`.

## Tier classification for literature language

### Hard-block, overridable: no

- `\citep{missing_key}` or `\citet{missing_key}` when `missing_key` is not in `refs.bib`.
- A fabricated bibliographic entry that the system cannot trace to user input or structured external notes.

### Flag-and-confirm, overridable: yes

- "No previous study has ..."
- "This is the first paper to ..."
- "The closest paper is ..."
- "Unlike all prior work ..."
- "The literature establishes that ..."
- "The consensus is ..."

The system should explain why these are high-risk literature claims and ask for author confirmation or structured notes.

### Style-advice, overridable: yes by ignoring advice

- Overly long literature-signposting sentences.
- Excessive hedging around well-cited conventional background.
- Repeated generic phrases such as "a growing literature" without specificity.

Style advice does not block generation and does not enter the hard-block section.

## External literature integration contract

v3 can integrate external systems, but only through structured notes.

### Accepted object

`external_literature_notes.json` must contain entries like:

```json
{
  "paper_key": "smith2020",
  "bibtex_entry": "@article{smith2020,...}",
  "what_it_did": "Studies how policy X affected firm investment using a staggered DID design.",
  "relation_to_this_paper": "This paper studies a related policy but uses household-level outcomes and a different treatment window.",
  "source_url_or_doi": "10.0000/example.doi",
  "source_type": "doi",
  "created_by": "external_tool_or_author",
  "confidence": "medium"
}
```

### Hard rules

- Hard rule (overridable: no): external tools must return structured notes with source identifiers; raw generated literature-review paragraphs are not accepted.
- Hard rule (overridable: no): Related Literature prose is generated by econpaper from structured notes and then passes citation safety.
- Hard rule (overridable: no): external notes are not allowed to bypass citekey validation.
- Hard rule (overridable: yes, by author assertion): an author may keep a literature positioning claim not backed by notes, but it is listed as author-asserted.

## P1: low-cost adapters

P1 can add adapters without owning the search problem.

### BibTeX / Better BibTeX

Support user-provided `.bib` files, especially those exported by Zotero + Better BibTeX.

### Zotero adapter

Optional:

```bash
--bib refs.bib
--zotero-export path/to/exported.bib
--zotero-local
```

The Zotero adapter should produce a normalized `.bib` file and citation index. It should not write literature prose.

### Metadata enrichment adapter

Optional:

```text
DOI/title -> Crossref/OpenAlex/Semantic Scholar metadata -> normalized BibTeX
```

This is for metadata cleanup, duplicate detection, DOI/year/journal sanity checks, and missing fields, not automated claims about what papers found.

## P2: discovery and RAG

P2 may add:

- related-paper suggestions;
- PaperQA-style PDF folder notes;
- citation graph exploration;
- annotated bibliography drafts;
- contribution-gap memos.

But all P2 outputs must become structured notes before they can influence manuscript prose.


---

# 04. Design-Specific Claim Gates

## Why generic claim gates are insufficient

A generic rule like "a claim needs a table reference" is not enough for economics and finance. Different designs fail in different ways. v3 keeps design-aware gates but changes their product role: gates advise, classify, and explain. They do not pretend to be the final referee.

## Shared three-tier gate contract

Every design gate outputs:

```json
{
  "design_type": "staggered_did",
  "declared_by_author": true,
  "paper_ready": false,
  "claim_levels": {
    "causal_language": {
      "tier": "flag_and_confirm",
      "overridable": true,
      "reason": "Declared staggered DID, but no modern staggered estimator is present.",
      "suggested_rewrite": "The estimates are consistent with a decline under the maintained DID assumptions, but modern staggered-DID estimates are still needed.",
      "reviewer_questions": ["How do results change under Callaway-Sant'Anna or Sun-Abraham?"],
      "next_actions": ["Run a modern staggered DID estimator."]
    }
  },
  "hard_blocks": [],
  "flags": [],
  "style_advice": [],
  "author_override": {
    "allowed": true,
    "field": "author_override"
  }
}
```

## Global tier definitions

### Hard-block

Non-overridable. The only hard-block classes are:

1. fabricated numeric value inconsistent with the evidence ledger; overridable: no;
2. fabricated citation key absent from `refs.bib` and not represented as `CITE_NEEDED`; overridable: no;
3. mock output masquerading as a real manuscript; overridable: no.

No design-specific identification dispute belongs in this tier.

### Flag-and-confirm

Overridable: yes.

This tier covers real reviewer risks. The system should not write the stronger language by default, but the author can keep or request it with `author_asserts: true` and a reason. The claim is then listed in `AUTHOR_REPORT.md`.

### Style-advice

Overridable: yes by ignoring advice.

This tier covers taste, tone, and field convention. Style advice never blocks generation and does not enter the hard-block section.

## Gate: OLS / Cross-sectional regression

### Must check

- outcome definition;
- treatment / exposure definition;
- controls;
- sample;
- robust or clustered standard errors;
- omitted-variable risk;
- reverse causality risk;
- variable scaling and magnitude context.

### Language rules

#### Hard-block, overridable: no

- Numeric coefficient, standard error, p-value, N, or percentage inconsistent with ledger.
- Citekey not present in `refs.bib`.
- Mock OLS output represented as a real table.

#### Flag-and-confirm, overridable: yes

- "causes" or "causal effect" from OLS without a declared causal design or credible quasi-experimental source.
- "identifies" without a design-based identification argument.
- "exogenous variation" without author-provided institutional or design support.
- Strong external-validity claims beyond the sample.

#### Style-advice, overridable: yes

- "effect of" in title or prose. The system may suggest "association" if appropriate, but must not block the phrase.
- Generic "significant at the 1% level" prose without economic magnitude.
- Excessive hedging if the claim is already framed as descriptive.

### Reviewer questions

- What omitted variables remain plausible?
- Is the exposure predetermined?
- Are standard errors clustered at the right level?
- Does the magnitude matter economically?

## Gate: Panel fixed effects

### Must check

- unit fixed effects;
- time fixed effects;
- within-unit variation;
- clustering level;
- treatment timing;
- time-varying confounders;
- bad controls;
- sample attrition.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent numbers.
- Missing citekeys.
- Mock-as-real output.

#### Flag-and-confirm, overridable: yes

- "causal effect" without a declared source of quasi-random variation.
- "rules out time-varying confounders" without diagnostics or institutional argument.
- "generalizes" beyond the panel sample.

#### Style-advice, overridable: yes

- "within-unit effect" vs "within-unit association" wording.
- Hedging level around descriptive fixed-effect results.

### Reviewer questions

- Are time-varying shocks correlated with treatment?
- Are controls post-treatment?
- Is clustering consistent with treatment assignment?

## Gate: DID / staggered DID

### Must check

- treatment timing;
- absorbing vs reversible treatment;
- never-treated / not-yet-treated controls;
- cohort support;
- anticipation windows;
- dynamic effects;
- pre-treatment coefficients;
- TWFE role;
- heterogeneous-treatment risk;
- modern estimator availability;
- inference and clustering.

### Required artifacts

- treatment timing summary;
- event-study plot or table;
- pretrend diagnostic;
- comparison group definition;
- modern staggered DID output when adoption is staggered;
- inference specification.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent treatment effects, standard errors, p-values, or event-study coefficients.
- Missing citekeys.
- Mock DID output presented as real.

#### Flag-and-confirm, overridable: yes

- "causal effect" when only TWFE exists for staggered adoption.
- "TWFE identifies the staggered DID effect" when heterogeneous timing exists and no modern estimator supports it.
- "parallel trends is proven."
- "no anticipation" without anticipation-window diagnostics or author-provided institutional timing.
- Strong claims based on pretrend tests with low power.

#### Style-advice, overridable: yes

- Whether to say "under the parallel trends assumption" in every Results sentence or once per subsection.
- Whether to use ATT terminology in abstract-level prose.

### Reviewer questions

- How sensitive are estimates to Callaway-Sant'Anna, Sun-Abraham, did_imputation, or DRDID equivalents?
- Are event-study pretrends informative with enough support?
- Are never-treated and not-yet-treated controls both examined?
- Is treatment timing possibly anticipated?

### Next actions

- run a modern staggered DID estimator;
- add anticipation windows;
- show cohort support;
- report dynamic effects;
- compare never-treated and not-yet-treated controls.

## Gate: IV

### Must check

- instrument definition;
- endogenous variable;
- first stage;
- weak-IV diagnostics;
- reduced form;
- exclusion restriction statement;
- monotonicity / LATE scope;
- overidentification test where relevant;
- clustered inference.

### Required artifacts

- first-stage table;
- second-stage table;
- reduced-form table if possible;
- weak-IV diagnostic;
- instrument narrative.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent IV coefficients or diagnostics.
- Missing citekeys.
- Mock IV output presented as real.

#### Flag-and-confirm, overridable: yes

- "causal effect" without first-stage and weak-IV diagnostics.
- "the instrument is valid" without exclusion-scope caveat.
- "effect for all units" when the design supports only LATE.
- Overidentification comfort language without the relevant test.

#### Style-advice, overridable: yes

- Whether to lead with "compliers" in abstract vs empirical strategy.
- Degree of hedging around exclusion restriction language.

### Reviewer questions

- What is the first-stage strength?
- Why is the exclusion restriction plausible?
- Who are the compliers?
- Are reduced-form effects consistent with the IV story?

## Gate: RDD

### Must check

- running variable;
- cutoff;
- bandwidth;
- kernel / polynomial order;
- manipulation / sorting;
- covariate continuity;
- donut robustness;
- placebo cutoffs;
- local estimand.

### Required artifacts

- RD plot;
- main bandwidth table;
- bandwidth sensitivity;
- manipulation test;
- covariate balance around cutoff.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent local estimates, bandwidths, or sample sizes.
- Missing citekeys.
- Mock RDD output presented as real.

#### Flag-and-confirm, overridable: yes

- "causal effect" without manipulation and covariate-continuity diagnostics.
- Global treatment-effect language away from the cutoff.
- "no sorting" without a manipulation test or institutional support.
- Strong extrapolation beyond the local estimand.

#### Style-advice, overridable: yes

- Whether to repeatedly say "local" in every sentence.
- Whether to place bandwidth details in text or table notes.

### Reviewer questions

- Is the running variable manipulable?
- How stable are results across bandwidths?
- Do covariates jump at the cutoff?
- What population is local to the cutoff?

## Gate: Finance event study

### Must check

- event date source;
- announcement timing;
- leakage window;
- estimation window;
- event window;
- market model / factor model;
- overlapping events;
- cross-sectional dependence;
- clustering;
- multiple testing.

### Required artifacts

- event timeline;
- CAR or BHAR table;
- pre-event leakage check;
- factor-adjusted robustness where relevant;
- sample construction and filters.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent CAR, BHAR, alpha, t-statistic, or event-window numbers.
- Missing citekeys.
- Mock event-study output presented as real.

#### Flag-and-confirm, overridable: yes

- "investors anticipated" without pre-event tests.
- "profitable strategy" without trading-cost and out-of-sample timing assumptions.
- "predicts returns" without formation and holding-period discipline.
- Market-efficiency conclusions without event-time validity checks.
- Look-ahead leakage in signal construction.

#### Style-advice, overridable: yes

- Whether to call estimates "abnormal returns" or "market reactions" in nontechnical sections.
- Whether to put multiple-testing caveats in text or report.

### Reviewer questions

- Are announcement times measured before market reaction windows?
- Are overlapping events handled?
- Are results robust to factor adjustment?
- Is multiple testing addressed?

## Gate: Portfolio sorts / asset pricing

### Must check

- signal formation date;
- return measurement window;
- rebalancing frequency;
- breakpoints;
- value-weight vs equal-weight;
- factor model;
- alpha inference;
- transaction costs and microcap filters for performance claims;
- multiple testing.

### Required artifacts

- portfolio sort table;
- long-short returns;
- factor alpha table;
- factor definitions;
- signal timing and lag discipline.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent returns, alphas, t-statistics, or portfolio counts.
- Missing citekeys.
- Mock portfolio output presented as real.

#### Flag-and-confirm, overridable: yes

- "predicts returns" if signal timing is not lagged.
- "alpha" without a factor model.
- "tradable" without trading-cost and implementation assumptions.
- "mispricing" without ruling out risk-based explanations.

#### Style-advice, overridable: yes

- Whether to put sorting mechanics in text vs table notes.
- Whether to use "spread" or "long-short" terminology.

### Reviewer questions

- Are breakpoints NYSE or full sample?
- Are portfolios value-weighted or equal-weighted?
- Are microcaps driving results?
- Are alphas robust across factor models?

## Gate: Fama-MacBeth

### Must check

- per-period cross-sectional regression setup;
- lagged predictors;
- time-series inference;
- Newey-West or other autocorrelation correction;
- factor and control set;
- cross-sectional sample filters;
- multiple testing.

### Required artifacts

- per-period coefficient aggregation;
- average coefficients and t-statistics;
- predictor construction audit;
- inference settings.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent average coefficients or t-statistics.
- Missing citekeys.
- Mock Fama-MacBeth output presented as real.

#### Flag-and-confirm, overridable: yes

- "priced risk factor" without factor model or cross-sectional pricing interpretation.
- "predicts returns" without lagged predictors.
- "robustly priced" without multiple-testing and inference checks.

#### Style-advice, overridable: yes

- Whether to describe coefficients as average slopes or premia.
- How much methodology to repeat outside the table notes.

### Reviewer questions

- Are predictors known at the time of return measurement?
- Is inference corrected for time-series dependence?
- Are results concentrated in one subperiod?

## Gate: Mechanism

Mechanism is not a design by itself. It is a claim type layered over a design.

### Must check

- mechanism proxy;
- timing relative to treatment;
- alternative channels;
- whether mechanism result is separately identified;
- whether mechanism is exploratory;
- whether the main design supports mechanism interpretation.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent mechanism estimates.
- Missing citekeys.
- Mock mechanism output presented as real.

#### Flag-and-confirm, overridable: yes

- "proves the channel."
- "confirms the mechanism."
- Mediation language without a mediation design.
- Mechanism claims using post-treatment bad controls without a clear interpretation.

#### Style-advice, overridable: yes

- "consistent with" vs "suggestive of" wording.
- Whether to put mechanism caveats in the paragraph or section opener.

### Reviewer questions

- Is the mechanism variable itself affected by treatment?
- Are alternative channels ruled out or merely discussed?
- Is the evidence timing-compatible with the proposed mechanism?

## Gate: External validity

External validity is a claim layer, not a standalone design.

### Must check

- sample country / industry / firm / household scope;
- period;
- institutional features;
- treatment scale;
- comparison to target population;
- heterogeneous effects.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent sample size, geography, period, or outcome scope.
- Missing citekeys.
- Mock sample metadata presented as real.

#### Flag-and-confirm, overridable: yes

- "generalizes globally" from a single-country or single-industry sample.
- "applies to all firms / households" when the sample is restricted.
- Broad policy recommendations beyond the institutional context.

#### Style-advice, overridable: yes

- Whether limitations are stated in Results or a separate section.
- Whether external-validity caveats are placed in the abstract.

### Reviewer questions

- What population is actually represented?
- Which institutional features are likely nonportable?
- Do heterogeneity results support broader claims?


---

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


---

# 06. Quality and False Confidence Tests

These tests are release blockers. v3 keeps the v2 false-confidence fixtures and adds quality tests. The product is not releasable if it is merely safe but produces timid, useless, or non-iterable text.

## Tier semantics for tests

```text
hard-block        fabricated numbers, fabricated citations, mock-as-real only
flag-and-confirm  serious design or reviewer risk; author override allowed
style-advice      wording preference; not a release-blocking claim status by itself
```

When a v2 test used the word "blocked" for an identification dispute, v3 preserves the fixture and expected warning but classifies the claim as `flag_and_confirm` unless it falls into the three hard-block categories.

## Test 1: unknown method cannot become paper-ready

### Fixture

`model_table.json` contains method `my_new_magic_estimator` with a coefficient and p-value.

### Expected

- Design profile status: `unknown_method`.
- Claim status: no automatic verified main result.
- Author may assert the claim, but it becomes `author_asserted` with original status recorded.
- Manuscript must not write a main result as system-verified paper-ready.

## Test 2: unknown run status cannot become success_with_warnings

### Fixture

`status.json` contains `status: weird_completed_state`.

### Expected

- Run validation fails closed.
- Result section is not generated automatically.
- `AUTHOR_REPORT.md` says status is unknown and requires validation.
- Author override, if used, is recorded as author-asserted rather than verified.

## Test 3: table path is not sufficient evidence

### Fixture

A LaTeX table exists, but there is no parsed cell mapping.

### Expected

- Manuscript may reference that a table exists only as an appendix/report artifact.
- No numeric effect sentence is automatically allowed.
- Author can manually assert a table interpretation, recorded as author-asserted.

## Test 4: invented coefficient hard-blocked

### Fixture

Evidence ledger coefficient is `0.03`, draft says `0.30`.

### Expected

- Claim verifier hard-blocks the numeric mismatch.
- Overridable: no.
- `AUTHOR_REPORT.md` includes the mismatch.
- Numeric renderer test explains why this should have been impossible if placeholders were used correctly.

## Test 5: robustness cannot become main result

### Fixture

Robustness table has a stronger estimate than the main table.

### Expected

- Writer cannot lead with robustness as primary result by default.
- Language must say robustness is supportive/sensitivity, not main evidence.
- If the author insists, the claim is `flag_and_confirm` and author-asserted.

## Test 6: mechanism cannot be written as proof

### Fixture

Mechanism artifact is flagged `suggestive_only`.

### Expected

- Default writer avoids "confirms the mechanism" and "proves the channel".
- Allowed default language: "consistent with the mechanism" or "suggestive of".
- Stronger mechanism language is `flag_and_confirm`, not hard-block, unless it contains fabricated numbers or citations.

## Test 7: staggered DID with TWFE-only flagged

### Fixture

Treatment adoption is staggered; only TWFE artifact exists.

### Expected

- Main causal DID claim is `flag_and_confirm`.
- TWFE may be described as a benchmark or preliminary estimate by default.
- Next actions recommend modern staggered DID estimator.
- Author can override with reason; `AUTHOR_REPORT.md` records the assertion.

## Test 8: IV without first stage flagged

### Fixture

Second-stage IV table exists; no first-stage or weak-IV diagnostic.

### Expected

- Causal language is `flag_and_confirm`.
- `AUTHOR_REPORT.md` asks for first stage and weak-IV diagnostics.
- Author override is allowed with reason.

## Test 9: RDD without manipulation test flagged

### Fixture

RDD coefficient exists; no manipulation or covariate-continuity diagnostic.

### Expected

- Causal language is `flag_and_confirm`.
- Local descriptive or assumption-qualified language is allowed.
- Required diagnostics are reported.

## Test 10: finance signal with look-ahead flagged

### Fixture

Signal uses data published after return formation date.

### Expected

- Return predictability or tradable-strategy claim is not written automatically.
- Claim is `flag_and_confirm` with high-severity leakage explanation.
- Author override is allowed, but the report records the leakage concern.

## Test 11: missing bibliography does not create fake citations

### Fixture

No `refs.bib`; writer asked for Introduction and Related Literature.

### Expected

- No fake `\citep{...}`.
- Literature claims replaced with `[CITE_NEEDED]`, `[AUTHOR_INPUT_NEEDED]`, or author-asserted placeholders.

## Test 12: unknown citation key hard-blocks cite command

### Fixture

Manuscript contains `\citep{nonexistent2025}`; `refs.bib` lacks that key.

### Expected

- Citation safety gate hard-blocks the cite command.
- Overridable: no for using the nonexistent cite command.
- The writer may replace it with `[CITE_NEEDED: source for claim]`.

## Test 13: absolute path leakage blocked from public output

### Fixture

Artifact path is `/Users/alice/private/project/data/table1.tex`.

### Expected

- Public manuscript uses relative path.
- Internal path appears only in redacted/internal provenance, not in `main.tex` or `AUTHOR_REPORT.md`.

## Test 14: mock output cannot masquerade as real draft

### Fixture

`--mock-runner` enabled.

### Expected

- All manuscript files contain `SMOKE TEST ONLY -- NOT A PAPER DRAFT`.
- Output status cannot be `paper_ready`.
- Overridable: no.

## Test 15: external validity overclaim flagged

### Fixture

Single-country sample; draft says results generalize globally.

### Expected

- Claim is `flag_and_confirm`, not non-overridable hard-block.
- Limitations section states sample scope.
- Author can override with reason; the report records the original external-validity concern.

## Q1: economic magnitude required in main Results

### Fixture

Main result paragraph says: "The coefficient is 0.03 and statistically significant."

### Expected

- Quality test fails.
- Paragraph is incomplete until it explains units, standard-deviation equivalent, mean-relative change, or another meaningful benchmark.
- If magnitude context is missing, `AUTHOR_REPORT.md` asks for the missing unit / mean / standard deviation.

## Q2: deterministic numeric rendering required

### Fixture

LLM output contains raw numeric prose rather than placeholders.

### Expected

- Quality test fails before publication.
- Prose must be rewritten with placeholders such as `{{coef:claim_main_001}}`.
- Test 4 remains a fallback mismatch detector, not the primary control.

## Q3: hedging density bounded

### Fixture

A Results paragraph contains "may," "suggestive," "consistent with," and "could" in nearly every sentence.

### Expected

- Quality test flags timid writing.
- Writer must consolidate caveats and state safe claims directly.
- Threshold is configurable, but default maximum is two hedge phrases per paragraph unless the section is explicitly limitations or mechanism.

## Q4: global numeric consistency

### Fixture

Abstract says coefficient is `0.03`, Results says `0.04`, and Conclusion says `3 percentage points` for the same claim id.

### Expected

- Coherence pass fails.
- All references to the same claim id must render from the same numeric slot and compatible unit conversions.

## Q5: abstract and body consistency

### Fixture

Abstract claims a mechanism result, but the body contains only main outcome and robustness claims.

### Expected

- Coherence pass flags unsupported abstract content.
- Abstract must be rewritten or the missing body section must be added.

## Q6: override trace completeness

### Fixture

Author overrides a flagged DID causal claim.

### Expected

- Claim ledger contains `author_override.asserted: true`.
- `original_status` is preserved.
- Author reason is non-empty.
- `AUTHOR_REPORT.md` includes the claim under Author-asserted claims.

## Q7: publication table quality

### Fixture

`model_table.json` is valid but generated LaTeX table lacks table notes, sample rows, or inference notes.

### Expected

- Quality test fails.
- Table must include model/sample mapping, inference convention, fixed effects where relevant, star/no-star policy, and provenance note.

## Q8: human evaluation release gate

### Fixture

Pre-release candidate passes automated tests.

### Expected

At least five real economics / finance scholars must run real projects. Release passes only if:

- median generated-text retention is at least 50%;
- at least four of five users report meaningful time saved;
- no user reports that the system silently fabricated a number or citation;
- at least three users say the `AUTHOR_REPORT.md` made next actions clearer than raw logs;
- all feedback is attached to the release notes.


---

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


---

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


---

# P0 Release Gate Checklist

## Safety release blockers

- [ ] Unknown run status cannot become success-with-warnings.
- [ ] Unknown method cannot become paper-ready automatically.
- [ ] Parser-only, adapter-only, missing-dependency, failed, and mock runs cannot produce verified claims.
- [ ] Fabricated numeric values are hard-blocked; overridable: no.
- [ ] Missing citekeys used as cite commands are hard-blocked; overridable: no.
- [ ] Mock-as-real output is hard-blocked; overridable: no.
- [ ] Absolute paths do not appear in public manuscript files or `AUTHOR_REPORT.md`.
- [ ] Machine-readable ledgers live under `reports/internal/`.

## Content quality release blockers

- [ ] Every main Results paragraph has economic magnitude interpretation.
- [ ] Every number in manuscript prose is rendered from a placeholder.
- [ ] Percentage and percentage-point claims are distinguished.
- [ ] Publication tables are generated from structured model tables.
- [ ] Table notes disclose inference, fixed effects, sample, and star/no-star policy.
- [ ] Abstract, Results, and Conclusion use consistent numbers.
- [ ] Hedging density is below the configured threshold.
- [ ] `sections/00_abstract.md` is present.

## UX release blockers

- [ ] `AUTHOR_REPORT.md` exists and is the single primary user-readable report.
- [ ] User-readable files under `reports/` are capped at two: `AUTHOR_REPORT.md` and optional PDF.
- [ ] `AUTHOR_REPORT.md` contains Author-asserted claims section.
- [ ] Failure outputs are written as human-readable memos.
- [ ] Lint mode produces an annotated draft.
- [ ] Rerun mode emits claim status diff.
- [ ] Human-edited regions are protected by default.

## Human evaluation release gate

- [ ] At least five real economics / finance scholars tested real run directories.
- [ ] Median generated-text retention >= 50%.
- [ ] At least four of five users report meaningful time saved.
- [ ] No user reports a silent fabricated number or citation.
- [ ] At least three users report that `AUTHOR_REPORT.md` made next actions clearer than raw logs.
- [ ] Human feedback is attached to release notes.


---

# Design Gate Checklist

## Shared checks

- [ ] Gate uses declared design from `intake_profile.json` when available.
- [ ] Gate records `declared_by_author`.
- [ ] Gate checks consistency between declared design and artifacts.
- [ ] Gate emits `reviewer_questions`.
- [ ] Gate emits `next_actions`.
- [ ] Gate classifies every language rule into `hard_block`, `flag_and_confirm`, or `style_advice`.
- [ ] Gate marks every rule with `overridable: yes/no`.
- [ ] Gate uses non-overridable hard-block only for fabricated numbers, fabricated citations, or mock-as-real.
- [ ] Gate supports `author_override` for flag-and-confirm claims.

## DID / staggered DID

- [ ] Treatment timing summary present or requested.
- [ ] Staggered adoption detected or declared.
- [ ] Event-study support checked.
- [ ] Modern estimator availability checked.
- [ ] Anticipation window checked.
- [ ] Parallel-trends language classified as flag-and-confirm when diagnostics are weak.

## IV

- [ ] First stage checked.
- [ ] Weak-IV diagnostic checked.
- [ ] Exclusion restriction statement checked.
- [ ] LATE scope checked.
- [ ] Causal language without diagnostics is flag-and-confirm, not hard-block.

## RDD

- [ ] Running variable and cutoff checked.
- [ ] Bandwidth checked.
- [ ] Manipulation test checked.
- [ ] Covariate continuity checked.
- [ ] Global claims classified as flag-and-confirm.

## Finance

- [ ] Event timing or signal formation checked.
- [ ] Look-ahead leakage checked.
- [ ] Factor model availability checked where alpha is claimed.
- [ ] Multiple-testing issue checked.
- [ ] Tradability language classified as flag-and-confirm unless implementation assumptions are present.

## Mechanism / external validity

- [ ] Mechanism proof language classified as flag-and-confirm.
- [ ] Post-treatment proxy risks checked.
- [ ] Sample scope checked before broad generalization.
- [ ] External-validity overclaim is flag-and-confirm with limitations rewrite.


---

# Lint Mode Checklist

## CLI

- [ ] `econpaper lint draft.tex --run-dir ... --refs refs.bib --out lint_pack` exists.
- [ ] Markdown drafts are accepted.
- [ ] Linter can run without generation mode.
- [ ] Linter uses the same evidence ledger, claim ledger, citation safety, and design gates as generation.

## Extraction

- [ ] Numeric claims extracted from prose.
- [ ] Table and figure references extracted.
- [ ] Citation commands extracted.
- [ ] Causal language extracted.
- [ ] Mechanism language extracted.
- [ ] External-validity language extracted.
- [ ] Contribution and novelty claims extracted.

## Findings

- [ ] Ledger-inconsistent numbers are hard-blocked.
- [ ] Missing citekeys are hard-blocked.
- [ ] Mock-as-real is hard-blocked.
- [ ] Design risks are flag-and-confirm.
- [ ] Wording preferences are style-advice only.
- [ ] Author overrides can be supplied and recorded.

## Output

- [ ] `annotated_draft.tex` or `annotated_draft.md` is produced.
- [ ] `AUTHOR_REPORT.md` is produced.
- [ ] JSON lives under `reports/internal/`.
- [ ] Author-asserted claims are listed with original status and reason.
- [ ] Next actions are ordered by expected value.


---

# Delivery Self-Check

- [x] Linter form has an independent CLI command, independent TODO section, and independent checklist.
- [x] Every gate language rule is assigned to hard-block, flag-and-confirm, or style-advice.
- [x] Hard-block is limited to fabricated numbers, fabricated citations, and mock-as-real output.
- [x] `claim_ledger.schema.json` contains `author_override`; `AUTHOR_REPORT.md` contains Author-asserted claims section.
- [x] Intake module exists and design profiler is rewritten as declare-and-confirm.
- [x] Abstract appears in the section writer list and the output directory as `sections/00_abstract.md`.
- [x] `evidence_ledger.schema.json` contains `variable_semantics`; magnitude module has explicit hard rules.
- [x] Numeric rendering is placeholder-first; Test 4 is described as fallback.
- [x] Reports are consolidated into `AUTHOR_REPORT.md`; JSON moves to `reports/internal/`.
- [x] User-readable reports under `reports/` are capped at two: `AUTHOR_REPORT.md` and optional PDF.
- [x] Quality tests include at least five Q-series tests and a human evaluation gate with a clear pass line.
- [x] Incremental rerun includes claim diff and human-edited region protection.
- [x] `--venue` controls templates and formatting; `main.pdf` has compile-loop and fallback strategy.
- [x] External literature interface contract exists and rejects externally generated prose as direct manuscript input.
- [x] README contains the information ceiling and "70% draft package" positioning.
- [x] External Stata/R/Python outputs and manually supplied tables are separated as a P1+ importer track with explicit cost.
- [x] The v2 fifteen false-confidence fixtures are retained; Test 15 is flag-and-confirm, and v3 tier semantics are applied to other design-risk tests.
