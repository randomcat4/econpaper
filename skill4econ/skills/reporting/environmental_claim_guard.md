# Skill: environmental_claim_guard
## Purpose
Guard claim language for environmental economics, applied micro, policy evaluation, climate, pollution, energy, and ESG reporting.
This skill reads skill4econ run artifacts and converts them into cautious, claim-gated prose.
It is a reporting and reviewer-risk skill, not an estimator, backend runner, artifact validator, legal authority, or certification service.
Its main job is to prevent the model from turning a table, diagnostic flag, parser output, or ESG text signal into a stronger claim than the artifacts support.
The primary source of truth for strong language is `claim_gate.json`.
Strong language includes causal, structural, paper-ready, audit-grade, legal, and backend-certified claims.
When artifacts conflict, use the most restrictive artifact and explain the downgrade.
When required artifacts are absent, report claim readiness as unknown or blocked, not as implicitly passed.

## Shared reporting contract

Shared reporting boilerplate lives in `./_reporting_shared_contract.md`; apply it before this file-specific logic and do not duplicate or weaken its artifact, claim-gate, parser-only, missing-dependency, forbidden-claims, or scholarly-depth rules.

## When to use
- Use when the user asks whether an environmental, ESG, pollution, climate, energy, or policy-evaluation result can be stated as a main claim.
- Use when a run directory includes status, diagnostics, model tables, claim gates, backend discovery, or reviewer-risk artifacts.
- Use when the user asks for safe manuscript prose, abstract wording, slide wording, referee-response wording, or policy-facing wording.
- Use when a result appears statistically significant but the design, backend, overlap, balance, pre-trend, measurement, or artifact provenance may limit the claim.
- Use when ESG disclosure text, greenwashing risk scores, climate commitments, carbon labels, or sustainability narratives are being interpreted.
- Use when spatial exposure or spatial policy variables are reported and the user might overstate structural spillovers.
- Use when backend availability is partial, parser-only, interface-only, missing, or not certified by artifacts.
- Use when the user wants allowed claims, downgraded claims, forbidden claims, blocking reasons, and a safe summary paragraph.
## Do not use when
- Do not use to estimate models, repair code, validate specs, install packages, discover backends, or rerun workflows.
- Do not use before reading `claim_gate.json`, or before explicitly documenting that it is missing.
- Do not use `model_table.csv` alone to authorize any main causal claim.
- Do not use `diagnostic_success` alone to authorize paper-ready causal, structural, legal, audit-grade, or backend-certified claims.
- Do not use parser-only output to state that Stata, R, Python, PPMLHDFE, SAR, SDM, or another backend actually ran.
- Do not convert reduced-form spatial exposure coefficients into structural direct, indirect, total, SAR, SDM, network, or equilibrium spillover effects.
- Do not classify ESG text evidence as fraud, illegality, intentional deception, or regulatory violation unless explicit legal authority is present in the artifacts.
- Do not substitute generic econometric advice for artifact-grounded claim gating.
- Do not hide missing artifacts behind cautious wording; missing claim gates must remain visible.
## Inputs expected
- User question, intended output audience, and intended claim strength.
- Run directory path or artifact bundle.
- `status.json` with agent status, workflow status, warnings, errors, and diagnostic-only flags.
- `claim_gate.json` with allowed, downgraded, blocked, or forbidden claim levels.
- `manifest.json` and, when present, `artifact_manifest.json` with artifact provenance and completeness.
- `diagnostics.json` with overlap, balance, pre-trend, placebo, support, W-matrix, measurement, and sample diagnostics when available.
- `model_table.csv` with coefficients, standard errors, confidence intervals, p-values, units, samples, model names, and backend labels when available.
- `reviewer_risk.json` with reviewer objections, limitations, and claim downgrade triggers when available.
- `backend_discovery.json` or equivalent backend inventory artifact.
- `backend_status.json` with installed, unavailable, missing dependency, parser-only, partial, or failed backend states.
- Any manuscript sentence, abstract sentence, policy memo sentence, figure caption, or slide claim that needs guarding.
- Any domain context needed to distinguish pollution, emissions, climate risk, ESG disclosure, abatement, compliance, adoption, exposure, health, firm, region, or market outcomes.
## Required repo artifacts to inspect
Inspect repo capability before writing claim language:
- `README.md`
- `skill4econ/registry.yml`
- `skill4econ/cli.py`
- `skill4econ/core.py`
- `skill4econ/python_wrappers.py`
- `skill4econ/workflows.py`
- `skill4econ/diagnostics/`
- `skill4econ/tests/fixtures/`
- `skill4econ/tests/backends/`
Inspect shared reporting rules before output:
- `../_shared/00_skill_authoring_rules.md`
- `../_shared/01_claim_language_rules.md`
- `../_shared/02_evidence_lookup_rules.md`
- `../_shared/03_artifact_reading_rules.md`
- `../_shared/04_spec_drafting_rules.md`
- `../_shared/05_forbidden_fallbacks.md`
- `../_shared/06_reviewer_mode_rules.md`
- `../_shared/07_scholarly_depth_rules.md`
Inspect run artifacts before authorizing claims:
- `status.json`
- `claim_gate.json`
- `manifest.json`
- `artifact_manifest.json` when present
- `diagnostics.json`
- `model_table.csv`
- `reviewer_risk.json`
- `backend_discovery.json` or equivalent backend discovery artifact
- `backend_status.json`
- Backend logs only as supporting provenance, never as a substitute for `claim_gate.json`
If any required run artifact is absent, name it in `blocking_reasons` or `uncertainty_notes`.
If artifact names differ, treat them as equivalent only when `manifest.json` or `artifact_manifest.json` documents the mapping.
## Domain reasoning steps
- Identify the intended claim: descriptive, predictive, associational, diagnostic, exploratory, causal, structural, policy-ready, audit-grade, legal, or backend-certified.
- Identify the research domain: pollution, emissions, energy transition, climate risk, carbon disclosure, ESG text, green finance, environmental justice, environmental health, policy compliance, firm behavior, local exposure, or spatial spillover.
- Read `claim_gate.json` first for claim permissions, blocking reasons, downgrade triggers, and allowed wording.
- If `claim_gate.json` is missing, set `main_claim_available` to `unknown` or `false` and prohibit strong claims.
- Read `status.json` for `agent_status`, diagnostic-only status, errors, warnings, parser-only status, partial completion, and failed components.
- Read `manifest.json` and `artifact_manifest.json` for artifact completeness, provenance, file hashes, timestamps, workflow names, and known omissions.
- Read `backend_discovery.json` or equivalent and `backend_status.json` for backend availability, missing dependencies, parser-only interfaces, version gaps, and failed calls.
- Read `diagnostics.json` for overlap, balance, pre-trends, support, placebo, leverage, W-matrix, measurement, and sample-selection diagnostics.
- Read `model_table.csv` only after the claim gate and diagnostics, and treat estimates as inputs to wording, not as claim authorization.
- Read `reviewer_risk.json` for likely referee objections and convert high-risk objections into caveats, downgrades, or code handoffs.
- Classify the strongest allowed claim level using `claim_gate.json`, then lower it when other artifacts are stricter.
- If overlap fails, state that point estimates are exploratory, diagnostic, or unreliable and cannot serve as main causal evidence.
- If balance fails, prohibit language that assumes comparable treated and control units without qualification.
- If pre-trends fail or are unavailable for a design requiring them, prohibit clean dynamic causal language.
- If placebo, falsification, or negative-control diagnostics fail, downgrade causal interpretation and name the threat.
- If backend status is parser-only or interface-only, prohibit claims that the backend model actually ran.
- If backend status is `missing_dependency`, prohibit statements that the backend passed or that backend-certified estimates exist.
- If a fallback model ran because a target backend was missing, do not present it as equivalent to the unavailable backend.
- If spatial results are reduced-form exposure or adjacency specifications, prohibit structural spillover, SAR, SDM, indirect-effect, total-effect, or equilibrium language unless the claim gate permits it.
- If W-matrix diagnostics show islands, non-normalization, instability, or sign flips, downgrade spatial claims and request W audit or sensitivity work.
- If ESG text is used, distinguish disclosure risk, greenwashing risk, inconsistency, ambiguity, and sentiment from fraud, illegality, or intentional deception.
- If legal or regulatory claims are requested, require explicit legal authority and current official source verification at use time.
- If policy, regulatory, ESG standard, carbon accounting, or official data-source facts may have changed, state that the latest official source must be checked at use time.
- If model estimates are significant but claim gate blocks the claim, explain that statistical precision does not override design or artifact failure.
- If model estimates are insignificant but artifacts are complete, avoid claiming no effect unless power, confidence intervals, and minimum detectable effects support that interpretation.
- Separate the safe empirical finding from the causal mechanism, policy interpretation, legal interpretation, and backend certification.
- Write allowed claims with verbs such as `is associated with`, `is consistent with`, `suggests`, `exploratory`, `diagnostic`, or `descriptive` when causal support is blocked.
- Write downgraded claims by naming the intended stronger claim and the precise artifact reason for downgrade.
- Write forbidden claims as sentence-level examples that the user should not publish.
- Write `safe_summary_paragraph` for a manuscript or report, not as a checklist.
- Write `reviewer_warning_paragraph` in referee mode, naming the objection that would likely block acceptance.
- Prefer direct downgrades over vague caution when artifacts identify a specific failure.
## Candidate outputs
- A YAML or JSON claim guard report with base fields, scholarly-depth fields, and `claim_guard_output`.
- A list of allowed claims with exact safe wording.
- A list of downgraded claims with the original claim strength and the artifact reason for downgrade.
- A list of forbidden claims phrased as claims to avoid.
- A list of blocking reasons tied to artifacts, not generic concerns.
- A safe summary paragraph suitable for results, abstract, slide, or memo use.
- A reviewer warning paragraph that states how a strict econometric or environmental-economics referee would object.
- A code handoff list for missing diagnostics, missing backends, missing claim gates, missing manifests, W-matrix audits, or ESG legal-source checks.
- A claim-language map with allowed and disallowed verbs.
## Output schema
Return YAML or JSON. Do not omit base fields. Include the exact `claim_guard_output` block.
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
scholarly_depth:
  estimand_definition: string
  identifying_assumptions: []
  measurement_model: []
  data_construction_risks: []
  method_decision_tree: []
  diagnostics_that_block_claims: []
  robustness_ranked_by_risk: []
  referee_objections: []
  downgrade_triggers: []
