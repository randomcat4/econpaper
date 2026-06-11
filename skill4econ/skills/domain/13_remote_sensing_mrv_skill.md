# Skill: remote_sensing_mrv

## Purpose

Plan scholar-grade remote-sensing MRV and satellite-proxy research for pollution, emissions, economic activity, land use, vegetation, fire, smoke, heat, climate exposure, flooding, water extent, and environmental monitoring.

This skill focuses on the measurement model before any causal, policy, financial, MRV, or certification claim. Satellite variables are proxies, retrievals, classifications, or exposure measures with spatial, temporal, atmospheric, calibration, aggregation, and missingness error.

It is a prompt and research-design rubric. It does not run estimators, validate backends, certify artifacts, provide audit-grade assurance, or certify environmental, legal, regulatory, compliance, or emissions-reporting conclusions.

Always read these shared rules before using this skill:

- `../_shared/01_claim_language_rules.md`
- `../_shared/02_evidence_lookup_rules.md`
- `../_shared/03_artifact_reading_rules.md`
- `../_shared/04_spec_drafting_rules.md`
- `../_shared/05_forbidden_fallbacks.md`
- `../_shared/06_reviewer_mode_rules.md`
- `../_shared/07_scholarly_depth_rules.md`
- `../_shared/08_domain_literature_anchor_rules.md`

Any causal, paper-ready, backend-certified, legal, audit-grade, assurance, compliance, or emissions-certification claim must be supported by code artifacts and `claim_gate.json`.

## When to use

Use this skill when satellite, aerial, raster, or gridded data enter a research design as proxy, exposure, outcome, validation source, or MRV input, including:

- Sentinel, MODIS, VIIRS, Landsat, or other official or research product families;
- night lights as a proxy for luminosity, activity, electrification, urbanization, or economic intensity;
- aerosol optical depth, or AOD, as an aerosol-column optical proxy related to particulate pollution or smoke only after a defended measurement model;
- NO2 retrievals as atmospheric-column or related retrieval proxies for combustion, traffic, industrial activity, or pollution only after a defended measurement model;
- land cover, land use, vegetation indices, burn scars, thermal anomalies, fire detections, smoke, surface temperature, water extent, flooding, or urban expansion;
- grid-to-area aggregation for counties, cities, firms, facilities, plants, concessions, census units, watersheds, airsheds, buffers, or administrative areas;
- calibration against ground monitors, inventories, surveys, facility reports, field measurements, or administrative records.

Product families, APIs, collections, processing levels, bands, algorithms, QA flags, coverage, revisit intervals, and official documentation change over time. Require official/latest lookup at use time for product-specific details.

## Do not use when

Do not use this skill when:

- the user only needs to run an already validated remote-sensing pipeline;
- the task is purely software engineering without a measurement or research-design question;
- the user asks for audit-grade emissions verification, legal compliance, regulatory certification, or assurance conclusions;
- the user wants to treat a satellite proxy as true ground-level pollution, true firm emissions, true GDP, or certified MRV measurement without validation;
- product-specific facts would need to be hardcoded instead of looked up from official/latest sources at use time.

Use a causal-inference or policy-evaluation skill in addition to this one when the satellite variable is part of a treatment-effect design.

## Inputs expected

- Research question, intended claim, unit of analysis, sample window, and time frequency.
- Proxy target: pollution, emissions, economic activity, land use, vegetation, fire or smoke, heat, flood or water, or other environmental condition.
- Candidate remote-sensing variable: night lights, AOD, NO2, land cover, vegetation index, fire detection, burned area, surface temperature, water extent, or other raster or retrieval variable.
- Candidate product family or source, with official/latest lookup at use time: Sentinel, MODIS, VIIRS, Landsat, or other official or research product.
- Spatial requirements: native pixel size, target grid, coordinate reference system, area boundaries, buffers, area weights, and boundary changes.
- Temporal requirements: overpass, daily, weekly, monthly, seasonal, annual, event-window timing, time-zone conversion, and compositing.
- Measurement constraints: spatial resolution, temporal resolution, cloud cover, missingness, retrieval error, QA flags, orbital or track coverage, atmospheric conditions, sensor changes, saturation, stray light, snow, surface reflectance, aerosol interference, and meteorology when relevant.
- Calibration and validation source: ground monitors, emissions inventories, administrative records, facility reports, field measurements, surveys, or independent satellite products.
- Existing pipeline artifacts, manifests, diagnostics, or claim-gate outputs when interpreting completed work.

## Required repo artifacts to inspect

Inspect workspace files first. Do not rely on installed user-level skills as the authority for this repository.

Repository structure and contracts: `README.md`, `registry.yml`, `cli.py`, `core.py`, `python_wrappers.py`, `workflows.py`, `docs/ARTIFACT_CONTRACT.md` when present, `docs/BACKEND_CONTRACT.md` when present, `diagnostics/`, `tests/fixtures/`, and `tests/backends/`.

Shared rules: `skills/_shared/01_claim_language_rules.md`, `skills/_shared/02_evidence_lookup_rules.md`, `skills/_shared/03_artifact_reading_rules.md`, `skills/_shared/04_spec_drafting_rules.md`, `skills/_shared/05_forbidden_fallbacks.md`, `skills/_shared/06_reviewer_mode_rules.md`, and `skills/_shared/07_scholarly_depth_rules.md`.

