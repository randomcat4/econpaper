# Skill: pollution_exposure_and_health

## Purpose

Plan pollution exposure and health or labor-supply designs using monitoring, remote-sensing, or source-based exposure.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- The user asks about PM2.5 exposure in environmental, ESG, low-carbon, or finance research.
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
    - "Dockery et al. (1993), 'An Association between Air Pollution and Mortality in Six U.S. Cities'"
    - "Pope et al. (2002), 'Lung Cancer, Cardiopulmonary Mortality, and Long-term Exposure to Fine Particulate Air Pollution'"
    - "Chay and Greenstone (2003), 'The Impact of Air Pollution on Infant Mortality: Evidence from Geographic Variation in Pollution Shocks Induced by a Recession'"
    - "Currie and Neidell (2005), 'Air Pollution and Infant Health: What Can We Learn from California's Recent Experience?'"
    - "Currie, Neidell, and Schmieder (2009), 'Air Pollution and Infant Health: Lessons from New Jersey'"
    - "Lleras-Muney (2010), 'The Needs of the Army: Using Compulsory Relocation in the Military to Estimate the Effect of Air Pollutants on Children's Health'"
    - "Moretti and Neidell (2011), 'Pollution, Health, and Avoidance Behavior: Evidence from the Ports of Los Angeles'"
    - "Deryugina et al. (2019), 'The Mortality and Medical Costs of Air Pollution: Evidence from Changes in Wind Direction'"
    - "Schlenker and Walker (2016), 'Airports, Air Pollution, and Contemporaneous Health'"
    - "Anderson (2020), 'As the Wind Blows: The Effects of Long-Term Exposure to Air Pollution on Mortality'"
    - "He, Liu, and Salvo (2019), 'Severe Air Pollution and Labor Productivity: Evidence from Industrial Towns in China'"
    - "Knittel, Miller, and Sanders (2016), 'Caution, Drivers! Children Present: Traffic, Pollution, and Infant Health'"
  canonical_data_sources:
    - "EPA Air Quality System (AQS): ambient monitor concentrations, monitor metadata, method codes, and quality flags"
    - "Medicare administrative claims and enrollment data: mortality, hospitalizations, diagnoses, procedures, spending, and beneficiary demographics"
    - "National Center for Health Statistics vital statistics: births, deaths, causes of death, gestational outcomes, and maternal/infant characteristics"
    - "State inpatient and emergency-department hospital discharge data, including HCUP SID/SEDD where available"
    - "MODIS aerosol optical depth and fire products: satellite-derived aerosol and fire-related inputs"
    - "MISR aerosol optical depth and aerosol-type retrievals"
    - "TROPOMI tropospheric NO2, SO2, CO, CH4, HCHO, and aerosol-related products where suitable for the pollutant and period"
    - "NOAA meteorology, reanalysis, wind fields, boundary-layer height, temperature inversions, and smoke-plume products"
    - "HMS smoke polygons and fire-perimeter data for wildfire-smoke exposure designs"
    - "EPA NEI, CEMS, TRI, and FRS when health exposure is linked to emissions sources rather than monitors alone"
  live_lookup_required_for:
    - "current AQS parameter codes, method codes, monitor completeness rules, exceptional-event flags, and quality-assurance conventions"
    - "current Medicare data access, variable names, diagnosis-code vintages, enrollment restrictions, and geographic identifiers"
    - "current vital-statistics restricted-use access, cause-of-death coding, bridged-race files, and geographic suppression rules"
    - "current hospital-discharge data availability, ICD-9/ICD-10 transition handling, payer fields, and state-specific suppression rules"
    - "current MODIS, MISR, and TROPOMI product versions, retrieval algorithms, spatial resolution, cloud screens, and data-quality flags"
    - "current wildfire-smoke plume products, fire-detection algorithms, and satellite overpass timing"
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "ambient pollution: AQS monitor concentration, monitor-network average, inverse-distance-weighted concentration, kriged surface, chemical-transport-model output, or satellite-fused prediction"
    - "individual exposure: residence-assigned exposure, time-location exposure, workplace exposure, school exposure, commuting exposure, indoor-adjusted exposure, or activity-weighted exposure"
    - "monitor assignment: nearest monitor, all monitors within radius, pollutant-specific monitor, population-weighted monitor set, upwind monitor, leave-one-monitor-out surface, or monitor fixed panel"
    - "satellite fusion: aerosol optical depth calibrated to ground PM2.5, land-use regression plus satellite predictors, chemical-transport-model fusion, machine-learning exposure surfaces, or reanalysis-derived exposure"
    - "acute exposure windows: same-day, lagged daily, distributed-lag, weekly, gestational trimester, wildfire episode, inversion episode, or hospital-admission risk window"
    - "chronic exposure windows: annual mean, multi-year average, moving average, cumulative exposure, childhood exposure, elderly exposure, or residence-history-weighted exposure"
    - "health outcomes: all-cause mortality, cause-specific mortality, infant mortality, birth weight, prematurity, hospital admission, emergency visit, asthma, COPD, cardiovascular events, dementia, medication use, and medical spending"
    - "sensitive subpopulations: infants, pregnant people, elderly Medicare beneficiaries, children with asthma, outdoor workers, low-income populations, racial and ethnic groups, nursing-home residents, and people with baseline chronic disease"
    - "instruments or quasi-shocks: wind direction, upwind/downwind exposure, atmospheric inversions, wildfire smoke transport, airport runway use, port congestion, traffic shocks, plant closures, regulatory shocks, and long-range pollutant transport"
  validation_targets:
    - "ambient monitor assignment predicts actual monitor readings without using monitors opened because of the health event or policy shock"
    - "satellite-fused exposure is validated against held-out AQS monitors by pollutant, season, region, urbanicity, and concentration range"
    - "pollutant timing aligns with biologically plausible exposure windows for mortality, morbidity, birth outcomes, and admissions"
    - "mortality outcomes use consistent ICD coding across ICD-9 and ICD-10 eras and distinguish all-cause from cause-specific outcomes"
    - "hospital outcomes separate admission date, discharge date, emergency visit, inpatient stay, primary diagnosis, secondary diagnosis, and repeat visits"
    - "Medicare samples define enrollment, age, fee-for-service or managed-care coverage, residence geography, and death capture before analysis"
    - "wildfire, inversion, wind, and transport instruments predict pollutant exposure in the first stage at the same spatial and temporal scale as health outcomes"
    - "avoidance proxies such as air-conditioning, staying indoors, mask use, medication, evacuation, school closures, and public warnings are measured or explicitly bounded"
  known_mismeasurement_channels:
    - "ambient outdoor concentration is not personal inhaled dose because people spend time indoors, commute, work, and avoid pollution episodes"
    - "nearest-monitor assignment can misclassify exposure when monitors are sparse, pollutant gradients are steep, or monitors target hotspots"
    - "monitor openings and closures can be endogenous to local pollution, complaints, regulation, or health concerns"
    - "satellite retrievals are missing under clouds, snow, high surface reflectance, smoke saturation, and nighttime conditions"
    - "AOD-to-PM conversion depends on humidity, vertical aerosol profile, aerosol type, boundary-layer height, and ground calibration"
    - "TROPOMI and other satellite overpasses measure specific times of day, not full daily exposure"
    - "wind-direction and upwind instruments can proxy weather, temperature, humidity, activity patterns, or regional shocks if not conditioned carefully"
    - "wildfire smoke exposure can co-move with heat, evacuation, school closures, road closures, power shutoffs, and health-system strain"
    - "diagnosis coding changes, billing incentives, and hospital access can move measured morbidity without true disease incidence"
    - "residential histories can be incomplete, causing exposure error for movers, institutionalized populations, students, workers, and commuters"
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "pollution is spatially correlated with income, race, housing prices, industry, traffic, health care access, baseline health, and public services"
    - "short-run instruments such as wind, inversions, and smoke transport may affect health through temperature, humidity, stress, mobility, fires, or other pollutants"
    - "monitor placement and monitor availability are selected, especially near roads, industrial sources, urban centers, and regulatory hotspots"
    - "satellite-fused exposure can mechanically smooth local shocks or import model assumptions that bias health-response estimates"
    - "avoidance behavior can attenuate measured health effects and create heterogeneous effects by income, information, housing, and adaptive capacity"
    - "residential sorting and migration confound long-run exposure gradients and change the population at risk"
    - "mortality displacement, competing risks, and selective survival complicate interpretation of short-run mortality effects"
    - "morbidity outcomes depend on health-care access, coding practices, insurance coverage, admission thresholds, and hospital capacity"
    - "multi-pollutant settings make it hard to attribute health effects to one pollutant when PM2.5, ozone, NO2, CO, SO2, smoke, and heat co-move"
  sorting_vs_siting_or_selection_channel:
    - "households choose neighborhoods based on pollution, housing costs, schools, employment, race, income, and information"
    - "polluting sources and roads are sited through zoning, land markets, historical segregation, political influence, and industrial access"
    - "monitors are sited to satisfy regulatory, population, source-oriented, background, or special-purpose monitoring objectives"
    - "hospitals and health-care access are spatially sorted, so morbidity data reflect both disease incidence and care-seeking capacity"
    - "elderly, infants, outdoor workers, and low-income households face different exposure, avoidance, and baseline-risk selection"
  why_method_not_magic:
    - "instrumental variables using wind or inversions are not magic if meteorology affects health directly or shifts unmeasured co-pollutants"
    - "upwind/downwind designs are not magic if upwind sources differ systematically, transport varies by season, or treated locations anticipate pollution"
    - "wildfire smoke instruments are not magic if smoke episodes also change heat exposure, evacuation, mental stress, mobility, school closure, or health-care access"
    - "satellite exposure surfaces are not magic if validation error is spatially correlated with health determinants"
    - "fixed effects do not solve time-varying avoidance, local economic shocks, migration, health-care access, or changing monitor composition"
    - "distributed lags do not solve exposure misclassification or identify biological mechanisms without credible timing and outcome coding"
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "the paper interprets ambient monitor pollution as individual exposure without discussing indoor time, commuting, avoidance, or residence history"
    - "monitor assignment is arbitrary and sensitive to radius, nearest-monitor rules, monitor type, or monitor entry and exit"
    - "satellite-fusion estimates are used as if observed without validating held-out prediction error by region, season, pollutant, and concentration range"
    - "the instrument predicts pollution but may directly affect health through meteorology, smoke, heat, disruption, or co-pollutants"
    - "mortality and morbidity coding choices are not aligned with the claimed mechanism or ICD vintage"
    - "hospital-discharge data are interpreted as disease incidence without addressing access, coding, insurance, and admission thresholds"
    - "the claimed sensitive subpopulation is not defined before estimation or is discovered from multiple subgroup searches"
    - "avoidance behavior is ignored even though pollution warnings, AC, evacuation, medication, and activity changes are first-order"
  minimal_empirical_section_checklist:
    - "define pollutant, exposure window, health outcome, population at risk, and biological mechanism before presenting the design"
    - "state whether the exposure measure is ambient concentration, predicted outdoor concentration, or individual exposure proxy"
    - "document monitor assignment rules, monitor completeness thresholds, monitor types, distance restrictions, and monitor entry or exit"
    - "for satellite fusion, report product, version, overpass timing, quality screens, calibration model, held-out validation, and missingness"
    - "show first-stage strength and reduced form for wind, inversion, wildfire, transport, or upwind/downwind designs"
    - "control or test direct meteorological channels: temperature, humidity, precipitation, pressure, wind speed, inversions, smoke, and seasonality"
    - "separate all-cause mortality, cause-specific mortality, admissions, emergency visits, repeat visits, and spending"
    - "handle ICD-9 to ICD-10 transitions, diagnosis-position rules, age restrictions, and enrollment definitions"
    - "pre-specify sensitive subpopulations and report baseline rates, exposure distributions, and multiple-testing discipline"
    - "discuss avoidance and sorting using residence history, AC penetration, income, warnings, mobility, or bounding exercises where possible"
  claims_to_downgrade:
    - "downgrade 'individual exposure' to 'ambient outdoor exposure proxy' unless time-location or personal exposure information is observed"
    - "downgrade 'causal pollutant-specific health effect' when the design cannot separate co-pollutants and meteorological channels"
    - "downgrade 'mortality incidence' when the estimate may include short-run harvesting or mortality displacement"
    - "downgrade 'morbidity incidence' when the outcome is hospital use and access or coding may change"
    - "downgrade 'satellite-measured exposure' to 'satellite-fused predicted exposure' when AOD or trace-gas retrievals are calibrated with models"
    - "downgrade 'effect on vulnerable groups' when subgroup definitions are post hoc or baseline risk and exposure distributions are not shown"
