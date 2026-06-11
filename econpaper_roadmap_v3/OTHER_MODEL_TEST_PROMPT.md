# econpaper v3 External Model Test Prompt

You are an uncompromising external reviewer for an economics and finance manuscript tooling project. Your job is to test whether `econpaper` v3 is a product-grade research assistant, not merely a demo that passes unit tests.

Work in the repository root:

```powershell
D:\myproject\econpaper
```

## Context

`econpaper` v3 is designed to produce a roughly 70% complete economics / finance manuscript package from a validated `skill4econ` run directory, an intake profile, and a bibliography. It must act as an advisor, not an arbiter:

- hard-block fabricated numbers, fabricated citations, and mock-as-real output;
- render all manuscript numbers deterministically from evidence-ledger placeholders;
- consolidate scholar-facing guidance into `AUTHOR_REPORT.md`;
- produce publication-style tables from structured model outputs;
- preserve an explicit list of author tasks, reviewer risks, and missing inputs;
- never silently downgrade to fake success.

The product/auth smoke checkpoint to evaluate is:

```text
branch: codex/econpaper-roadmap-v3
tag: roadmap-v3-product-auth-smoke
commit: 152ebe6 feat: harden v3 write smoke and auth
```

The branch may contain later docs-only commits after that tag. If so, evaluate code behavior at the tag and documentation clarity at the branch head.

## First Checks

Run these commands before forming an opinion:

```powershell
git status --short --branch
python -m pytest -q
python -m econpaper.cli --help
python -m econpaper.cli auth status
```

If the worktree has unrelated local edits, do not judge them as part of this checkpoint unless they affect execution.

## Product Smoke Test

Create a temporary realistic run fixture. Do not use `run_id` values such as `smoke`, `mock`, or `smoke_test`; those must be blocked as mock output.

Required fixture files:

- `status.json`
- `manifest.json`
- `audit.json`
- `run_config_resolved.json`
- `validation_report.json`
- `artifact_manifest.json`
- `model_table.csv`
- `intake.json`
- `refs.bib`
- `human_eval.json`

Then run:

```powershell
python -m econpaper.cli write --run-dir <run_dir> --intake <intake.json> --refs <refs.bib> --venue aea --out <pack_dir> --latex-command definitely_missing_pdflatex
python -m econpaper.cli release-gate --pack-dir <pack_dir> --human-eval <human_eval.json> --out <release_dir>
python -m econpaper.cli quality-suite --out <quality_dir>
```

Expected:

- `write` exits 0 for a real, validated fixture.
- `main.md`, `main.tex`, `AUTHOR_REPORT.md`, `sections/`, `tables/`, and `reports/internal/` exist.
- `main.pdf` may be absent if LaTeX is unavailable, but the markdown fallback and compile memo must be present.
- `sections/04_results.md` and `main.md` must contain no unresolved `{{...}}` numeric placeholders.
- `reports/internal/numeric_rendering_sections.json` must exist.
- `release-gate` passes only when the human-evaluation fixture satisfies the v3 thresholds.
- `quality-suite` reports the false-confidence and Q-series manifest.

Also test external table importing:

```powershell
python -m econpaper.cli import-table --input <stata_or_r_or_python_or_latex_table> --format auto --out <import_dir>
python -m econpaper.cli evidence --run-dir <run_dir> --model-table <import_dir>\model_table.csv --out <evidence_dir>
```

Expected:

- common Stata/R/Python/statsmodels/CSV/LaTeX coefficient tables produce `model_table.csv`;
- random prose numbers do not become evidence;
- LaTeX significance stars do not become exact p-values;
- coefficient-only rows without inference are marked non-claimable;
- duplicate term/model pairs hard-block as ambiguous.

## Negative Tests

Try to break the system. At minimum:

1. Change `run_id` or config to `smoke` or `mock`; `write` must hard-block mock-as-real output.
2. Remove `validation_report.json`; verified Results writing must be disabled.
3. Use an unknown method name; automatic claims must be disabled.
4. Leave a numeric placeholder unresolved; `release-gate` must fail.
5. Remove magnitude context; Results must not pass as release-ready unless the author-input-needed magnitude gap is explicit.
6. Put a missing citation key into citation safety; claim ledger must hard-block.
7. Use PowerShell-generated UTF-8 BOM JSON; the current code should accept it.
8. Run `auth verify openai` and `auth verify claude` without credentials; both must fail with `credential_missing`, not fake success.
9. Configure fake API keys with `auth login`; `auth status` must not print the key, and live `auth verify` must reject them.
10. Check that root-level user-readable reports are consolidated and JSON remains under `reports/internal/`.

## Auth Checks

Official behavior expected:

- OpenAI verification uses `GET https://api.openai.com/v1/models` with `Authorization: Bearer <key>`.
- Claude verification uses `GET https://api.anthropic.com/v1/models` with `x-api-key` and `anthropic-version: 2023-06-01`.
- `auth status` must be redacted.
- Missing credentials are hard failures.
- Provider/network errors are hard failures.

Run:

```powershell
python -m econpaper.cli auth login openai --api-key-env OPENAI_API_KEY
python -m econpaper.cli auth login claude --api-key-env ANTHROPIC_API_KEY
python -m econpaper.cli auth status
python -m econpaper.cli auth verify openai
python -m econpaper.cli auth verify claude
```

If real credentials are unavailable, say that live verification could not be completed because credentials are missing. Do not treat that as success.

## Known Boundaries To Evaluate Honestly

Do not mark these as accidental regressions unless the code claims otherwise:

- P0 does not implement literature search, citation graph discovery, PDF crawling, or literature RAG.
- P0 now has a common-format external table importer for Stata/R/Python/statsmodels/CSV/LaTeX tables, but arbitrary nonstandard or ambiguous tables must still fail closed or require parser expansion.
- The release-gate machinery exists, but a real five-scholar evaluation campaign is still external evidence that must be supplied.
- `main.pdf` depends on local LaTeX availability; markdown fallback is expected when LaTeX is missing.
- Auth commands exist, but live OpenAI/Claude verification requires real keys.
- Section prose is intentionally conservative and ledger-driven; the remaining scholarly 30% requires author input.

## Required Output

Write a structured review with these sections:

1. Executive verdict: production-ready, usable-but-limited, demo-only, or unsafe.
2. Smoke-test transcript summary: commands, exit codes, and key output files.
3. Release-gate assessment: what passed and what still blocks a real release.
4. Auth assessment: OpenAI/Claude status, live verification result, and any credential caveats.
5. False-confidence risks: top 10 ways the system could still mislead a scholar.
6. Known unfinished work: distinguish roadmap-intentional P1/P2 work from missing P0 quality.
7. Code findings: only high-impact bugs, with file paths and reproduction steps.
8. Recommendation: the next 5 changes that most improve real economics/finance usefulness.

Be strict. Passing unit tests is not enough. The standard is whether a serious economics, finance, accounting, or management scholar could use the package as a trustworthy research-writing assistant and understand what remains their responsibility.
