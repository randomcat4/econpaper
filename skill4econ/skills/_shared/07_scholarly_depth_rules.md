# Skill: scholarly_depth_rules

## Purpose

Upgrade skill4econ editing from formal checklist completion to scholar-grade
research design reasoning for environmental economics, ESG, climate finance,
and causal inference.

Use this shared skill before authoring or revising any domain skill. The goal is
not to make markdown longer. The goal is to make each skill behave like a careful
econometric researcher: define the estimand, name identification assumptions,
model measurement, anticipate failure modes, state referee objections, and
downgrade claims when code artifacts do not support them.

This skill packages the GPT-5.5 Pro scholarly upgrade roadmap supplied on
2026-06-07. Treat it as the scholar-facing planning layer for future skill
revisions, not as an estimator, backend, validator, or artifact certifier.

## When to use

- Revising any `skills/domain/*.md` file.
- Auditing whether a skill is useful to econometricians rather than merely
  structurally complete.
- Deciding whether to call GPT-5.5 Pro again because the scholarly design is not
  mature enough.
- Preparing the next small editing wave, with at most two markdown files in
  scope.

## Do not use when

- Do not use as a substitute for code validation, backend discovery, artifact
  validation, W-matrix checks, overlap checks, or claim gating.
- Do not use to implement estimators or modify Stata/R/Python estimation code.
- Do not use to hardcode volatile policy, regulatory, disclosure, standard,
  package, satellite-product, MRIO, or carbon-accounting facts.
- Do not use as a reason to keep editing a large batch in one pass. If more than
  five exchanges with GPT-5.5 Pro are needed, start a fresh ChatGPT sidebar
  conversation and keep the new prompt focused on at most two markdown files.

## Inputs expected

- The target markdown skill file or planned skill revision.
- The current repository files and artifact contracts from the workspace.
- The original TODO requirements when available.
- The latest GPT-5.5 Pro planning or review response, if one exists.
- Any relevant empirical context from the user, such as policy design, unit,
  timing, outcome, treatment, exposure, or target audience.

## Required repo artifacts to inspect

Inspect workspace files first. Do not rely on installed user-level skills as the
authority for this repository.

- `README.md`
- `registry.yml`
- `cli.py`
- `core.py`
- `python_wrappers.py`
- `workflows.py`
- `docs/ARTIFACT_CONTRACT.md` when present
- `docs/BACKEND_CONTRACT.md` when present
- `diagnostics/`
- `tests/fixtures/`
- `tests/backends/`
- Existing shared, intake, domain, reporting, schema, and delivery-check files.
- `skills/_shared/08_domain_literature_anchor_rules.md`
- Run artifacts such as `status.json`, `claim_gate.json`, `manifest.json`,
  `artifact_manifest.json`, `diagnostics.json`, `reviewer_risk.json`,
  `backend_discovery.json`, and `model_table.csv` when a run exists.

If these artifacts are unavailable, the skill may still draft scholarly
questions and candidate routes, but it must mark capability-dependent claims as
unknown or blocked.

## Domain reasoning steps

Use these rules when revising a domain skill.

1. Start with the research object, not the estimator.
   - Define unit, time, outcome, treatment or exposure, and the estimand.
   - Explain whether the estimand is ATT(g,t), dynamic ATT, CATE, direct or
     indirect impact, scenario exposure, efficiency score, or descriptive
     measurement target.
   - If the estimand is unclear, the skill must ask for clarification instead
     of recommending a main method.

2. Replace generic steps with domain-specific reasoning.
   - Generic text such as "clarify unit/time/outcome, map risks, rank methods"
     is not enough.
   - Each domain skill should contain at least eight field-specific reasoning
     steps before it is treated as scholar-ready.

3. Add the mandatory scholarly-depth block to domain outputs.

```yaml
scholarly_depth:
  estimand_definition: string
  identification_assumptions: []
  measurement_model: []
  data_construction_risks: []
  method_decision_tree: []
  diagnostics_that_block_claims: []
  robustness_ranked_by_risk: []
  referee_objections: []
  downgrade_triggers: []
```

4. Add the mandatory domain literature-anchor contract to domain outputs.

```yaml
literature_anchors:
  canonical_papers_or_authors: []
  canonical_data_sources: []
  live_lookup_required_for: []

measurement_regimes:
  competing_proxy_definitions: []
  validation_targets: []
  known_mismeasurement_channels: []

identification_debate:
  core_threats: []
  sorting_vs_siting_or_selection_channel: null
  why_method_not_magic: []

referee_entry_points:
  likely_major_objections: []
  minimal_empirical_section_checklist: []
  claims_to_downgrade: []
```