```

## Domain reasoning steps

- Name the pollutant, health endpoint, affected population, and exposure window before choosing the design.
- Distinguish ambient outdoor concentration from individual exposure and inhaled dose.
- Assign monitors using pollutant-specific rules and document distance, monitor type, completeness, entry, exit, and exceptional-event handling.
- For satellite-fused exposure, track the product, retrieval variable, overpass time, quality flags, calibration model, held-out validation, and missingness pattern.
- For wind, inversion, wildfire, transport, or upwind/downwind instruments, write the first-stage physics before the exclusion restriction.
- Separate direct meteorological channels from pollution channels, especially heat, humidity, wind speed, precipitation, smoke, and seasonality.
- Match health coding to mechanism: all-cause mortality, cardiovascular mortality, respiratory admissions, asthma ED visits, birth outcomes, or spending.
- Treat hospital discharge as utilization unless access, admission threshold, coding, and payer coverage are addressed.
- Model avoidance explicitly when public warnings, AC, masks, evacuation, indoor time, medications, or mobility changes are plausible.
- Mark current data schemas, satellite product versions, ICD coding rules, and access restrictions as live_lookup_required.

## Forbidden claims

- Do not call ambient outdoor concentration individual exposure without time-location, indoor, residence, or personal-monitor evidence.
- Do not treat nearest-monitor assignment as harmless without sensitivity to monitor distance, monitor type, and monitor entry or exit.
- Do not treat satellite-fused predictions as raw observed pollution.
- Do not use wildfire smoke, inversions, wind direction, or transport as instruments without discussing direct health and co-pollutant channels.
- Do not claim pollutant-specific effects when PM2.5, ozone, NO2, smoke, heat, and humidity move together and are not separated.
- Do not interpret hospital admissions as disease incidence without addressing access, coding, and utilization margins.
- Do not combine ICD-9 and ICD-10 cause codes without documenting crosswalk and break handling.
- Do not claim sensitive-subpopulation effects from post hoc subgroup searches.
- Do not ignore avoidance behavior when pollution warnings, indoor time, evacuation, or AC are plausible.
- Do not make long-run health claims from short-run pollution shocks without addressing mortality displacement, adaptation, and migration.

## Candidate outputs

- `pollution_health_plan` YAML block.
- Candidate workflows and methods.
- Required diagnostics and robustness plan.
- Forbidden claim list.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
pollution_exposure_design:
  pollutant_candidates: []
  exposure_source: monitor | remote_sensing | emissions_inventory | facility_distance | mixed | unknown
  matching_strategy_candidates: []
  endogeneity_risks: []
  iv_candidates: []
  placebo_checks: []
  weather_controls_needed: []
  spatial_se_needed: true | false | unknown
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- Key risks include: exposure misclassification, avoidance behavior, migration, monitor placement, health selection.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not claim `PM2.5 exposure` has a causal effect until artifacts and claim_gate.json allow it.
- Do not skip measurement, timing, support, and backend caveats.

## Handoff to code

- Draft and validate specs; run backend discovery; run diagnostics; write artifact manifests and claim gate.

## Handoff from code artifacts

- Read claim_gate.json, status.json, artifact_manifest.json, reviewer_risk.json, diagnostics, and model tables before any result language.

## Minimal examples

### Input

User: Does PM2.5 affect labor supply?

### Expected skill output

```yaml
skill_name: pollution_exposure_and_health
user_question_summary: "PM2.5 and labor supply."
research_domain: pollution_health
research_brief:
  unit: worker_or_city
  time_frequency: day_or_month
  outcome_candidates: [labor_supply, hospital_visits]
  treatment_or_exposure: pm25
  estimand_candidates: [exposure_response]
