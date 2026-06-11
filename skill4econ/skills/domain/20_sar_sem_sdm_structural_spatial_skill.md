# Skill: sar_sem_sdm_structural_spatial

## Purpose

Guide domain reasoning for SAR, SEM, and SDM structural spatial panel designs in environmental, resource, energy, ESG, finance, and regional economics.
This is a prompt and rubric layer for future agents, not an estimator, backend runner, package selector, artifact certifier, or reporting skill.
The core task is to define the estimand, identification assumptions, measurement model, diagnostics that block claims, referee objections, and downgrade triggers.
Keep structural SAR/SEM/SDM distinct from reduced-form spatial exposure DID, border exposure, distance-weighted treatment, or W*treatment regressions.
Strong structural, causal, paper-ready, audit-grade, or backend-certified language requires live backend artifacts and claim_gate.json approval.

## When to use

* The user asks about SAR, SEM, SDM, SAC, SARAR, spatial lag, spatial error, spatial Durbin, rho, lambda, theta, direct impacts, indirect impacts, or total impacts.
* The user wants a domain plan before specification drafting, backend execution, artifact review, reviewer response, or result interpretation.
* The user asks whether W*y, W*x, or W*treatment supports spillover, leakage, diffusion, displacement, pollution transport, regional competition, or neighborhood effect claims.
* The design involves environmental or economic outcomes observed over regions, grids, firms, plants, watersheds, monitors, or administrative units.
* W construction, row normalization, islands, self links, CRS, connectedness, directionality, or time-varying networks could change the interpretation.
* Existing results need claim-language triage against backend status, impact tables, W metadata, diagnostics, and claim_gate.json.

## Do not use when

* Do not use to run an estimator, install a backend, certify package availability, or assert current software support.
* Do not use when the user only needs syntax for an already validated spec and no domain interpretation is needed.
* Do not use to certify a completed run without claim_gate.json, status.json, backend_status.json, artifact manifests, diagnostics, and model outputs.
* Do not relabel reduced-form spatial exposure, spatial DID, border exposure, or W*treatment regressions as structural SAR or SDM.
* Do not claim an SDM indirect effect without a direct, indirect, and total impact table with uncertainty from a live backend run.
* Do not accept parser-only, interface-only, dry-run, mocked, skipped, failed, or missing-dependency output as a structural result.
* Do not make current policy, legal, regulatory, API, package, or data-access claims unless official/latest sources are checked at use time.

## Inputs expected

* User question, intended claim, and whether the task is planning, interpretation, reviewer risk, or artifact triage.
* Unit, geography, period, time frequency, panel balance, sample restrictions, and connected components if known.
* Outcome definition, data source, spatial aggregation, treatment or exposure definition, and timing.
* Candidate estimand: structural direct impact, indirect impact, total impact, equilibrium multiplier, error-correlation adjustment, or reduced-form exposure contrast.
* Candidate model family: SAR, SEM, SDM, mixed, reduced-form spatial exposure, or unknown.
* Candidate W matrices: contiguity, distance, k-nearest neighbors, economic network, hydrology, wind, supply chain, trade, migration, commuting, or other theory-based W.
* W metadata: normalization, thresholds, symmetry, direction, self links, islands, zero-neighbor units, CRS, distance units, time variation, and whether W is pre-treatment.
* Covariates, fixed effects, trends, dynamic terms, lagged outcomes, instruments, and clustering or uncertainty plan.
* Existing artifacts: status, backend status, claim gate, manifest, diagnostics, reviewer risk, model table, impact table, W audit, W metadata, and logs.

## Required repo artifacts to inspect

Inspect workspace files first; do not rely on globally installed skill4econ behavior, local memories, or assumed backend capability.
Inspect these repository artifacts when available:

* README.md
* skill4econ/registry.yml
* skill4econ/cli.py
* skill4econ/core.py
* skill4econ/python_wrappers.py
* skill4econ/workflows.py
* skill4econ/diagnostics/
* skill4econ/tests/fixtures/
* skill4econ/tests/backends/
* skills/domain/
* status.json when a run exists
* claim_gate.json when a run exists
* manifest.json or artifact_manifest.json when a run exists
* backend_status.json when a run exists
* diagnostics.json when a run exists
* reviewer_risk.json when a run exists
* model_table.csv or equivalent model output when present
* impact_decomposition.csv or equivalent impact table when present
* W_audit.json, W_metadata.json, or equivalent W construction record when present
* spec.yml, spec.json, or submitted model specification when present
Also read shared rules before writing output:
* `../_shared/00_skill_authoring_rules.md`
* `../_shared/01_claim_language_rules.md`
* `../_shared/02_evidence_lookup_rules.md`
* `../_shared/03_artifact_reading_rules.md`
* `../_shared/04_spec_drafting_rules.md`
* `../_shared/05_forbidden_fallbacks.md`
* `../_shared/06_reviewer_mode_rules.md`
* `../_shared/07_scholarly_depth_rules.md`
* `../_shared/08_domain_literature_anchor_rules.md`
The scholarly depth rules, especially `../_shared/07_scholarly_depth_rules.md`, control estimands, assumptions, measurement, blocking diagnostics, referee objections, and downgrade triggers.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Cliff and Ord (1981), Spatial Processes: Models & Applications"
    - "Anselin (1988), Spatial Econometrics: Methods and Models"
    - "Anselin, Bera, Florax, and Yoon (1996), Regional Science and Urban Economics, Simple Diagnostic Tests for Spatial Dependence"
    - "Kelejian and Prucha (1998), Journal of Real Estate Finance and Economics, A Generalized Spatial Two-Stage Least Squares Procedure"
    - "LeSage and Pace (2009), Introduction to Spatial Econometrics"
    - "Elhorst (2014), Spatial Econometrics: From Cross-Sectional Data to Spatial Panels"
    - "Gibbons and Overman (2012), Journal of Regional Science, Mostly Pointless Spatial Econometrics?"
  canonical_data_sources:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  live_lookup_required_for:
    - "current GIS boundaries"
    - "current network data"
    - "current package W construction defaults"
    - "current package row-standardization and islands defaults"
    - "current estimator/backend defaults"
    - "current package diagnostics and estimator options"
    - "current package impact-calculation defaults"
    - "current package islands handling and connected-component rules"
    - "current package simulation, variance, and impact defaults"
    - "current weather, boundary, and network data"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Cliff and Ord (1981), Spatial Processes: Models & Applications"
    use_for: "spatial dependence, spatial autocorrelation, spatial stochastic processes"
    live_lookup_required: []

    citation: "Anselin (1988), Spatial Econometrics: Methods and Models"
    use_for: "SAR, SEM, spatial dependence diagnostics, spatial weights matrix foundations"
    live_lookup_required: []

    citation: "Anselin, Bera, Florax, and Yoon (1996), Regional Science and Urban Economics, Simple Diagnostic Tests for Spatial Dependence"
    use_for: "LM diagnostics for spatial lag and spatial error dependence"
    live_lookup_required: []

    citation: "Kelejian and Prucha (1998), Journal of Real Estate Finance and Economics, A Generalized Spatial Two-Stage Least Squares Procedure"
    use_for: "spatial IV/GMM estimation for spatial autoregressive models"
    live_lookup_required: []

    citation: "LeSage and Pace (2009), Introduction to Spatial Econometrics"
    use_for: "direct, indirect, and total impacts; SAR/SDM interpretation; impact simulation"
    live_lookup_required: []

    citation: "Elhorst (2014), Spatial Econometrics: From Cross-Sectional Data to Spatial Panels"
    use_for: "spatial panel models, fixed effects, dynamic spatial panels, model choice"
    live_lookup_required: []

    citation: "Gibbons and Overman (2012), Journal of Regional Science, Mostly Pointless Spatial Econometrics?"
    use_for: "identification skepticism, correlated shocks versus spillovers, model dependence"
    live_lookup_required: []
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "Spatial weights matrix W"
    - "contiguity, distance-band, inverse-distance, k-nearest-neighbor, economic distance, wind/downwind, river network, trade network, or commuting weights"
    - "Row-standardization"
    - "weights scaled so each non-island row sums to one"
    - "coefficient becomes average-neighbor exposure"
    - "row-standardization changes distance decay and total exposure"
    - "islands and sparse neighbors need explicit handling"
    - "SAR spatial lag"
    - "outcome depends on neighboring outcomes through Wy"
    - "SEM spatial error"
  validation_targets:
    - "W justification"
    - "Is W tied to the environmental mechanism rather than chosen for convenience?"
    - "W sensitivity"
    - "Are results shown under alternative contiguity, distance, directional, and unstandardized/row-standardized weights?"
    - "Islands"
    - "Are islands, disconnected components, and dropped units reported?"
    - "Model interpretation"
    - "Are SAR, SEM, and SDM interpretations separated, especially spillovers versus correlated errors?"
    - "Impact decomposition"
    - "Are direct, indirect, and total impacts reported with uncertainty rather than raw spatial coefficients alone?"
  known_mismeasurement_channels:
    - "W is identifying structure, not a nuisance choice"
    - "results can flip across plausible W"
    - "endogenous networks contaminate spillover interpretation"
    - "coefficient becomes average-neighbor exposure"
    - "row-standardization changes distance decay and total exposure"
    - "islands and sparse neighbors need explicit handling"
    - "reflection and simultaneity"
    - "reduced-form spillovers require structural interpretation"
    - "direct coefficient is not marginal effect"
    - "SEM spatial error"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "Spatial weights matrix W"
    measure: "contiguity, distance-band, inverse-distance, k-nearest-neighbor, economic distance, wind/downwind, river network, trade network, or commuting weights"
    pitfalls: ["W is identifying structure, not a nuisance choice", "results can flip across plausible W", "endogenous networks contaminate spillover interpretation"]
    live_lookup_required: ["current GIS boundaries", "current network data", "current package W construction defaults"]

    item: "Row-standardization"
    measure: "weights scaled so each non-island row sums to one"
    pitfalls: ["coefficient becomes average-neighbor exposure", "row-standardization changes distance decay and total exposure", "islands and sparse neighbors need explicit handling"]
    live_lookup_required: ["current package row-standardization and islands defaults"]

    item: "SAR spatial lag"
    measure: "outcome depends on neighboring outcomes through Wy"
    pitfalls: ["reflection and simultaneity", "reduced-form spillovers require structural interpretation", "direct coefficient is not marginal effect"]
    live_lookup_required: ["current estimator/backend defaults"]

    item: "SEM spatial error"
    measure: "spatially correlated unobservables through error process"
    pitfalls: ["SEM captures omitted spatial shocks, not substantive spillovers", "policy spillover claims require more than spatial error correlation"]
    live_lookup_required: ["current package diagnostics and estimator options"]

    item: "SDM spatial Durbin"
    measure: "own covariates and neighboring covariates enter with spatial outcome feedback"
    pitfalls: ["coefficient signs are not direct/indirect effects", "impact decomposition depends on W and spatial multiplier", "overparameterization in small panels"]
    live_lookup_required: ["current package impact-calculation defaults"]

    item: "Islands and disconnected components"
    measure: "units with no neighbors, singleton components, disconnected networks, boundary exclusions"
    pitfalls: ["dropping islands changes sample", "zero-neighbor treatment changes estimand", "connected components can have separate multiplier behavior"]
    live_lookup_required: ["current package islands handling and connected-component rules"]

    item: "Direct, indirect, and total impacts"
    measure: "average own-unit, spillover, and aggregate marginal effects derived from spatial multiplier"
    pitfalls: ["impact uncertainty must include spatial parameters", "coefficients are not impacts in SAR/SDM", "finite-sample and simulation choices matter"]
    live_lookup_required: ["current package simulation, variance, and impact defaults"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "calling residual spatial autocorrelation a spillover"
    - "Reflection problem"
    - "interpreting Wy coefficient as peer or pollution spillover without instruments or timing"
    - "one arbitrary W drives the result"
    - "interpreting average-neighbor exposure as cumulative burden"
    - "drawing spillover conclusions from raw SDM coefficients"
    - "Unit and time fixed effects remove some spatial confounding but not spatially correlated shocks or endogenous spillovers."
    - "assuming FE automatically identifies spatial causal effects"
    - "using queen contiguity for airborne or watershed processes without justification"
  sorting_vs_siting_or_selection_channel:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  why_method_not_magic:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Correlated shocks versus spatial spillovers"
    core_issue: "Spatial correlation can reflect shared weather, markets, regulation, monitoring, or omitted geography rather than causal spillovers."
    acceptable_designs: ["shock-specific exposure", "rich spatial controls", "boundary designs", "upwind/downwind or network directionality", "placebo W matrices"]
    referee_risk: "calling residual spatial autocorrelation a spillover"
    live_lookup_required: ["current weather, boundary, and network data"]

    item: "Reflection problem"
    core_issue: "Spatially lagged outcomes create simultaneity between a unit and its neighbors."
    acceptable_designs: ["valid spatial instruments", "pre-determined neighbor shocks", "dynamic timing", "structural simultaneity model"]
    referee_risk: "interpreting Wy coefficient as peer or pollution spillover without instruments or timing"
    live_lookup_required: []

    item: "W sensitivity"
    core_issue: "Spatial effects are conditional on the chosen W matrix, normalization, and sample geography."
    acceptable_designs: ["multiple plausible W matrices", "distance-band sensitivity", "unstandardized exposure robustness", "leave-boundary-out checks"]
    referee_risk: "one arbitrary W drives the result"
    live_lookup_required: ["current GIS/network and package W defaults"]

    item: "Row-standardization interpretation"
    core_issue: "Row-standardized W estimates average-neighbor effects, not total exposure to all nearby sources."
    acceptable_designs: ["report raw exposure and row-standardized results", "explain estimand", "test alternative normalizations"]
    referee_risk: "interpreting average-neighbor exposure as cumulative burden"
    live_lookup_required: ["current package normalization defaults"]

    item: "Direct, indirect, and total impact uncertainty"
    core_issue: "In SAR/SDM models, impacts are nonlinear functions of coefficients, rho, W, and sample layout."
    acceptable_designs: ["simulation or delta-method intervals", "impact tables not coefficient tables alone", "W-robust impact comparison"]
    referee_risk: "drawing spillover conclusions from raw SDM coefficients"
    live_lookup_required: ["current package impact and variance implementation"]

    item: "Spatial panels and fixed effects"
    core_issue: "Unit and time fixed effects remove some spatial confounding but not spatially correlated shocks or endogenous spillovers."
    acceptable_designs: ["unit/time FE", "region-by-time controls", "spatially clustered inference", "dynamic and lag robustness"]
    referee_risk: "assuming FE automatically identifies spatial causal effects"
    live_lookup_required: ["current spatial panel package defaults"]

    item: "Environmental transport versus administrative adjacency"
    core_issue: "Environmental spillovers often follow wind, water, slope, commuting, or supply networks rather than polygon contiguity."
    acceptable_designs: ["physics-informed W", "directional W", "hydrological or atmospheric transport models", "placebo non-transport neighbors"]
    referee_risk: "using queen contiguity for airborne or watershed processes without justification"
    live_lookup_required: ["current meteorological, hydrological, and transport-network data"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "W justification"
    - "Is W tied to the environmental mechanism rather than chosen for convenience?"
    - "W sensitivity"
    - "Are results shown under alternative contiguity, distance, directional, and unstandardized/row-standardized weights?"
    - "Islands"
    - "Are islands, disconnected components, and dropped units reported?"
    - "Model interpretation"
    - "Are SAR, SEM, and SDM interpretations separated, especially spillovers versus correlated errors?"
    - "Impact decomposition"
    - "Are direct, indirect, and total impacts reported with uncertainty rather than raw spatial coefficients alone?"
  minimal_empirical_section_checklist:
    - "W justification"
    - "Is W tied to the environmental mechanism rather than chosen for convenience?"
    - "current GIS, network, and package W-construction defaults"
    - "W sensitivity"
    - "Are results shown under alternative contiguity, distance, directional, and unstandardized/row-standardized weights?"
    - "current boundary and network files"
    - "Islands"
    - "Are islands, disconnected components, and dropped units reported?"
    - "current package islands handling"
    - "Model interpretation"
  claims_to_downgrade:
    - "Do not call spatial autocorrelation a causal spillover without identification."
    - "Do not interpret SAR or SDM raw coefficients as direct, indirect, or total impacts."
    - "Do not use one arbitrary W matrix without mechanism and sensitivity checks."
    - "Do not ignore row-standardization: average-neighbor exposure is not total cumulative exposure."
    - "Do not hide islands, disconnected components, dropped units, or W normalization."
    - "Do not interpret SEM spatial-error dependence as substantive policy spillover."
    - "Do not ignore reflection when using spatially lagged outcomes."
    - "Do not make current claims about spatial package defaults, W construction, row-standardization, islands handling, impact simulation, or backend behavior without live lookup."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "W justification"
    ask: "Is W tied to the environmental mechanism rather than chosen for convenience?"
    live_lookup_required: ["current GIS, network, and package W-construction defaults"]

    check: "W sensitivity"
    ask: "Are results shown under alternative contiguity, distance, directional, and unstandardized/row-standardized weights?"
    live_lookup_required: ["current boundary and network files"]

    check: "Islands"
    ask: "Are islands, disconnected components, and dropped units reported?"
    live_lookup_required: ["current package islands handling"]

    check: "Model interpretation"
    ask: "Are SAR, SEM, and SDM interpretations separated, especially spillovers versus correlated errors?"
    live_lookup_required: ["current estimator defaults"]

    check: "Impact decomposition"
    ask: "Are direct, indirect, and total impacts reported with uncertainty rather than raw spatial coefficients alone?"
    live_lookup_required: ["current package impact-simulation defaults"]

    check: "Reflection and simultaneity"
    ask: "Does Wy have credible timing, instruments, or structural assumptions?"
    live_lookup_required: []

    check: "Correlated shocks"
    ask: "Are common shocks, regional policies, weather, markets, and monitoring intensity separated from spatial spillovers?"
    live_lookup_required: ["current weather, policy, monitoring, and market data"]
```

## Forbidden claims

- Do not call spatial autocorrelation a causal spillover without identification.
- Do not interpret SAR or SDM raw coefficients as direct, indirect, or total impacts.
- Do not use one arbitrary W matrix without mechanism and sensitivity checks.
- Do not ignore row-standardization: average-neighbor exposure is not total cumulative exposure.
- Do not hide islands, disconnected components, dropped units, or W normalization.
- Do not interpret SEM spatial-error dependence as substantive policy spillover.
- Do not ignore reflection when using spatially lagged outcomes.
- Do not make current claims about spatial package defaults, W construction, row-standardization, islands handling, impact simulation, or backend behavior without live lookup.

## Domain reasoning steps

1. Restate the question as an estimand question before choosing a model.
2. Identify unit, time frequency, outcome, treatment or exposure, geography, W candidates, and the target claim.
3. Classify the target as structural spatial, reduced-form spatial exposure, descriptive association, forecasting, or unknown.
4. Separate estimands: reduced-form W*treatment or spatial DID estimates an exposure contrast, not an SDM indirect impact.
5. Map model candidates:

   * SAR: spatial lag of outcome, usually W*y, with equilibrium feedback through the spatial multiplier.
   * SEM: spatial error correlation, usually lambda in the disturbance, with no direct policy spillover interpretation by itself.
   * SDM: spatial lag of outcome and covariates, usually W*y and W*x, requiring direct, indirect, and total impacts.
   * Mixed, SAC, or SARAR: separate outcome feedback from spatially correlated shocks and document both.
6. Interpret parameters cautiously:

   * rho is not a simple spillover coefficient; it enters the spatial multiplier.
   * lambda is not a treatment spillover; it captures spatial error dependence.
   * theta on W*x is not the indirect impact; impacts must be computed from the model.
7. For SAR and SDM, flag simultaneity because W*y is jointly determined with y.
8. Treat naive OLS on W*y as invalid for structural claims unless an accepted structural estimator and artifacts support it.
9. For SEM, state that the model can adjust for spatially correlated unobservables but does not decompose direct and indirect impacts.
10. For SDM, require an impact table with direct, indirect, and total impacts plus uncertainty before any SDM spillover claim.
11. Specify whether impacts are average marginal impacts, period-specific impacts, short-run impacts, long-run impacts, or equilibrium impacts.
12. Audit W as part of the identifying design, not as harmless preprocessing.
13. Check W construction: contiguity, distance band, inverse distance, k-nearest neighbors, economic network, hydrological network, wind, river flow, trade, migration, commuting, or supply chain.
14. Check W normalization: row-standardized, binary, spectral, globally standardized, unnormalized, symmetric, directed, or time-varying.
15. Check W support: islands, zero-neighbor units, disconnected components, hubs, self links, duplicate geometries, missing coordinates, and boundary changes.
16. Check geography: CRS, projection, distance units, polygon topology, coastal or border handling, and grid-to-region aggregation.
17. Check timing: W measured pre-treatment, contemporaneously, post-treatment, or updated by behavior affected by the treatment.
18. Flag W endogeneity when W is built from migration, trade, commuting, infrastructure, firm links, policy choices, or post-treatment outcomes.
19. Define the measurement model for outcomes, exposures, and W*x; note monitor data, satellite data, administrative data, firm disclosures, modeled grids, and spatial aggregation risks.
20. State identification assumptions: correct structural equation, correct W, exogenous covariates or valid instruments, no omitted spatially correlated shocks, stable units, support across connected components, and valid timing.
21. For causal policy claims, add assumptions on treatment timing, anticipation, selection into treatment, spatial interference structure, and pre-treatment W.
22. Treat lagged outcomes and dynamic panels as separate endogeneity risks; do not conflate temporal lag dynamics with SAR simultaneity.
23. Use model comparison tests only as diagnostics: LM, robust LM, LR, Wald, Hausman, information criteria, and common factor tests do not prove causal spillovers.
24. Common factor restrictions can compare SDM against SAR or SEM restrictions, but cannot replace identification or W validation.
25. Diagnostics that block claims include missing live backend status, parser-only status, missing claim_gate.json, missing W metadata, missing impact table, missing impact uncertainty, failed W audit, artifact conflicts, and denied claim gate.
26. Rank robustness by risk: theory-based alternative W, normalization changes, thresholds or k changes, directed versus symmetric W, pre-treatment W, island handling, spatial scale, outcome measurement, placebo W, and reduced-form comparison as a separate estimand.
27. Draft claim language from artifact status:

* Before live artifacts: "candidate design" or "requires live backend execution."
* Live model without impact table: "model output exists, but SDM impact claims are blocked."
* Impact table without W metadata: "impacts are not spatially interpretable until W is audited."
* Missing claim gate: "claim readiness unknown or blocked."
* Denied claim gate: use only downgraded language allowed by the gate.

28. Anticipate referee objections: why this W, whether W is exogenous, whether spillovers are physical or economic, whether impacts are decomposed correctly, whether uncertainty is valid, and whether reduced-form and structural estimands are mixed.
29. If the user asks for a strong claim, first identify the exact artifact that would allow it; otherwise downgrade.
30. If current policy, package, backend, data-source, or legal facts matter, instruct the agent to check official/latest sources at use time.

## Candidate outputs

* `structural_spatial_plan` YAML or JSON block.
* Method selection note distinguishing SAR, SEM, SDM, mixed, and reduced-form alternatives.
* Estimand statement for direct, indirect, total, structural, or reduced-form quantities.
* W matrix audit checklist and required W metadata.
* Diagnostics that block claims and ranked robustness plan.
* Referee objections, downgrade triggers, and safe claim language.
* Handoff to code execution and handoff from artifacts.

## Output schema

Return YAML or JSON. Do not omit the base fields. Preserve nulls and empty arrays when unknown. The domain-specific block must match this structure.

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
structural_spatial_plan:
  model_candidates: SAR | SEM | SDM | mixed | unknown
  W_candidates: []
  impact_decomposition_required: true
  backend_live_required: true
  parser_only_claim_allowed: false
  diagnostics_required: []
  comparison_to_reduced_form: string
  forbidden_claims: []
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
```

## Required caveats

* This skill drafts reasoning, rubrics, and language; it does not validate specs, run backends, inspect hidden files, or certify artifacts.
* SAR, SEM, and SDM have different estimands; do not pool their interpretations.
* SAR and SDM require care because W*y is jointly determined with y.
* SEM captures spatial error dependence and does not by itself estimate direct or indirect policy impacts.
* SDM impact claims require direct, indirect, and total impacts with uncertainty.
* A coefficient on W*treatment or W*x is not a substitute for an SDM indirect effect.
* W construction is part of identification; alternative W matrices are design sensitivity, not cosmetic robustness.
* Model comparison and common factor tests are diagnostics, not causal proof.
* Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
* Missing claim_gate.json, backend_status.json, W metadata, or SDM impact table blocks the corresponding strong claim.
* Volatile policy, regulation, standard, API, package, and data-source facts must be checked against official/latest sources at use time.

## Forbidden claims

* Do not bypass claim_gate.json or turn diagnostic_success into paper-ready causal success.
* Do not turn parser-only, interface-only, dry-run, mock, skipped, failed, or missing-dependency output into a live backend result.
* Do not claim SAR, SEM, or SDM estimation unless live backend artifacts support it.
* Do not present unsupported fallback estimators as equivalent substitutes for SAR, SEM, or SDM.
* Do not claim causal structural effects unless assumptions, diagnostics, artifacts, and claim_gate.json allow them.
* Do not use W*treatment as a substitute for an SDM indirect effect.
* Do not make an SDM impact claim without a direct, indirect, and total impact table.
* Do not interpret theta alone as the indirect effect, lambda as policy spillover, or rho as a simple coefficient spillover.
* Do not ignore simultaneity in SAR or SDM.
* Do not skip W metadata on normalization, islands, self links, time variation, CRS, and connectedness.
* Do not call reduced-form spatial exposure, spatial DID, or border exposure a structural SAR or SDM estimate.
* Do not claim W is exogenous when built from post-treatment behavior, contemporaneous networks, or policy-induced links without a credible design argument.
* Do not use model comparison tests as proof of causal identification.
* Do not make current policy, legal, package, API, or data-source claims without official/latest checks at use time.

## Handoff to code

Ask code-facing agents to draft or inspect a specification only after the domain estimand, W candidates, diagnostics, and artifact gates are explicit.
The handoff should request:

* Parse and validate the structural spatial specification.
* Record whether execution is live backend, parser-only, interface-only, dry-run, mock, skipped, failed, or missing-dependency.
* Save status.json, backend_status.json, manifest.json or artifact_manifest.json, diagnostics.json, reviewer_risk.json, and claim_gate.json.
* Save W metadata and W audit artifacts, including normalization, islands, self links, connectedness, CRS, and time variation.
* Save model outputs with parameter estimates and uncertainty.
* Save direct, indirect, and total impacts with uncertainty when SAR or SDM impact language is requested.
* Avoid fallback estimators unless explicitly labeled as separate exploratory or reduced-form analyses.
* Do not replace structural impact decomposition with W*x or W*treatment coefficients.
* Do not assert package, backend, wrapper, or estimator availability unless current workspace artifacts or official/latest sources at use time establish it.

## Handoff from code artifacts

Before writing result language, inspect claim_gate.json, status.json, backend_status.json, artifact manifest, diagnostics, reviewer risk, model table, impact table, W audit, W metadata, spec, and logs.
Classify result state conservatively:

* live_and_claim_gate_allows: limited structural result language may be used.
* live_but_no_claim_gate: claim readiness is unknown or blocked.
* live_but_no_impact_table_for_SDM: SDM impact claims are blocked.
* live_but_no_W_metadata: spatial interpretation is blocked.
* parser_only_or_interface_only: structural result claims are blocked.
* missing_backend_or_failed_run: report design only, not results.
* inconsistent_artifacts: report artifact conflict and downgrade to unknown.
  Use the most conservative interpretation when artifacts conflict.
  Do not infer success from a model table alone.
  Do not infer SDM impact claims from theta, W*x, W*treatment, or parser acceptance.
  Only use strong causal, structural, paper-ready, or backend-certified language when claim_gate.json allows it.

## Minimal examples

### Example 1: good planning output

Input: User wants to estimate whether a regional low-carbon pilot reduced local emissions and spilled over to neighboring cities using an SDM with yearly city panel data.

```yaml
skill_name: sar_sem_sdm_structural_spatial
user_question_summary: "Plan an SDM design for local and neighboring emissions effects of a low-carbon pilot."
research_domain: structural_spatial_environmental_economics
research_brief:
  unit: city
  time_frequency: year
  outcome_candidates: [emissions]
  treatment_or_exposure: low_carbon_pilot
  estimand_candidates: [direct_impact, indirect_impact, total_impact]
  identification_risks: [endogenous_policy_timing, spatially_correlated_unobservables, W_matrix_sensitivity, simultaneity_from_W_y]
structural_spatial_plan:
  model_candidates: SDM
  W_candidates: [contiguity_W, distance_band_W, economic_distance_W]
  impact_decomposition_required: true
  backend_live_required: true
  parser_only_claim_allowed: false
  diagnostics_required: [backend_live_status, claim_gate, W_audit, impact_table, impact_uncertainty]
  comparison_to_reduced_form: "Reduced-form W*treatment can be reported only as a separate exposure estimand, not as the SDM indirect impact."
  forbidden_claims: [do_not_claim_SDM_impacts_without_impact_table, do_not_use_W_treatment_as_indirect_effect, do_not_claim_live_backend_from_parser_only_output]
candidate_workflows: [draft_structural_spatial_spec, verify_live_backend, audit_W_matrix, compute_impact_decomposition, run_claim_gate]
candidate_methods: [SDM_if_theory_requires_outcome_feedback_and_covariate_spillovers, SEM_only_for_error_correlation, reduced_form_spatial_DID_as_separate_estimand]
required_diagnostics: [backend_status_json_confirms_live_run, claim_gate_json_allows_structural_language, W_audit_no_blocking_errors, direct_indirect_total_impacts_with_uncertainty]
recommended_robustness: [alternative_theory_based_W, alternative_W_normalization, pre_treatment_W, island_sensitivity, alternative_outcome_measurement]
forbidden_claims: ["The coefficient on W*treatment is the SDM indirect effect.", "Parser-only output estimates a structural SDM.", "Rho significance proves causal spillovers."]
claim_language:
  allowed: ["The proposed estimand is direct, indirect, and total SDM impacts conditional on a verified W and live backend run.", "Reduced-form spatial exposure estimates should be labeled as a separate estimand."]
  disallowed: ["The W*treatment coefficient is the spillover effect.", "The model proves regional causal spillovers before claim_gate.json allows that language."]
uncertainty_notes: ["W construction, policy timing, and spatially correlated shocks are first-order risks.", "Backend and package availability must be checked from workspace artifacts or official/latest sources at use time."]
next_code_actions: [inspect_workspace_rules_and_artifacts, draft_spec_with_W_metadata, require_live_backend_status, require_impact_decomposition_artifact, run_claim_gate]
scholarly_depth:
  estimand_definition: "Average direct, indirect, and total SDM impacts of the policy on emissions, not the raw coefficient on W*treatment."
  identification_assumptions: [correct_structural_equation, exogenous_policy_timing_conditional_on_design, exogenous_or_pretreatment_W, no_unmodeled_spatial_shocks]
  measurement_model: [document_emissions_source, check_spatial_aggregation, verify_city_boundaries_and_panel_consistency]
  data_construction_risks: [post_treatment_network_W, CRS_or_distance_errors, islands_or_disconnected_components]
  method_decision_tree: ["Use SDM only if outcome feedback and covariate spillovers are part of the estimand.", "Use SEM for spatial error correlation, not policy impacts.", "Use reduced-form spatial DID only as a separate estimand."]
  diagnostics_that_block_claims: [missing_backend_live_status, missing_claim_gate, missing_impact_table, missing_W_metadata]
  robustness_ranked_by_risk: [alternative_theory_based_W, pretreatment_W, island_sensitivity, alternative_outcome_measurement]
  referee_objections: ["Why is this W the correct spillover channel?", "Is policy placement spatially endogenous?", "Are indirect effects calculated from the spatial multiplier?"]
  downgrade_triggers: ["No live backend artifact: describe design only.", "No impact table: no SDM impact claim.", "No claim_gate.json: claim readiness unknown or blocked."]
not_recommended_methods: [OLS_on_W_y_as_structural_SAR, W_treatment_coefficient_as_SDM_indirect_effect, arbitrary_single_W_without_sensitivity]
```

### Example 2: downgrade or refusal output

Input: User says the parser accepted a spatial DID with W*treatment and asks to write that they estimated an SDM spillover effect.

```yaml
skill_name: sar_sem_sdm_structural_spatial
user_question_summary: "Assess whether parser-only W*treatment output supports an SDM spillover claim."
research_domain: structural_spatial_environmental_economics
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: W_treatment
  estimand_candidates: [reduced_form_spatial_exposure]
  identification_risks: [parser_only_output, missing_live_backend, missing_impact_decomposition, W_treatment_overclaim]
structural_spatial_plan:
  model_candidates: unknown
  W_candidates: []
  impact_decomposition_required: true
  backend_live_required: true
  parser_only_claim_allowed: false
  diagnostics_required: [backend_live_status, claim_gate, W_metadata_and_audit, impact_decomposition_table_if_SDM_is_claimed]
  comparison_to_reduced_form: "The accepted W*treatment term is at most a reduced-form spatial exposure contrast unless a live SDM is estimated and impacts are decomposed."
  forbidden_claims: [do_not_use_parser_only_as_live_backend, do_not_call_W_treatment_an_SDM_indirect_effect, do_not_claim_structural_spillovers_without_claim_gate]
candidate_workflows: [downgrade_to_reduced_form_design_language, request_live_structural_backend, require_W_audit_and_impact_table]
candidate_methods: [reduced_form_spatial_exposure_design, structural_SDM_only_after_live_backend_and_impact_decomposition]
required_diagnostics: [backend_status_json_confirms_live_run, claim_gate_json_allows_structural_claim, impact_decomposition_table, W_metadata_and_W_audit]
recommended_robustness: [alternative_W_if_reduced_form_design_is_kept, placebo_W_if_design_supports_it, sensitivity_to_neighbor_definition]
forbidden_claims: ["I estimated an SDM because the parser accepted W*treatment.", "W*treatment is the indirect effect.", "The output is backend-certified without backend_status.json and claim_gate.json."]
claim_language:
  allowed: ["The parser accepted a candidate specification, but this does not establish a live structural SDM estimate.", "The W*treatment coefficient may be described only as a reduced-form spatial exposure coefficient if the design supports that label."]
  disallowed: ["We estimate SDM spillover effects.", "The indirect effect equals the W*treatment coefficient."]
uncertainty_notes: ["Backend execution, impact decomposition, W metadata, and claim_gate.json are missing or unverified.", "Downgrade to design-only or reduced-form exposure language."]
next_code_actions: [inspect_status_json_and_backend_status_json, inspect_claim_gate_json, inspect_W_metadata, run_live_SDM_backend_if_structural_claim_is_needed, produce_direct_indirect_total_impact_table]
scholarly_depth:
  estimand_definition: "No structural SDM estimand is established by parser acceptance; the current object is a candidate reduced-form W*treatment contrast."
  identification_assumptions: [not_established_from_parser_only_output, structural_equation_not_verified, W_exogeneity_not_documented]
  measurement_model: [W_construction_metadata_missing_or_unverified, treatment_timing_and_spatial_support_missing_or_unverified]
  data_construction_risks: [unknown_row_normalization, unknown_islands, unknown_self_links, unknown_time_variation_in_W]
  method_decision_tree: ["If only parser output exists, block structural result claims.", "If live SDM exists but no impact table exists, block indirect and total impact claims.", "If W metadata is missing, block spatial interpretation."]
  diagnostics_that_block_claims: [parser_only_status, missing_backend_status, missing_claim_gate, missing_impact_decomposition, missing_W_audit]
  robustness_ranked_by_risk: [verify_live_backend_before_robustness, audit_W_before_spatial_language, compare_reduced_form_and_structural_estimands_only_after_both_are_valid]
  referee_objections: ["Parser acceptance is not estimation.", "The W*treatment coefficient is not an SDM impact decomposition.", "No W audit or claim gate supports the claimed spillover."]
  downgrade_triggers: ["Parser-only output: refuse structural result claim.", "Missing backend_status.json: no live backend claim.", "Missing impact table: no SDM indirect effect claim."]
not_recommended_methods: [parser_only_as_estimation, interface_only_as_backend_result, W_treatment_as_structural_indirect_effect]
```

## Completion checklist

* First line is `# Skill: sar_sem_sdm_structural_spatial`.
* Required second-level headings are present in the specified order.
* File is ASCII-only markdown with no YAML frontmatter.
* Required repo artifacts say to inspect workspace files first and list shared rules 01 through 07.
* Output schema includes all base fields, structural_spatial_plan, scholarly_depth, and not_recommended_methods.
* SAR, SEM, and SDM are distinguished by estimand and interpretation.
* Structural and reduced-form spatial estimands are not conflated.
* Rho, lambda, theta, simultaneity, spatial error correlation, and SDM impact decomposition are covered.
* W construction, normalization, islands, self links, time variation, CRS, connectedness, and endogeneity are covered.
* Diagnostics that block claims include missing backend status, parser-only status, missing W metadata, missing impact table, and missing claim_gate.json.
* Model comparison and common factor tests are diagnostics only.
* Handoff to code and handoff from code artifacts are explicit.
* Minimal examples include one good planning example and one downgrade/refusal example.
* Forbidden claims include parser-only structural claims, W*treatment as SDM indirect effect, and SDM impact claims without an impact table.