not_recommended_methods: []
claim_guard_output:
  agent_status: string
  main_claim_available: true | false | unknown
  allowed_claims: []
  downgraded_claims: []
  forbidden_claims: []
  blocking_reasons: []
  safe_summary_paragraph: string
  reviewer_warning_paragraph: string
```
Use `main_claim_available: true` only when `claim_gate.json` permits the main claim and no stricter artifact blocks it.
Use `main_claim_available: false` when the claim gate or required diagnostics block the main claim.
Use `main_claim_available: unknown` when required artifacts are missing or artifact provenance cannot be established.
## Required caveats
- `claim_gate.json` controls strong causal, structural, paper-ready, audit-grade, legal, and backend-certified claims.
- `diagnostic_success` is not paper-ready causal success.
- A statistically significant coefficient is not a claim gate.
- A small p-value cannot repair overlap failure, failed pre-trends, failed balance, missing backend evidence, or missing artifact provenance.
- Overlap failure means the point estimate can only be described as exploratory, diagnostic, or unreliable; it cannot be main causal evidence.
- Parser-only status means the skill cannot say the backend model actually ran.
- Interface-only status means the skill cannot say the target estimator was executed.
- `missing_dependency` means the skill cannot say the backend passed.
- Backend partial availability means claims must identify what actually ran and what did not run.
- Missing `claim_gate.json` means strong claims are unknown or blocked, not allowed by default.
- Missing `manifest.json` or undocumented artifact origin means provenance is incomplete and should be disclosed.
- Reduced-form spatial exposure does not identify structural SAR, SDM, direct, indirect, total, network, or equilibrium spillover effects.
- ESG text scores can support disclosure-risk or greenwashing-risk language, not fraud, illegality, intentional deception, or regulatory violation language absent explicit legal authority.
- Volatile policy, regulation, ESG standard, carbon accounting, API, and data-source facts must be checked from official latest sources at use time, not hard-coded in the skill output.
- If external legal authority is needed, request official-source verification rather than inventing legal conclusions.
- If artifacts disagree, use the more conservative interpretation and record the conflict.
- If code ran a fallback because the requested backend was unavailable, state that the fallback is not equivalent to the requested backend unless the claim gate explicitly permits equivalence.
- If measurement error or sample selection is flagged, avoid welfare, compliance, or distributional claims that require stronger measurement validity.
## Forbidden claims
- Do not say `the policy caused emissions to fall` unless the claim gate permits a causal claim and diagnostics do not block it.
- Do not say `paper-ready causal evidence` from `diagnostic_success` alone.
- Do not say `the backend passed` when `backend_status.json` reports missing, partial, parser-only, interface-only, failed, or `missing_dependency`.
- Do not say `the Stata/R/PPMLHDFE/SAR/SDM model ran` unless backend artifacts certify execution.
- Do not say `the reduced-form spatial estimate identifies spillovers` unless structural spatial effect claims are allowed by `claim_gate.json`.
- Do not say `direct and indirect effects` from a plain spatial exposure regression.
- Do not say `audit-grade ESG finding` unless the claim gate and artifact provenance support audit-grade language.
- Do not say `the firm committed fraud`, `the disclosure is illegal`, or `management intentionally deceived investors` from ESG text scores alone.
- Do not say `greenwashing is proven` when the artifacts support only greenwashing risk, disclosure inconsistency, or text-risk indicators.
- Do not say `no effect` from an insignificant estimate without power, confidence interval, and minimum detectable effect support.
- Do not hide sign flips, failed overlap, failed balance, failed pre-trends, missing W audits, missing dependencies, or missing manifests.
- Do not let abstract, conclusion, executive summary, or slide language exceed the strongest claim allowed in `claim_guard_output`.
- Do not use legal, regulatory, or standard-specific facts without checking current official sources at use time.
## Handoff to code
- Request regeneration of `claim_gate.json` when missing, malformed, stale, or not linked in the manifest.
- Request regeneration of `status.json` when agent status, diagnostic-only flags, errors, or warnings are absent.
- Request `manifest.json` or `artifact_manifest.json` when artifact provenance, file origin, hashes, or timestamps are missing.
- Request `diagnostics.json` when overlap, balance, pre-trend, placebo, support, W-matrix, measurement, or sample-selection diagnostics are missing.
- Request `model_table.csv` only for numerical wording; do not use it to override the claim gate.
- Request `reviewer_risk.json` when likely referee objections or downgrade triggers are absent.
- Request `backend_discovery.json` or equivalent and `backend_status.json` when backend availability, parser-only status, or missing dependency status is unclear.
- Request backend reruns only through code; the skill does not run or certify backends.
- Request W-matrix validation, islands checks, normalization checks, and W sensitivity when spatial claims are requested.
- Request overlap repair, trimming, reweighting, alternative control group construction, or design redesign when overlap fails.
- Request balance, pre-trend, placebo, falsification, and negative-control diagnostics when a causal claim is requested.
- Request measurement provenance checks when outcomes are emissions, pollution monitors, remote sensing, self-reported ESG text, carbon accounts, or disclosure scores.
- Request sample-selection diagnostics when treatment adoption, facility reporting, monitor coverage, firm disclosure, or attrition may be nonrandom.
- Request official-source verification when policy dates, regulatory standards, ESG reporting rules, or legal claims are part of the prose.
- Request a revised claim gate after any new diagnostic or backend run.
## Handoff from code artifacts
- From `status.json`, use agent status, workflow status, diagnostic-only flags, parser-only flags, warnings, errors, and partial-completion markers.
- From `claim_gate.json`, use allowed claim levels, blocked claim levels, downgrade triggers, forbidden phrases, paper-readiness flags, and main-claim availability.
- From `manifest.json`, use artifact completeness, workflow provenance, file timestamps, artifact links, known omissions, and provenance warnings.
- From `artifact_manifest.json`, use artifact lineage and completeness if it is present and linked.
- From `diagnostics.json`, use overlap, balance, pre-trends, support, placebo, W-matrix, leverage, measurement, and sample-selection diagnostics.
- From `model_table.csv`, use sign, magnitude, units, confidence intervals, p-values, sample sizes, model names, and backend labels only after claim gating.
- From `reviewer_risk.json`, use the highest-severity reviewer objection as a default caveat unless the claim gate explicitly resolves it.
- From `backend_discovery.json` or equivalent, use discovered versus unavailable backend information.
- From `backend_status.json`, use installed, missing, failed, parser-only, interface-only, `missing_dependency`, and partial status labels.
- If a field is absent but required for the intended claim, name the absence and downgrade the claim rather than inferring success.
- If artifacts conflict, record the conflict in `uncertainty_notes` and use the stricter claim level.
## Minimal examples
### Example 1: blocked overlap and parser-only backend
Input facts:
- User asks: `Can I say the low-emission-zone policy reduced NO2?`
- `status.json` reports `agent_status: diagnostic_success` and `backend_mode: parser_only`.
- `claim_gate.json` blocks main causal claims with `blocking_reasons: [overlap_fail, parser_only_backend]`.
- `diagnostics.json` reports treated units outside common support.
- `model_table.csv` has a negative and statistically significant coefficient.
Expected output:
```yaml
skill_name: environmental_claim_guard
user_question_summary: "Can I say the low-emission-zone policy reduced NO2?"
research_domain: "environmental economics reporting"
research_brief:
  unit: "monitor-zone-month"
  time_frequency: "monthly"
  outcome_candidates: ["NO2 concentration"]
  treatment_or_exposure: "low-emission-zone policy exposure"
  estimand_candidates: ["ATT for treated zones within common support"]
  identification_risks: ["overlap_fail", "parser_only_backend"]
