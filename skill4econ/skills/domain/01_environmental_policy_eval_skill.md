# Skill: environmental_policy_eval

## Purpose

Plan environmental policy evaluation designs for pilots, inspections, trading schemes, restrictions, subsidies, and disclosure rules.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- The user asks about low-carbon city pilot in environmental, ESG, low-carbon, or finance research.
- A domain-specific plan is needed before spec drafting or result interpretation.

## Do not use when

- Do not use when the user only needs to run an already validated spec.
- Do not use to certify a completed run without reporting skills and claim_gate.json.

## Inputs expected

- Research question and intended unit/time/outcome.
- Available data sources, policy or exposure source, geography, and backend constraints.
- Existing artifacts if interpreting prior runs.

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
- `../_shared/07_scholarly_depth_rules.md`
- `../_shared/08_domain_literature_anchor_rules.md`

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Greenstone (2002), 'The Impacts of Environmental Regulations on Industrial Activity: Evidence from the 1970 and 1977 Clean Air Act Amendments and the Census of Manufactures'"
    - "Chay and Greenstone (2003), 'The Impact of Air Pollution on Infant Mortality: Evidence from Geographic Variation in Pollution Shocks Induced by a Recession'"
    - "Currie and Neidell (2005), 'Air Pollution and Infant Health: What Can We Learn from California's Recent Experience?'"
    - "Hanna and Oliva (2010), 'The Impact of Inspections on Plant-Level Air Emissions'"
    - "Fowlie (2010), 'Emissions Trading, Electricity Restructuring, and Investment in Pollution Abatement'"
    - "Greenstone, List, and Syverson (2012), 'The Effects of Environmental Regulation on the Competitiveness of U.S. Manufacturing'"
    - "Ryan (2012), 'The Costs of Environmental Regulation in a Concentrated Industry'"
    - "Fowlie, Holland, and Mansur (2012), 'What Do Emissions Markets Deliver and to Whom? Evidence from Southern California's NOx Trading Program'"
    - "Duflo, Greenstone, Pande, and Ryan (2013), 'Truth-Telling by Third-Party Auditors and the Response of Polluting Firms: Experimental Evidence from India'"
    - "Deschenes, Greenstone, and Shapiro (2017), 'Defensive Investments and the Demand for Air Quality: Evidence from the NOx Budget Program'"
    - "Shapiro and Walker (2018), 'Why Is Pollution from US Manufacturing Declining? The Roles of Environmental Regulation, Productivity, and Trade'"
  canonical_data_sources:
    - "EPA Air Quality System (AQS): ambient monitor concentrations and monitor metadata"
    - "EPA National Emissions Inventory (NEI): facility-, county-, process-, and source-category emissions inventory"
    - "EPA Toxics Release Inventory (TRI): facility-reported toxic releases and transfers"
    - "EPA Facility Registry Service (FRS): facility identifiers, geocodes, and cross-program facility links"
    - "EPA Continuous Emissions Monitoring Systems (CEMS) via Air Markets Program Data: unit-level power-sector emissions and heat input"
    - "EPA Enforcement and Compliance History Online (ECHO), ICIS-Air, PCS/ICIS-NPDES, and RCRAInfo: inspections, violations, enforcement actions, permits, and compliance histories"
    - "Census ASM/CMF/LBD where available under restricted access: plant output, inputs, employment, entry, exit, productivity, and ownership"
    - "PACE where historically available: pollution abatement operating and capital expenditures"
  live_lookup_required_for:
    - "current NAAQS thresholds, attainment/nonattainment designations, and effective dates"
    - "current EPA enforcement targeting initiatives, inspection definitions, penalty policies, and ECHO schema changes"
    - "latest NEI release year, revision status, sector coverage, and emissions-method flags"
    - "current TRI reporting thresholds, chemical lists, PFAS additions, and reporting exemptions"
    - "current FRS crosswalk behavior, retired facility IDs, parent-company fields, and geocode quality flags"
    - "current CEMS/AMPD unit coverage, monitoring-rule changes, and available hourly fields"
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "regulation: pollutant-specific Clean Air Act nonattainment, permit limits, emissions-trading coverage, MACT/NESHAP applicability, NSR/PSD status, consent decrees, and inspection/enforcement exposure"
    - "enforcement: inspection count, inspection probability, days since last inspection, violation indicator, high-priority violation status, penalty amount, injunctive relief, and regulator-assigned compliance status"
    - "compliance: permitted emissions versus reported emissions, violation episodes, exceedance days, stack-test failures, audit backcheck discrepancies, and enforcement closure outcomes"
    - "technology adoption: scrubber/SCR/SNCR installation, fuel switching, low-NOx burners, process changes, abatement capital, CEMS-observed emissions-rate changes, and permit-control requirements"
    - "pollution outcomes: AQS ambient concentrations, CEMS stack emissions, NEI inventory emissions, TRI toxic releases, satellite/model-fused exposure where justified, and pollutant-specific exceedance days"
    - "firm outcomes: output, revenue, employment, payroll, capital, TFP, entry, exit, product mix, investment, electricity generation, heat input, and market share"
    - "health outcomes: mortality, hospital admissions, emergency visits, birth weight, gestation, infant mortality, school absences, and worker productivity"
    - "welfare outcomes: monetized health effects, defensive expenditures, hedonic capitalization, avoidance behavior, compliance costs, markups, producer surplus, consumer surplus, and distributional incidence"
    - "estimands: facility-level direct effect, county-level ambient or health effect, market-level equilibrium effect, cross-border spillover, and sector-level reallocation effect"
  validation_targets:
    - "FRS crosswalk maps one physical site to the same AQS/NEI/TRI/ECHO/CEMS entity without conflating parent firms, colocated units, or retired IDs"
    - "AQS monitors used for exposure are present before treatment, not opened in response to enforcement, and have stable pollutant-method codes"
    - "CEMS hourly emissions aggregate to annual plant totals consistent with AMPD reporting and expected operating hours"
    - "NEI and TRI emissions move in the expected direction for regulated pollutants, recognizing that TRI toxic releases and criteria-pollutant emissions are not interchangeable"
    - "inspection and violation measures are separated from pollution outcomes when inspections mechanically reveal violations"
    - "firm outcome panels distinguish true exit from ID changes, ownership changes, county moves, and reporting-threshold dropout"
    - "health-exposure links specify pollutant, temporal window, spatial assignment, and avoidance channel before welfare interpretation"
  known_mismeasurement_channels:
    - "monitor siting is nonrandom and may follow pollution hotspots, complaints, permitting disputes, or enforcement priorities"
    - "AQS ambient concentration is not facility emissions and can reflect transport, meteorology, chemistry, and upwind sources"
    - "NEI contains imputation, engineering estimates, temporal allocation, and reporting-method changes"
    - "TRI is self-reported, threshold-based, chemical-specific, and not a clean measure of criteria-pollutant regulation"
    - "CEMS covers monitored units in regulated sectors, especially power-sector units, and does not represent all industrial emissions"
    - "FRS many-to-one and one-to-many matches can create false facility births, deaths, mergers, and spillovers"
    - "inspection intensity is an outcome of regulator targeting, complaints, facility risk, and prior compliance history"
    - "observed emissions can fall because of output contraction, fuel switching, abatement, outsourcing, shutdown, or reporting changes"
    - "county averages can mask within-county exposure gradients and facility-level treatment heterogeneity"
    - "avoidance, migration, defensive investments, and selective survival can attenuate or reallocate measured health and firm effects"
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "Clean Air Act nonattainment compares dirtier places to cleaner places unless the design isolates threshold timing, pollutant-specific rules, or credible untreated counterfactuals"
    - "monitoring and enforcement are selected on risk, complaints, regulator capacity, political pressure, and previous violations"
    - "compliance measures can be mechanically produced by inspections, making inspection-adjusted violation outcomes necessary"
    - "firm outcomes are selected by entry, exit, survival, ownership changes, market restructuring, and differential reporting thresholds"
    - "ambient pollution and health effects can be contaminated by upwind transport, concurrent local policies, recession shocks, and avoidance behavior"
    - "technology adoption may be caused by expected future regulation, electricity-market restructuring, fuel-price shocks, or permit negotiations rather than the focal rule"
    - "leakage can occur through output shifting to unregulated facilities, imports, nearby counties, unmonitored pollutants, or unregulated media"
    - "spillovers can operate through product markets, labor markets, power dispatch, transport of pollutants, and regulator learning"
  sorting_vs_siting_or_selection_channel:
    - "dirty facilities may locate where baseline pollution, zoning, land prices, workforce composition, and political resistance make regulation less costly"
    - "households may sort away from pollution or toward cheaper housing near regulated facilities, confounding health and welfare incidence"
    - "regulators may site monitors or target inspections near known hotspots, repeat violators, large emitters, or politically salient facilities"
    - "markets may reallocate output from treated to untreated plants, making facility-level estimates different from market-level welfare effects"
    - "technology adopters may be plants with better management, easier retrofit options, higher utilization, or longer expected survival"
  why_method_not_magic:
    - "DID is not credible without pollutant-specific pretrends, treatment timing logic, stable reporting, and evidence against selective monitoring or enforcement"
    - "RD around attainment thresholds is not magic if counties manipulate monitor placement, pollutant readings, industrial composition, or boundary exposure"
    - "IV using regulatory assignment is not magic if the instrument changes enforcement, market structure, health behavior, or monitoring intensity through channels other than the stated treatment"
    - "event studies do not solve anticipation when firms adopt technology before permit deadlines or when regulators phase in enforcement"
    - "facility fixed effects do not solve time-varying compliance selection, output-induced emissions changes, or survival conditioning"
    - "county fixed effects do not identify facility-level compliance margins or market-level leakage"
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "the paper calls the variable regulation, but the measured shock is monitoring, nonattainment, inspection, violation discovery, or reporting coverage"
    - "inspection or enforcement variation is selected and not plausibly as-good-as-random"
    - "ambient AQS outcomes are attributed to a facility rule without emissions transport, monitor distance, wind, or source-apportionment logic"
    - "TRI/NEI/CEMS outcomes are mixed as if they measure the same pollutant, medium, or regulated margin"
    - "firm productivity effects condition on surviving plants and omit exit, entry, markups, utilization, and output reallocation"
    - "technology adoption is inferred from lower emissions without direct evidence on abatement, fuel switching, process change, or shutdown"
    - "health or welfare claims exceed the measured pollution, exposure, avoidance, and monetization evidence"
    - "leakage and spillovers make the stated facility, county, or market estimand unclear"
  minimal_empirical_section_checklist:
    - "state the estimand as facility, county, airshed, sector, or market before presenting the regression"
    - "name the regulated pollutant, statutory trigger, compliance date, enforcement mechanism, and treated universe"
    - "separate regulation, monitoring, enforcement, violation discovery, compliance, and technology adoption variables"
    - "document AQS/NEI/TRI/FRS/CEMS/ECHO linkage rules, dropped matches, duplicate facilities, and geocode restrictions"
    - "show baseline emissions, monitor coverage, inspection rates, industry composition, and facility size for treated and comparison units"
    - "plot event-study coefficients for pollutant-specific pretrends and placebo pollutants not targeted by the rule"
    - "test leakage to nearby counties, untreated facilities, unregulated pollutants, imports, dispatch substitution, or product-market competitors"
    - "distinguish intensive-margin emissions-rate changes from output contraction, shutdown, and reporting-threshold exit"
    - "report clustering and spatial correlation choices at the policy-assignment and pollution-transport scale"
    - "state whether welfare combines producer costs, consumer prices, health benefits, defensive behavior, and distributional incidence"
  claims_to_downgrade:
    - "downgrade 'regulation caused emissions reductions' to 'the measured policy/enforcement shock is associated with pollutant-specific emissions changes' unless assignment and mechanisms are established"
    - "downgrade 'compliance improved' when the outcome is only fewer detected violations after fewer inspections"
    - "downgrade 'technology adoption occurred' when evidence is only lower emissions or lower emissions intensity"
    - "downgrade 'health benefits of regulation' when ambient exposure, affected population, dose-response, and avoidance are not measured"
    - "downgrade 'welfare improved' when only partial compliance costs or partial health endpoints are estimated"
    - "downgrade 'no leakage' when the design observes only treated facilities or treated counties"
