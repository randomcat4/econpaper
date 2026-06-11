# Skill: artifact_to_appendix_mapper
## Purpose
Map repository artifacts from environmental economics and econometrics projects into a paper appendix, online appendix, replication package, provenance inventory, and missing-artifact list.
This is a prompt/rubric skill for scholarly reporting triage, not an estimator, backend runner, artifact validator, or certifier.
Preserve distinctions among empirical results, diagnostics, robustness checks, figures, code, data manifests, logs, specifications, and provenance records.
Identify what can be placed where, what remains missing, and what claim language is blocked by evidence or claim_gate.json.
Support appendix drafting, reviewer response, replication-package transparency, and handoff to code inventory tools.
Treat absence, conflict, parser-only output, and missing dependencies as substantive reporting facts, not as narrative gaps to fill.

## Shared reporting contract

Shared reporting boilerplate lives in `./_reporting_shared_contract.md`; apply it before this file-specific logic and do not duplicate or weaken its artifact, claim-gate, parser-only, missing-dependency, forbidden-claims, or scholarly-depth rules.

## When to use
Use when the user asks how to organize artifacts into a manuscript appendix, online appendix, replication package, or provenance section.
Use when model outputs, diagnostics, robustness checks, figures, manifests, logs, or code need scholarly classification.
Use when the task is to identify missing artifacts that block appendix completeness or claim language.
Use when claim_gate.json, status.json, manifest files, diagnostics, model tables, reviewer risk files, or backend status files are present.
Use for environmental economics projects involving policy timing, emissions, pollution, climate, energy, land use, water, health, or spatial spillovers.
Use for econometric designs such as DiD, event study, IV, RDD, panel FE, spatial models, structural models, and descriptive measurement designs.
Use when the user needs conservative YAML that another tool can consume.

## Do not use when
Do not use to estimate models, rerun pipelines, execute backends, or generate numerical results.
Do not use as a checksum certifier, legal certifier, audit certifier, backend certifier, or replication certifier.
Do not use to bypass claim_gate.json.
Do not use to turn diagnostic_success into paper-ready causal success.
Do not use to turn parser-only, interface-only, skipped, mock, dry-run, or missing_dependency output into live backend results.
Do not use to present fallback estimators as equivalent to requested estimators.
Do not use to list missing model output as if it exists.
Do not use because missing artifacts cannot be replaced with narrative.
Do not use to infer data provenance, sample sizes, estimates, or standard errors from filenames alone.
Do not use to decide current policy, regulatory, legal, or data-source facts without official/latest source checks.
Do not use for unrelated engineering boilerplate, deployment notes, or CI-only documentation.

## Inputs expected
User question describing appendix, replication package, provenance, or missing-artifact mapping needs.
Repository root, file tree, artifact bundle, pasted metadata, or code-generated file inventory.
Research brief: unit, time period, geography, outcome, treatment or exposure, method, and estimand if known.
Manuscript draft, appendix draft, table shells, figure shells, journal instructions, or reviewer comments if available.
claim_gate.json or equivalent claim policy file.
status.json, manifest.json, artifact_manifest.json, diagnostics.json, model_table.csv, reviewer_risk.json, backend_status.json, and backend_discovery.json when present.
README.md, registry.yml, workflow wrappers, backend tests, logs, specs, run_config_resolved.yaml, and code/scripts.
Raw data manifests, derived data manifests, data licenses, data vintages, and restricted-use notes.
W audit, W_audit.json, spatial-neighbor audit, exposure audit, or buffer-construction audit when spatial claims exist.
Robustness outputs, falsification checks, sensitivity checks, placebo checks, alternative specifications, figures, and backend caveats.
Treat any uninspected expected input as missing or unknown, not implicitly available.

