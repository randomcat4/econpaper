# Skill: env_econ_research_intake

## Purpose

Convert a natural-language environmental economics, ESG, low-carbon, or climate-finance question into a structured research brief.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- The user describes a research idea but has not specified unit, time, treatment, outcome, or estimand.
- The question mixes policy, exposure, spatial spillovers, firm heterogeneity, or measurement error.

## Do not use when

- Do not select a final estimator before data inventory and policy design are known.
- Do not claim the research design is identified.

## Inputs expected

- User research question.
- Known data fields, period, geography, and policy/exposure description if available.

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

- Restate the question as a research brief.
- Identify unit, time frequency, outcome, treatment/exposure, and estimand candidates.
- Flag likely staggered adoption, continuous treatment, spatial spillover, and measurement-error risks.
- Route to next intake/domain skill files.

## Candidate outputs

- Research brief.
- Clarifying questions.
- Candidate downstream skills.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
research_brief:
  domain: environmental_economics | esg | low_carbon | climate_finance | mixed
  user_question_rewrite: string
  unit_candidates: []
  time_frequency_candidates: []
  outcome_candidates: []
  treatment_or_exposure_candidates: []
  estimand_candidates: []
  likely_design:
    binary_policy: boolean
    staggered_adoption: unknown | true | false
    continuous_treatment: unknown | true | false
    spatial_spillover_risk: low | medium | high | unknown
    measurement_error_risk: low | medium | high | unknown
  required_user_clarifications: []
  candidate_skill_files_next: []
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- Natural-language intake is not a validated design.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not map a broad environmental question directly to TWFE main estimation.

## Handoff to code

- Ask code to inspect data columns, panel integrity, policy timing, and available backends.

## Handoff from code artifacts

- Use data audits and design diagnostics to update the brief before claim language.

## Minimal examples

### Input

User: I want to study whether low-carbon city pilots increased firm green patents.

### Expected skill output

```yaml
skill_name: env_econ_research_intake
user_question_summary: "Low-carbon pilot effects on firm green patents."
research_domain: low_carbon
research_brief:
  unit: firm
  time_frequency: year
  outcome_candidates: [green_patent_count, citation_weighted_green_patents]
  treatment_or_exposure: low_carbon_city_pilot
  estimand_candidates: [ATT_by_adoption_cohort, dynamic_ATT]
  identification_risks: [staggered_adoption, policy_selection, spatial_spillover, patent_lag]
candidate_workflows: [did_paper_run, spatial_spillover_run]
candidate_methods: [cs_did_attgt, did_imputation_event, twfe_event_study_diagnostic_only]
required_diagnostics: [treatment_timing_check, pretrend_check, never_treated_support_check]
recommended_robustness: [alternative_green_patent_measure, lag_structure]
forbidden_claims: [do_not_use_twfe_as_staggered_main_claim]
claim_language:
  allowed: ["Candidate design only."]
  disallowed: ["The policy caused green innovation."]
uncertainty_notes: ["Need official pilot timing and firm-city mapping."]
next_code_actions: [draft_spec, validate_spec]
```

## Completion checklist

- Fixed sections are present.
- Output is YAML or JSON.
- Forbidden claims are listed.
- Handoff to code and handoff from artifacts are explicit.
- claim_gate.json controls all strong claims.
- Unsupported backends and volatile facts are not overclaimed.
- Minimal example includes input and YAML output.
