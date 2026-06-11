# Skill: climate_exposure_design

## Purpose

Plan exposure designs for temperature, precipitation, drought, flood, heatwave, wind, and other climate shocks.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- The user asks about high temperature exposure in environmental, ESG, low-carbon, or finance research.
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
    - "Schlenker, Hanemann, and Fisher (2005), 'Will U.S. Agriculture Really Benefit from Global Warming? Accounting for Irrigation in the Hedonic Approach'"
    - "Deschenes and Greenstone (2007), 'The Economic Impacts of Climate Change: Evidence from Agricultural Output and Random Fluctuations in Weather'"
    - "Schlenker and Roberts (2009), 'Nonlinear Temperature Effects Indicate Severe Damages to U.S. Crop Yields under Climate Change'"
    - "Hsiang (2010), 'Temperatures and Cyclones Strongly Associated with Economic Production in the Caribbean and Central America'"
    - "Deschenes and Greenstone (2011), 'Climate Change, Mortality, and Adaptation: Evidence from Annual Fluctuations in Weather in the US'"
    - "Dell, Jones, and Olken (2012), 'Temperature Shocks and Economic Growth: Evidence from the Last Half Century'"
    - "Auffhammer, Hsiang, Schlenker, and Sobel (2013), 'Using Weather Data and Climate Model Output in Economic Analyses of Climate Change'"
    - "Graff Zivin and Neidell (2014), 'Temperature and the Allocation of Time: Implications for Climate Change'"
    - "Burke, Hsiang, and Miguel (2015), 'Global Non-Linear Effect of Temperature on Economic Production'"
    - "Barreca, Clay, Deschenes, Greenstone, and Shapiro (2016), 'Adapting to Climate Change: The Remarkable Decline in the U.S. Temperature-Mortality Relationship over the Twentieth Century'"
    - "Carleton et al. (2022), 'Valuing the Global Mortality Consequences of Climate Change Accounting for Adaptation Costs and Benefits'"
  canonical_data_sources:
    - "PRISM Climate Group: gridded U.S. daily and monthly temperature and precipitation"
    - "ERA5 / ERA5-Land: ECMWF global reanalysis for temperature, precipitation, humidity, radiation, wind, and related atmospheric fields"
    - "Daymet: North American gridded daily surface weather and derived variables"
    - "gridMET: CONUS gridded daily meteorology combining PRISM with NLDAS"
    - "CMIP model output: global climate-model simulations and projections, including scenario-based future climate fields"
    - "NOAA GHCN-Daily and GHCN-Monthly: station-level weather observations"
    - "CRU TS and Berkeley Earth: gridded historical climate products for global long panels"
    - "NLDAS: North American land-surface forcing fields useful for humidity, radiation, wind, and soil-moisture-related checks"
  live_lookup_required_for:
    - "current PRISM, Daymet, gridMET, ERA5, ERA5-Land, GHCN, and CMIP version numbers and download endpoints"
    - "current CMIP generation, scenario labels, ensemble availability, model-membership rules, and bias-correction products"
    - "current data-access licensing, deprecations, variable names, calendars, units, and missing-value conventions"
    - "current heat-index or wet-bulb formula recommended for the jurisdiction or health agency being cited"
    - "current gridded population, cropland, building, or administrative-boundary files used for exposure weighting"
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "weather shock: realized short-run deviation in daily, monthly, seasonal, or annual weather from a unit-specific climatology"
    - "climate exposure: long-run distribution of weather states or projected future distribution from climate-model output"
    - "temperature level: daily mean, maximum, minimum, hourly approximation, monthly mean, growing-season mean, or annual mean"
    - "temperature bins: counts of days in mutually exclusive bins such as below 0C, 0-10C, 10-20C, 20-30C, 30-35C, and above 35C"
    - "degree days: growing degree days, harmful degree days, cooling degree days, heating degree days, and crop- or sector-specific threshold exposure"
    - "splines and thresholds: piecewise linear splines, restricted cubic splines, quadratic forms, and threshold exceedance days"
    - "precipitation: daily total, monthly total, seasonal total, dry-day count, extreme precipitation days, drought index, snow-water equivalent where relevant"
    - "humidity and heat stress: relative humidity, specific humidity, dew point, wet-bulb temperature, vapor pressure deficit, heat index, and apparent temperature"
    - "seasonal timing: crop calendar windows, school-year windows, labor-shift timing, gestational exposure windows, wildfire season, and monsoon timing"
    - "grid-to-unit aggregation: area-weighted, population-weighted, cropland-weighted, employment-weighted, nighttime-residence-weighted, or exposure-surface-weighted aggregation"
  validation_targets:
    - "temperature distributions reproduce station-based climatology for the units and years used in estimation"
    - "bin counts sum to the intended number of days in the temporal window after calendar and leap-day handling"
    - "precipitation totals and extreme-day counts match source units and aggregation conventions"
    - "humidity, heat index, and wet-bulb measures use physically consistent temperature, pressure, and humidity variables"
    - "grid-to-unit aggregation weights match the economic population at risk: people, crops, firms, schools, workers, or land"
    - "daily weather dates align with local time, crop calendars, gestational windows, and administrative outcome dates"
    - "historical weather product choice is tested against at least one station, reanalysis, or alternative gridded product when feasible"
    - "CMIP projections are bias-corrected or otherwise reconciled with the historical weather product before projection exercises"
  known_mismeasurement_channels:
    - "coarse grids smooth extremes and attenuate threshold effects"
    - "station interpolation can perform poorly in mountains, coasts, deserts, snow zones, and data-sparse regions"
    - "reanalysis products are model-data hybrids and can inherit model assumptions, especially for precipitation and humidity"
    - "precipitation is spatially intermittent and generally measured with more error than temperature"
    - "daily mean temperature can hide damaging maximum-temperature or nighttime-minimum-temperature exposure"
    - "area-weighted exposure can mismatch population exposure in urban, coastal, irrigated, or spatially concentrated units"
    - "current residence can mismeasure exposure when people commute, migrate seasonally, work outdoors, or spend time indoors"
    - "administrative boundaries, gridded weather cells, and economic decision units may not share spatial support"
    - "calendar-year aggregation can hide biologically or economically relevant seasonal timing"
    - "CMIP ensemble spread, scenario choice, downscaling, bias correction, and model dependence can dominate projected impacts"
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "historical weather shocks identify short-run responses, not automatically long-run climate damages"
    - "temperature, precipitation, humidity, seasonality, air pollution, wildfire smoke, and economic shocks can co-move"
    - "adaptation changes the dose-response through air conditioning, irrigation, crop switching, work timing, migration, building quality, and public health responses"
    - "migration and selective survival change the exposed population and can make panel composition endogenous"
    - "seasonal aggregation can put exposure outside the relevant biological, production, or behavioral window"
    - "spatial correlation and serial correlation can make conventional standard errors misleading"
    - "nonlinear response functions can be sensitive to sparse support in extreme bins"
    - "climate projections extrapolate beyond historical support for hot, humid, compound, or persistent events"
    - "grid-to-unit aggregation choices can change both treatment intensity and interpretation of the estimand"
  sorting_vs_siting_or_selection_channel:
    - "people, firms, crops, infrastructure, and housing capital are sorted across climates before the panel begins"
    - "hotter places differ in income, institutions, energy access, health systems, crop mix, irrigation, and industrial composition"
    - "migration after shocks changes who remains exposed and who is observed in outcome data"
    - "crop planting dates, school calendars, work shifts, and technology adoption are selected responses to expected seasonal climate"
    - "population-weighted exposure estimates an effect for where people live; cropland-weighted exposure estimates an effect for where crops grow; employment-weighted exposure estimates an effect for where work occurs"
  why_method_not_magic:
    - "unit and time fixed effects do not convert weather coefficients into climate-change damages without assumptions about adaptation and extrapolation"
    - "temperature bins are flexible approximations, not structural proof of thresholds"
    - "splines can overfit tails when extreme-temperature support is thin"
    - "including precipitation controls does not solve humidity, radiation, wildfire, air pollution, or disaster confounding"
    - "CMIP projections are not randomized treatments; projection exercises inherit scenario, model, downscaling, and bias-correction assumptions"
    - "population weights do not solve endogenous migration or differential avoidance"
    - "clustered standard errors at administrative units may not address spatially correlated weather shocks across neighboring units"
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "the paper labels the estimate climate exposure, but the research design identifies short-run weather-shock responses"
    - "temperature bins, splines, or thresholds are chosen without support, tail counts, or sensitivity to alternative bin definitions"
    - "precipitation, humidity, heat index, wet-bulb temperature, or seasonal timing is omitted despite being relevant to the outcome"
    - "the grid-to-unit aggregation weights do not match the population, crop, firm, or worker exposure concept"
    - "adaptation, migration, air conditioning, irrigation, crop switching, or work shifting is mentioned but not measured or bounded"
    - "projection results use CMIP output without model ensemble rules, bias correction, historical validation, or scenario caveats"
    - "standard errors ignore spatial and serial correlation in weather"
    - "the effect is extrapolated outside historical support for extreme heat, humid heat, drought, or compound events"
  minimal_empirical_section_checklist:
    - "state whether the estimand is a short-run weather response, a medium-run adaptation response, or a projected climate exposure effect"
    - "name the weather product, version, variables, units, spatial resolution, temporal resolution, and calendar convention"
    - "define temperature bins, splines, thresholds, precipitation measures, humidity measures, and heat-index formula before estimation"
    - "show grid-to-unit aggregation formula and weights: area, population, cropland, employment, school enrollment, or residence"
    - "report support in each temperature bin or spline segment by unit, season, and estimation sample"
    - "align exposure windows to agronomic, health, labor, school, gestational, or mortality timing"
    - "include sensitivity to alternative weather products such as PRISM versus Daymet/gridMET or station versus reanalysis where feasible"
    - "separate temperature, precipitation, humidity, and seasonal timing rather than treating climate as a scalar"
    - "test adaptation heterogeneity using air conditioning, irrigation, income, urbanization, crop mix, baseline climate, or historical exposure"
    - "describe clustering, spatial HAC, block bootstrap, or randomization-inference choices for spatially correlated weather"
    - "for CMIP projections, state scenarios, models, ensemble handling, bias correction, baseline period, and extrapolation limits"
  claims_to_downgrade:
    - "downgrade 'climate change causes' to 'historical weather variation implies' unless projection and adaptation assumptions are explicit"
    - "downgrade 'temperature effect' when the proxy is daily mean but the mechanism is maximum heat, nighttime heat, wet-bulb stress, or heat index"
    - "downgrade 'heat exposure' when humidity or heat-index components are unavailable and only dry-bulb temperature is measured"
    - "downgrade 'national exposure' when aggregation is area-weighted but the affected population is spatially concentrated"
    - "downgrade 'adaptation effect' when the design only compares baseline hot and cold places without observing adaptive capital or behavior"
    - "downgrade 'future damages' when estimates rely on historical support that excludes projected extreme bins"