## Required repo artifacts to inspect
Always inspect the shared rule paths before drafting the mapping:
../_shared/00_skill_authoring_rules.md
../_shared/01_claim_language_rules.md
../_shared/02_evidence_lookup_rules.md
../_shared/03_artifact_reading_rules.md
../_shared/04_spec_drafting_rules.md
../_shared/05_forbidden_fallbacks.md
../_shared/06_reviewer_mode_rules.md
../_shared/07_scholarly_depth_rules.md
Inspect README.md and registry.yml for repository purpose, declared workflows, expected outputs, data requirements, and caveats.
Inspect cli/core/workflows/wrappers and diagnostics/tests/backends for workflow wrappers, flags, parser tests, live-backend tests, skips, and missing dependencies.
Inspect status.json and claim_gate.json for run state, errors, warnings, diagnostic_success, and blocked strong causal, structural, paper-ready, legal, audit-grade, and backend-certified language.
Inspect manifest.json and artifact_manifest.json for declared inputs, outputs, paths, versions, bytes, hashes, timestamps, and provenance completeness.
Inspect diagnostics.json and model_table.csv for diagnostics, warnings, failed checks, estimates, standard errors, N, model labels, controls, clustering, and sample definitions.
Inspect reviewer_risk.json, backend_status.json, and backend_discovery.json or equivalent for reviewer risks, backend status, parser-only status, missing dependencies, skipped calls, and discovered capabilities.
Inspect logs, specs, and run_config_resolved.yaml for errors, fallbacks, mock data, formulas, variable construction, realized options, seeds, bandwidths, clustering, and sample filters.
Inspect code/scripts, raw and derived data manifests, licenses, vintages, hashes, filters, transformations, and access conditions.
Inspect W audit when spatial claims exist, including W_audit.json or equivalent spatial-neighbor evidence.
Inspect robustness outputs and figures, including alternative specifications, falsification tests, rendered files, plot data, captions, and generation scripts.
Inspect equivalent artifact names when exact names differ, but record equivalence and uncertainty.
Volatile policy, regulatory, legal, program, price, API, and data-source facts must be checked from official/latest sources at use time.

## Domain reasoning steps
Start by restating the empirical object: unit, geography, period, outcome, treatment or exposure, and candidate estimand.
Separate design evidence from result evidence; specs and assumptions are not estimates.
Separate result evidence from diagnostic evidence; diagnostics support credibility but do not replace model output.
Separate robustness evidence from main evidence; robustness is not the main result unless declared and authorized.
Separate provenance evidence from empirical evidence; manifests and logs show origin or execution, not treatment effects.
Read claim_gate.json before drafting strong claim language and treat it as controlling.
Read status.json and diagnostics.json before treating any workflow as complete.
Read backend_status.json and backend_discovery.json before describing backend execution.
Treat parser-only, interface-only, dry-run, skipped, mock, or missing_dependency records as non-live backend evidence.
Check model_table.csv against manifest.json and artifact_manifest.json before listing it as an existing table.
Check artifact bytes, hashes, and paths before treating an artifact as present.
Check for conflicts among artifact_manifest.json, manifest.json, status.json, diagnostics.json, README.md, registry.yml, and logs.
If conflicts exist, create uncertainty_notes and use the most restrictive claim language.
Map each artifact to one primary role and optional secondary roles.
Allowed primary roles are main table, robustness table, diagnostic table, figure, replication file, provenance, logs, specs, code, raw data manifest, derived data manifest, claim gate, reviewer risk, and backend status.
A complete model_table.csv can be a main table only if it exists, resolves in manifests, and is not blocked by status or claim gate.
A model_table.csv missing standard errors, N, model labels, clustering, sample definition, or method labels is incomplete.
A diagnostics.json file maps to diagnostic table or provenance, not to main causal results.
A reviewer_risk.json file maps to reviewer risk and caveat planning, not to empirical evidence.
A claim_gate.json file maps to claim gate and language control, not to empirical evidence.
A backend_status.json file maps to backend status and execution caveats, not to model output.
A backend_discovery.json file maps to capability evidence, not live execution unless live status confirms it.
Logs map to logs or provenance and may expose fallback, mock data, errors, missing dependencies, or unresolved paths.
Specs map to methods appendix or replication files and may define intended estimands.
Code maps to replication files only if present and referenced; code presence does not prove execution.
Raw data manifests map to raw-data provenance; derived data manifests map to derived-data construction traceability.
Figures map to figures only if rendered files exist; reproducibility also needs plot data or generation scripts.
Spatial W audits map to diagnostics or provenance and are required for spatial weights, spillovers, buffers, distances, contiguity, or clusters.
Environmental exposure claims require measurement source, spatial join, temporal aggregation, missingness, unit conversion, and monitor or grid assignment evidence.
Policy treatment claims require timing, treated units, comparison units, anticipation windows, staggered adoption, and policy source provenance.
Climate or weather claims require gridding, interpolation, reanalysis or station version, and aggregation evidence.
Regulatory claims require current official facts at use time and cannot rely only on stale repository text.
Causal claims require identification assumptions, design diagnostics, uncertainty, and claim_gate authorization.
Structural claims require equations, parameters, estimation routine, fit diagnostics, counterfactual logic, and claim_gate authorization.
Evaluate missingness as missing file, missing bytes/hash/path, or missing substantive contents.
Evaluate backend evidence as discovered capability, installed dependency, and live run evidence.
Evaluate appendix completeness as placement, provenance, and authorized language.
When an artifact is missing, list it under missing_artifacts and state the blocked appendix item.
When an artifact is incomplete, mark candidate or incomplete and explain the limitation.
When evidence conflicts, prefer blocked, incomplete, or provenance_only over available.
Use terms such as candidate, available, incomplete, blocked, missing, provenance_only, diagnostic_only, parser_only, and missing_dependency.
Avoid verified, certified, audit-grade, backend-certified, causal success, and paper-ready unless claim_gate.json and artifacts authorize them.
Remember: appendix placement is not claim authorization.

