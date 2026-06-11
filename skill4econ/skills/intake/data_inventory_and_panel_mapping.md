# Skill: data_inventory_and_panel_mapping

## Purpose

Inventory heterogeneous environmental, firm, geography, policy, ESG, carbon, climate, and finance data before panel construction.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- The user has datasets or column names but no validated unit-time panel.
- The project requires merging policy, exposure, emissions, firm, finance, or geospatial data.

## Do not use when

- Do not assume a clean panel from column names alone.
- Do not ignore boundary changes, CRS, duplicate IDs, or crosswalk uncertainty.

## Inputs expected

- Data dictionaries or sample columns.
- Merge keys, geography, coordinates, CRS, and time variables if known.

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

- Classify unit IDs, time fields, geography, outcomes, treatment, exposure, covariates, and merge keys.
- Identify crosswalk and geocoding needs.
- Flag duplicate unit-time, boundary, CRS, address, and firm-name risks.
- Recommend code validations.

## Candidate outputs

- Data inventory.
- Panel risk list.
- Missing metadata list.
- Next code actions.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
data_inventory:
  unit_id_fields: []
  time_fields: []
  geography_fields: []
  outcome_fields: []
  treatment_fields: []
  exposure_fields: []
  covariate_fields: []
  merge_keys: []
  known_crosswalks: []
  missing_metadata: []
  panel_risks:
    duplicate_unit_time: unknown
    boundary_changes: unknown
    missing_crs: unknown
    address_geocoding_error: unknown
    firm_name_matching_error: unknown
next_code_actions: []
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- A data inventory is not evidence that merges are correct.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not treat remote-sensing, address, or firm-name joins as validated without code checks.

## Handoff to code

- Run panel uniqueness, merge loss, CRS, geocoding, and boundary-change checks.

## Handoff from code artifacts

- Read panel manifest, sample-construction records, and diagnostics before method selection.

## Minimal examples

### Input

Input: Columns include firm_id, city, year, pm25, pilot, green_patents, lat, lon.

### Expected skill output

```yaml
skill_name: data_inventory_and_panel_mapping
user_question_summary: "Inventory firm-city-year low-carbon panel."
research_domain: low_carbon
research_brief:
  unit: firm
  time_frequency: year
  outcome_candidates: [green_patents]
  treatment_or_exposure: pilot
  estimand_candidates: [firm_level_ATT]
data_inventory:
  unit_id_fields: [firm_id]
  time_fields: [year]
  geography_fields: [city, lat, lon]
  outcome_fields: [green_patents]
  treatment_fields: [pilot]
  exposure_fields: [pm25]
  merge_keys: [firm_id, city, year]
  missing_metadata: [CRS, pilot_start_date, city_boundary_version]
  panel_risks:
    duplicate_unit_time: unknown
    boundary_changes: unknown
    missing_crs: true
    address_geocoding_error: unknown
    firm_name_matching_error: unknown
required_diagnostics: [panel_uniqueness, merge_loss, geo_integrity]
forbidden_claims: [do_not_assume_clean_panel]
claim_language:
  allowed: ["Candidate panel fields identified."]
  disallowed: ["Panel is validated."]
uncertainty_notes: [Need CRS and official policy timing.]
next_code_actions: [validate_panel_integrity, validate_geo_integrity]
```

## Completion checklist

- Fixed sections are present.
- Output is YAML or JSON.
- Forbidden claims are listed.
- Handoff to code and handoff from artifacts are explicit.
- claim_gate.json controls all strong claims.
- Unsupported backends and volatile facts are not overclaimed.
- Minimal example includes input and YAML output.
