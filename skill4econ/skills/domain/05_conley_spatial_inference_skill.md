# Skill: conley_spatial_inference

## Purpose

Plan spatial inference sensitivity for clustered or spatially correlated environmental panels.

This skill is a prompt/rubric layer, not an estimator, validator, backend
installer, or artifact certifier.

## When to use

- The user asks about spatially correlated errors in environmental, ESG, low-carbon, or finance research.
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
    - "Conley (1999), 'GMM Estimation with Cross Sectional Dependence'"
    - "Conley (2008), 'Spatial Econometrics' in The New Palgrave Dictionary of Economics"
    - "Newey and West (1987), 'A Simple, Positive Semi-definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix'"
    - "Driscoll and Kraay (1998), 'Consistent Covariance Matrix Estimation with Spatially Dependent Panel Data'"
    - "Bertrand, Duflo, and Mullainathan (2004), 'How Much Should We Trust Differences-in-Differences Estimates?'"
    - "Cameron, Gelbach, and Miller (2011), 'Robust Inference with Multiway Clustering'"
    - "Cameron and Miller (2015), 'A Practitioner's Guide to Cluster-Robust Inference'"
    - "Abadie, Athey, Imbens, and Wooldridge (2017), 'When Should You Adjust Standard Errors for Clustering?'"
    - "MacKinnon and Webb (2017), 'Wild Bootstrap Inference for Wildly Different Cluster Sizes'"
    - "Ibragimov and Müller (2010), 't-Statistic Based Correlation and Heterogeneity Robust Inference'"
    - "Young (2019), 'Channeling Fisher: Randomization Tests and the Statistical Insignificance of Seemingly Significant Experimental Results'"
  canonical_data_sources:
    - "unit latitude/longitude from source administrative records, facility registries, survey geocodes, or GIS boundary centroids"
    - "Census TIGER/Line and NHGIS boundary files for tract, county, block-group, and commuting-zone geometries"
    - "EPA FRS, AQS, NEI, TRI, CEMS, and ECHO geocodes when environmental units are facilities, monitors, or regulated sources"
    - "NOAA, PRISM, gridMET, Daymet, ERA5, and related gridded weather or pollution-exposure panels when spatial correlation follows meteorology"
    - "USGS NHD and WBD when spatial dependence follows river or watershed systems rather than Euclidean distance"
    - "LODES commuting flows, road networks, or market links when dependence follows networks rather than geography"
    - "EPSG coordinate reference definitions and PROJ transformations for distance-preserving projection choices"
  live_lookup_required_for:
    - "current software implementations, defaults, kernels, distance formulas, finite-sample corrections, and package version behavior"
    - "current CRS definitions, EPSG codes, datum transformations, and projection metadata"
    - "current boundary vintages, centroid definitions, geocode precision flags, and coordinate-quality fields"
    - "current package names and syntax for Conley, spatial-HAC, Driscoll-Kraay, multiway cluster, wild-bootstrap, and randomization-inference routines"
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "spatial-HAC variance: Conley covariance estimator with distance-based kernel and finite spatial cutoff"
    - "distance metric: great-circle distance from latitude/longitude, projected Euclidean distance in an appropriate CRS, network distance, travel-time distance, or hydrologic distance"
    - "kernel choice: uniform cutoff, Bartlett or triangular decay, quadratic spectral or other HAC kernel where implemented"
    - "spatial cutoff: fixed kilometers, policy-relevant exposure radius, empirical residual-correlation range, variogram-informed range, or sensitivity grid"
    - "temporal correlation: no time correction, Newey-West lag correction, panel HAC with temporal lags, Driscoll-Kraay correction, or two-way clustering by unit and time"
    - "comparison inference: heteroskedastic-robust SE, one-way cluster, two-way cluster, Conley spatial-HAC, Driscoll-Kraay, block bootstrap, wild cluster bootstrap, and randomization inference"
    - "spatial unit: point coordinate, polygon centroid, population-weighted centroid, source-weighted centroid, grid-cell center, monitor location, facility stack/outfall coordinate, or administrative capital"
    - "bandwidth sensitivity table: coefficient, standard error, t-statistic, p-value, and confidence interval reported across several spatial cutoffs and temporal lags"
  validation_targets:
    - "coordinates are in a documented CRS and are not mixed across latitude/longitude, projected meters, miles, and kilometers"
    - "distance matrix uses the same units as the stated cutoff"
    - "spatial cutoff is compared with the empirical residual-correlation range and substantive exposure scale"
    - "temporal lag length is justified by panel frequency, serial correlation, treatment timing, and outcome persistence"
    - "bandwidth sensitivity table shows whether inference is stable across plausible spatial cutoffs"
    - "small-sample behavior is checked when there are few spatial clusters, few treated units, sparse regions, or unbalanced panels"
    - "Conley results are compared with cluster, two-way cluster, and randomization-inference alternatives when assignment is clustered or randomized"
    - "spatial-HAC correction is applied after the same estimating equation, sample, weights, fixed effects, and residualization as the main specification"
  known_mismeasurement_channels:
    - "lat/lon degrees are angular units and cannot be used as if they were meters or kilometers in Euclidean buffer calculations"
    - "polygon centroids can place exposure outside the actual population or economic activity, especially for large counties, coastal units, or irregular borders"
    - "administrative centroids can misrepresent units when population, facilities, monitors, or treatment sites are spatially concentrated"
    - "wrong CRS or datum transformation changes distance rankings, neighbor sets, and cutoff inclusion"
    - "edge effects arise when nearby units outside the study region are omitted from the covariance calculation"
    - "distance-based cutoffs can miss network, watershed, wind, market, or commuting dependence"
    - "large cutoffs can absorb most pairwise residual covariance and behave poorly in small samples"
    - "small cutoffs can leave relevant spatial correlation untreated and understate uncertainty"
    - "temporal correlation can remain even when spatial correlation is corrected"
    - "software implementations differ in kernels, finite-sample corrections, panel handling, singleton treatment, and positive-semidefinite adjustments"
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "Conley corrects inference for spatially correlated errors; it does not create exogenous treatment variation"
    - "spatial correlation in residuals is not evidence of causal spillovers"
    - "causal spillovers require an exposure mapping or interference model, not only spatial-HAC standard errors"
    - "misspecified treatment assignment, sorting, siting, omitted spatial trends, and contaminated controls remain identification threats after Conley correction"
    - "cutoff choice can change standard errors enough to alter inference when residual dependence is long-range or sample size is small"
    - "temporal serial correlation can make Conley-only standard errors anti-conservative in panels"
    - "few treated clusters, uneven spatial density, and highly leveraged units can produce misleading asymptotic approximations"
    - "spatial-HAC inference can be unstable when the number of independent spatial regions is small"
  sorting_vs_siting_or_selection_channel:
    - "units near one another share markets, amenities, infrastructure, weather, regulation, demographics, and historical shocks"
    - "polluting facilities, roads, schools, hospitals, firms, and households are spatially sorted before treatment"
    - "policy adoption and enforcement can be spatially clustered because of regional politics, regulators, industry composition, or local shocks"
    - "nearby untreated units can be contaminated controls if treatment affects air, water, labor markets, product markets, housing, commuting, or information"
    - "spatially correlated outcomes can reflect omitted gradients rather than residual dependence around a valid identifying design"
  why_method_not_magic:
    - "Conley is an inference correction, not an identification design"
    - "robust Conley standard errors do not imply robust causal identification"
    - "changing the covariance estimator cannot fix endogenous treatment, bad controls, omitted spatial shocks, or invalid instruments"
    - "a spatial cutoff is a tuning parameter, not proof of the true spillover radius"
    - "larger standard errors do not validate the estimand; smaller standard errors do not validate exogeneity"
    - "cluster and two-way cluster corrections may be more appropriate when assignment is grouped by administrative unit or time shock"
    - "randomization inference may be more appropriate when treatment assignment comes from an explicit randomized or quasi-random assignment rule"
    - "spatial-HAC correction should be matched to the dependence process, not selected only because it preserves significance"
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "the paper uses Conley standard errors as if they solve spatial sorting or endogenous exposure"
    - "the spatial cutoff is arbitrary and no bandwidth sensitivity table is reported"
    - "coordinates are latitude/longitude but distances appear to be computed as planar Euclidean distances"
    - "temporal correlation is ignored in a panel with persistent outcomes or staggered treatment"
    - "spatial correlation is confused with causal spillovers"
    - "Conley inference is reported without comparison to cluster, two-way cluster, wild bootstrap, or randomization inference"
    - "sample has few treated regions or sparse spatial support, making asymptotic spatial-HAC behavior questionable"
    - "boundary, centroid, or geocode choices change neighbor sets but are not documented"
  minimal_empirical_section_checklist:
    - "state that Conley is used only for inference and does not identify the treatment effect"
    - "report coordinate source, coordinate quality, CRS, distance formula, distance units, and projection choice"
    - "justify the main spatial cutoff using residual correlation, exposure physics, market geography, commuting range, or institutional geography"
    - "show a bandwidth sensitivity table across multiple spatial cutoffs and, for panels, multiple temporal lags"
    - "compare heteroskedastic-robust, one-way cluster, two-way cluster, Conley, and randomization-inference or bootstrap results where applicable"
    - "document whether the kernel is uniform, Bartlett, or another HAC kernel and whether finite-sample corrections are applied"
    - "address serial correlation separately from spatial correlation in panel settings"
    - "discuss small-sample risks when treated units, spatial clusters, or independent regions are few"
    - "separate discussion of spatial correlation in errors from discussion of causal spillovers or partial interference"
    - "keep the identifying assumptions in the design section, not in the standard-error section"
  claims_to_downgrade:
    - "downgrade 'spatially robust identification' to 'standard errors adjusted for spatial correlation'"
    - "downgrade 'spillover evidence' when the only evidence is that Conley standard errors differ from clustered standard errors"
    - "downgrade 'results are robust' when only one Conley cutoff is shown"
    - "downgrade 'spatial dependence handled' when temporal serial correlation remains untreated"
    - "downgrade 'distance-based inference is appropriate' when dependence follows networks, watersheds, wind fields, or markets rather than Euclidean distance"
    - "downgrade 'precisely estimated' when small-sample behavior, few treated clusters, or leverage is not examined"