## Candidate outputs
Structured appendix map in YAML-compatible form.
Table inventory by main, robustness, and diagnostics roles.
Figure inventory with provenance status.
Replication package inventory separating code, specs, configs, data manifests, logs, and provenance files.
Missing-artifact list explaining blocked appendix items and minimum resolution.
Claim-language summary separating allowed phrasing from disallowed phrasing.
Scholarly-depth block with estimand, assumptions, measurement risks, diagnostics, robustness, objections, and downgrade triggers.
Reviewer caveat list, manifest-conflict note, backend-status note, spatial-provenance note, and robustness-priority note.
Next-code-actions list limited to evidence collection, parsing, hashing, locating, and inventory work.

## Output schema
Return a YAML-compatible object unless the user requests prose.
The object must include these base fields:
skill_name: string
user_question_summary: string
research_domain: string
research_brief:
unit: ""
time_frequency: ""
outcome_candidates: []
treatment_or_exposure: ""
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
The object must include this exact appendix_map block:
appendix_map:
tables:
main: []
robustness: []
diagnostics: []
figures: []
replication_files: []
missing_artifacts: []
provenance_files: []
The object must include scholarly_depth with these fields:
scholarly_depth:
estimand_definition: ""
identifying_assumptions: []
measurement_model: ""
data_construction_risks: []
method_decision_tree: []
diagnostics_that_block_claims: []
robustness_ranked_by_risk: []
referee_objections: []
downgrade_triggers: []
not_recommended_methods: []
For each artifact entry, include path, role, status, evidence_basis, appendix_destination, claim_effect, and caveats when possible.
For missing_artifacts, include expected_path, blocked_appendix_item, why_required, and minimum_resolution.
For provenance_files, include path, role, status, provenance_scope, and caveats.
For claim_language.allowed, use only conservative descriptive language or language authorized by claim_gate.json.
For claim_language.disallowed, include strong causal, structural, paper-ready, legal, audit-grade, or backend-certified claims blocked by claim_gate.json.
For uncertainty_notes, include manifest conflicts, absent bytes, absent hashes, unresolved paths, stale source concerns, and backend ambiguity.
For next_code_actions, request evidence collection and inventory work, not estimation claims.
Do not put nonexistent artifacts in appendix_map.tables or appendix_map.figures.
Do not put missing files in replication_files except as missing_artifacts.
Do not describe any appendix destination as authorizing a claim.
Do not omit not_recommended_methods when a method was considered but rejected, blocked, or unsupported.

