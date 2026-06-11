# Skill: method_selection_rubric

## Purpose

Rank candidate method families from research brief, data inventory, and policy design while naming required conditions and blocked methods.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- The user asks which econometric method or workflow to use.
- A draft research brief and design summary exist.

## Do not use when

- Do not output a single estimator without alternatives and risks.
- Do not use method names to imply repo backends are available.

## Inputs expected

- Research brief.
- Data inventory.
- Policy design.
- Known repo capabilities and backend status.

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

- Match design to candidate method families.
- Separate primary, secondary, diagnostic-only, and blocked methods.
- Attach required conditions and diagnostics.
- Respect forbidden fallbacks and repo capability boundaries.

## Candidate outputs

- Method recommendation.
- Blocked method list.
- Next spec drafts.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
method_recommendation:
  primary_candidates:
    - method: string
      reason: string
      required_conditions: []
      required_diagnostics: []
  secondary_candidates: []
  diagnostic_only: []
  blocked_methods:
    - method: string
      blocked_reason: string
  next_spec_drafts: []
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- Recommendation is not execution; code must validate method availability and run artifacts.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not call sklearn DML fallback DoubleML/EconML.
- Do not call reduced-form spatial exposure structural spillover.

## Handoff to code

- Create draft specs for chosen candidates and validate method/backends.

## Handoff from code artifacts

- Use manifests, backend status, claim levels, and reviewer risks to update recommendations.

## Minimal examples

### Input

Input: Staggered policy, firm-year panel, green patent count, possible spillover.

### Expected skill output

```yaml
skill_name: method_selection_rubric
user_question_summary: "Choose methods for staggered low-carbon pilot."
research_domain: low_carbon
research_brief:
  unit: firm
  time_frequency: year
  outcome_candidates: [green_patent_count]
  treatment_or_exposure: low_carbon_city_pilot
  estimand_candidates: [ATT_g_t, dynamic_ATT]
method_recommendation:
  primary_candidates:
    - method: cs_did_attgt
      reason: "Staggered absorbing binary treatment."
      required_conditions: [valid_gvar, support_for_controls]
      required_diagnostics: [cohort_support, pretrend_check]
  secondary_candidates: [did_imputation_event, spatial_exposure_did_sensitivity]
  diagnostic_only: [twfe_event_study]
  blocked_methods:
    - method: twfe_main_claim
      blocked_reason: "Staggered adoption and heterogeneity risk."
  next_spec_drafts: [modern_did_spec, spatial_exposure_spec]
candidate_methods: [cs_did_attgt, did_imputation_event]
required_diagnostics: [pretrend_check, support_check, spillover_check]
recommended_robustness: [alternative_outcomes, event_window_sensitivity]
forbidden_claims: [do_not_treat_twfe_as_main]
claim_language:
  allowed: ["Candidate methods ranked."]
  disallowed: ["Estimator has run."]
uncertainty_notes: [Need backend status.]
next_code_actions: [validate_method, run_preflight]
```

## Completion checklist

- Fixed sections are present.
- Output is YAML or JSON.
- Forbidden claims are listed.
- Handoff to code and handoff from artifacts are explicit.
- claim_gate.json controls all strong claims.
- Unsupported backends and volatile facts are not overclaimed.
- Minimal example includes input and YAML output.