```

## Domain reasoning steps

- Separate the design from inference: first state the source of identifying variation, then state that Conley adjusts the covariance matrix for spatial dependence.
- Define the spatial unit used in the variance estimator: point, centroid, monitor, facility, grid cell, polygon centroid, or weighted centroid.
- Verify coordinates, CRS, datum, distance units, and projection before computing distances.
- Choose the main cutoff from the residual-correlation range, exposure physics, market geography, commuting radius, policy geography, or institutional scale.
- Report a bandwidth sensitivity table with several spatial cutoffs; in panels, cross spatial cutoffs with temporal lags.
- Treat temporal correlation separately using panel HAC, lag corrections, cluster by unit, cluster by time, or two-way clustering as appropriate.
- Compare Conley with cluster, two-way cluster, wild-bootstrap, Driscoll-Kraay, and randomization-inference results when those map to the assignment process.
- Diagnose small-sample fragility when treated units, spatial clusters, or effective independent regions are few.
- Keep spillovers conceptually separate: causal spillovers require exposure mapping or interference assumptions, not only spatial-HAC errors.
- Mark current software defaults, CRS metadata, and package implementation details as live_lookup_required.

## Forbidden claims

- Do not say Conley identifies the causal effect.
- Do not say robust Conley standard errors imply robust causal identification.
- Do not say spatial correlation is causal spillover evidence.
- Do not use Conley standard errors to excuse endogenous sorting, endogenous siting, invalid instruments, or contaminated controls.
- Do not compute planar Euclidean distances from raw latitude/longitude degrees.
- Do not report only one spatial cutoff when inference is bandwidth-sensitive.
- Do not ignore temporal serial correlation in panels.
- Do not claim Conley is always preferred to clustering, two-way clustering, wild bootstrap, or randomization inference.
- Do not treat a larger Conley standard error as proof the design is conservative.
- Do not treat a significant coefficient under Conley standard errors as evidence that the identifying assumptions are valid.

## Candidate outputs

- `conley_inference_plan` YAML block.
- Candidate workflows and methods.
- Required diagnostics and robustness plan.
- Forbidden claim list.

## Output schema

Return YAML or JSON. Do not omit the base fields.

```yaml
spatial_inference_plan:
  coordinates_available: unknown | true | false
  suggested_cutoffs: []
  kernel_candidates: []
  panel_dimension_notes: []
  cluster_comparison_needed: true | false | unknown
  sensitivity_table_required: true
  forbidden_claims: []
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any causal, structural, paper-ready, legal, audit-grade, or backend-certified claim must be allowed by claim_gate.json.
- If claim_gate.json or required artifacts are missing, report claim readiness as unknown or blocked.
- For volatile policy, regulation, standard, API, and data-source facts, query official/latest sources at use time.
- Key risks include: coordinate CRS, distance cutoff choice, unbalanced panels, spatial clustering, not a structural model.