Run artifacts when a run exists: remote-sensing product manifest, raster preprocessing manifest, QA and missingness report, grid-to-area aggregation manifest, calibration or validation manifest, `status.json`, `manifest.json` or `artifact_manifest.json`, `diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json` or `backend_status.json`, `model_table.csv`, and `claim_gate.json`.

If these artifacts are absent, measurement, validation, causal, policy, MRV, audit, assurance, compliance, or emissions-certification claims must be marked as unknown, partial, exploratory, or blocked as appropriate.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Hansen et al. (2013), Science, High-Resolution Global Maps of 21st-Century Forest Cover Change"
    - "Olofsson et al. (2014), Remote Sensing of Environment, Good Practices for Estimating Area and Assessing Accuracy of Land Change"
    - "Baccini et al. (2012), Nature Climate Change, Estimated Carbon Dioxide Emissions from Tropical Deforestation Improved by Carbon-Density Maps"
    - "Saatchi et al. (2011), Proceedings of the National Academy of Sciences, Benchmark Map of Forest Carbon Stocks in Tropical Regions"
    - "Zhu and Woodcock (2014), Remote Sensing of Environment, Continuous Change Detection and Classification of Land Cover"
    - "Varon et al. (2018), Atmospheric Measurement Techniques, Quantifying Methane Point Sources from Fine-Scale Satellite Observations"
    - "GFOI (2020), Methods and Guidance Documentation for REDD+ Measurement, Reporting and Verification"
  canonical_data_sources:
    - "Varon et al. (2018), Atmospheric Measurement Techniques, Quantifying Methane Point Sources from Fine-Scale Satellite Observations"
    - "current classifier model version"
    - "current training-label source"
    - "current imagery archive"
    - "current ground-truth dataset version"
    - "current validation-site metadata"
    - "aggregation changes estimand"
    - "mixed pixels blur treatment boundaries"
    - "facility coordinates may not match emission sources"
    - "current validation dataset"
  live_lookup_required_for:
    - "current Global Forest Change release and sensor-processing version"
    - "current biomass-map version and uncertainty layer"
    - "current remote-sensing biomass product vintage"
    - "current Landsat collection and preprocessing version"
    - "current methane-satellite product version and retrieval algorithm"
    - "latest GFOI guidance edition"
    - "current REDD+ MRV requirements"
    - "current satellite product version"
    - "current retrieval algorithm"
    - "current quality flags"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Hansen et al. (2013), Science, High-Resolution Global Maps of 21st-Century Forest Cover Change"
    use_for: "global forest-cover loss measurement, pixel-level land-cover change, resolution and classification limits"
    live_lookup_required: ["current Global Forest Change release and sensor-processing version"]

    citation: "Olofsson et al. (2014), Remote Sensing of Environment, Good Practices for Estimating Area and Assessing Accuracy of Land Change"
    use_for: "accuracy assessment, validation samples, confusion matrices, area-adjusted estimates"
    live_lookup_required: []

    citation: "Baccini et al. (2012), Nature Climate Change, Estimated Carbon Dioxide Emissions from Tropical Deforestation Improved by Carbon-Density Maps"
    use_for: "forest carbon stocks, emissions from deforestation, biomass-map uncertainty"
    live_lookup_required: ["current biomass-map version and uncertainty layer"]

    citation: "Saatchi et al. (2011), Proceedings of the National Academy of Sciences, Benchmark Map of Forest Carbon Stocks in Tropical Regions"
    use_for: "aboveground biomass mapping, satellite-field data fusion, carbon-stock uncertainty"
    live_lookup_required: ["current remote-sensing biomass product vintage"]

    citation: "Zhu and Woodcock (2014), Remote Sensing of Environment, Continuous Change Detection and Classification of Land Cover"
    use_for: "time-series classification, temporal change detection, compositing and break detection"
    live_lookup_required: ["current Landsat collection and preprocessing version"]

    citation: "Varon et al. (2018), Atmospheric Measurement Techniques, Quantifying Methane Point Sources from Fine-Scale Satellite Observations"
    use_for: "satellite methane retrievals, plume detection, wind-field dependence, validation requirements"
    live_lookup_required: ["current methane-satellite product version and retrieval algorithm"]

    citation: "GFOI (2020), Methods and Guidance Documentation for REDD+ Measurement, Reporting and Verification"
    use_for: "forest MRV, activity data, emission factors, validation and uncertainty reporting"
    live_lookup_required: ["latest GFOI guidance edition", "current REDD+ MRV requirements"]
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "Retrieval"
    - "biophysical quantity inferred from sensor radiance or backscatter, such as NO2 column, methane enhancement, aerosol optical depth, vegetation index, biomass, land surface temperature"
    - "retrieval algorithm is not raw observation"
    - "vertical-column retrieval may not equal ground-level exposure"
    - "wind, surface reflectance, terrain, and instrument drift matter"
    - "Proxy"
    - "remote-sensing variable used as proxy for emissions, activity, enforcement, production, deforestation, flaring, crop stress, or pollution exposure"
    - "proxy can move for non-treatment reasons"
    - "light, greenness, plume, or heat signatures need domain validation"
    - "proxy-performance relationship may vary by region and season"
  validation_targets:
    - "proxy can move for non-treatment reasons"
    - "light, greenness, plume, or heat signatures need domain validation"
    - "proxy-performance relationship may vary by region and season"
    - "Validation ground truth"
    - "ground truth has its own measurement error"
    - "validation sites are selected"
    - "time mismatch between field and satellite observation biases accuracy"
    - "current ground-truth dataset version"
    - "current validation-site metadata"
    - "Measurement type"
  known_mismeasurement_channels:
    - "retrieval algorithm is not raw observation"
    - "vertical-column retrieval may not equal ground-level exposure"
    - "wind, surface reflectance, terrain, and instrument drift matter"
    - "proxy can move for non-treatment reasons"
    - "light, greenness, plume, or heat signatures need domain validation"
    - "proxy-performance relationship may vary by region and season"
    - "classifier error is spatially correlated"
    - "training labels can encode policy boundaries"
    - "domain shift across countries and years breaks accuracy"
    - "Cloud, snow, aerosol, and orbital missingness"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "Retrieval"
    measure: "biophysical quantity inferred from sensor radiance or backscatter, such as NO2 column, methane enhancement, aerosol optical depth, vegetation index, biomass, land surface temperature"
    pitfalls: ["retrieval algorithm is not raw observation", "vertical-column retrieval may not equal ground-level exposure", "wind, surface reflectance, terrain, and instrument drift matter"]
    live_lookup_required: ["current satellite product version", "current retrieval algorithm", "current quality flags"]

    item: "Proxy"
    measure: "remote-sensing variable used as proxy for emissions, activity, enforcement, production, deforestation, flaring, crop stress, or pollution exposure"
    pitfalls: ["proxy can move for non-treatment reasons", "light, greenness, plume, or heat signatures need domain validation", "proxy-performance relationship may vary by region and season"]
    live_lookup_required: ["current sensor calibration and product documentation"]

    item: "Classifier"
    measure: "land cover, facility activity, crop type, burn scar, mine expansion, road, flood, or deforestation label from supervised, semi-supervised, or LLM-assisted image classification"
    pitfalls: ["classifier error is spatially correlated", "training labels can encode policy boundaries", "domain shift across countries and years breaks accuracy"]
    live_lookup_required: ["current classifier model version", "current training-label source", "current imagery archive"]

    item: "Cloud, snow, aerosol, and orbital missingness"
    measure: "masked pixels, valid-observation count, revisit timing, cloud/snow/aerosol flags, sensor downtime"
    pitfalls: ["missingness is non-random in tropics, mountains, winter, fire seasons, and polluted regions", "treatment can affect observability through smoke, aerosols, or land-surface change"]
    live_lookup_required: ["current QA-mask definitions", "current cloud/snow/aerosol screening rules"]

    item: "Validation ground truth"
    measure: "field plots, monitors, inventories, aircraft campaigns, administrative records, manual labels, high-resolution imagery"
    pitfalls: ["ground truth has its own measurement error", "validation sites are selected", "time mismatch between field and satellite observation biases accuracy"]
    live_lookup_required: ["current ground-truth dataset version", "current validation-site metadata"]

    item: "Resolution mismatch"
    measure: "pixel size, point monitor, facility boundary, parcel, census tract, watershed, grid cell, administrative unit"
    pitfalls: ["aggregation changes estimand", "mixed pixels blur treatment boundaries", "facility coordinates may not match emission sources"]
    live_lookup_required: ["current geocoding, boundary, and raster product versions"]

    item: "Temporal compositing"
    measure: "daily, monthly, seasonal, annual, median, maximum, clear-sky, or best-pixel composites"
    pitfalls: ["compositing can hide events", "post-treatment observation frequency can change", "phenology and seasonality can mimic policy effects"]
    live_lookup_required: ["current compositing method and product calendar"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "treating a satellite-derived label as audited emissions"
    - "policy effects driven by changing observability rather than changing pollution or land cover"
    - "global product accuracy cited as if it applied to treated units"
    - "assigning pixel changes to the wrong plant, parcel, or community"
    - "claiming immediate effects from temporally smoothed products"
    - "mistaking targeted MRV visibility for causal treatment response"
  sorting_vs_siting_or_selection_channel:
    - "Temporal compositing and event timing"
    - "event-time windows aligned to observation dates"
    - "season-by-year controls"
    - "alternative compositing windows"
    - "raw-observation robustness"
    - "current product time stamps and compositing rules"
    - "pre-treatment imagery trends"
    - "targeting-rule controls"
  why_method_not_magic:
    - "A retrieval, a proxy, and a classifier label have different error structures and cannot be interpreted as the same MRV object."
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Retrieval versus proxy versus classifier"
    core_issue: "A retrieval, a proxy, and a classifier label have different error structures and cannot be interpreted as the same MRV object."
    acceptable_designs: ["declare measurement estimand", "validate against independent ground truth", "propagate measurement error", "triangulate with administrative records"]
    referee_risk: "treating a satellite-derived label as audited emissions"
    live_lookup_required: ["current product algorithm and validation documentation"]

    item: "Observed imagery endogeneity"
    core_issue: "Treatment status can affect whether pixels are observed, cloud-free, classified, monitored, or included in composites."
    acceptable_designs: ["valid-observation-count controls", "missingness event studies", "QA-mask robustness", "bounds for unobserved pixels"]
    referee_risk: "policy effects driven by changing observability rather than changing pollution or land cover"
    live_lookup_required: ["current QA flags and observation metadata"]

    item: "Validation and transferability"
    core_issue: "Classifier accuracy in one geography, season, sensor, or land-cover regime may not transfer to the study sample."
    acceptable_designs: ["local validation set", "spatial and temporal holdouts", "confusion-matrix correction", "class-specific precision/recall"]
    referee_risk: "global product accuracy cited as if it applied to treated units"
    live_lookup_required: ["current validation sample and product release notes"]

    item: "Resolution and boundary mismatch"
    core_issue: "Treatment units, emissions sources, and satellite pixels often differ in spatial scale."
    acceptable_designs: ["pre-specified aggregation rule", "buffer sensitivity", "mixed-pixel diagnostics", "facility-boundary overlays"]
    referee_risk: "assigning pixel changes to the wrong plant, parcel, or community"
    live_lookup_required: ["current raster resolution, boundary files, facility coordinates"]

    item: "Temporal compositing and event timing"
    core_issue: "Annual or seasonal composites can blur treatment timing, short-run shocks, and recovery dynamics."
    acceptable_designs: ["event-time windows aligned to observation dates", "season-by-year controls", "alternative compositing windows", "raw-observation robustness"]
    referee_risk: "claiming immediate effects from temporally smoothed products"
    live_lookup_required: ["current product time stamps and compositing rules"]

    item: "Treatment endogeneity in imagery"
    core_issue: "Policies, enforcement, and project placement often target visible degradation or detectable emissions."
    acceptable_designs: ["pre-treatment imagery trends", "targeting-rule controls", "matched untreated units", "boundary or threshold designs"]
    referee_risk: "mistaking targeted MRV visibility for causal treatment response"
    live_lookup_required: ["current targeting criteria and monitoring-program metadata"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Measurement type"
    - "Is the satellite variable identified as retrieval, proxy, or classifier output before causal interpretation?"
    - "Validation"
    - "Are independent ground truth, confusion matrices, precision/recall, and uncertainty reported for the study sample?"
    - "Missingness"
    - "Are cloud, snow, aerosol, smoke, sensor, orbit, and QA-mask missingness modeled rather than dropped silently?"
    - "Resolution"
    - "Are pixel, facility, parcel, monitor, and administrative-unit resolutions reconciled with sensitivity to aggregation?"
    - "Temporal alignment"
    - "Are observation dates, compositing windows, treatment dates, and seasonality aligned?"
  minimal_empirical_section_checklist:
    - "Measurement type"
    - "Is the satellite variable identified as retrieval, proxy, or classifier output before causal interpretation?"
    - "current product documentation"
    - "Validation"
    - "Are independent ground truth, confusion matrices, precision/recall, and uncertainty reported for the study sample?"
    - "current validation dataset"
    - "Missingness"
    - "Are cloud, snow, aerosol, smoke, sensor, orbit, and QA-mask missingness modeled rather than dropped silently?"
    - "current QA-mask rules"
    - "Resolution"
  claims_to_downgrade:
    - "Do not call a satellite retrieval, proxy, or classifier output audited MRV without independent validation."
    - "Do not ignore cloud, snow, aerosol, smoke, orbit, or QA-mask missingness."
    - "Do not use global product accuracy as study-sample accuracy without local or held-out validation."
    - "Do not assign pixel-level changes to facilities or communities without resolution and boundary checks."
    - "Do not infer treatment timing from annual or seasonal composites without temporal-alignment sensitivity."
    - "Do not treat observed imagery as exogenous when policy targeting or treatment affects observability."
    - "Do not make current claims about satellite products, retrieval algorithms, QA flags, biomass maps, methane products, Landsat/Sentinel/MODIS/VIIRS collections, or MRV standards without live lookup."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Measurement type"
    ask: "Is the satellite variable identified as retrieval, proxy, or classifier output before causal interpretation?"
    live_lookup_required: ["current product documentation"]

    check: "Validation"
    ask: "Are independent ground truth, confusion matrices, precision/recall, and uncertainty reported for the study sample?"
    live_lookup_required: ["current validation dataset"]

    check: "Missingness"
    ask: "Are cloud, snow, aerosol, smoke, sensor, orbit, and QA-mask missingness modeled rather than dropped silently?"
    live_lookup_required: ["current QA-mask rules"]

    check: "Resolution"
    ask: "Are pixel, facility, parcel, monitor, and administrative-unit resolutions reconciled with sensitivity to aggregation?"
    live_lookup_required: ["current raster and boundary versions"]

    check: "Temporal alignment"
    ask: "Are observation dates, compositing windows, treatment dates, and seasonality aligned?"
    live_lookup_required: ["current product calendar and compositing method"]

    check: "Endogenous observability"
    ask: "Could treatment change whether a location is imaged, classified, cloud-free, or selected for monitoring?"
    live_lookup_required: ["current monitoring and sampling metadata"]
```

## Forbidden claims

- Do not call a satellite retrieval, proxy, or classifier output audited MRV without independent validation.
- Do not ignore cloud, snow, aerosol, smoke, orbit, or QA-mask missingness.
- Do not use global product accuracy as study-sample accuracy without local or held-out validation.
- Do not assign pixel-level changes to facilities or communities without resolution and boundary checks.
- Do not infer treatment timing from annual or seasonal composites without temporal-alignment sensitivity.
- Do not treat observed imagery as exogenous when policy targeting or treatment affects observability.
- Do not make current claims about satellite products, retrieval algorithms, QA flags, biomass maps, methane products, Landsat/Sentinel/MODIS/VIIRS collections, or MRV standards without live lookup.

## Domain reasoning steps

1. Define the measurement estimand before choosing a product: proxy construction, ground-truth validation, exposure assignment, MRV screening, event response, or causal effect in a later design.
2. Separate the satellite observable from the latent target: night lights measure luminosity, AOD measures aerosol optical properties, NO2 retrievals measure atmospheric-column or related quantities, and classifications are algorithmic labels.
3. Require official/latest product lookup at use time for Sentinel, MODIS, VIIRS, Landsat, and other product families: collection, processing level, band or variable, resolution, revisit, QA flags, coverage, algorithm changes, known issues, and access method.
4. Specify spatial support: native pixel or grid, target unit, CRS, resampling, mixed pixels, geolocation error, boundary vintage, and whether the target unit is smaller than the observable support.
5. Block firm-, facility-, neighborhood-, or event-window claims when pixel size, geolocation error, temporal aggregation, mixed pixels, or boundary uncertainty make attribution weak.
6. Specify timing: overpass, local time, revisit frequency, compositing window, event window, seasonality, missing days, and alignment with pollution, emissions, activity, fire, land-use, or policy timing.
7. Model missingness and selection: clouds, snow, smoke, aerosols, orbital tracks, sun angle, surface reflectance, QA screening, instrument outages, and differential treatment-period observability.
8. For night lights, address saturation, blooming, stray light, lunar effects, gas flares, fishing fleets, sensor or processing changes, and non-economic lighting sources when relevant.
9. For AOD and NO2, address cloud screening, vertical profiles, meteorology, boundary-layer conditions, atmospheric transport, surface conditions, retrieval quality, and the gap between column retrievals and ground exposure or facility emissions.
10. Design grid-to-area aggregation: raster alignment, CRS, area weights, population or exposure weights, buffer rules, partial pixels, modifiable areal unit problems, and boundary changes.
11. For facility or firm attribution, state whether values are point extractions, buffer averages, administrative averages, airshed measures, or model-linked exposure; require buffer and weighting sensitivity.
12. Specify calibration and validation before strong measurement language: ground monitors, inventories, facility reports, field data, surveys, administrative records, holdout validation, or independent products.
13. Translate measurement error into identification risk: attenuation, nonclassical error from clouds or treatment timing, seasonality, urbanization, industrial composition, atmospheric transport, spatial autocorrelation, and repeated composites.
14. Match method to readiness: proxy construction only; proxy validation with ground truth; descriptive exposure mapping; event response only if timing and missingness support it; causal effect only with a separate design, diagnostics, artifacts, and `claim_gate.json`.
15. Identify diagnostics that block claims: missing product manifest, no QA filtering, high or differential missingness, no aggregation manifest, no ground-truth calibration for ground-pollution or emissions language, unsupported resolution, or missing/blocking `claim_gate.json`.
16. Rank robustness by measurement risk: alternative product or collection, QA thresholds, cloud/missingness rules, aggregation weights, buffer size, temporal composites, ground-truth validation, meteorological controls, and boundary vintage.
17. Anticipate referee objections: night lights are not GDP; AOD or NO2 are not firm emissions; clouds may be correlated with treatment; the target unit may be below resolution; aggregation may drive results; ground monitors may be sparse; product algorithms may change; atmospheric transport breaks local attribution.
18. Define downgrade triggers before reviewing results: proxy-only without calibration; area-level only when facility attribution is unsupported; exploratory association when missingness is unresolved; no event claim when timing is too coarse; no audit, compliance, certification, or causal claim without artifacts and `claim_gate.json`.

## Candidate outputs

- `remote_sensing_mrv_plan` YAML or JSON block.
- Product lookup and metadata checklist.
- Measurement model for the satellite observable and proxy target.
- Resolution, timing, missingness, QA, retrieval-error, and aggregation plan.
- Ground-truth calibration and validation plan.
- Diagnostics and robustness plan ranked by measurement risk.
- Safe claim-language block.
- Downgrade/refusal block for proxy overclaims, audit-grade claims, certification claims, or causal overclaims.

## Output schema

Return YAML by default, or JSON if requested. Do not omit the base fields.

```yaml
skill_name: remote_sensing_mrv
user_question_summary: string
research_domain: remote_sensing_mrv
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: null
  estimand_candidates: []
  identification_risks: []
remote_sensing_mrv_plan:
  remote_sensing_variable: []
  proxy_target: pollution | emissions | economic_activity | land_use | vegetation | fire_smoke | heat | flood_water | unknown
  product_family_candidates:
    - Sentinel
    - MODIS
    - VIIRS
    - Landsat
    - other_official_or_research_product
  official_latest_lookup_required: true
  resolution_requirements:
    spatial_resolution: []
    temporal_resolution: []
    support_check: []
  aggregation_strategy:
    source_grid: string
    target_area: string
    weighting: []
    boundary_and_crs_checks: []
    buffer_or_partial_pixel_rules: []
  calibration_needs: []
  measurement_error_risks: []
  validation_checks: []
  proxy_interpretation_limits:
    night_lights: string
    NO2: string
    AOD: string
    other: []
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

- This skill is a planning and review rubric, not an estimator, backend validator, artifact certifier, auditor, regulator, compliance reviewer, or assurance provider.
- Satellite variables are usually proxies, retrievals, classifications, or exposure measures; they are not automatically ground truth.
- Night lights do not equal GDP.
- NO2 and AOD do not equal true ground pollution, true exposure, or firm emissions without a defended measurement model, calibration, validation, and claim-gate support.
- A satellite proxy is not audit-grade MRV without official/latest standards, validation evidence, artifacts, and claim-gate support.
- Sentinel, MODIS, VIIRS, Landsat, and other product-family details must be checked from official/latest documentation at use time.
- Spatial resolution, temporal resolution, cloud cover, missingness, retrieval error, QA filtering, ground-truth calibration, and grid-to-area aggregation must be addressed before strong claims.
- Facility-, firm-, neighborhood-, or event-window claims require support checks showing product resolution and timing can identify the claimed unit and period.
- Grid-to-area aggregation choices can change results and must be documented.
- Atmospheric transport, meteorology, and vertical profiles can break local attribution for AOD and NO2.
- `claim_gate.json` and diagnostics control strong claim readiness.

## Forbidden claims

- Do not bypass `claim_gate.json`.
- Do not call night lights GDP.
- Do not call NO2 or AOD true ground pollution, true exposure, true firm emissions, or certified emissions without calibration and claim-gate support.
- Do not call satellite proxy output audit-grade, assurance-grade, certified, or compliance-ready MRV.
- Do not ignore cloud cover, missingness, orbital tracks, QA flags, spatial resolution, temporal resolution, retrieval error, calibration, atmospheric transport, or grid-to-area aggregation.
- Do not infer firm-level emissions from a coarse grid, column retrieval, night-light value, or administrative average without a defensible attribution model.
- Do not claim a policy or firm caused a satellite change until a separate causal design, diagnostics, artifacts, and `claim_gate.json` support the claim.
- Do not treat parser-only, interface-only, missing-dependency, or diagnostic-only output as a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not hardcode current product, API, algorithm, collection, processing-level, standard, regulatory, or access details.

## Handoff to code

Draft a concrete spec for code to validate:

- candidate product family and official/latest lookup requirement;
- product version or collection, variable or band name, and QA flags after lookup;
- native spatial resolution, target unit, temporal resolution, and compositing window;
- CRS, resampling method, raster alignment, grid-to-area aggregation, buffer rules, and partial-pixel rules;
- missingness, cloud-screening, retrieval-quality, meteorology, and seasonality diagnostics;
- calibration and validation data;
- panel, event, or causal design only if the measurement layer is adequate;
- artifact and claim-gate requirements.

Ask code to verify only what code can verify: file existence, metadata, CRS, raster alignment, aggregation, missingness, QA filters, backend availability, diagnostics, manifests, and claim-gate status. Do not ask code to certify emissions, legal compliance, audit assurance, or regulatory status.

## Handoff from code artifacts

Before writing strong language, inspect the remote-sensing product manifest, raster preprocessing manifest, QA and missingness report, grid-to-area aggregation manifest, calibration or validation report, `status.json`, `manifest.json` or `artifact_manifest.json`, `diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json` or `backend_status.json`, `model_table.csv`, and `claim_gate.json`.

Interpret artifacts conservatively:

- If product metadata are missing, do not make product-specific measurement claims.
- If QA or missingness diagnostics are missing, do not make clean trend or event claims.
- If aggregation artifacts are missing, do not make area-level exposure claims.
- If calibration artifacts are missing, call AOD, NO2, or night lights proxies only.
- If `claim_gate.json` blocks strong language, do not make causal, audit-grade, certified MRV, or compliance claims.

## Minimal examples

### Good planning example

User: "Can we use NO2, AOD, and night lights to study whether a low-emission zone reduced pollution and economic activity in treated districts?"

Expected skill output:

```yaml
skill_name: remote_sensing_mrv
user_question_summary: NO2, AOD, and night-light proxies in a district-level policy study
research_domain: remote_sensing_mrv
research_brief:
  unit: district_month
  time_frequency: monthly
  outcome_candidates: [NO2_proxy, AOD_proxy, night_lights_proxy]
  treatment_or_exposure: low_emission_zone_policy
  estimand_candidates: [proxy_validation, event_response, causal_policy_effect_if_design_and_claim_gate_allow]
  identification_risks: [differential_cloud_missingness, meteorology_confounding, spatial_spillovers, policy_selection, night_lights_not_GDP]
remote_sensing_mrv_plan:
  remote_sensing_variable: [NO2, AOD, night_lights]
  proxy_target: pollution
  product_family_candidates: [Sentinel, MODIS, VIIRS, Landsat, other_official_or_research_product]
  official_latest_lookup_required: true
  resolution_requirements:
    spatial_resolution: [native_pixel_size_from_official_latest_docs, district_support_check, mixed_pixel_risk_check]
    temporal_resolution: [observation_frequency_from_official_latest_docs, monthly_compositing_window, policy_timing_alignment]
    support_check: [district_area_relative_to_pixel_size, treated_control_coverage_balance]
  aggregation_strategy:
    source_grid: "Product-native grid after official/latest lookup."
    target_area: "District boundaries for the study period."
    weighting: [area_weighted_average, population_weighted_sensitivity_if_exposure_claim]
    boundary_and_crs_checks: [CRS_consistency, boundary_vintage_check, raster_alignment_check]
    buffer_or_partial_pixel_rules: [partial_pixel_documentation, boundary_or_buffer_sensitivity]
  calibration_needs: [ground_monitor_validation_for_NO2_or_AOD, meteorological_controls, independent_activity_validation_for_night_lights]
  measurement_error_risks: [cloud_missingness, retrieval_error, column_to_ground_gap, atmospheric_transport, night_light_saturation_or_blooming, sensor_or_algorithm_changes]
  validation_checks: [product_manifest_check, QA_filter_check, missingness_by_treatment_and_time, ground_truth_validation, aggregation_sensitivity]
  proxy_interpretation_limits:
    night_lights: "Luminosity/activity proxy, not GDP."
    NO2: "Atmospheric proxy requiring calibration before ground-pollution or emissions language."
    AOD: "Aerosol optical proxy requiring calibration before PM, smoke-exposure, or emissions language."
    other: []
  forbidden_claims: [NO2_equals_true_ground_pollution, AOD_equals_true_PM25_or_emissions, night_lights_equals_GDP, satellite_proxy_is_audit_grade_MRV]
candidate_workflows: [remote_sensing_product_lookup, raster_QA_and_missingness_pipeline, grid_to_district_aggregation, proxy_validation, causal_policy_design_only_after_measurement_diagnostics]
candidate_methods: [proxy_validation_against_ground_truth, descriptive_exposure_mapping, event_study_if_timing_and_missingness_support_it, modern_DID_only_if_claim_gate_supports_it]
required_diagnostics: [official_latest_product_documentation_check, spatial_support_check, temporal_support_check, cloud_missingness_by_treatment, retrieval_QA_summary, CRS_boundary_check, calibration_validation_report, claim_gate_status]
recommended_robustness: [alternative_product_or_collection, alternative_QA_thresholds, alternative_compositing_windows, population_vs_area_weighting, meteorological_controls, placebo_policy_dates]
claim_language:
  allowed: ["NO2 and AOD can be planned as satellite pollution proxies subject to calibration and missingness diagnostics.", "Night lights can be planned as a luminosity/activity proxy, not GDP."]
  disallowed: ["The satellite data prove firm emissions fell.", "Night lights show GDP declined.", "The proxy is audit-grade MRV."]
uncertainty_notes: ["Official/latest product documentation is required at use time."]
next_code_actions: [look_up_product_metadata, build_product_manifest, apply_QA_filters, compute_missingness_by_treatment, aggregate_grid_to_districts, validate_against_ground_truth]
scholarly_depth:
  estimand_definition: "District-month proxy response in satellite NO2, AOD, and night-light measures after the policy, with causal effects allowed only if a separate design is validated."
  identification_assumptions: [correct_policy_timing, comparable_counterfactual_trends, nondifferential_retrieval_quality_after_controls, spillovers_addressed_or_downgraded]
  measurement_model: [NO2_is_atmospheric_proxy, AOD_is_aerosol_optical_proxy, night_lights_measure_luminosity_not_GDP, district_values_are_weighted_raster_aggregates]
  data_construction_risks: [QA_filter_changes, cloud_missingness, boundary_mismatch, aggregation_sensitivity, sparse_ground_monitors]
  method_decision_tree: ["no validation data -> proxy construction only", "validation data and support -> proxy validation plus exposure mapping", "precise timing -> event response", "diagnostics and claim_gate pass -> causal design may be drafted"]
  diagnostics_that_block_claims: [missing_product_manifest, high_differential_cloud_missingness, no_QA_report, no_ground_truth_calibration, no_aggregation_manifest, claim_gate_missing_or_blocking]
  robustness_ranked_by_risk: [alternative_QA_filters, alternative_product_or_collection, missingness_adjustment, alternative_weights, alternative_temporal_composites, placebo_dates]
  referee_objections: [satellite_columns_may_not_represent_ground_exposure, night_lights_are_not_GDP, clouds_and_meteorology_may_drive_results, district_aggregation_hides_heterogeneity]
  downgrade_triggers: [no_calibration_to_proxy_language, differential_missingness_to_exploratory_claims, coarse_timing_to_no_event_claim, blocking_claim_gate_to_no_causal_claim]
not_recommended_methods: [OLS_or_DID_on_satellite_proxy_without_measurement_diagnostics, firm_emissions_inference_from_NO2_or_AOD_without_attribution_model, GDP_estimation_from_night_lights_without_validation]
```

### Downgrade and overclaim-block example

User: "Use VIIRS night lights and AOD to certify that a firm's emissions fell and that local GDP rose after its ESG program."

Expected skill output:

```yaml
skill_name: remote_sensing_mrv
user_question_summary: certify firm emissions and GDP from night lights and AOD
research_domain: remote_sensing_mrv
research_brief:
  unit: firm_or_local_area
  time_frequency: monthly_or_annual
  outcome_candidates: [night_lights_proxy, AOD_proxy]
  treatment_or_exposure: firm_ESG_program
  estimand_candidates: [proxy_exposure_or_activity_association]
  identification_risks: [satellite_proxy_not_audit_grade, AOD_not_firm_emissions, night_lights_not_GDP, local_attribution_problem, no_claim_gate_for_certification]
remote_sensing_mrv_plan:
  remote_sensing_variable: [night_lights, AOD]
  proxy_target: unknown
  product_family_candidates: [VIIRS, MODIS, Sentinel, Landsat, other_official_or_research_product]
  official_latest_lookup_required: true
  resolution_requirements:
    spatial_resolution: [official_latest_native_resolution_lookup, facility_or_local_area_support_check, mixed_pixel_and_buffer_check]
    temporal_resolution: [official_latest_observation_or_composite_frequency_lookup, ESG_program_timing_alignment_check]
    support_check: [firm_location_vs_pixel_size, local_area_boundary_check]
  aggregation_strategy:
    source_grid: "Night-light and AOD grids after official/latest lookup."
    target_area: "Firm buffer or local administrative area only if support is defensible."
    weighting: [area_weighting, buffer_sensitivity]
    boundary_and_crs_checks: [CRS_consistency, raster_alignment, boundary_vintage]
    buffer_or_partial_pixel_rules: [report_buffer_radius, test_alternative_buffers]
  calibration_needs: [emissions_inventory_or_stack_monitor_data_for_emissions_claims, ground_pollution_monitors_for_AOD_claims, local_economic_data_for_GDP_or_activity_claims]
  measurement_error_risks: [AOD_column_to_ground_gap, atmospheric_transport, cloud_missingness, night_light_saturation_or_non_economic_light, firm_attribution_error, ESG_program_selection]
  validation_checks: [product_manifest_check, QA_missingness_report, ground_truth_calibration, aggregation_sensitivity, local_confounder_check, claim_gate_status]
  proxy_interpretation_limits:
    night_lights: "Luminosity measure, not GDP."
    NO2: "Not used here; if added, still a proxy requiring calibration."
    AOD: "Aerosol optical proxy, not true firm emissions or certified ground pollution."
    other: []
  forbidden_claims: [certify_firm_emissions_reduction, night_lights_equal_GDP, AOD_equal_firm_emissions, audit_grade_MRV_claim]
candidate_workflows: [proxy_feasibility_review, measurement_validation_design, exploratory_area_level_association_if_supported]
candidate_methods: [descriptive_proxy_mapping, validation_against_ground_truth]
required_diagnostics: [official_latest_product_lookup, QA_filter_report, cloud_missingness_report, facility_buffer_support_check, calibration_data_availability, claim_gate_status]
recommended_robustness: [alternative_buffer_sizes, alternative_QA_filters, alternative_temporal_composites, validation_against_independent_ground_truth]
claim_language:
  allowed: ["The request can be reframed as a proxy feasibility and validation plan.", "AOD and night lights may support exploratory area-level proxy analysis if diagnostics pass."]
  disallowed: ["The firm's emissions fell.", "Local GDP rose.", "The ESG program is certified by satellite MRV."]
uncertainty_notes: ["Official/latest product documentation and validation data are required at use time."]
next_code_actions: [build_product_and_QA_manifest, check_facility_buffer_support, search_for_ground_truth_calibration_sources, generate_proxy_only_outputs_if_requested]
scholarly_depth:
  estimand_definition: "At most an area-level proxy change around a firm location; firm emissions, GDP, and certification are not identified from night lights and AOD alone."
  identification_assumptions: [no_certification_claim_supported, local_proxy_changes_not_attributed_to_firm_without_design, AOD_cannot_identify_firm_emissions_by_itself, night_lights_need_validation_before_GDP_language]
  measurement_model: [AOD_is_aerosol_optical_proxy, night_lights_are_luminosity_measures, firm_buffer_values_are_area_proxies_with_attribution_error]
  data_construction_risks: [buffer_choice_drives_results, cloud_missingness, non_firm_sources_in_same_pixel_or_airshed, local_economic_confounders, missing_ground_truth]
  method_decision_tree: ["no emissions inventory or stack data -> no firm-emissions claim", "no economic ground truth -> no GDP claim", "only satellite proxies -> exploratory proxy mapping", "certification request -> refuse or downgrade"]
  diagnostics_that_block_claims: [no_ground_truth_emissions_data, no_GDP_or_activity_validation_data, no_product_manifest, no_QA_missingness_report, claim_gate_missing_or_blocking]
  robustness_ranked_by_risk: [buffer_sensitivity, QA_filter_sensitivity, alternative_product_comparison, validation_against_ground_truth]
  referee_objections: [firm_cannot_be_isolated_from_other_sources, AOD_is_not_firm_emissions, night_lights_reflect_infrastructure_and_non_economic_light, ESG_adoption_is_endogenous]
  downgrade_triggers: [certification_language_blocked, emissions_claims_to_AOD_proxy_language, GDP_claims_to_night_light_proxy_language]
not_recommended_methods: [audit_grade_MRV_from_satellite_proxy_only, firm_emissions_claim_from_AOD_without_ground_truth_or_attribution_model, GDP_claim_from_night_lights_without_validation]
```

## Completion checklist

- Fixed sections are present.
- Shared rules `01` through `07` are cited, especially `../_shared/07_scholarly_depth_rules.md`.
- Output schema includes base fields, `remote_sensing_mrv_plan`, `scholarly_depth`, and `not_recommended_methods`.
- Sentinel, MODIS, VIIRS, and Landsat product families are covered with official/latest lookup at use time.
- Spatial resolution, temporal resolution, cloud/missingness, retrieval error, ground-truth calibration, and grid-to-area aggregation are covered.
- Night lights are treated as proxies, not GDP.
- AOD and NO2 are explicitly treated as proxies, not true ground pollution or firm emissions.
- Cloud, track, resolution, calibration, QA, atmospheric transport, and aggregation risks are not ignored.
- Domain reasoning includes estimand, measurement model, identification assumptions, diagnostics that block claims, robustness ranked by risk, referee objections, and downgrade triggers.
- Strong claims require code artifacts and `claim_gate.json`.
- Audit-grade MRV, compliance, legal, emissions-certification, and unsupported causal claims are blocked.
- Volatile product, API, collection, algorithm, standard, regulatory, and data-source details require official/latest lookup at use time.
