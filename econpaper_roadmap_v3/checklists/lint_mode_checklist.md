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