candidate_workflows: []
candidate_methods: []
required_diagnostics: ["overlap", "backend_certification", "claim_gate"]
recommended_robustness: ["support-restricted sample", "alternative control group"]
forbidden_claims:
  - "The policy reduced NO2."
  - "The backend model ran successfully."
claim_language:
  allowed:
    - "The diagnostic table reports a negative association in the available comparison sample."
    - "Because overlap failed, the point estimate is exploratory and not main causal evidence."
  disallowed:
    - "caused"
    - "paper-ready"
    - "backend-certified"
uncertainty_notes:
  - "Backend status is parser-only, so execution of the target backend is not established."
next_code_actions:
  - "Repair overlap or redefine the comparison design."
  - "Run and certify the target backend before backend language is used."
scholarly_depth:
  estimand_definition: "A credible ATT would require treated units to have comparable controls inside common support."
  identifying_assumptions: ["common support", "parallel trends conditional on design", "stable measurement"]
  measurement_model: ["NO2 monitor readings require monitor coverage checks"]
  data_construction_risks: ["treated zones outside support"]
  method_decision_tree: ["block main claim until overlap and backend status are resolved"]
  diagnostics_that_block_claims: ["overlap_fail", "parser_only_backend"]
  robustness_ranked_by_risk: ["support restriction", "control pool redesign", "pre-trend check"]
  referee_objections: ["No credible counterfactual for treated zones outside support."]
  downgrade_triggers: ["overlap_fail", "parser_only_backend"]
