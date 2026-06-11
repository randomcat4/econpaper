# Skill: artifact_reading_rules

## Purpose

Define the required order for reading skill4econ run outputs before writing any result interpretation.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- Authoring or auditing any skill4econ domain, intake, or reporting skill.

## Do not use when

- Do not use as a substitute for code validation or artifact validation.

## Inputs expected

- A draft skill output or a planned skill response.
- Any relevant run artifacts if claims are being written.

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

- Read `status.json`, `claim_gate.json`, `manifest.json`, and `artifact_manifest.json` first.
- Then read diagnostics, reviewer risks, backend status, logs, and model tables.
- Never infer readiness from `model_table.csv` alone.
- Never infer readiness from CLI exit code alone.
- If required artifacts are missing, downgrade to insufficient evidence for claim readiness.

## Candidate outputs

- A safer draft, checklist, or set of blocked claims.
- Explicit uncertainty notes when sources or artifacts are missing.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
skill_name: string
user_question_summary: string
research_domain: string
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: null
  estimand_candidates: []
  identification_risks: []
candidate_workflows: []
candidate_methods: []
required_diagnostics: []
recommended_robustness: []
forbidden_claims: []
claim_language:
  allowed: []
  disallowed: []
uncertainty_notes: []
next_code_actions: []
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- Shared rules constrain downstream skills but cannot certify the result themselves.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not weaken these rules to make a result sound stronger.

## Handoff to code

- Ask code to validate specs, discover backends, run diagnostics, and write artifacts.

## Handoff from code artifacts

- Read claim levels, agent status, reviewer risks, and missing artifact lists before prose.

## Minimal examples

### Input

Input: A draft says TWFE proves a staggered policy reduced PM2.5.

### Expected skill output

```yaml
skill_name: artifact_reading_rules
user_question_summary: "A model_table.csv exists but claim_gate.json is missing."
research_domain: reporting
claim_language:
  allowed:
    - "The estimate table exists, but claim readiness is not established."
  disallowed:
    - "The result is paper-ready."
forbidden_claims:
  - do_not_use_model_table_alone
```

## Completion checklist

- Fixed sections are present.
- Output is YAML or JSON.
- Forbidden claims are listed.
- Handoff to code and handoff from artifacts are explicit.
- claim_gate.json controls all strong claims.
- Unsupported backends and volatile facts are not overclaimed.
- Minimal example includes input and YAML output.