## Required caveats
Appendix placement is not claim authorization.
claim_gate.json controls strong causal, structural, paper-ready, legal, audit-grade, and backend-certified language.
diagnostic_success is not paper-ready causal success.
Parser-only, interface-only, dry-run, skipped, mock, and missing_dependency outputs are not live backend results.
Fallback estimators are not equivalent to requested estimators unless explicitly defined as the estimand and allowed by claim_gate.json.
Missing model output must be listed as missing, not narrated as present.
Missing artifacts cannot be replaced with narrative.
A table shell is not a model result.
A figure file without plot data or generation code has incomplete provenance.
A model output without sample definition, standard errors, clustering, or method labels is incomplete for most econometric appendices.
A robustness table does not repair a failed main identification design.
A diagnostic table does not repair missing model estimates.
A manifest entry without bytes, hash, or resolvable path is insufficient for artifact presence unless repository rules explicitly allow it.
Conflicts among manifest.json, artifact_manifest.json, status.json, diagnostics.json, README.md, registry.yml, and logs must be reported.
Spatial claims require W audit or equivalent when weights, contiguity, buffers, distances, spillovers, or clusters matter.
Environmental exposure claims require measurement and aggregation caveats when exposure construction artifacts are absent.
Policy and regulatory facts that may be volatile must be checked from official/latest sources at use time.
A backend discovered in backend_discovery.json is not the same as a backend successfully used.
A passed parser test is not a passed live-backend test; a skipped backend test is not evidence of backend validity.
Reviewer risk files can guide caveats but cannot authorize stronger claims.
When evidence is mixed, use the most restrictive claim language.

## Forbidden claims
Do not claim verified replication unless completeness, hashes, paths, execution evidence, and claim_gate.json support it.
Do not claim causal identification is established from appendix placement alone.
Do not claim diagnostics passed if diagnostics.json is absent or only status.json says diagnostic_success without details.
Do not claim a live backend ran when backend_status.json shows parser_only, interface_only, dry_run, skipped, mock, unavailable, or missing_dependency.
Do not claim model estimates exist when model_table.csv is missing, empty, corrupt, or only declared in a manifest.
Do not claim a fallback estimator is equivalent to the requested estimator.
Do not claim structural estimation if only reduced-form or descriptive outputs exist.
Do not claim audit-grade provenance when artifact_manifest.json lacks bytes, hash, path, or when conflicts are unresolved.
Do not claim legal, regulatory, or current policy facts from stale repository text.
Do not claim spatial weights are valid without W audit or equivalent support.
Do not claim exposure construction is reproducible without raw and derived data manifests or equivalent documentation.
Do not claim a figure is reproducible when only a rendered image exists.
Do not claim code is executable when dependencies, paths, or backends are missing.
Do not claim reviewer-ready appendix completeness when missing_artifacts is nonempty for required items.
Do not infer estimates, signs, significance, sample size, or standard errors from filenames.
Do not hide uncertainty by moving items to an online appendix.

## Handoff to code
Ask code to list files matching required artifact names and accepted equivalents.
Ask code to parse README.md, registry.yml, status.json, claim_gate.json, manifest.json, artifact_manifest.json, diagnostics.json, reviewer_risk.json, backend_status.json, and backend_discovery.json if present.
Ask code to inspect cli/core/workflows/wrappers and diagnostics/tests/backends for workflow and backend evidence.
Ask code to summarize model_table.csv columns, row count, missing cells, model identifiers, standard errors, sample sizes, and method labels.
Ask code to check whether artifact_manifest.json records bytes, hashes, paths, timestamps, and whether paths resolve.
Ask code to compare manifest.json against artifact_manifest.json, status.json, diagnostics.json, README.md, registry.yml, and logs for conflicts.
Ask code to identify logs mentioning fallback, mock, dry_run, skipped, parser_only, interface_only, missing_dependency, error, warning, or unresolved path.
Ask code to summarize specs, run_config_resolved.yaml, code/scripts, data manifests, W audits, robustness outputs, and figures.
Ask code to report missing files explicitly rather than creating placeholders.
Ask code not to certify artifacts, authorize claims, override claim_gate.json, or run estimators unless a separate execution skill is invoked.
Ask code to return machine-readable findings with path, exists, bytes, hash, role_hint, status_hint, and notes.

