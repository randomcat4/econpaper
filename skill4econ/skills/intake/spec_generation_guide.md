# Skill: spec_generation_guide

## Purpose

Draft code-ready but unvalidated specs from research brief, data inventory, policy design, and method recommendation.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- The user wants a structured spec for skill4econ code.
- The design has been narrowed but not validated.

## Do not use when

- Do not emit raw Stata/R command strings as the spec.
- Do not mark a draft spec as validated.

## Inputs expected

- Research brief, data inventory, policy design, chosen candidate methods, and required metadata.

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

- Write a draft spec with unit, time, y, treatment/exposure, covariates, FE, cluster, engine, method, and output paths.
- Mark user-confirm fields.
- Require W, CRS, emissions units, carbon boundaries, and policy timing metadata when relevant.
- Send to code validation.

## Candidate outputs

- Draft spec.
- Fields needing confirmation.
- Validation tasks.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
spec_draft:
  method: string
  engine: python | stata | unknown
  data_path: null
  unit_id: null
  time: null
  outcome: null
  treatment_or_exposure: null
  covariates: []
  fixed_effects: []
  cluster: []
  metadata_required: []
  fields_need_user_confirmation: []
  validation_required: true
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- The draft is not runnable until code validates required fields and backends.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not hide missing metadata by filling plausible-looking defaults.

## Handoff to code

- Run validate-method or workflow preflight with strict artifact checks.

## Handoff from code artifacts

- Read validation errors and update the draft without claiming estimation ran.

## Minimal examples

### Input

Input: Build a draft spec for staggered firm DID with city-level policy.

### Expected skill output

```yaml
skill_name: spec_generation_guide
user_question_summary: "Draft modern DID spec."
research_domain: low_carbon
research_brief:
  unit: firm
  time_frequency: year
  outcome_candidates: [green_patent_count]
  treatment_or_exposure: low_carbon_city_pilot
  estimand_candidates: [ATT_g_t]
spec_draft:
  method: cs_did_attgt
  engine: stata
  data_path: null
  unit_id: firm_id
  time: year
  outcome: green_patent_count
  treatment_or_exposure: pilot
  covariates: []
  fixed_effects: [firm, year]
  cluster: [city]
  metadata_required: [policy_adoption_year, firm_city_crosswalk]
  fields_need_user_confirmation: [data_path, covariates, cluster]
  validation_required: true
forbidden_claims: [do_not_call_draft_validated]
claim_language:
  allowed: ["Draft spec only."]
  disallowed: ["The model has run."]
uncertainty_notes: [Need data path and policy timing.]
next_code_actions: [validate_method]
```

## Completion checklist

- Fixed sections are present.
- Output is YAML or JSON.
- Forbidden claims are listed.
- Handoff to code and handoff from artifacts are explicit.
- claim_gate.json controls all strong claims.
- Unsupported backends and volatile facts are not overclaimed.
- Minimal example includes input and YAML output.
