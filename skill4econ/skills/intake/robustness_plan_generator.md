# Skill: robustness_plan_generator

## Purpose

Generate a prioritized robustness and sensitivity plan matched to design risks.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- The user has a candidate design and needs reviewer-ready robustness planning.
- Diagnostics show possible design, measurement, spillover, or backend risks.

## Do not use when

- Do not use robustness checks to rescue a failed main design.
- Do not list generic checks without mapping them to risks.

## Inputs expected

- Research brief, method recommendation, diagnostics, reviewer risks, and run status if available.

## Required repo artifacts to inspect

- README.md
- skill4econ/registry.yml
- skill4econ/cli.py
- skill4econ/core.py
- skill4econ/python_wrappers.py
- skill4econ/workflows.py
- skill4econ/diagnostics/
- skill4econ/tests/fixtures/
- skill4econ/tests/backends/
- status.json when a run exists
- claim_gate.json when a run exists
- manifest.json or artifact_manifest.json when a run exists
- diagnostics.json, reviewer_risk.json, backend_status.json, and model_table.csv when present

Also read shared rules before writing output:

- `../_shared/00_skill_authoring_rules.md`
- `../_shared/01_claim_language_rules.md`
- `../_shared/02_evidence_lookup_rules.md`
- `../_shared/03_artifact_reading_rules.md`
- `../_shared/04_spec_drafting_rules.md`
- `../_shared/05_forbidden_fallbacks.md`
- `../_shared/06_reviewer_mode_rules.md`

## Domain reasoning steps

- Separate required-before-claim checks from secondary robustness.
- Map each check to an identification or measurement risk.
- Flag missing data needed.
- Name not-applicable checks to avoid checklist inflation.

## Candidate outputs

- Prioritized robustness plan.
- Missing data list.
- Claim-blocking diagnostics.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
robustness_plan:
  required_before_claim: []
  high_priority: []
  medium_priority: []
  optional: []
  not_applicable: []
  missing_data_needed: []
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- Robustness cannot override claim_gate.json or failed overlap/backend diagnostics.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not write that many robustness checks prove causality when the design is blocked.

## Handoff to code

- Ask code to run feasible robustness checks and record outputs in artifact manifests.

## Handoff from code artifacts

- Read robustness tables, diagnostics, and claim gate before ranking evidence.

## Minimal examples

### Input

Input: Staggered DID with possible spillover and green patent measurement error.

### Expected skill output

```yaml
skill_name: robustness_plan_generator
user_question_summary: "Robustness for low-carbon pilot and green patents."
research_domain: low_carbon
research_brief:
  unit: firm
  time_frequency: year
  outcome_candidates: [green_patent_count]
  treatment_or_exposure: low_carbon_city_pilot
  estimand_candidates: [dynamic_ATT]
robustness_plan:
  required_before_claim: [pretrend_check, cohort_support, spillover_contamination_check]
  high_priority: [alternative_green_patent_definitions, lagged_outcomes, excluding_neighbor_exposed_controls]
  medium_priority: [alternative_cluster_levels, balanced_panel_sensitivity]
  optional: [placebo_policy_dates]
  not_applicable: [ppmlhdfe_if_outcome_can_be_negative]
  missing_data_needed: [official_policy_batch_dates, patent_classification_metadata]
required_diagnostics: [pretrend_check, support_check]
forbidden_claims: [do_not_use_robustness_to_override_failed_design]
claim_language:
  allowed: ["Robustness plan identifies checks before a claim."]
  disallowed: ["Robustness establishes causality."]
uncertainty_notes: []
next_code_actions: [run_required_diagnostics]
```

## Completion checklist

- Fixed sections are present.
- Output is YAML or JSON.
- Forbidden claims are listed.
- Handoff to code and handoff from artifacts are explicit.
- claim_gate.json controls all strong claims.
- Unsupported backends and volatile facts are not overclaimed.
- Minimal example includes input and YAML output.