not_recommended_methods: ["publishing the full-sample significant coefficient as main causal evidence"]
claim_guard_output:
  agent_status: "diagnostic_success"
  main_claim_available: false
  allowed_claims:
    - "The diagnostic estimate is negative in the reported table."
    - "The estimate should be described as exploratory because overlap failed."
  downgraded_claims:
    - "Main causal policy-effect language is downgraded to exploratory diagnostic language."
  forbidden_claims:
    - "The low-emission-zone policy caused NO2 reductions."
    - "The backend model actually ran."
  blocking_reasons: ["overlap_fail", "parser_only_backend"]
  safe_summary_paragraph: "The available artifacts report a negative diagnostic estimate for NO2, but overlap failure and parser-only backend status block a main causal claim. The result can be described only as exploratory evidence from the available comparison sample."
  reviewer_warning_paragraph: "A referee would likely object that treated units lack credible support and that the target backend execution is not certified, so significance in the table cannot support causal policy language."
```
### Example 2: ESG legal overclaim and missing dependency downgrade
Input facts:
- User asks: `Can I say the firm illegally greenwashed its carbon neutrality pledge?`
- `claim_gate.json` allows disclosure-risk language but blocks legal and intent claims.
- `backend_status.json` reports `missing_dependency` for the target text-classification backend.
- `diagnostics.json` reports text-score uncertainty and limited labeled validation data.
Expected output:
```yaml
skill_name: environmental_claim_guard
user_question_summary: "Can I say the firm illegally greenwashed its carbon neutrality pledge?"
research_domain: "ESG disclosure reporting"
research_brief:
  unit: "firm-year disclosure"
  time_frequency: "annual"
  outcome_candidates: ["ESG text risk score", "carbon-neutrality disclosure inconsistency"]
  treatment_or_exposure: "carbon neutrality pledge language"
  estimand_candidates: ["difference in disclosure-risk score across pledged and non-pledged firm-years"]
  identification_risks: ["missing_dependency", "legal_authority_absent", "measurement_validation_limited"]
