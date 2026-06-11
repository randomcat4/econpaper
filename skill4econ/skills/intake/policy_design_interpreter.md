# Skill: policy_design_interpreter

## Purpose

Translate policy timing, intensity, treatment reversal, anticipation, spillover, and concurrent-policy features into design implications.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- A research question involves a policy, rule, pilot, disclosure mandate, price shock, or event.
- The user needs to know which design family is plausible.

## Do not use when

- Do not recommend a main estimator before treatment timing and controls are assessed.
- Do not treat staggered policy as simple two-by-two DID.

## Inputs expected

- Policy description, adoption dates, treated units, controls, intensity variables, and geography.

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

- Classify policy type.
- Assess simultaneous vs staggered adoption.
- Check never-treated and not-yet-treated support.
- Flag anticipation, reversal, spillover, concurrent policies, and selection risk.
- Recommend and block design families.

## Candidate outputs

- Policy design summary.
- Recommended design family.
- Blocked designs.
- Diagnostics before estimation.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
policy_design:
  policy_type: binary | staggered_binary | continuous_intensity | price_shock | disclosure_rule | event | unknown
  adoption_timing: simultaneous | staggered | unknown
  never_treated_available: unknown | true | false
  not_yet_treated_support: unknown | strong | weak | none
  anticipation_risk: low | medium | high | unknown
  spillover_risk: low | medium | high | unknown
  concurrent_policy_risk: low | medium | high | unknown
  recommended_design_family: []
  blocked_designs: []
  diagnostics_required_before_estimation: []
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- Policy coding must be checked against official/latest policy sources when facts may change.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not mark TWFE as the main staggered-policy estimator.

## Handoff to code

- Validate treatment timing, reversals, never-treated support, and concurrent-policy overlap.

## Handoff from code artifacts

- Read treatment timing diagnostics and reviewer risks before method selection.

## Minimal examples

### Input

Input: Cities enter a low-carbon pilot in several batches; some never enter.

### Expected skill output

```yaml
skill_name: policy_design_interpreter
user_question_summary: "Batched low-carbon pilot."
research_domain: environmental_policy
research_brief:
  unit: city
  time_frequency: year
  outcome_candidates: [pm25]
  treatment_or_exposure: low_carbon_city_pilot
  estimand_candidates: [ATT_g_t, event_time_ATT]
policy_design:
  policy_type: staggered_binary
  adoption_timing: staggered
  never_treated_available: true
  not_yet_treated_support: strong
  anticipation_risk: medium
  spillover_risk: medium
  concurrent_policy_risk: unknown
  recommended_design_family: [modern_did, spatial_exposure_sensitivity]
  blocked_designs: [twfe_main_claim]
  diagnostics_required_before_estimation: [cohort_counts, pretrend_check, spillover_contamination_check]
candidate_methods: [cs_did_attgt, did_imputation_event]
forbidden_claims: [do_not_use_twfe_only_success_for_staggered]
claim_language:
  allowed: ["Staggered design requires modern DID diagnostics."]
  disallowed: ["TWFE is the default main result."]
uncertainty_notes: [Need exact adoption dates.]
next_code_actions: [draft_modern_did_spec]
```

## Completion checklist

- Fixed sections are present.
- Output is YAML or JSON.
- Forbidden claims are listed.
- Handoff to code and handoff from artifacts are explicit.
- claim_gate.json controls all strong claims.
- Unsupported backends and volatile facts are not overclaimed.
- Minimal example includes input and YAML output.
