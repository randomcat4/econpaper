# Reporting shared contract

## Purpose

Shared contract for `skills/reporting/*.md`. Reporting skills may keep their
specialized logic, but they should not duplicate this boilerplate in full.

## Required artifact paths

Before writing strong language, inspect the relevant available artifacts:

- `status.json`
- `claim_gate.json`
- `manifest.json`
- `artifact_manifest.json`
- `diagnostics.json`
- `model_table.csv`
- `reviewer_risk.json`
- `backend_status.json`
- `backend_discovery.json` or equivalent
- logs, specs, robustness outputs, event-study tables, placebo outputs,
  balance outputs, W-sensitivity outputs, and power notes when relevant

If an artifact is referenced but missing, treat it as missing evidence. If
`claim_gate.json` is missing, paper-ready, causal, structural, legal,
audit-grade, and backend-certified claims are unavailable.

## Claim gate wording

- State what the artifacts support before stating what they do not support.
- Use the strictest artifact when evidence conflicts.
- A favorable model table cannot override a failed diagnostic or claim gate.
- `diagnostic_success` means the diagnostic ran; it does not authorize the
  paper claim.
- Missing diagnostics require `unknown`, `diagnostic_only`, or `blocked`
  readiness depending on the intended claim.

## Parser-only and dependency caveats

- Parser-only, interface-only, dry-run, skipped, mock, failed, unavailable, or
  unknown backend status is not live backend execution.
- `missing_dependency` is not a backend pass.
- Backend discovery is discovery evidence only unless execution artifacts show
  the backend actually ran.

## Global forbidden claims

- Failure to reject pre-treatment differences is not evidence that parallel
  trends holds. It is only a diagnostic non-rejection and must be interpreted
  with power, event-window length, support, anticipation, and cohort-specific
  pretrends.
- A short-run pass-through coefficient is not a long-run welfare, incidence, or
  general-equilibrium result. Long-run welfare claims require explicit
  assumptions about demand, supply, market structure, adjustment margins,
  incidence, and the policy counterfactual.
- Do not claim paper readiness when `claim_gate.json` is missing, failed, or
  stricter than the summary.
- Do not convert parser-only or missing-dependency output into live backend
  execution.
- Do not infer legal, fraud, intent, compliance, or audit assurance from ESG
  text risk or emissions estimates alone.

## Shared schema references

Reporting outputs should preserve the base fields from shared rules and add
domain-specific fields only when they are needed:

- `../_shared/01_claim_language_rules.md`
- `../_shared/03_artifact_reading_rules.md`
- `../_shared/05_forbidden_fallbacks.md`
- `../_shared/06_reviewer_mode_rules.md`
- `../_shared/07_scholarly_depth_rules.md`
- `../_shared/08_domain_literature_anchor_rules.md`

The `scholarly_depth` block and forbidden-claims schema must be carried forward
when result interpretation, appendix mapping, environmental claim guarding,
policy-brief translation, or referee reporting can affect claim strength.

## Shared claim guards

- `../_shared/09_global_claim_guards.md`
