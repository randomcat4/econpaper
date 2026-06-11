# Skill: spatial_exposure_design

## Purpose

Plan reduced-form spatial exposure designs using neighbor treatment, distance rings, buffers, and contaminated-control checks.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- The user asks about neighbor treatment exposure in environmental, ESG, low-carbon, or finance research.
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
    - "Anselin (1988), 'Spatial Econometrics: Methods and Models'"
    - "Cliff and Ord (1981), 'Spatial Processes: Models and Applications'"
    - "Conley (1999), 'GMM Estimation with Cross Sectional Dependence'"
    - "Kelejian and Prucha (1998), 'A Generalized Spatial Two-Stage Least Squares Procedure for Estimating a Spatial Autoregressive Model with Autoregressive Disturbances'"
    - "Case (1991), 'Spatial Patterns in Household Demand'"
    - "Topa (2001), 'Social Interactions, Local Spillovers and Unemployment'"
    - "Keller and Levinson (2002), 'Pollution Abatement Costs and Foreign Direct Investment Inflows to U.S. States'"
    - "Black (1999), 'Do Better Schools Matter? Parental Valuation of Elementary Education'"
    - "Holmes (1998), 'The Effect of State Policies on the Location of Manufacturing: Evidence from State Borders'"
    - "Currie, Davis, Greenstone, and Walker (2015), 'Environmental Health Risks and Housing Values: Evidence from 1,600 Toxic Plant Openings and Closings'"
    - "Heblich, Trew, and Zylberberg (2021), 'East-Side Story: Historical Pollution and Persistent Neighborhood Sorting'"
    - "Hsiang (2010), 'Temperatures and Cyclones Strongly Associated with Economic Production in the Caribbean and Central America'"
  canonical_data_sources:
    - "EPA Facility Registry Service (FRS), NEI, TRI, AQS, CEMS, RSEI, ECHO, and Superfund/NPL geospatial records for environmental-source locations"
    - "Census TIGER/Line and NHGIS boundary files for tracts, counties, block groups, roads, and historical geography"
    - "LEHD Origin-Destination Employment Statistics (LODES) for commuting flows"
    - "Bureau of Transportation Statistics, FHWA HPMS, OpenStreetMap, and TIGER roads for road-network exposure"
    - "USGS National Hydrography Dataset (NHD) and Watershed Boundary Dataset (WBD) for river, stream, and watershed networks"
    - "NOAA, NARR, ERA5, HRRR, and other meteorological wind fields for directional exposure and transport"
    - "BEA input-output tables, Compustat segment data, FactSet/Revere where licensed, and firm supplier-customer disclosures for supply-chain exposure"
    - "EPA EJSCREEN and ACS for population, housing, income, race, age, and baseline vulnerability covariates"
    - "MODIS, Landsat, NLCD, VIIRS, and building-footprint products for land cover, night lights, and spatial validation"
  live_lookup_required_for:
    - "current TIGER/Line, NHGIS, ACS, EJSCREEN, LODES, HPMS, NHD, and WBD vintages and variable definitions"
    - "current EPA geospatial datasets, facility coordinates, retired IDs, and source-status flags"
    - "current CRS definitions, datum transformations, road-network releases, watershed versions, and boundary changes"
    - "current supply-chain database coverage, licensing, firm identifiers, and public disclosure rules"
    - "current spatial product versions for MODIS, Landsat, NLCD, VIIRS, building footprints, and road networks"
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "buffer exposure: any source within radius, count of sources within radius, emissions-weighted source count, distance-to-nearest source, inverse-distance-weighted exposure, or ring-specific exposure"
    - "distance decay: linear distance, log distance, inverse distance, inverse-square distance, kernel decay, flexible bins, plume-weighted distance, travel-time distance, or network distance"
    - "wind exposure: downwind indicator, wind-frequency-weighted source exposure, pollution-rose exposure, seasonal wind transport, or source-receptor matrix"
    - "watershed exposure: upstream facility count, upstream emissions, flow-distance-weighted exposure, hydrologic unit exposure, downstream treatment, or drainage-area-weighted exposure"
    - "road exposure: distance to highway, traffic volume within buffer, truck-route exposure, road-density measure, network travel time, or dispersion-adjusted road pollution"
    - "commuting exposure: origin-residence exposure, workplace exposure, commute-path exposure, LODES-flow-weighted exposure, or time-weighted daily activity exposure"
    - "supply-chain exposure: direct supplier exposure, customer exposure, input-output-sector exposure, firm-network centrality exposure, or shipment-route exposure"
    - "partial-interference exposure: own treatment, neighbor treatment, spillover intensity, treated-neighbor count, network-weighted treatment, and exposure mapping by distance or adjacency"
    - "contaminated controls: untreated units inside exposure radius, downwind untreated units, same-market untreated units, upstream/downstream linked controls, and commuting-linked controls"
    - "spatial model object: exposure construction by geography or network versus spatial autoregressive lag, spatial error process, or spatial HAC correction"
  validation_targets:
    - "coordinates are projected into an appropriate CRS before distance, area, buffer, or network calculations"
    - "boundaries match the outcome year or are harmonized to a stable vintage before panel construction"
    - "buffer, ring, and distance-decay choices reproduce known exposure gradients or monitoring evidence where available"
    - "wind and watershed links follow physical directionality rather than Euclidean proximity alone"
    - "road and commuting exposure use plausible routes, traffic volumes, workplace locations, and time allocation"
    - "supply-chain links are contemporaneous with the shock and do not use future supplier-customer relationships"
    - "edge units near borders, coastlines, missing facilities, or dataset coverage limits are flagged and tested"
    - "partial-interference exposure mappings are reported separately from own-treatment status and control definition"
  known_mismeasurement_channels:
    - "latitude-longitude distances are wrong for buffers unless transformed to a suitable projected CRS"
    - "boundary vintage changes create false exposure changes through tract splits, county changes, annexations, or coastline edits"
    - "facility coordinates may point to headquarters, parcel centroids, permit offices, stacks, outfalls, or approximate ZIP centroids"
    - "buffers ignore wind, topography, stack height, hydrology, traffic, commuting, and network flows"
    - "distance-to-nearest-source ignores source intensity, timing, emissions composition, and multiple-source exposure"
    - "network exposure can be endogenous if commuting, supply chains, or routes respond to treatment"
    - "controls can be contaminated by spillovers through air, water, roads, markets, commuting, or supply chains"
    - "edge effects arise when sources outside the study region, upstream watershed, market, or road network are unobserved"
    - "spatial smoothing can mechanically spread treatment into controls and attenuate effects"
    - "spatial econometric lags can mix exposure, behavioral spillovers, correlated shocks, and reflection problems"
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "spatial exposure is rarely as-good-as-random because people, firms, sources, roads, and amenities are colocated through markets and policy"
    - "near-source exposure is confounded by land prices, zoning, race, income, industrial history, transportation access, and public services"
    - "buffer definitions can select treated and control units mechanically and produce arbitrary treatment discontinuities"
    - "spillovers create partial interference, so untreated nearby units may not be valid controls"
    - "spatially correlated shocks violate independent error assumptions and can make naive standard errors too small"
    - "network exposure can be endogenous when commuting flows, supply chains, roads, or residential locations respond to the shock"
    - "boundary discontinuities can identify policy borders but not local exposure effects if agents sort around the boundary"
    - "measurement error in coordinates, CRS, or boundary harmonization can dominate estimated treatment variation"
  sorting_vs_siting_or_selection_channel:
    - "polluting facilities, roads, warehouses, ports, and industrial corridors are sited where land is cheaper and political resistance is lower"
    - "households sort by housing costs, schools, amenities, jobs, pollution, race, income, and information"
    - "firms sort by transport access, input suppliers, labor pools, regulation, zoning, and agglomeration economies"
    - "commuters choose jobs, residences, and routes jointly, so commuting-network exposure is a behavioral equilibrium"
    - "suppliers and customers match endogenously by productivity, geography, contracts, sector, and firm size"
    - "administrative boundaries reflect historical settlement, politics, annexation, and service provision, not random partitions"
  why_method_not_magic:
    - "buffers are exposure-construction devices, not identification strategies"
    - "distance decay is not causal unless siting, sorting, and omitted spatial gradients are addressed"
    - "border designs are not magic if units sort around borders, policies spill over, or boundaries coincide with other discontinuities"
    - "spatial fixed effects do not solve omitted gradients that vary within the fixed-effect cell or change over time"
    - "spatial lag models do not distinguish spillovers from correlated shocks, reflection, or omitted network structure by default"
    - "Conley or spatial-HAC standard errors adjust inference but do not fix biased exposure construction"
    - "network weights do not solve endogenous networks unless the network is predetermined or instrumented"
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "the exposure buffer is arbitrary and not justified by physics, behavior, monitoring, hydrology, traffic, commuting, or supply-chain logic"
    - "the paper treats exposure construction as if it were a spatial econometric identification model"
    - "controls are contaminated because they lie inside plausible spillover, market, watershed, road, wind, commuting, or supply-chain networks"
    - "coordinates, CRS, and boundary vintages are undocumented and may create mechanical exposure changes"
    - "distance decay is assumed rather than validated against monitors, emissions, traffic, flow, or observed outcomes"
    - "partial interference is ignored even though treatment of one unit changes outcomes for nearby or network-linked units"
    - "sorting and siting explain exposure gradients more plausibly than the treatment effect"
    - "spatial correlation is handled only by clustering at an arbitrary administrative level"
  minimal_empirical_section_checklist:
    - "state the spatial estimand: own exposure, neighbor spillover, market spillover, network exposure, or total effect"
    - "name the exposure support: Euclidean space, wind field, watershed, road network, commuting network, supply-chain network, or administrative boundary"
    - "document geocoding source, coordinate precision, CRS, datum, boundary vintage, and harmonization rules"
    - "justify buffers, rings, distance decay, or network weights using source physics, behavior, or institutional knowledge"
    - "separate own-treatment exposure from spillover exposure and define contaminated controls before estimation"
    - "show sensitivity to buffer radii, decay functions, boundary vintages, edge exclusions, and coordinate quality restrictions"
    - "test sorting and siting using baseline demographics, housing, land values, industry, roads, historical pollution, and pretrends"
    - "report inference robust to spatial and network correlation at the relevant exposure scale"
    - "for watershed, road, wind, commuting, or supply-chain networks, show that links are predetermined or plausibly exogenous to treatment"
    - "distinguish exposure construction choices from spatial lag, spatial error, or spatial-HAC modeling choices"
  claims_to_downgrade:
    - "downgrade 'local exposure effect' to 'association with constructed proximity measure' when siting and sorting are not addressed"
    - "downgrade 'spillover effect' when the design only includes neighbor treatment without a defined exposure mapping"
    - "downgrade 'unexposed controls' when controls are inside plausible air, water, road, market, commuting, or supply-chain spillover range"
    - "downgrade 'distance-gradient effect' when distance is measured with wrong CRS, low-quality coordinates, or unstable boundaries"
    - "downgrade 'network effect' when the network is measured after treatment or responds to the treatment"
    - "downgrade 'spatial model solves dependence' when only standard errors or spatial lags are added after exposure is mismeasured"
