# econpaper

`econpaper` is an economics and finance manuscript-pack tooling workspace. The v3 track turns validated empirical artifacts into a ledger-backed draft package: deterministic numbers, publication-style tables, consolidated author guidance, and release gates that fail closed when evidence is missing.

The current v3 product/auth smoke checkpoint is intended to be directly smoke-testable, not a smallest possible demo. The branch may contain later docs-only commits after this tag.

```text
branch: codex/econpaper-roadmap-v3
product/auth smoke checkpoint tag: roadmap-v3-product-auth-smoke
product/auth smoke checkpoint commit: 152ebe6 feat: harden v3 write smoke and auth
```

## What v3 Does Now

- Validates `skill4econ` run directories with fail-closed status, method, artifact, validation, and mock-output checks.
- Provides an independent linter mode for human-written drafts.
- Builds intake profiles, evidence ledgers, claim ledgers, design profiles, publication tables, manuscript sections, coherence reports, compile fallbacks, release-gate reports, and quality-suite manifests.
- Renders numeric placeholders from the evidence ledger before coherence and compile, so generated `main.md` and Results sections should not retain unresolved `{{...}}` numeric slots.
- Consolidates scholar-facing output into `AUTHOR_REPORT.md`; machine-readable JSON lives under `reports/internal/`.
- Provides OpenAI and Claude auth commands for redacted login/status and live verification.
- Accepts Windows PowerShell UTF-8 BOM JSON inputs.
- Imports common external regression tables from Stata logs, R coefficient summaries, Python/statsmodels summaries, CSV/TSV tables, and LaTeX publication tables into structured `model_table.csv` with an audit report.

## What v3 Does Not Claim Yet

- It is not a one-click publishable paper generator. The intended endpoint is a roughly 70% draft package plus a precise author task list.
- It does not run literature search, citation-graph discovery, PDF crawling, or literature RAG in P0.
- It does not guarantee perfect parsing of every arbitrary pasted regression table. The importer supports common Stata/R/Python/LaTeX layouts and fails closed on ambiguous or unsupported structures.
- It does not replace the author on institutional background, contribution judgment, field positioning, mechanism interpretation, or external-validity argumentation.
- The release-gate machinery exists, but a real release still needs five real economics/finance scholar evaluations with attached feedback.
- `main.pdf` depends on local LaTeX availability. If LaTeX is missing or fails, v3 should produce `main.md`, `main.tex`, and a human-readable compile memo instead.
- OpenAI/Claude live auth verification requires real credentials; missing or invalid credentials are hard failures, not degraded success.

## Repository Layout

- `econpaper/`: v3 Python package and CLI.
- `tests/`: v3 unit and smoke-style tests.
- `econpaper_roadmap_v3/`: roadmap, schemas, checklists, and external review prompt.
- `EasyPaper/`: upstream/downstream manuscript-generation reference layer and legacy integration surface.
- `skill4econ/`: econometrics and finance artifact producer, contracts, docs, and integration snapshot.
- `notes/`: local planning and review notes.

## Install And Test

From the repository root:

```powershell
python -m pip install -e .
python -m pytest -q
```

Expected at the latest checkpoint:

```text
114 passed
```

## Core CLI

```powershell
python -m econpaper.cli validate-run --run-dir path\to\skill4econ_run --out validation_pack

python -m econpaper.cli lint draft.tex `
  --run-dir path\to\skill4econ_run `
  --refs refs.bib `
  --out lint_pack

python -m econpaper.cli intake `
  --answers answers.json `
  --out intake_pack

python -m econpaper.cli import-table `
  --input raw_stata_or_latex_table.txt `
  --format auto `
  --out imported_table

python -m econpaper.cli write `
  --run-dir path\to\skill4econ_run `
  --intake intake_profile.json `
  --refs refs.bib `
  --model-table imported_table\model_table.csv `
  --venue aea `
  --out manuscript_pack

python -m econpaper.cli release-gate `
  --pack-dir manuscript_pack `
  --human-eval human_eval.json `
  --out release_gate_pack

python -m econpaper.cli quality-suite --out quality_suite_pack
```

## Auth Commands

`econpaper auth` supports OpenAI and Claude/Anthropic API verification without printing secrets.

```powershell
python -m econpaper.cli auth login openai --api-key-env OPENAI_API_KEY
python -m econpaper.cli auth login claude --api-key-env ANTHROPIC_API_KEY
python -m econpaper.cli auth status
python -m econpaper.cli auth verify openai
python -m econpaper.cli auth verify claude
```

Behavior:

- OpenAI verification calls `https://api.openai.com/v1/models` using Bearer auth.
- Claude verification calls `https://api.anthropic.com/v1/models` using `x-api-key` and `anthropic-version: 2023-06-01`.
- Missing credentials fail with `credential_missing`.
- Provider/network/auth errors fail; there is no fallback success.
- `auth status` is redacted.

## Product Smoke Expectations

A valid generation smoke should:

- exit 0 from `write`;
- create `AUTHOR_REPORT.md`, `main.md`, `main.tex`, `sections/`, `tables/`, `bibliography/refs.bib`, and `reports/internal/`;
- write `reports/internal/numeric_rendering_sections.json`;
- accept an imported external `model_table.csv` through `--model-table` when native `skill4econ` tables are unavailable;
- leave no unresolved `{{...}}` numeric placeholders in `sections/04_results.md` or `main.md`;
- pass `release-gate` only with a human-evaluation file meeting v3 thresholds;
- pass `quality-suite`;
- hard-block mock/smoke outputs masquerading as real manuscripts.

See [`econpaper_roadmap_v3/OTHER_MODEL_TEST_PROMPT.md`](econpaper_roadmap_v3/OTHER_MODEL_TEST_PROMPT.md) for a strict external-model testing prompt.

## Known Unfinished Work

Highest-impact known gaps:

- Run a real five-scholar economics/finance evaluation campaign and attach feedback to release notes.
- Expand external table importing beyond common Stata/R/Python/statsmodels/CSV/LaTeX layouts, especially multi-panel tables, custom `esttab` notes, modelsummary variants, and nonstandard confidence-interval-only tables.
- Add structured literature-note adapters for Zotero, Better BibTeX, OpenAlex, Crossref, Semantic Scholar, NBER, RePEc, or similar systems.
- Improve field-specific writing depth for finance, accounting, management, and applied micro subfields beyond conservative ledger-driven sections.
- Expand design gates beyond current deterministic coverage, especially for staggered DID, IV, RDD, finance event studies, factor alphas, multiple testing, and mechanism claims.
- Add richer human-edit preservation workflows and reviewer-facing diffs across reruns.
- Exercise live OpenAI and Claude verification with real credentials in the deployment environment.
- Exercise real LaTeX toolchains across Windows and non-Windows machines.

## Design Boundary

`econpaper` does not implement OLS, FE, DID, IV, RDD, DML, spatial, DEA, Fama-MacBeth, or other estimators. It consumes file-backed `skill4econ` artifacts, applies evidence and claim gates, and generates manuscript/reporting outputs.

Empirical claims are allowed only when artifacts are claimable, paper-ready, have a main claim available, and have no non-overridable blocking risk.

## Legacy Provenance

EasyPaper skeleton provenance:

```text
9d43889cbbdffb05deedc4812d4b8e3afb6f0257
```

skill4econ provenance:

```text
a4476f5bc853c0d93fe540f5d3b3da4aa19aa685
```