```

## Domain reasoning steps

- Define the policy object first: statute, rule, permit, market program, inspection regime, audit reform, or enforcement initiative.
- Fix the estimand before the method: facility direct effect, county ambient effect, exposed-population health effect, market equilibrium effect, or welfare incidence.
- Map the regulatory chain explicitly: assignment -> monitoring/enforcement -> compliance behavior -> technology/output/fuel response -> emissions -> ambient exposure -> health/welfare.
- Build the facility spine with FRS, then attach NEI/TRI/CEMS/ECHO records only after resolving duplicate sites, unit-level versus facility-level records, parent changes, and geocode quality.
- Treat AQS ambient pollution as exposure, not emissions; treat NEI/TRI/CEMS as emissions or releases, not population exposure.
- Separate inspection occurrence from violation discovery; an observed violation is partly a monitoring outcome.
- For technology adoption, require direct evidence from permits, CEMS emissions rates, engineering controls, abatement expenditures, fuel mix, or operating behavior.
- For leakage, inspect untreated facilities, nearby counties, substitute pollutants, output markets, power dispatch, imports, and entry/exit.
- For health and welfare, state the pollutant, exposed population, exposure window, dose-response, avoidance margin, and monetization assumptions.
- Mark current rule thresholds, enforcement priorities, reporting schemas, and dataset versions as live_lookup_required.

## Forbidden claims

- Do not say nonattainment is random assignment.
- Do not say inspections identify enforcement effects without addressing regulator targeting.
- Do not interpret fewer detected violations as better compliance when inspections also changed.
- Do not treat TRI toxic releases as criteria-pollutant emissions.
- Do not treat CEMS-covered power units as representative of all industrial facilities.
- Do not merge AQS, NEI, TRI, FRS, ECHO, and CEMS without documenting identifier and geocode conflicts.
- Do not call an emissions decline technology adoption without direct adoption, fuel, control-equipment, or process evidence.
- Do not claim welfare effects from pollution coefficients alone.
- Do not ignore shutdown, selective survival, and output contraction when estimating firm productivity or compliance costs.
- Do not claim no leakage from a sample that cannot observe untreated substitutes, markets, or nearby jurisdictions.

## Candidate outputs

- `environmental_policy_plan` YAML block.
- Candidate workflows and methods.
- Required diagnostics and robustness plan.
- Forbidden claim list.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
environmental_policy_eval:
  policy_name: string
  policy_type: string
  likely_estimand: []
  primary_design_candidates: []
  design_risks:
    staggered_twfe_bias: unknown | low | medium | high
    policy_selection: unknown | low | medium | high
    spatial_spillover: unknown | low | medium | high
    anticipation: unknown | low | medium | high
    concurrent_policy: unknown | low | medium | high
  required_diagnostics: []
  forbidden_claims: []
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- Key risks include: staggered adoption, policy selection, anticipation, concurrent policies, spatial spillovers.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not claim `low-carbon city pilot` has a causal effect until artifacts and claim_gate.json allow it.
- Do not skip measurement, timing, support, and backend caveats.

## Handoff to code

- Draft and validate specs; run backend discovery; run diagnostics; write artifact manifests and claim gate.

## Handoff from code artifacts

- Read claim_gate.json, status.json, artifact_manifest.json, reviewer_risk.json, diagnostics, and model tables before any result language.

## Minimal examples

### Input

User: Did low-carbon city pilots reduce PM2.5?

### Expected skill output

```yaml
skill_name: environmental_policy_eval
user_question_summary: "Low-carbon city pilots and PM2.5."
research_domain: environmental_policy
research_brief:
  unit: city
  time_frequency: year
  outcome_candidates: [pm25]
  treatment_or_exposure: low_carbon_city_pilot
  estimand_candidates: [ATT_g_t, dynamic_ATT]
environmental_policy_eval:
  policy_name: low_carbon_city_pilot
  policy_type: staggered_binary
  likely_estimand: [ATT_g_t, event_time_ATT]
  primary_design_candidates: [cs_did_attgt, did_imputation_event, spatial_exposure_sensitivity]
  design_risks:
    staggered_twfe_bias: high
    policy_selection: medium
    spatial_spillover: medium
    anticipation: unknown
    concurrent_policy: unknown
  required_diagnostics: [cohort_support, pretrend_check, spillover_contamination_check]
  forbidden_claims: [do_not_use_twfe_significance_as_policy_success]
candidate_workflows: [did_paper_run, spatial_spillover_run]
candidate_methods: [cs_did_attgt, did_imputation_event]
required_diagnostics: [cohort_support, pretrend_check]
recommended_robustness: [alternative_policy_timing, neighbor_exposure_exclusion]
forbidden_claims: [respect_claim_gate]
claim_language:
  allowed: ["Candidate design only until artifacts pass claim gate."]
  disallowed: ["The policy reduced PM2.5."]
uncertainty_notes: [Need official policy timing and treated city list.]
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