The contract can be populated by a domain skill only when the entries are real
and defensible. Put volatile details in `live_lookup_required_for`; do not
invent citations or data sources.

5. Use a method-decision tree, not a method list.
   - Explain why candidate methods fit or do not fit.
   - Include `not_recommended_methods` when common choices are unsafe.
   - Never present TWFE, OLS/log-linear fallback, parser-only output, or
     structural spatial language as a default main claim.

6. Treat code handoff as a boundary.
   - The skill states what code must validate.
   - The skill does not validate specs, certify backends, or declare artifacts
     complete.
   - The skill names which artifacts would downgrade or block claims.

7. Require a downgrade example.
   - Each domain skill should eventually have at least two examples: one good
     planning example and one refusal or downgrade example.
   - Downgrade examples are required where users ask for causal, structural,
     legal, fraud, assurance, audit-grade, or backend-certified claims.

8. Keep volatile facts out of the skill body.
   - For standards, disclosure rules, CBAM coverage, satellite products,
     carbon-accounting factors, MRIO vintages, package availability, and policy
     status, instruct the user or downstream agent to check official/latest
     sources at use time.

9. Call GPT-5.5 Pro when scholarly confidence is below 90%.
   - Use a fresh Chrome ChatGPT sidebar conversation after at most five
     back-and-forth exchanges.
   - Keep each prompt focused on no more than two markdown files.
   - Ask GPT-5.5 Pro to reason as an econometrician or field scholar, not as an
     engineering reviewer.

## Candidate outputs

- Scholar-grade revision notes for one or two markdown skill files.
- A domain-specific `scholarly_depth` block.
- A ranked method decision tree.
- A list of diagnostics that block or downgrade claims.
- Referee objections and must-fix design weaknesses.
- A downgrade/refusal example for overclaims.
- A next-wave editing plan with at most two markdown files.

## Output schema

Return YAML or JSON. Do not omit the base fields. Add the scholarly-depth fields
when editing or auditing a domain skill.

```yaml
skill_name: scholarly_depth_rules
user_question_summary: string
research_domain: environmental_economics | esg | climate_finance | causal_inference | mixed
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
scholarly_depth:
  estimand_definition: string
  identification_assumptions: []
  measurement_model: []
  data_construction_risks: []
  method_decision_tree: []
  diagnostics_that_block_claims: []
  robustness_ranked_by_risk: []
  referee_objections: []
  downgrade_triggers: []
not_recommended_methods: []
next_markdown_files_to_edit: []
call_gpt55_pro_if_below_90: boolean
```

## Required caveats

- Formal structure is not scholarly completeness.
- A long markdown file is still weak if it cannot say what a referee would
  challenge or which artifact would downgrade the claim.
- These skills are prompt and rubric files. They do not run estimators,
  validate specs, discover backends, certify artifacts, or override
  `claim_gate.json`.
- Modern methods are not magic words. DID, SDID, GSC, DML, PPMLHDFE, SAR/SDM,
  DEA, MRIO, and remote-sensing proxies each require design-specific
  assumptions and diagnostics.
- Official/latest lookup is required at use time for volatile standards,
  policies, data products, APIs, packages, and regulatory facts.

## Shared claim guards

- `../_shared/09_global_claim_guards.md`

## Forbidden claims

- Do not treat TWFE as the default main causal design for staggered policy
  adoption.
- Do not call a pretrend check "passed" without discussing power, event window,
  support, anticipation, and cohort-specific diagnostics.
- Failure to reject pre-treatment differences is not evidence that parallel
  trends holds. It is only a diagnostic non-rejection and must be interpreted
  with power, event-window length, support, anticipation, and cohort-specific
  pretrends.
- A short-run pass-through coefficient is not a long-run welfare, incidence, or
  general-equilibrium result. Long-run welfare claims require explicit
  assumptions about demand, supply, market structure, adjustment margins,
  incidence, and the policy counterfactual.
- Do not turn `W*treatment` in reduced-form spatial exposure into an SDM/SAR
  indirect effect.
- Do not treat parser-only or interface-only output as a live structural model.
- Do not replace a missing PPMLHDFE backend with OLS/log-linear flow estimates
  and call the result equivalent.
- Do not call CATE, causal forest, or subgroup heatmaps confirmatory without
  orthogonality, cross-fitting, overlap, leakage audit, holdout confirmation,
  and multiple-testing discipline.
- Do not infer fraud, legal violation, intent, audit assurance, or compliance
  status from ESG text or emissions estimates.
- Do not call financed emissions direct bank operating emissions.
- Do not call MRIO/network exposure certified supply-chain emissions.
- Do not turn DEA second-stage associations into causal determinants by
  default.

## Handoff to code

Ask code to verify only what code can verify:

- Spec field validity.
- Backend availability and live-run status.
- Estimator package, version, and dependency status.
- Artifact completeness.
- W-matrix metadata, CRS, islands, normalization, and sensitivity outputs.
- Overlap, balance, prefit, placebo, separation, convergence, leakage, and
  diagnostics.
- Claim gate status and reviewer-risk artifacts.

The skill should hand off concrete checks, not prose confidence.

## Handoff from code artifacts

Before writing strong language, read the artifacts that establish or block
claim readiness:

- `claim_gate.json`
- `status.json`
- `manifest.json` or `artifact_manifest.json`
- `diagnostics.json`
- `reviewer_risk.json`
- `backend_discovery.json` or equivalent
- `model_table.csv`, only after the claim gate and diagnostics

If an artifact is missing, the skill must say which claim is unknown, partial,
or blocked.

## Minimal examples

### Input

User: "Revise `skills/domain/18_sdid_gsc_for_pilot_policies_skill.md`. It already has all required sections, so just make it more polished."

### Expected skill output

```yaml
skill_name: scholarly_depth_rules
user_question_summary: revise a pilot-policy synthetic design skill
research_domain: environmental_policy
research_brief:
  unit: city_or_region
  time_frequency: annual_or_monthly
  outcome_candidates:
    - emissions
    - pollution
    - green_innovation
  treatment_or_exposure: first_batch_pilot_policy
  estimand_candidates:
    - treated_unit_dynamic_effect
    - ATT_for_pilot_units
  identification_risks:
    - small_number_of_treated_units
    - donor_pool_contamination
    - weak_prefit
    - anticipation
candidate_workflows:
  - synthetic_control_feasibility
  - sdid_feasibility
  - generalized_synthetic_control_feasibility
candidate_methods:
  - SCM when donor pool is clean and pre-period is long
  - SDID when reweighting plus DID contrast is defensible
  - GSC when interactive fixed effects are plausible
required_diagnostics:
  - treated_unit_count
  - pre_period_length
  - donor_pool_contamination_check
  - prefit_error
  - placebo_or_permutation
recommended_robustness:
  - donor_pool_restrictions
  - leave_one_donor_out
  - alternative_pre_periods
forbidden_claims:
  - do_not_claim_policy_effect_when_prefit_is_poor
  - do_not_call_synthetic_result_automatically_more_credible_than_DID
claim_language:
  allowed:
    - candidate synthetic design if prefit and donor pool checks pass
  disallowed:
    - paper-ready policy effect without prefit and placebo evidence
uncertainty_notes:
  - capability notes and live artifacts still determine claim readiness
next_code_actions:
  - inspect donor pool
  - compute prefit diagnostics
  - run placebo diagnostics
scholarly_depth:
  estimand_definition: effect for treated pilot units relative to a constructed counterfactual
  identification_assumptions:
    - donor units approximate treated counterfactual absent treatment
    - no donor contamination
    - no severe anticipation
  measurement_model:
    - define outcome construction and timing before estimator choice
  data_construction_risks:
    - policy timing ambiguity
    - boundary changes
    - missing pre-period data
  method_decision_tree:
    - few treated and long clean pre-period -> SCM or SDID feasibility
    - many staggered treated cohorts -> modern DID estimand-first route
    - poor prefit -> exploratory only
  diagnostics_that_block_claims:
    - weak prefit
    - contaminated donor pool
    - missing policy timing
  robustness_ranked_by_risk:
    - donor pool restrictions
    - placebo tests
    - alternative pre-periods
  referee_objections:
    - policy selection into pilot status
    - spillovers to donor pool
    - synthetic weights extrapolate beyond credible support
  downgrade_triggers:
    - no prefit diagnostics
    - no placebo diagnostics
    - claim_gate.json missing
not_recommended_methods:
  - default TWFE main claim for few pilot units
next_markdown_files_to_edit:
  - skills/domain/18_sdid_gsc_for_pilot_policies_skill.md
call_gpt55_pro_if_below_90: true
```

## Completion checklist

- The revision is written for econometric researchers, not only for engineers.
- The estimand is defined in words, not only named.
- Identification assumptions are explicit and domain-specific.
- Measurement and data-construction risks are named.
- A method decision tree explains why methods fit or do not fit.
- Diagnostics that block claims are explicit.
- Robustness checks are ranked by the risk they address.
- Referee objections are listed.
- Downgrade triggers are clear and non-negotiable.
- The domain literature-anchor contract is present and no fake anchors are
  inserted.
- The skill still cannot bypass `claim_gate.json` or code artifacts.
- No more than two markdown files are in the current editing scope.
- GPT-5.5 Pro is called in a fresh sidebar conversation if scholarly confidence
  is below 90%.