pollution_exposure_design:
  pollutant_candidates: [PM2.5]
  exposure_source: monitor
  matching_strategy_candidates: [nearest_monitor, inverse_distance_weighting, grid_to_area]
  endogeneity_risks: [avoidance_behavior, monitor_placement, migration]
  iv_candidates: [wind_direction, upwind_pollution]
  placebo_checks: [future_pollution, unaffected_outcome]
  weather_controls_needed: [temperature, precipitation, wind]
  spatial_se_needed: true
candidate_workflows: [pollution_panel_spec]
candidate_methods: [panel_fe, iv_if_valid]
required_diagnostics: [exposure_match_audit, weather_control_check]
recommended_robustness: [alternative_matching_radius, placebo_outcome]
forbidden_claims: [do_not_treat_monitor_match_as_true_personal_exposure]
claim_language:
  allowed: ["Pollution exposure design proposed."]
  disallowed: ["Pollution causally reduced labor supply."]
uncertainty_notes: [Need exposure source metadata.]
next_code_actions: [validate_exposure_mapping]
```

## Completion checklist

- Fixed sections are present.
- Output is YAML or JSON.
- Forbidden claims are listed.
- Handoff to code and handoff from artifacts are explicit.
- claim_gate.json controls all strong claims.
- Unsupported backends and volatile facts are not overclaimed.
- Minimal example includes input and YAML output.