## Handoff from code artifacts
Receive file inventory with existence, bytes, hashes, paths, and parse status.
Receive parsed claim_gate.json and treat restrictions as controlling.
Receive parsed status.json and diagnostics.json and downgrade success flags lacking supporting diagnostic details.
Receive parsed backend_status.json and backend_discovery.json and distinguish discovered capability from live execution.
Receive model_table.csv summary and decide whether it can enter main, robustness, diagnostics, or missing_artifacts.
Receive manifest comparisons and flag conflicts, missing bytes, missing hash, unresolved path, or stale path.
Receive log summaries and propagate warnings about fallback, parser-only, missing dependencies, mock data, dry runs, and errors.
Receive spec, run_config, code, data manifest, W audit, robustness, and figure inventories and map them by role.
Convert code findings into appendix_map entries without adding unsupported claims.
When code reports unavailable, unreadable, corrupt, missing, conflict, parser_only, or missing_dependency, use blocked or incomplete status.
When code reports missing model_table.csv, diagnostics.json, W audit, or artifact_manifest bytes/hash/path, list the blocked appendix items.
When code reports manifest conflicts or stale external facts, add uncertainty_notes and avoid paper-ready claims.

## Minimal examples
Example 1: incomplete diagnostics appendix map.

```yaml
skill_name: artifact_to_appendix_mapper
user_question_summary: "Map available panel outputs into an appendix."
research_domain: "environmental economics"
research_brief:
  unit: "county-month"
  time_frequency: "monthly"
  outcome_candidates: ["respiratory admissions"]
  treatment_or_exposure: "PM2.5 exposure"
  estimand_candidates: ["reduced-form exposure-outcome association"]
  identification_risks: ["exposure measurement error", "seasonality"]
candidate_workflows: ["panel_fixed_effects"]
candidate_methods: ["two-way fixed effects"]
required_diagnostics: ["diagnostics.json"]
recommended_robustness: ["alternative exposure windows", "weather controls"]
forbidden_claims: ["paper-ready causal effect", "diagnostics passed"]
claim_language:
  allowed: ["candidate main estimates are available", "diagnostics appendix is incomplete"]
  disallowed: ["diagnostic_success establishes causal validity", "the appendix is paper-ready"]
uncertainty_notes: ["status.json reports diagnostic_success, but diagnostics.json is absent"]
next_code_actions: ["locate diagnostics.json or equivalent diagnostic artifact"]
appendix_map:
  tables:
    main:
      - path: "model_table.csv"
        role: "main table"
        status: "candidate"
        evidence_basis: "file exists with bytes and hash in artifact_manifest.json"
        appendix_destination: "Appendix table A1 with limited descriptive language"
        claim_effect: "does not authorize causal or paper-ready language"
        caveats: ["diagnostics missing", "claim_gate blocks paper-ready causal wording"]
    robustness: []
    diagnostics: []
  figures: []
  replication_files: []
  missing_artifacts:
    - expected_path: "diagnostics.json"
      blocked_appendix_item: "diagnostics appendix table"
      why_required: "status flag alone does not provide diagnostic contents"
      minimum_resolution: "provide detailed diagnostics artifact"
  provenance_files: [{path: "artifact_manifest.json", role: "provenance", status: "available", provenance_scope: "bytes and hash for model_table.csv", caveats: []}]
scholarly_depth:
  estimand_definition: "Association under the stated panel model."
  identifying_assumptions: ["parallel unobserved shocks after controls"]
  measurement_model: "County-month exposure assignment depends on exposure construction artifacts."
  data_construction_risks: ["missing exposure provenance"]
  method_decision_tree: ["use candidate main table", "block diagnostics appendix"]
  diagnostics_that_block_claims: ["missing diagnostics.json"]
  robustness_ranked_by_risk: ["alternative exposure windows", "weather controls"]
  referee_objections: ["status flag lacks diagnostic detail"]
  downgrade_triggers: ["claim_gate blocks paper-ready causal wording", "diagnostics artifact absent"]
not_recommended_methods: [{method: "structural welfare estimation", reason: "no structural model artifacts provided"}]
```

Example 2: parser-only or missing_dependency backend map with blocked appendix completeness.

