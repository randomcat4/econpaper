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
