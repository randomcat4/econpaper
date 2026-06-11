# Skill: environmental_justice_distribution
## Purpose
Plan scholar-grade environmental justice and distributional analysis for pollution exposure, climate risk, policy benefits, policy costs, cumulative burden, subgroup effects, and map-ready outputs.

This skill treats environmental justice as a distributional research design problem. It defines who is exposed, who benefits, who bears costs, where support exists, which estimand is credible, and which claims must be downgraded until code artifacts and `claim_gate.json` allow stronger language.

This skill is a prompt and rubric layer. It does not run estimators, validate backends, certify artifacts, make legal determinations, or establish civil-rights violations.

Always read and apply these shared rules before using this skill:

* `../_shared/01_claim_language_rules.md`
* `../_shared/02_evidence_lookup_rules.md`
* `../_shared/03_artifact_reading_rules.md`
* `../_shared/04_spec_drafting_rules.md`
* `../_shared/05_forbidden_fallbacks.md`
* `../_shared/06_reviewer_mode_rules.md`
* `../_shared/07_scholarly_depth_rules.md`
* `../_shared/08_domain_literature_anchor_rules.md`

Any causal, paper-ready, backend-certified, legal, compliance, audit, or civil-rights claim must be supported by code artifacts and allowed by `claim_gate.json`.
## When to use
Use this skill when the user asks about distributional consequences of environmental exposure or policy, including:

* subgroup ATT, dynamic subgroup ATT, CATE-style equity heterogeneity, or group-specific event studies;
* whether pollution reductions, climate adaptation benefits, mitigation costs, enforcement benefits, subsidies, or infrastructure siting differ by income, race/ethnicity proxies, age, baseline burden, vulnerability, geography, or officially designated priority area;
* quantile DID, RIF DID, distributional DID, exposure inequality, concentration curves, concentration indices, or benefit incidence;
* cumulative burden indices combining pollution, climate risk, health burden, socioeconomic vulnerability, or infrastructure access;
* vulnerable communities, disadvantaged communities, environmental justice communities, or priority-community flags;
* map-ready outputs requiring CRS, boundary vintage, crosswalks, areal interpolation, raster-vector overlay, spatial aggregation, missing-geography rules, or exposure surfaces;
* interpretation of completed subgroup, distributional, burden, benefit-incidence, or mapping artifacts.
## Do not use when
Do not use this skill when:

* the question is only an average effect with no subgroup, distributional, exposure-burden, or benefit-incidence component;
* the user asks for legal discrimination, civil-rights, protected-class, compliance, enforcement, liability, or audit determinations;
* the task is only cartographic styling with no research design, measurement, or claim-language decision;
* the user asks to certify that a map, index, or model proves fairness, equity, legal compliance, or absence of discrimination;
* the user wants backend execution, estimator implementation, geocoder validation, or artifact certification rather than design and claim-gating guidance.
## Inputs expected
Collect or infer these inputs before recommending a main design:

* Research question and intended claim: descriptive inequality, causal policy effect, benefit incidence, cost incidence, cumulative burden, or map output.
* Unit of analysis: individual, household, parcel, facility, block group, tract, school catchment, county, commuting zone, plant, firm, grid cell, watershed, or other geography.
* Time frequency and window: daily, monthly, annual, event-time, panel length, pre-period length, and post-period length.
* Treatment, exposure, policy, or benefit: regulation, enforcement, cleanup, subsidy, transit investment, climate adaptation, hazard shock, facility opening, facility closure, or pollution shock.
* Outcome candidates: pollution exposure, exceedance, health proxy, energy burden, housing value, climate risk, access benefit, cleanup benefit, fiscal cost, or vulnerability score.
* Equity estimand: subgroup ATT, group-specific dynamic ATT, difference in exposure distribution, quantile effect, RIF effect, benefit-incidence share, concentration index, or cumulative-burden gradient.
* Population group definitions, source, year, geography, and whether each label is self-reported, administrative, modeled, imputed, or spatially proxied.
* Vulnerability index or priority-community definition, with official/latest lookup required at use time.
* Exposure measurement model: monitors, modeled surfaces, satellite products, emissions inventories, proximity buffers, plumes, flood/fire/heat risk, benefit allocation, or cost incidence.
* Spatial metadata: CRS, boundary vintage, shapefile source, aggregation level, crosswalk, areal interpolation, population denominators, islands, topology, and missing geography policy.
* Existing run artifacts when interpreting completed work.

For volatile definitions, require official/latest lookup at use time. Do not hardcode demographic boundaries, vulnerability indexes, priority-community definitions, legal categories, agency definitions, geospatial boundaries, program eligibility rules, or classification maps inside the skill response.
## Required repo artifacts to inspect
Inspect workspace files first. Do not rely on installed user-level skills as authority for this repository.

Required repository files and folders:

* `README.md`
* `registry.yml`
* `cli.py`
* `core.py`
* `python_wrappers.py`
* `workflows.py`
* `docs/ARTIFACT_CONTRACT.md` when present
* `docs/BACKEND_CONTRACT.md` when present
* `diagnostics/`
* `tests/fixtures/`
* `tests/backends/`
* existing shared, intake, domain, reporting, schema, and delivery-check files

When a run exists, inspect available artifacts before interpreting results:

* `status.json`, `claim_gate.json`, `manifest.json`, `artifact_manifest.json`
* `diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json` or `backend_status.json`
* subgroup support, overlap, balance, pretrend, event-study, weight, and power diagnostics
* multiple-testing, FDR, family-wise, hierarchical, or holdout artifacts
* map manifest, CRS, boundary vintage, crosswalk, areal-interpolation, raster-vector overlay, and population-denominator metadata
* cumulative-burden component manifest and sensitivity outputs
* benefit-incidence allocation and denominator outputs
* `model_table.csv`, only after diagnostics and claim gate

If these artifacts are unavailable, the skill may draft design questions and candidate routes, but it must mark capability-dependent claims as unknown, partial, exploratory, or blocked.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "United Church of Christ Commission for Racial Justice (1987), Toxic Wastes and Race in the United States"
    - "Bullard (1990), Dumping in Dixie"
    - "Been (1994), Ecology Law Quarterly, Locally Undesirable Land Uses in Minority Neighborhoods"
    - "Banzhaf and Walsh (2008), American Economic Review, Do People Vote with Their Feet?"
    - "Currie, Davis, Greenstone, and Walker (2015), American Economic Review, Environmental Health Risks and Housing Values"
    - "Ash and Fetter (2004), Social Science Quarterly, Who Lives on the Wrong Side of the Environmental Tracks?"
    - "Konisky and Reenock (2013), State Politics & Policy Quarterly, Compliance Bias and Environmental Injustice"
  canonical_data_sources:
    - "current index methodology"
    - "current percentile thresholds"
    - "current component datasets"
    - "current facility registry, permits, TRI/NEI, ECHO, RCRA, NPDES, and state records"
    - "current ECHO, state enforcement, complaint, and penalty datasets"
  live_lookup_required_for:
    - "current EJScreen version"
    - "current CalEnviroScreen version"
    - "current CEJST fields"
    - "current TRI/NEI/AQS data vintages"
    - "current CDC, CMS, hospital-discharge, ACS, HMDA, and property data vintages"
    - "current Justice40, EPA grant, enforcement, Superfund, Brownfields, and state EJ policy files"
    - "current index methodology"
    - "current percentile thresholds"
    - "current component datasets"
    - "current ACS demographic vintages"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "United Church of Christ Commission for Racial Justice (1987), Toxic Wastes and Race in the United States"
    use_for: "foundational EJ evidence on race and hazardous-waste facility proximity"
    live_lookup_required: []

    citation: "Bullard (1990), Dumping in Dixie"
    use_for: "historical siting, race, local politics, and community mobilization"
    live_lookup_required: []

    citation: "Been (1994), Ecology Law Quarterly, Locally Undesirable Land Uses in Minority Neighborhoods"
    use_for: "siting versus post-siting demographic change problem"
    live_lookup_required: []

    citation: "Banzhaf and Walsh (2008), American Economic Review, Do People Vote with Their Feet?"
    use_for: "household sorting responses to environmental quality"
    live_lookup_required: []

    citation: "Currie, Davis, Greenstone, and Walker (2015), American Economic Review, Environmental Health Risks and Housing Values"
    use_for: "facility entry/exit event study, toxic plants, housing, infant health"
    live_lookup_required: []

    citation: "Ash and Fetter (2004), Social Science Quarterly, Who Lives on the Wrong Side of the Environmental Tracks?"
    use_for: "race, income, and proximity to industrial hazards"
    live_lookup_required: []

    citation: "Konisky and Reenock (2013), State Politics & Policy Quarterly, Compliance Bias and Environmental Injustice"
    use_for: "political economy of enforcement and unequal regulatory compliance"
    live_lookup_required: []
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "EJ exposure"
    - "ambient pollution, modeled concentrations, monitor readings, facility proximity, toxic releases, traffic, wildfire smoke, flood/heat hazard, cumulative burden index"
    - "facility proximity is not exposure"
    - "emissions are not concentrations"
    - "monitor placement is endogenous"
    - "cumulative indices embed normative weights"
    - "EJ outcome"
    - "mortality, hospitalizations, asthma, birth weight, gestation, test scores, labor supply, housing values, displacement, insurance loss"
    - "EJ policy incidence"
    - "who receives enforcement, cleanup, permit denial, monitoring, grants, adaptation funds, buyouts, inspections, or pollution reductions"
  validation_targets:
    - "Estimand separation"
    - "Does the paper distinguish EJ exposure, EJ outcome, and EJ policy-incidence estimands?"
    - "Cumulative burden"
    - "Are cumulative-burden components, weights, percentile cutoffs, and sensitivity to alternative indices disclosed?"
    - "Subgroup ATT"
    - "Are race, income, and age subgroup treatment effects estimated with common support, stable denominators, and multiple-testing discipline?"
    - "Sorting versus siting"
    - "Are pre-siting demographics, facility entry/exit timing, mover-stayer decomposition, and post-siting composition changes separately shown?"
    - "Facility event timing"
    - "Are announcement, permit, construction, operation, emissions, closure, and remediation dates separated?"
  known_mismeasurement_channels:
    - "facility proximity is not exposure"
    - "emissions are not concentrations"
    - "monitor placement is endogenous"
    - "cumulative indices embed normative weights"
    - "outcomes require latency and mobility handling"
    - "health access and coding differ by group"
    - "housing values mix amenity, sorting, and wealth effects"
    - "targeted communities may have worse baseline trends"
    - "program eligibility is not treatment receipt"
    - "benefits can be capitalized into rents and displacement"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "EJ exposure"
    measure: "ambient pollution, modeled concentrations, monitor readings, facility proximity, toxic releases, traffic, wildfire smoke, flood/heat hazard, cumulative burden index"
    pitfalls: ["facility proximity is not exposure", "emissions are not concentrations", "monitor placement is endogenous", "cumulative indices embed normative weights"]
    live_lookup_required: ["current EJScreen version", "current CalEnviroScreen version", "current CEJST fields", "current TRI/NEI/AQS data vintages"]

    item: "EJ outcome"
    measure: "mortality, hospitalizations, asthma, birth weight, gestation, test scores, labor supply, housing values, displacement, insurance loss"
    pitfalls: ["outcomes require latency and mobility handling", "health access and coding differ by group", "housing values mix amenity, sorting, and wealth effects"]
    live_lookup_required: ["current CDC, CMS, hospital-discharge, ACS, HMDA, and property data vintages"]

    item: "EJ policy incidence"
    measure: "who receives enforcement, cleanup, permit denial, monitoring, grants, adaptation funds, buyouts, inspections, or pollution reductions"
    pitfalls: ["targeted communities may have worse baseline trends", "program eligibility is not treatment receipt", "benefits can be capitalized into rents and displacement"]
    live_lookup_required: ["current Justice40, EPA grant, enforcement, Superfund, Brownfields, and state EJ policy files"]

    item: "Cumulative burden"
    measure: "multi-pollutant exposure plus social vulnerability, health sensitivity, infrastructure deficit, climate hazard, and historical burden"
    pitfalls: ["index weights drive rankings", "correlated components can double count", "ranking thresholds create manipulation and bunching risks"]
    live_lookup_required: ["current index methodology", "current percentile thresholds", "current component datasets"]

    item: "Race, income, and age subgroup ATT"
    measure: "group-specific treatment effects by race/ethnicity, income, age, children, elderly, renters, linguistic isolation, and baseline health"
    pitfalls: ["subgroup ATT changes with treatment timing and group composition", "small-area race-income cells can be noisy", "intersectional groups need power and multiple-testing discipline"]
    live_lookup_required: ["current ACS demographic vintages", "current small-area population denominators"]

    item: "Mover-stayer decomposition"
    measure: "exposure changes decomposed into pollution change for stayers, moves across neighborhoods, and demographic composition changes"
    pitfalls: ["movers are selected", "address histories are incomplete", "stayer exposure can change through facility entry/exit or meteorology"]
    live_lookup_required: ["current address-history, LEHD, IRS migration, voter, credit-panel, or school-enrollment availability"]

    item: "Facility entry/exit event study"
    measure: "openings, closures, expansions, permit changes, violations, inspections, abatement, local exposure, health, housing, and demographic dynamics"
    pitfalls: ["announcements precede operation", "closure may follow local decline", "entry/exit dates differ across permits, emissions, and production"]
    live_lookup_required: ["current facility registry, permits, TRI/NEI, ECHO, RCRA, NPDES, and state records"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "calling exposure inequality a health-impact result or policy-incidence result"
    - "inferring discriminatory siting from cross-sectional proximity alone"
    - "treating an index percentile as a structural health dose"
    - "comparing subgroup coefficients without common support or baseline-risk normalization"
    - "using boundaries that also sort schools, taxes, policing, or amenities"
    - "interpreting fewer violations as cleaner facilities when inspection intensity differs"
  sorting_vs_siting_or_selection_channel:
    - "Sorting versus siting"
    - "Observed proximity gaps can arise from discriminatory facility siting, household sorting after siting, or both."
    - "pre-siting demographic baselines"
    - "facility entry/exit event studies"
    - "mover-stayer decomposition"
    - "historical zoning and land-use instruments"
    - "inferring discriminatory siting from cross-sectional proximity alone"
    - "Cumulative-burden measures are useful for targeting but not automatically causal dose-response measures."
  why_method_not_magic:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Exposure versus outcome versus policy incidence"
    core_issue: "Unequal exposure, unequal damages conditional on exposure, and unequal policy benefits are distinct estimands."
    acceptable_designs: ["separate first-stage exposure models", "dose-response health models", "policy-treatment incidence models", "distributional welfare accounting"]
    referee_risk: "calling exposure inequality a health-impact result or policy-incidence result"
    live_lookup_required: ["current exposure, outcome, and policy data vintages"]

    item: "Sorting versus siting"
    core_issue: "Observed proximity gaps can arise from discriminatory facility siting, household sorting after siting, or both."
    acceptable_designs: ["pre-siting demographic baselines", "facility entry/exit event studies", "mover-stayer decomposition", "historical zoning and land-use instruments"]
    referee_risk: "inferring discriminatory siting from cross-sectional proximity alone"
    live_lookup_required: ["current historical parcel, zoning, address, and facility-opening data availability"]

    item: "Cumulative burden identification"
    core_issue: "Cumulative-burden measures are useful for targeting but not automatically causal dose-response measures."
    acceptable_designs: ["component-level estimates", "pre-specified weights", "rank-threshold designs", "sensitivity to alternative index weights"]
    referee_risk: "treating an index percentile as a structural health dose"
    live_lookup_required: ["current index component definitions and weights"]

    item: "Subgroup ATT"
    core_issue: "Race, income, and age subgroup effects require clear estimands and stable denominators."
    acceptable_designs: ["group-specific ATT", "interaction models with common support", "multiple-testing adjustments", "intersectional subgroup power checks"]
    referee_risk: "comparing subgroup coefficients without common support or baseline-risk normalization"
    live_lookup_required: ["current demographic denominators and geography crosswalks"]

    item: "Boundary and zoning designs"
    core_issue: "Administrative boundaries, school zones, redlining maps, industrial zoning, and wind/downwind contrasts can identify local discontinuities but require no-sorting checks."
    acceptable_designs: ["boundary RD", "historical zoning instruments", "parcel-level land-use panels", "upwind-downwind designs", "placebo boundaries"]
    referee_risk: "using boundaries that also sort schools, taxes, policing, or amenities"
    live_lookup_required: ["current and historical zoning, HOLC, parcel, and boundary GIS files"]

    item: "Political economy of enforcement"
    core_issue: "Inspections, penalties, and cleanup can be distributed by race, income, political power, media attention, and agency capacity."
    acceptable_designs: ["facility fixed effects", "inspector or agency shocks", "complaint-to-inspection pipelines", "political-representation interactions", "violation-severity controls"]
    referee_risk: "interpreting fewer violations as cleaner facilities when inspection intensity differs"
    live_lookup_required: ["current ECHO/enforcement, state inspection, complaint, and penalty records"]
```

## Sorting-vs-siting decomposition

```yaml
sorting_vs_siting_decomposition:
facility_siting:
estimand: "whether new or expanded facilities are disproportionately placed near already disadvantaged communities"
required_inputs: ["facility opening/permit date", "pre-siting demographics", "pre-siting land use", "zoning and parcel history", "baseline pollution"]
designs: ["entry event study", "permit-boundary design", "historical zoning design", "upwind-downwind placebo"]
live_lookup_required: ["current facility registry and permit vintages", "current zoning/parcel data availability"]
household_sorting:
estimand: "whether households move toward or away from pollution after facility siting or pollution shocks"
required_inputs: ["address histories", "mover characteristics", "housing prices/rents", "school and labor-market controls", "exposure before and after move"]
designs: ["mover-stayer decomposition", "event-time migration model", "repeat-mover or household fixed effects", "rent capitalization checks"]
live_lookup_required: ["current address-history and housing-transaction data availability"]
post_siting_composition_change:
estimand: "whether neighborhood race, income, age, renter share, or vulnerability changes after facility entry/exit"
required_inputs: ["small-area demographics before and after siting", "consistent geography crosswalks", "facility operating dates", "housing-stock changes"]
designs: ["dynamic event study", "cohort-stayer decomposition", "synthetic controls", "geography harmonization sensitivity"]
live_lookup_required: ["current ACS/decennial census vintages and crosswalks"]
policy_targeting:
estimand: "whether monitoring, enforcement, cleanup, grants, or adaptation funds reach high-burden groups and reduce disparities"
required_inputs: ["eligibility rule", "application and award files", "baseline burden", "implementation date", "realized exposure/outcome changes"]
designs: ["eligibility-threshold RD", "difference-in-differences around targeting rule", "oversubscription design", "agency-capacity shock"]
live_lookup_required: ["current Justice40, EPA, state EJ, grant, enforcement, and cleanup program files"]
required_designs:
- "Report pre-siting demographics separately from post-siting composition."
- "Estimate mover and stayer exposure changes separately."
- "Use facility entry/exit dates, not only cross-sectional distance."
- "Separate policy eligibility, receipt, implementation, and realized burden reduction."
- "Show race, income, and age subgroup ATT with common-support and geography-crosswalk checks."
- "Test whether enforcement intensity differs before interpreting violation counts."
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Estimand separation"
    - "Does the paper distinguish EJ exposure, EJ outcome, and EJ policy-incidence estimands?"
    - "Cumulative burden"
    - "Are cumulative-burden components, weights, percentile cutoffs, and sensitivity to alternative indices disclosed?"
    - "Subgroup ATT"
    - "Are race, income, and age subgroup treatment effects estimated with common support, stable denominators, and multiple-testing discipline?"
    - "Sorting versus siting"
    - "Are pre-siting demographics, facility entry/exit timing, mover-stayer decomposition, and post-siting composition changes separately shown?"
    - "Facility event timing"
    - "Are announcement, permit, construction, operation, emissions, closure, and remediation dates separated?"
  minimal_empirical_section_checklist:
    - "Estimand separation"
    - "Does the paper distinguish EJ exposure, EJ outcome, and EJ policy-incidence estimands?"
    - "Cumulative burden"
    - "Are cumulative-burden components, weights, percentile cutoffs, and sensitivity to alternative indices disclosed?"
    - "current EJScreen, CalEnviroScreen, CEJST, and state index versions"
    - "Subgroup ATT"
    - "Are race, income, and age subgroup treatment effects estimated with common support, stable denominators, and multiple-testing discipline?"
    - "current ACS/census denominators"
    - "Sorting versus siting"
    - "Are pre-siting demographics, facility entry/exit timing, mover-stayer decomposition, and post-siting composition changes separately shown?"
  claims_to_downgrade:
    - "Do not infer discriminatory facility siting from cross-sectional proximity without pre-siting demographics and entry timing."
    - "Do not treat facility distance, emissions, concentration, exposure, dose, and health outcome as interchangeable."
    - "Do not call cumulative-burden index rankings causal health effects without component-level or dose-response evidence."
    - "Do not compare race, income, or age subgroup effects without common-support, denominator, and geography-crosswalk checks."
    - "Do not interpret neighborhood demographic change after siting as proof of initial siting discrimination without mover-stayer decomposition."
    - "Do not treat fewer violations as cleaner facilities when inspection intensity, complaints, and enforcement capacity differ."
    - "Do not claim EJ policy success from eligibility or spending alone without realized exposure, outcome, or incidence evidence."
    - "Do not make current claims about EJScreen, CEJST, CalEnviroScreen, Justice40, EPA enforcement, TRI/NEI/AQS, zoning, or state EJ policies without live lookup."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Estimand separation"
    ask: "Does the paper distinguish EJ exposure, EJ outcome, and EJ policy-incidence estimands?"
    live_lookup_required: []

    check: "Cumulative burden"
    ask: "Are cumulative-burden components, weights, percentile cutoffs, and sensitivity to alternative indices disclosed?"
    live_lookup_required: ["current EJScreen, CalEnviroScreen, CEJST, and state index versions"]

    check: "Subgroup ATT"
    ask: "Are race, income, and age subgroup treatment effects estimated with common support, stable denominators, and multiple-testing discipline?"
    live_lookup_required: ["current ACS/census denominators"]

    check: "Sorting versus siting"
    ask: "Are pre-siting demographics, facility entry/exit timing, mover-stayer decomposition, and post-siting composition changes separately shown?"
    live_lookup_required: ["current facility, address-history, and geography-crosswalk data"]

    check: "Facility event timing"
    ask: "Are announcement, permit, construction, operation, emissions, closure, and remediation dates separated?"
    live_lookup_required: ["current permit, facility, and enforcement records"]

    check: "Boundary and historical design"
    ask: "Do zoning, boundary, HOLC, or siting designs include placebo boundaries and checks for schools, taxes, policing, and amenities?"
    live_lookup_required: ["current GIS, zoning, parcel, and historical boundary files"]

    check: "Enforcement political economy"
    ask: "Does the analysis separate pollution, violations, inspections, penalties, complaints, and agency capacity?"
    live_lookup_required: ["current ECHO, state enforcement, complaint, and penalty datasets"]
```

## Forbidden claims

- Do not infer discriminatory facility siting from cross-sectional proximity without pre-siting demographics and entry timing.
- Do not treat facility distance, emissions, concentration, exposure, dose, and health outcome as interchangeable.
- Do not call cumulative-burden index rankings causal health effects without component-level or dose-response evidence.
- Do not compare race, income, or age subgroup effects without common-support, denominator, and geography-crosswalk checks.
- Do not interpret neighborhood demographic change after siting as proof of initial siting discrimination without mover-stayer decomposition.
- Do not treat fewer violations as cleaner facilities when inspection intensity, complaints, and enforcement capacity differ.
- Do not claim EJ policy success from eligibility or spending alone without realized exposure, outcome, or incidence evidence.
- Do not make current claims about EJScreen, CEJST, CalEnviroScreen, Justice40, EPA enforcement, TRI/NEI/AQS, zoning, or state EJ policies without live lookup.

## Domain reasoning steps
1. Define the equity object before the estimator.

   * Decide whether the question concerns baseline exposure inequality, causal policy effects, distribution of benefits, distribution of costs, cumulative burden, siting burden, or climate-risk incidence.
   * State the target estimand in words: group-specific ATT(g,t), subgroup dynamic ATT, exposure-reduction gap between groups, quantile treatment effect, RIF effect on high-exposure share, benefit-incidence share, or burden gradient.

2. Separate average ATT from equity.

   * Average ATT can be useful for policy magnitude but cannot establish equity improvement.
   * Require subgroup, distributional, burden-incidence, or benefit-incidence evidence for equity claims.
   * If only average effects exist, restrict language to average exposure or cost changes.

3. Define population groups and label status.

   * List each group variable, source, vintage, geography, construction rule, missingness rule, and proxy status.
   * Mark labels as direct, administrative, modeled, imputed, or area-level proxies.
   * Proxy labels are not complete identities, protected-class determinations, or legal classifications.

4. Check support before heterogeneity.

   * Require treated and comparison counts by group, cohort, event time, geography, and exposure baseline.
   * Inspect common support in baseline exposure, covariates, policy eligibility, treatment timing, geography, and pre-period outcome levels.
   * Small cells, thin cohorts, sparse group-by-event-time cells, extreme weights, or poor overlap block strong subgroup conclusions.

5. Diagnose subgroup pretrends and anticipation.

   * Pooled pretrends do not validate subgroup parallel trends.
   * Compare event-study leads by group and cohort when feasible.
   * Non-rejection in small groups is not evidence of credible counterfactual trends; discuss power.
   * Anticipation, migration, avoidance, compliance, or adaptation may differ by group.

6. Choose distributional methods by estimand.

   * Subgroup ATT fits discrete groups with adequate support.
   * Quantile DID targets changes at outcome quantiles and needs careful assumptions about counterfactual distributions.
   * RIF DID targets distributional statistics such as quantiles, variance, Gini, high-exposure shares, or exceedance shares.
   * Distributional DID compares full distributions when distributional common trends are credible.
   * Concentration curves and inequality decompositions are descriptive unless embedded in a credible causal design.

7. Specify exposure, burden, and index construction.

   * Define level, change, duration, exceedance, percentile, proximity, cumulative exposure, health-risk-weighted exposure, cost burden, benefit receipt, or fiscal incidence.
   * For cumulative burden indices, state components, scaling, weights, missing-data rule, aggregation level, and whether weights are normative, empirical, or official.
   * Require sensitivity to weights, components, transformations, and aggregation.

8. Treat benefit incidence separately from exposure reduction.

   * A policy can reduce pollution on average while benefits accrue mainly to already advantaged areas.
   * Define eligibility, take-up, access, allocation mechanism, per-capita denominator, fiscal incidence, spatial spillovers, and timing.
   * Distinguish benefit availability, benefit receipt, monetized benefit, exposure reduction, and risk reduction.

9. Address spatial aggregation and ecological inference.

   * Require CRS, boundary vintage, spatial unit, crosswalks, areal interpolation, raster-vector overlay, population weighting, islands, and topology checks for map-ready outputs.
   * Boundary changes, MAUP, missing geometries, and interpolation can reverse distributional conclusions.
   * Area-level demographic shares cannot establish individual exposure, identity, legal category, or individual benefit without additional assumptions.

10. Define multiple-testing families before reading results.

    * Families may be groups for one outcome, outcomes for one group, event-time coefficients, burden components, quantiles, geographies, or subgroup-by-outcome cells.
    * Require FDR, family-wise control, hierarchical testing, preregistered primary contrasts, or holdout confirmation when many tests are run.
    * Exploratory heatmaps require exploratory language.

11. Rank robustness by failure mode.

    * Alternative group definitions address label and boundary sensitivity.
    * Alternative exposure surfaces address measurement error.
    * Alternative crosswalks address spatial interpolation risk.
    * Alternative controls and donor restrictions address selection and support.
    * Placebo outcomes, placebo geographies, and pseudo dates address spurious spatial-temporal patterns.
    * Multiple-testing correction addresses false discovery risk.

12. Gate claims using code artifacts.

    * Strong equity, heterogeneity, causal, map-comparison, or policy-ready claims require diagnostics plus `claim_gate.json`.
    * Missing support, overlap, subgroup pretrends, FDR, map metadata, index manifest, or denominator artifacts forces downgrade.
    * Never substitute narrative polish or `model_table.csv` for claim gating.
## Candidate outputs
This skill may return:

* an `environmental_justice_plan` YAML or JSON plan;
* a distributional estimand and method decision tree;
* subgroup support, overlap, pretrend, power, and multiple-testing requirements;
* cumulative-burden, benefit-incidence, and exposure-inequality measurement plans;
* map-ready metadata checklist;
* safe claim language with explicit downgrades;
* code handoff instructions for diagnostics, artifacts, and claim gating;
* reviewer-risk notes for environmental, public, urban, health, and climate economics.
## Output schema
Return YAML by default, or JSON if requested. Do not omit the base fields. Include the domain-specific block exactly as shown, with additions allowed after it. Include `scholarly_depth` and `not_recommended_methods`.

```yaml
skill_name: environmental_justice_distribution
user_question_summary: string
research_domain: environmental_justice
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: null
  estimand_candidates: []
  identification_risks: []
environmental_justice_plan:
  population_groups: []
  exposure_burden_measures: []
  distributional_methods: []
  equity_outcomes: []
  required_disaggregation: []
  multiple_testing_warning: true
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
* Average effects do not establish equity, fairness, equal benefit, or reduced disparity.
* Subgroup ATT requires support, overlap, credible subgroup counterfactual trends, adequate subgroup sample size, and power discussion.
* Pooled pretrends do not validate subgroup-specific parallel trends.
* Multiple subgroup, quantile, outcome, event-time, and map tests require a stated testing family and correction or exploratory language.
* Proxy group labels are not complete identities, protected classes, individual attributes, or legal classifications.
* Vulnerable-community or disadvantaged-community labels require official/latest lookup at use time.
* Spatial aggregation creates ecological inference, MAUP, boundary-vintage, and areal-interpolation risks.
* Map-ready outputs require CRS, boundary, crosswalk, aggregation, missing-geography, topology, and population-denominator metadata.
* Cumulative burden indices embed measurement and weighting choices; index changes may reverse rankings.
* Benefit incidence requires allocation and denominator assumptions; it is not identical to exposure reduction.
* Code artifacts and `claim_gate.json` control strong causal, equity, paper-ready, or policy-ready claims.
## Forbidden claims
Do not claim or imply:

* average ATT proves environmental justice, fairness, equal benefit, or equitable distribution;
* a policy improved equity only because mean exposure fell;
* subgroup heterogeneity is strong when subgroup samples are small, support is weak, weights are extreme, subgroup pretrends are missing, or multiple testing is unaddressed;
* exploratory subgroup maps, CATE heatmaps, or many coefficients are confirmatory without FDR, family-wise control, hierarchical design, or holdout evidence;
* area-level proxy labels are complete identities, individual attributes, protected classes, or legal classifications;
* this skill can determine discrimination, civil-rights violation, disparate treatment, disparate impact, compliance, liability, or legal protected-class status;
* a vulnerability index, priority-community flag, environmental justice screen, boundary, or program definition is current without official/latest lookup at use time;
* maps are comparable without CRS, boundary, crosswalk, population denominator, and aggregation metadata;
* ecological inference from area-level shares establishes individual exposure or benefit;
* distributional DID, RIF, quantile DID, causal forest, or CATE heatmaps are credible without design-specific assumptions and diagnostics;
* `model_table.csv` alone authorizes equity claims.
## Handoff to code
Draft a concrete spec and ask code to verify only what code can verify.

Required code handoff fields:

* unit, geography, time, panel keys, treatment timing, anticipation window, comparison group, support restrictions, controls, fixed effects, clusters, and weights;
* outcomes and exposure surface source, including monitors, modeled surface, satellite product, emissions inventory, hazard layer, proximity measure, or benefit/cost allocation;
* population group variables, source, vintage, coding, missingness, proxy status, and official/latest lookup requirement for vulnerable-community or priority-area flags;
* subgroup definitions, minimum cell-size rules, estimand, and multiple-testing families;
* spatial metadata: CRS, boundary vintage, joins, raster-vector overlay, crosswalks, areal interpolation, population denominators, islands, topology, and missing geographies;
* cumulative-burden components, weights, scaling, and sensitivity rules;
* benefit-incidence allocation mechanism, eligibility, take-up, denominator, and timing.

Ask code to produce or verify:

* subgroup treated/control counts by group, cohort, geography, and event time;
* overlap, balance, weight, power, pretrend, and anticipation diagnostics by group;
* FDR, family-wise, hierarchical, or holdout outputs;
* map manifest with CRS, boundaries, joins, crosswalks, denominators, and missing-geography logs;
* cumulative-burden component manifest and sensitivity outputs;
* benefit-incidence denominator and allocation checks;
* `diagnostics.json`, `reviewer_risk.json`, `manifest.json` or `artifact_manifest.json`, and `claim_gate.json`.

Do not ask code to certify legal identity, civil-rights status, fairness, discrimination, compliance, or audit-grade conclusions.
## Handoff from code artifacts
Before writing strong language, read the artifacts that establish or block claim readiness:

* `claim_gate.json`, `status.json`, `manifest.json` or `artifact_manifest.json`
* `diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json` or `backend_status.json`
* subgroup support, overlap, balance, weight, power, pretrend, event-study, and anticipation diagnostics
* multiple-testing or FDR artifacts
* map manifest and geospatial metadata
* cumulative-burden component and sensitivity outputs
* benefit-incidence allocation and denominator outputs
* `model_table.csv`, only after claim gate and diagnostics

Downgrade rules:

* If `claim_gate.json` is missing, mark strong causal, equity, and paper-ready claims as unknown or blocked.
* If subgroup support, overlap, or sample size fails, report only descriptive or pooled patterns for affected groups.
* If subgroup pretrends are missing, block subgroup causal language.
* If FDR or family definition is missing after many tests, use exploratory language.
* If CRS, boundary, crosswalk, aggregation, or denominator metadata is missing, block map-comparison and spatial-incidence claims.
* If population labels are proxies, state proxy status and block identity or legal classification claims.
* If burden weights or benefit allocation rules are undocumented, call the index or incidence result exploratory.
## Minimal examples
### Good planning example
User: "Did a clean-air policy reduce pollution more in low-income neighborhoods than in high-income neighborhoods?"

```yaml
skill_name: environmental_justice_distribution
user_question_summary: "Assess whether exposure reductions differ by neighborhood income."
research_domain: environmental_justice
research_brief:
  unit: neighborhood
  time_frequency: annual
  outcome_candidates: [population_weighted_pm25, high_exposure_share]
  treatment_or_exposure: clean_air_policy
  estimand_candidates: [subgroup_dynamic_ATT_by_income, RIF_DID_for_high_exposure_share]
  identification_risks: [targeting_by_baseline_exposure, subgroup_pretrend_failure, weak_overlap, spillovers]
environmental_justice_plan:
  population_groups: [income_quintile_from_official_or_documented_source]
  exposure_burden_measures: [baseline_pm25, post_policy_pm25_change, top_decile_exposure_indicator]
  distributional_methods: [subgroup_ATT, subgroup_event_study, RIF_DID]
  equity_outcomes: [exposure_reduction_by_income_quintile, reduction_in_high_exposure_share]
  required_disaggregation: [boundary_vintage, population_denominator, CRS, income_crosswalk]
  multiple_testing_warning: true
  forbidden_claims: [average_ATT_as_equity_improvement, legal_discrimination_claim]
candidate_workflows: [modern_DID_with_subgroup_event_studies, RIF_DID_for_tail_exposure, map_ready_distributional_output]
candidate_methods: [subgroup_dynamic_ATT_if_support_and_pretrends_pass, RIF_DID_if_tail_estimand_is_primary]
required_diagnostics: [counts_by_group_cohort_event_time, overlap_by_group, subgroup_pretrends, exposure_surface_metadata, FDR_family]
recommended_robustness: [alternative_income_cutpoints, alternative_exposure_surface, population_weighted_vs_unweighted, alternative_crosswalk]
forbidden_claims: [do_not_claim_fair_distribution_from_average_effect, do_not_claim_legal_discrimination]
claim_language:
  allowed: ["The design targets whether measured exposure reductions were larger for specified income groups, conditional on subgroup support and claim gating."]
  disallowed: ["The policy proved environmental justice."]
uncertainty_notes: ["Income labels are area-level proxies unless individual data are available."]
next_code_actions: [build_group_support_table, run_subgroup_event_studies, create_map_manifest, produce_FDR_adjusted_outputs]
scholarly_depth:
  estimand_definition: "Group-specific dynamic ATT for exposure and RIF DID for high-exposure tail."
  identification_assumptions: [subgroup_parallel_trends, no_group_specific_anticipation, credible exposure assignment]
  measurement_model: [population_weighted_neighborhood_exposure, documented_income_proxy, predeclared_high_exposure_threshold]
  data_construction_risks: [boundary_changes, ecological_inference, exposure_surface_error]
  method_decision_tree: ["support and subgroup pretrends pass -> subgroup dynamic ATT", "tail exposure primary -> RIF DID", "only average ATT -> no equity claim"]
  diagnostics_that_block_claims: [missing_support_table, missing_subgroup_pretrends, unaddressed_multiple_testing, missing_map_metadata]
  robustness_ranked_by_risk: [alternative_exposure_surface, alternative_group_cutpoints, alternative_crosswalk, placebo_dates]
  referee_objections: [policy_targeting, mobility_or_avoidance, area_proxy_limits, false_discovery]
  downgrade_triggers: [claim_gate_missing, small_cells, extreme_weights, FDR_missing]
not_recommended_methods: [pooled_average_ATT_as_equity_evidence, TWFE_only_staggered_DID_without_group_diagnostics, subgroup_heatmap_without_FDR]
```

### Downgrade and overclaim-block example
User: "The average pollution effect is negative. Write that the policy ended environmental racism and complied with civil-rights law."

```yaml
skill_name: environmental_justice_distribution
user_question_summary: "User asks to convert an average pollution reduction into legal and equity claims."
research_domain: environmental_justice
research_brief:
  unit: unknown
  time_frequency: unknown
  outcome_candidates: [pollution_exposure]
  treatment_or_exposure: environmental_policy
  estimand_candidates: [average_ATT_only]
  identification_risks: [average_effect_not_distributional, legal_claim_out_of_scope, subgroup_support_unknown]
environmental_justice_plan:
  population_groups: []
  exposure_burden_measures: [average_pollution_change_only]
  distributional_methods: []
  equity_outcomes: []
  required_disaggregation: [subgroup_definitions, group_support, subgroup_pretrends, multiple_testing_plan, map_metadata_if_spatial]
  multiple_testing_warning: true
  forbidden_claims: [civil_rights_compliance, fairness_claim_from_average_ATT]
candidate_workflows: [downgrade_to_average_effect_language, request_distributional_design_before_equity_claim]
candidate_methods: [none_for_legal_claim]
required_diagnostics: [claim_gate_json, subgroup_support, subgroup_pretrends, FDR_if_many_groups]
recommended_robustness: [alternative_group_definitions_if_equity_analysis_is_added]
forbidden_claims: [do_not_claim_policy_ended_environmental_racism, do_not_claim_civil_rights_compliance, do_not_claim_equity_from_average_ATT]
claim_language:
  allowed: ["If claim-gated, the evidence may support an average reduction in measured pollution exposure."]
  disallowed: ["The policy ended environmental racism.", "The policy complied with civil-rights law."]
uncertainty_notes: ["No subgroup, support, pretrend, multiple-testing, or legal evidence is provided."]
next_code_actions: [inspect_claim_gate, add_subgroup_and_distributional_spec_if_equity_is_the_research_question]
scholarly_depth:
  estimand_definition: "Only an average ATT is described; no equity estimand is validated."
  identification_assumptions: [average_parallel_trends_if_DID_was_used]
  measurement_model: [measured_pollution_outcome_only]
  data_construction_risks: [no_group_labels, no_distributional_outcome, no_legal_identity_measure]
  method_decision_tree: ["average ATT only -> average-effect language only", "equity claim requested -> require subgroup or distributional design", "legal claim requested -> block"]
  diagnostics_that_block_claims: [missing_claim_gate, missing_subgroup_support, missing_subgroup_pretrends, missing_multiple_testing_plan]
  robustness_ranked_by_risk: [none_until_equity_estimand_is_defined]
  referee_objections: [mean_reduction_can_coexist_with_increased_burden_for_some_groups, legal_compliance_not_inferred_from_ATT]
  downgrade_triggers: [legal_claim_requested, average_ATT_used_as_fairness_evidence]
not_recommended_methods: [average_ATT_to_fairness_claim, proxy_group_labels_to_legal_identity]
```
## Completion checklist
* All required section headers are present exactly.
* Shared rules `01` through `07` are explicitly cited.
* The output schema includes the required `environmental_justice_plan` block exactly.
* The output schema includes `scholarly_depth` and `not_recommended_methods`.
* The skill starts from equity estimand, group definitions, support, and measurement, not from a default estimator.
* Average ATT is explicitly blocked as evidence of equity by itself.
* Subgroup ATT, subgroup pretrends, support, overlap, sample size, and power are required before heterogeneity claims.
* Quantile, RIF, and distributional DID are included as estimand-dependent options.
* Exposure inequality, cumulative burden, benefit incidence, and vulnerable communities are covered.
* Multiple testing, FDR, and family definitions are required for many subgroup or distributional tests.
* Map-ready outputs require CRS, boundaries, aggregation, crosswalks, areal interpolation, denominators, and missing-geography metadata.
* Ecological inference and proxy-label risks are explicit.
* Legal discrimination, civil-rights, protected-class, compliance, and audit claims are blocked.
* Official/latest lookup is required for volatile definitions and boundaries.
* Handoff to and from code names concrete artifacts and diagnostics.
* Downgrade rules rely on artifacts and `claim_gate.json`.