```yaml
skill_name: artifact_to_appendix_mapper
user_question_summary: "Map a spatial workflow into appendix and replication files."
research_domain: "environmental economics, spatial econometrics"
research_brief:
  unit: "tract-year"
  time_frequency: "annual"
  outcome_candidates: ["housing price", "emissions exposure"]
  treatment_or_exposure: "facility exposure and spatial spillovers"
  estimand_candidates: ["direct and spillover association"]
  identification_risks: ["spatial sorting", "weight matrix misspecification"]
candidate_workflows: ["spatial_panel"]
candidate_methods: ["spatial lag candidate"]
required_diagnostics: ["W_audit.json", "backend live-run evidence", "model_table.csv", "diagnostics.json"]
recommended_robustness: ["alternative W definitions", "distance bands", "placebo facilities"]
forbidden_claims: ["live spatial backend ran", "spatial spillover estimates exist", "backend-certified results"]
claim_language:
  allowed: ["a parser-only spatial backend interface was discovered", "appendix completeness is blocked"]
  disallowed: ["the spatial backend produced estimates", "README claims are verified"]
uncertainty_notes: ["backend discovery is not live execution", "README conflicts with missing model_table.csv and missing W audit"]
next_code_actions: ["locate W_audit.json", "locate model_table.csv", "confirm backend_status.json dependency state"]
appendix_map:
  tables:
    main: []
    robustness: []
    diagnostics: []
  figures: []
  replication_files:
    - path: "backend_discovery.json"
      role: "backend status"
      status: "parser_only"
      evidence_basis: "interface discovered but backend_status reports parser_only"
      appendix_destination: "replication package provenance only"
      claim_effect: "blocks backend-certified and live-run language"
      caveats: ["missing_dependency", "no model output"]
  missing_artifacts:
    - expected_path: "model_table.csv"
      blocked_appendix_item: "main spatial estimates table"
      why_required: "no model estimates can be listed without output"
      minimum_resolution: "provide actual model output with estimates and uncertainty"
    - expected_path: "W_audit.json"
      blocked_appendix_item: "spatial diagnostics appendix"
      why_required: "spatial weights and spillover claims require W audit or equivalent"
      minimum_resolution: "provide W construction and validation audit"
  provenance_files: [{path: "backend_status.json", role: "backend status", status: "missing_dependency", provenance_scope: "backend availability", caveats: ["not live execution"]}]
scholarly_depth:
  estimand_definition: "Direct and spillover association is only a candidate because no estimates exist."
  identifying_assumptions: ["valid spatial weights", "no endogenous sorting"]
  measurement_model: "Exposure and W are undocumented until W audit and data manifests exist."
  data_construction_risks: ["missing W audit", "missing model output", "backend dependency absent"]
  method_decision_tree: ["classify backend files as provenance only", "block main table", "block spatial diagnostics"]
  diagnostics_that_block_claims: ["missing W_audit.json", "missing diagnostics.json", "backend missing_dependency"]
  robustness_ranked_by_risk: ["alternative W matrices", "distance-band sensitivity", "placebo facilities"]
  referee_objections: ["README overclaims relative to artifacts", "parser-only backend is not execution"]
  downgrade_triggers: ["model_table.csv missing", "backend_status missing_dependency"]
not_recommended_methods: [{method: "using non-spatial fallback OLS as equivalent", reason: "fallback estimator does not identify the same spatial estimand"}]
```

## Completion checklist
The mapping starts with skill_name: artifact_to_appendix_mapper when returning YAML.
The mapping includes all base fields, the exact appendix_map structure, scholarly_depth, and not_recommended_methods.
Every listed artifact has role, status, evidence basis, and caveat when relevant.
Artifacts are classified by role, including main table, robustness table, diagnostic table, figure, replication file, provenance, logs, specs, code, raw data manifest, derived data manifest, claim gate, reviewer risk, and backend status.
Missing model_table.csv is handled as missing and not listed as an existing main table.
Missing diagnostics.json is handled as blocked diagnostics, not as diagnostics passed.
Missing W audit blocks spatial claims when spatial claims exist.
Parser-only and missing_dependency backends are treated as non-live evidence.
Artifact manifest entries without bytes, hash, or resolvable path are downgraded, and manifest conflicts are reported in uncertainty_notes.
claim_gate.json is inspected before strong claim language is drafted.
Appendix placement is distinguished from claim authorization.
diagnostic_success is not converted into paper-ready causal success.
Fallback estimators are not presented as equivalent, and missing artifacts are not replaced with narrative.
Volatile policy, regulatory, legal, and data-source facts are flagged for official/latest source checks.
The handoff to code requests evidence collection and inventory work, not estimator execution.
The output avoids certification, legal, audit-grade, backend-certified, paper-ready, or causal language unless explicitly authorized.