candidate_workflows: []
candidate_methods: []
required_diagnostics: ["claim_gate", "backend_status", "text validation", "legal authority check"]
recommended_robustness: ["human validation sample", "alternative dictionary", "official legal-source review"]
forbidden_claims:
  - "The firm illegally greenwashed."
  - "The firm committed fraud."
  - "The text backend passed."
claim_language:
  allowed:
    - "The disclosures show elevated greenwashing risk under the reported text metric."
    - "The artifacts do not support legal or intent language."
  disallowed:
    - "illegal"
    - "fraud"
    - "intentional deception"
    - "backend passed"
uncertainty_notes:
  - "The target backend has a missing dependency, so backend-certified text classification is unavailable."
  - "Legal authority is not documented in the artifacts."
next_code_actions:
  - "Install or document the missing dependency and rerun backend status."
  - "Add official legal-source evidence before any legal wording is considered."
scholarly_depth:
  estimand_definition: "The defensible estimand is a disclosure-risk contrast, not a legal violation."
  identifying_assumptions: ["consistent text measurement", "comparable disclosure contexts"]
  measurement_model: ["text score approximates disclosure risk and requires validation"]
  data_construction_risks: ["limited labels", "ambiguous pledge language"]
  method_decision_tree: ["allow risk language", "block legal and intent language"]
  diagnostics_that_block_claims: ["missing_dependency", "legal_authority_absent"]
  robustness_ranked_by_risk: ["human-coded validation", "alternative text metric", "official legal-source check"]
  referee_objections: ["A text-risk score is not evidence of illegality or intent."]
  downgrade_triggers: ["missing_dependency", "legal_overclaim"]