## Forbidden claims

- Do not bypass claim_gate.json.
- Do not turn diagnostic_success into paper-ready causal success.
- Do not turn parser-only, interface-only, or missing-dependency output into a live backend result.
- Do not present unsupported fallback estimators as equivalent substitutes.
- Do not claim `spatially correlated errors` has a causal effect until artifacts and claim_gate.json allow it.
- Do not skip measurement, timing, support, and backend caveats.
- Do not call reduced-form spatial exposure a structural SAR/SDM indirect effect.

## Handoff to code

- Draft and validate specs; run backend discovery; run diagnostics; write artifact manifests and claim gate.

## Handoff from code artifacts

- Read claim_gate.json, status.json, artifact_manifest.json, reviewer_risk.json, diagnostics, and model tables before any result language.

## Minimal examples

### Input

User: My cities are spatially clustered; how should inference be checked?

### Expected skill output

```yaml
skill_name: conley_spatial_inference
user_question_summary: "Spatially clustered city panel inference."
research_domain: spatial_inference
research_brief:
  unit: city
  time_frequency: year
  outcome_candidates: [pollution]
  treatment_or_exposure: policy
  estimand_candidates: [ATT]
spatial_inference_plan:
  coordinates_available: unknown
  suggested_cutoffs: [50km, 100km, 200km]
  kernel_candidates: [uniform, bartlett]
  panel_dimension_notes: [check_time_frequency_and_balance]
  cluster_comparison_needed: true
  sensitivity_table_required: true
  forbidden_claims: [do_not_call_cluster_only_spatially_robust]
candidate_workflows: [spatial_se_comparison]
candidate_methods: [cluster_sensitivity, cutoff_grid]
required_diagnostics: [coordinate_crs_check, cutoff_sensitivity]
recommended_robustness: [alternative_cutoffs]
forbidden_claims: [respect_claim_gate]
claim_language:
  allowed: ["Inference sensitivity plan."]
  disallowed: ["Conley-certified inference before code runs."]
uncertainty_notes: [Need coordinates and CRS.]
next_code_actions: [run_spatial_se_comparison]
```

## Completion checklist

- Fixed sections are present.
- Output is YAML or JSON.
- Forbidden claims are listed.
- Handoff to code and handoff from artifacts are explicit.
- claim_gate.json controls all strong claims.
- Unsupported backends and volatile facts are not overclaimed.
- Minimal example includes input and YAML output.