```

## Domain reasoning steps

- Define the spatial object before regression: point source, polygon, grid cell, road segment, watershed, wind field, commuting edge, supply-chain edge, or administrative unit.
- Decide whether the estimand is own exposure, neighbor spillover, total exposure, market exposure, network exposure, or partial-interference exposure.
- Project coordinates into a suitable CRS before distance, area, buffer, and network calculations.
- Match boundary vintage to outcome timing or harmonize units to a stable geography before constructing exposure.
- Choose buffers, rings, kernels, or decay functions from physics, hydrology, traffic, commuting behavior, supply-chain timing, or monitoring evidence.
- Separate exposure construction from the spatial econometric model; a spatial lag or spatial-HAC correction is not a substitute for a credible exposure measure.
- Identify contaminated controls before estimation, especially units linked by wind, watersheds, roads, commuting, markets, or suppliers.
- Diagnose endogenous sorting and siting using baseline demographics, housing markets, land use, industry, roads, historical pollution, and pretrends.
- Stress-test edge effects from study boundaries, missing sources, coastlines, upstream omissions, road-network truncation, and cross-border markets.
- Mark current CRS, boundary, road, watershed, facility, and network dataset vintages as live_lookup_required.

## Forbidden claims

- Do not call a buffer an identification strategy.
- Do not compute distances or buffers in unprojected latitude-longitude coordinates.
- Do not ignore CRS, datum, boundary vintage, or edge effects.
- Do not call controls unexposed when they are linked through air, water, roads, commuting, markets, or supply chains.
- Do not assume partial interference away when spillovers are physically or economically plausible.
- Do not interpret distance decay causally without addressing siting, sorting, and omitted spatial gradients.
- Do not use future commuting or supply-chain links to define historical exposure.
- Do not treat a spatial lag model as proof of spillovers.
- Do not use spatially robust standard errors as a fix for endogenous exposure.
- Do not merge spatial datasets without documenting geocoding precision, coordinate quality, and boundary harmonization.

## Candidate outputs

- `spatial_exposure_plan` YAML block.
- Candidate workflows and methods.
- Required diagnostics and robustness plan.
- Forbidden claim list.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
spatial_exposure_design:
  mechanism: pollution_transport | policy_diffusion | industrial_relocation | technology_diffusion | supply_chain | financial_network | unknown
  W_candidates:
    - name: string
      reason: string
      required_metadata: []
  exposure_definition_candidates: []
  diagnostics_required:
    - W_dimension_check
    - W_unit_order_check
    - row_standardization_check
    - islands_check
    - exposed_controls_check
    - W_sensitivity
  claim_level: reduced_form_by_default
  forbidden_claims: []
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- Key risks include: W matrix choice, contaminated controls, reflection/endogenous sorting, ordinary SE not spatial HAC by default.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not claim `neighbor treatment exposure` has a causal effect until artifacts and claim_gate.json allow it.
- Do not skip measurement, timing, support, and backend caveats.
- Do not call reduced-form spatial exposure a structural SAR/SDM indirect effect.

## Handoff to code

- Draft and validate specs; run backend discovery; run diagnostics; write artifact manifests and claim gate.

## Handoff from code artifacts

- Read claim_gate.json, status.json, artifact_manifest.json, reviewer_risk.json, diagnostics, and model tables before any result language.

## Minimal examples

### Input

User: Do treated cities spill over to neighboring cities?

### Expected skill output

```yaml
skill_name: spatial_exposure_design
user_question_summary: "Neighbor spillovers from treated cities."
research_domain: spatial_exposure
research_brief:
  unit: city
  time_frequency: year
  outcome_candidates: [pollution]
  treatment_or_exposure: neighbor_treatment
  estimand_candidates: [local_ATT, reduced_form_neighbor_exposure]