not_recommended_methods: ["equating ESG text risk with fraud"]
claim_guard_output:
  agent_status: "partial_backend_unavailable"
  main_claim_available: false
  allowed_claims:
    - "The ESG text artifacts indicate elevated disclosure or greenwashing risk."
  downgraded_claims:
    - "Legal violation language is downgraded to disclosure-risk language."
    - "Backend-certified language is blocked because the target backend has a missing dependency."
  forbidden_claims:
    - "The firm illegally greenwashed."
    - "The firm intentionally deceived investors."
    - "The target backend passed."
  blocking_reasons: ["legal_authority_absent", "missing_dependency", "measurement_validation_limited"]
  safe_summary_paragraph: "The artifacts can support a cautious statement that the disclosure receives an elevated greenwashing-risk score under the reported text measure. They do not support legal, fraud, intent, or backend-certified claims."
  reviewer_warning_paragraph: "A reviewer would likely object that the text measure has limited validation, the target backend did not pass because a dependency is missing, and no legal authority is documented for illegality or intent language."
```
## Completion checklist
- The first line is exactly `# Skill: environmental_claim_guard`.
- All required second-level headings are present and in the required order.
- No YAML frontmatter, installation notes, changelog, or README content is included.
- All required shared rule paths are listed exactly.
- `status.json`, `claim_gate.json`, `manifest.json`, `diagnostics.json`, `model_table.csv`, `reviewer_risk.json`, `backend_discovery.json` or equivalent, and `backend_status.json` are required inspection artifacts.
- The output schema includes all base fields.
- The output schema includes `scholarly_depth` and `not_recommended_methods`.
- The output schema includes the exact `claim_guard_output` block.
- The language rules for overlap fail, parser-only, missing dependency, spatial reduced-form, ESG legal overclaim, and diagnostic success are explicit.
- `claim_gate.json` controls causal, structural, paper-ready, audit-grade, legal, and backend-certified claims.
- Minimal examples include a blocked overlap and parser-only case.
- Minimal examples include an ESG legal-overclaim and missing-dependency downgrade case.
- Handoff to code is explicit and does not claim the skill can run or certify backends.
- Handoff from code artifacts is explicit and artifact-grounded.
- Volatile policy, regulation, standard, API, and data-source facts are routed to current official-source checks at use time.
