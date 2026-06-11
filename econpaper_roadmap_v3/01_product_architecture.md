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