```

## Domain reasoning steps

- Classify the design as weather-shock estimation, climate-exposure description, or projection of historical dose-response under future climate.
- Define the economic unit at risk: person, county, crop, grid cell, school, firm, worker, building, or market.
- Choose the weather variable to match the mechanism: maximum heat for acute heat stress, minimum temperature for nighttime recovery, degree days for crops or energy, precipitation timing for agriculture, humidity or wet-bulb for physiological heat stress.
- Build daily exposure first, then aggregate to biologically or economically relevant windows.
- Use bins, splines, or thresholds only after checking support in the tails and reporting omitted-bin interpretation.
- Include precipitation, humidity, and heat-index measures when the mechanism involves water stress, humid heat, labor productivity, mortality, or disease.
- Aggregate grid cells to units with weights that match the outcome denominator: population for mortality, cropland for crop yields, employment for labor, and area only when land exposure is the estimand.
- Distinguish short-run weather responses from long-run climate adaptation; do not make climate-damage claims without adaptation and projection assumptions.
- Test timing and adaptation margins: migration, air conditioning, irrigation, crop switching, work hours, seasonal calendars, and baseline climate.
- For CMIP exercises, validate historical weather alignment, specify model/scenario/ensemble rules, and mark current model availability as live_lookup_required.

## Forbidden claims

- Do not call a weather-shock coefficient a climate-change effect without stating adaptation and projection assumptions.
- Do not say fixed effects solve climate adaptation, migration, or sorting.
- Do not treat daily mean temperature as equivalent to maximum heat, minimum heat, heat index, or wet-bulb exposure.
- Do not use temperature bins without reporting the omitted bin, bin support, and tail sparsity.
- Do not claim threshold effects when the threshold is chosen after looking at outcomes.
- Do not ignore precipitation, humidity, or seasonal timing when the mechanism requires them.
- Do not area-weight exposure for population health, labor, or crop outcomes unless area exposure is the estimand.
- Do not mix PRISM, ERA5, Daymet, gridMET, station data, and CMIP projections without reconciling units, calendars, resolution, and bias correction.
- Do not extrapolate beyond historical support without labeling it as extrapolation.
- Do not present CMIP scenario results as forecasts rather than conditional projections.

## Candidate outputs

- `climate_exposure_plan` YAML block.
- Candidate workflows and methods.
- Required diagnostics and robustness plan.
- Forbidden claim list.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
climate_exposure_design:
  exposure_type: temperature | precipitation | drought | flood | storm | mixed | unknown
  proposed_exposure_variables: []
  aggregation_unit: null
  time_frequency: null
  lag_structure_candidates: []
  nonlinear_spec_candidates: []
  adaptation_checks: []
  spatial_inference_needed: true | false | unknown
  measurement_error_notes: []
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- Key risks include: weather measurement error, adaptation, nonlinear dose response, seasonality, spatial correlation.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not claim `high temperature exposure` has a causal effect until artifacts and claim_gate.json allow it.
- Do not skip measurement, timing, support, and backend caveats.

## Handoff to code

- Draft and validate specs; run backend discovery; run diagnostics; write artifact manifests and claim gate.

## Handoff from code artifacts

- Read claim_gate.json, status.json, artifact_manifest.json, reviewer_risk.json, diagnostics, and model tables before any result language.

## Minimal examples

### Input

User: Does high temperature reduce manufacturing output?

### Expected skill output

```yaml
skill_name: climate_exposure_design
user_question_summary: "High temperature and manufacturing output."
research_domain: climate_exposure
research_brief:
  unit: firm
  time_frequency: day_or_month
  outcome_candidates: [output, employment, energy_demand]
  treatment_or_exposure: temperature
  estimand_candidates: [dose_response, distributed_lag_effect]
climate_exposure_design:
  exposure_type: temperature
  proposed_exposure_variables: [daily_mean_temperature, heatwave_days]
  aggregation_unit: firm_location
  time_frequency: day_or_month
  lag_structure_candidates: [same_period, distributed_lag]
  nonlinear_spec_candidates: [temperature_bins, splines]
  adaptation_checks: [cooling_access_proxy, historical_climate_bins]
  spatial_inference_needed: true
  measurement_error_notes: [weather_station_or_grid_matching]
candidate_workflows: [climate_panel_spec]
candidate_methods: [fixed_effect_panel, nonlinear_bins]
required_diagnostics: [weather_match_check, seasonal_balance]
recommended_robustness: [alternative_temperature_source, lag_window_sensitivity]
forbidden_claims: [do_not_ignore_adaptation_or_spatial_correlation]
claim_language:
  allowed: ["Exposure design drafted."]
  disallowed: ["Temperature effect certified."]
uncertainty_notes: [Need weather source and aggregation rule.]
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