spatial_exposure_design:
  mechanism: pollution_transport
  W_candidates:
    - name: contiguity_or_distance_W
      reason: "Represent nearby exposure, not structural spatial equilibrium."
      required_metadata: [unit_order, row_standardization, islands]
  exposure_definition_candidates: [W_times_treatment, distance_rings, buffer_exclusion]
  diagnostics_required: [W_dimension_check, W_unit_order_check, row_standardization_check, islands_check, exposed_controls_check, W_sensitivity]
  claim_level: reduced_form_by_default
  forbidden_claims: [do_not_call_W_treatment_SDM_indirect_effect]
candidate_workflows: [spatial_spillover_run]
candidate_methods: [spatial_exposure_did, spatial_w_audit]
required_diagnostics: [W_audit, exposed_controls_check]
recommended_robustness: [alternative_W, buffer_deletion]
forbidden_claims: [respect_claim_gate]
claim_language:
  allowed: ["Reduced-form spatial exposure only."]
  disallowed: ["Structural spillover effect."]
uncertainty_notes: [Need W metadata.]
next_code_actions: [run_spatial_w_audit]
```

## Completion checklist

- Fixed sections are present.
- Output is YAML or JSON.
- Forbidden claims are listed.
- Handoff to code and handoff from artifacts are explicit.
- claim_gate.json controls all strong claims.
- Unsupported backends and volatile facts are not overclaimed.
- Minimal example includes input and YAML output.
