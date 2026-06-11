# Skill: input_output_carbon_network

## Purpose

Plan input-output, MRIO, product-flow, and buyer-supplier carbon network research designs for Scope 3 screening, CBAM exposure, carbon leakage, sector carbon transmission, supply-chain risk, and network exposure.

This skill is a Codex prompt/rubric layer: a research design reviewer plus method constraint layer. It does not run estimators, validate backends, certify artifacts, make legal/compliance/audit claims, or override `claim_gate.json`.

The W matrix in this skill is an economic input-output or buyer-supplier network: IO technical coefficients, MRIO country-sector blocks, product flows, transaction shares, or firm-supplier links. It is not a geographic spatial W unless a separate spatial design is supplied.

## When to use

* The user asks to construct direct, indirect, upstream, downstream, imported, domestic, or total embodied carbon variables.
* The project concerns Scope 3 screening, CBAM exposure, leakage, carbon-cost pass-through, sector carbon transmission, supplier risk, or network exposure.
* The unit is sector, country-sector, product, firm, plant, transaction, portfolio holding, or supplier-buyer pair.
* The task must separate descriptive embodied-carbon exposure from causal shock propagation or certified supply-chain emissions.
* Prior artifacts exist and the user wants claim-safe interpretation under diagnostics and `claim_gate.json`.

## Do not use when

* The task is only geographic spillovers or SAR/SDM with a spatial W; use a spatial skill and keep IO W separate.
* The user asks for certified Scope 3, CBAM filing compliance, legal assurance, or audit-grade supply-chain emissions.
* The user wants to run an already validated spec without redesigning IO variables or claims.
* There is no credible IO, MRIO, product, sector, firm-sector, or supplier-buyer mapping.
* The user requires current IO/MRIO vintages, emission factors, policy coverage, or concordances but forbids official/latest lookup.
* The user wants network correlation treated as causal propagation without shock timing, counterfactual, and design artifacts.

## Inputs expected

* Research question and target claim: descriptive exposure, scenario exposure, causal propagation, accounting support, or blocked certified claim.
* Unit, time frequency, country coverage, sector/product classification, and whether W varies over time.
* Outcomes: embodied emissions, carbon intensity, input cost, price, export, output, emissions, productivity, or risk score.
* Exposure source: IO coefficients, MRIO Leontief inverse, supplier-buyer links, product bill of materials, import shares, carbon price, CBAM exposure, or sector shock.
* Carbon inputs: sector emissions, energy use, emission factors, output, value added, final demand, product quantities, direct emissions, and boundary definitions.
* Mapping inputs: firm-sector, product-sector, country-sector, sector concordance, supplier-buyer links, ownership/affiliate links, and import sourcing.
* Import assumptions: domestic technology assumption, proportional import assumption, domestic/import split, MRIO country sourcing, or customs/product sourcing.
* Existing artifacts: `claim_gate.json`, status, manifests, diagnostics, W metadata, concordance reports, model tables, and reviewer-risk files when interpreting results.

## Required repo artifacts to inspect

Inspect workspace files first; do not use installed user-level skills as the authority for this repository.

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
* Existing shared, intake, domain, reporting, schema, and delivery-check files.

Read these shared rules before producing output:

* `../_shared/01_claim_language_rules.md`
* `../_shared/02_evidence_lookup_rules.md`
* `../_shared/03_artifact_reading_rules.md`
* `../_shared/04_spec_drafting_rules.md`
* `../_shared/05_forbidden_fallbacks.md`
* `../_shared/06_reviewer_mode_rules.md`
* `../_shared/07_scholarly_depth_rules.md`
* `../_shared/08_domain_literature_anchor_rules.md`

When a run exists, inspect `claim_gate.json`, `status.json`, `manifest.json` or `artifact_manifest.json`, `diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json`, W metadata, concordance metadata, vintage metadata, import-split diagnostics, and `model_table.csv` only after gates and diagnostics.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Leontief (1936), Review of Economics and Statistics, Quantitative Input and Output Relations in the Economic Systems of the United States"
    - "Miller and Blair (2009), Input-Output Analysis: Foundations and Extensions, second edition"
    - "Peters (2008), Global Biogeochemical Cycles, From Production-Based to Consumption-Based National Emission Inventories"
    - "Davis and Caldeira (2010), Proceedings of the National Academy of Sciences, Consumption-Based Accounting of CO2 Emissions"
    - "Timmer, Dietzenbacher, Los, Stehrer, and de Vries (2015), Review of International Economics, An Illustrated User Guide to the World Input-Output Database"
    - "Lenzen, Moran, Kanemoto, and Geschke (2013), Economic Systems Research, Building Eora: A Global Multi-Region Input-Output Database at High Country and Sector Resolution"
    - "Stadler et al. (2018), Journal of Industrial Ecology, EXIOBASE 3: Developing a Time Series of Detailed Environmentally Extended Multi-Regional Input-Output Tables"
  canonical_data_sources:
    - "Timmer, Dietzenbacher, Los, Stehrer, and de Vries (2015), Review of International Economics, An Illustrated User Guide to the World Input-Output Database"
    - "WIOD structure, international value chains, prudent database use"
    - "Lenzen, Moran, Kanemoto, and Geschke (2013), Economic Systems Research, Building Eora: A Global Multi-Region Input-Output Database at High Country and Sector Resolution"
    - "detailed environmentally extended MRIO with product/industry detail and emissions/resource satellite accounts"
    - "global economic database for CGE and IO-style trade, production, final demand, protection, and energy accounts"
    - "current national emissions inventory"
    - "current MRIO trade and final-demand tables"
    - "Database pinning"
    - "current database releases and release notes"
    - "current MRIO and inventory vintages"
  live_lookup_required_for:
    - "current WIOD release and environmental satellite availability"
    - "current Eora release, country coverage, sector concordance, satellite accounts"
    - "current EXIOBASE version, extensions, deflators, concordances"
    - "current WIOD release"
    - "current environmental accounts"
    - "current sector-country coverage"
    - "current EXIOBASE release"
    - "current environmental extensions"
    - "current concordance files"
    - "current Eora release"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Leontief (1936), Review of Economics and Statistics, Quantitative Input and Output Relations in the Economic Systems of the United States"
    use_for: "input-output accounting foundation and interindustry requirements"
    live_lookup_required: []

    citation: "Miller and Blair (2009), Input-Output Analysis: Foundations and Extensions, second edition"
    use_for: "Leontief inverse, multipliers, price and quantity IO interpretation"
    live_lookup_required: []

    citation: "Peters (2008), Global Biogeochemical Cycles, From Production-Based to Consumption-Based National Emission Inventories"
    use_for: "consumption-based emissions, embodied trade, domestic versus imported emissions"
    live_lookup_required: []

    citation: "Davis and Caldeira (2010), Proceedings of the National Academy of Sciences, Consumption-Based Accounting of CO2 Emissions"
    use_for: "global consumption-based CO2 accounting and embodied emissions in trade"
    live_lookup_required: []

    citation: "Timmer, Dietzenbacher, Los, Stehrer, and de Vries (2015), Review of International Economics, An Illustrated User Guide to the World Input-Output Database"
    use_for: "WIOD structure, international value chains, prudent database use"
    live_lookup_required: ["current WIOD release and environmental satellite availability"]

    citation: "Lenzen, Moran, Kanemoto, and Geschke (2013), Economic Systems Research, Building Eora: A Global Multi-Region Input-Output Database at High Country and Sector Resolution"
    use_for: "Eora MRIO construction, uncertainty, high-country-coverage MRIO"
    live_lookup_required: ["current Eora release, country coverage, sector concordance, satellite accounts"]

    citation: "Stadler et al. (2018), Journal of Industrial Ecology, EXIOBASE 3: Developing a Time Series of Detailed Environmentally Extended Multi-Regional Input-Output Tables"
    use_for: "EXIOBASE environmental extensions, detailed sectoral MRIO, time-series construction"
    live_lookup_required: ["current EXIOBASE version, extensions, deflators, concordances"]
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "WIOD"
    - "inter-country input-output tables with sectoral production, trade, final demand, and satellite extensions where available"
    - "EXIOBASE"
    - "detailed environmentally extended MRIO with product/industry detail and emissions/resource satellite accounts"
    - "Eora"
    - "high-country-coverage MRIO with heterogeneous national table structures and environmental/social satellite accounts"
    - "country detail can come with heterogeneous sector reliability"
    - "uncertainty varies by country-sector"
    - "harmonized and full Eora variants differ"
    - "OECD TiVA"
  validation_targets:
    - "Database pinning"
    - "Are WIOD, EXIOBASE, Eora, OECD TiVA/ICIO, and GTAP releases, years, sectors, countries, and satellite accounts pinned?"
    - "Leontief estimand"
    - "Is the Leontief inverse described as fixed-coefficient accounting unless a causal structural model is explicitly added?"
    - "Concordance"
    - "Are sector, product, country, firm, tariff, and emissions concordances disclosed with many-to-many weighting rules?"
    - "Domestic/import split"
    - "Are domestic embodied emissions, imported embodied emissions, and re-exports separated before policy claims?"
    - "Price/quantity interpretation"
    - "Are nominal, constant-price, physical, price-model, and quantity-model results kept conceptually separate?"
  known_mismeasurement_channels:
    - "release-specific country and year coverage"
    - "sector aggregation"
    - "environmental accounts may not match current emissions inventories"
    - "hybrid monetary/physical layers require careful interpretation"
    - "version changes alter totals"
    - "large sector detail increases concordance risk"
    - "country detail can come with heterogeneous sector reliability"
    - "uncertainty varies by country-sector"
    - "harmonized and full Eora variants differ"
    - "TiVA is not identical to a full emissions MRIO"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "WIOD"
    measure: "inter-country input-output tables with sectoral production, trade, final demand, and satellite extensions where available"
    pitfalls: ["release-specific country and year coverage", "sector aggregation", "environmental accounts may not match current emissions inventories"]
    live_lookup_required: ["current WIOD release", "current environmental accounts", "current sector-country coverage"]

    item: "EXIOBASE"
    measure: "detailed environmentally extended MRIO with product/industry detail and emissions/resource satellite accounts"
    pitfalls: ["hybrid monetary/physical layers require careful interpretation", "version changes alter totals", "large sector detail increases concordance risk"]
    live_lookup_required: ["current EXIOBASE release", "current environmental extensions", "current concordance files"]

    item: "Eora"
    measure: "high-country-coverage MRIO with heterogeneous national table structures and environmental/social satellite accounts"
    pitfalls: ["country detail can come with heterogeneous sector reliability", "uncertainty varies by country-sector", "harmonized and full Eora variants differ"]
    live_lookup_required: ["current Eora release", "current uncertainty metadata", "current country-sector mapping"]

    item: "OECD TiVA"
    measure: "trade in value added, domestic and foreign value-added content, GVC indicators, embodied production networks"
    pitfalls: ["TiVA is not identical to a full emissions MRIO", "indicator definitions and country coverage change by edition", "linking emissions requires compatible sectors"]
    live_lookup_required: ["current OECD TiVA edition", "current ICIO tables", "current emissions-link files"]

    item: "GTAP"
    measure: "global economic database for CGE and IO-style trade, production, final demand, protection, and energy accounts"
    pitfalls: ["CGE benchmark data are not automatically causal shocks", "region-sector aggregation choices matter", "base-year updates change calibration"]
    live_lookup_required: ["current GTAP Data Base version", "current energy/emissions extensions", "current concordances"]

    item: "Domestic versus imported emissions"
    measure: "production-based emissions, consumption-based emissions, domestic embodied emissions, imported embodied emissions, re-exported embodied emissions"
    pitfalls: ["territorial and footprint accounts answer different questions", "imports depend on MRIO trade allocation assumptions", "re-exports and processing trade can distort attribution"]
    live_lookup_required: ["current national emissions inventory", "current MRIO trade and final-demand tables"]

    item: "Price versus quantity IO"
    measure: "monetary IO coefficients, constant-price tables, physical IO, price model, quantity model, deflated time-series"
    pitfalls: ["monetary coefficients mix prices and quantities", "deflation at coarse sectors can create false intensity changes", "Leontief price and quantity models have different counterfactual meaning"]
    live_lookup_required: ["current price-base year", "current deflators", "current supply-use balancing method"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "calling IO multipliers causal treatment effects"
    - "mechanical effects from lossy concordances"
    - "claiming national decarbonization from territorial emissions while embodied imports rise"
    - "MRIO vintage risk"
    - "irreproducible footprint estimates from unpinned MRIO versions"
    - "interpreting nominal value-chain changes as physical carbon reductions"
    - "ranking sectors as causal bottlenecks from centrality alone"
  sorting_vs_siting_or_selection_channel:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  why_method_not_magic:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Leontief inverse interpretation"
    core_issue: "The Leontief inverse is an accounting propagation object under fixed coefficients, not a causal multiplier without identifying assumptions."
    acceptable_designs: ["transparent accounting estimand", "shock-specific structural assumptions", "sensitivity to coefficient updating", "supply-constraint caveats"]
    referee_risk: "calling IO multipliers causal treatment effects"
    live_lookup_required: []

    item: "Sector concordance"
    core_issue: "Policy, firm, emissions, tariff, patent, and IO sectors rarely align cleanly."
    acceptable_designs: ["many-to-many concordance disclosure", "weighting-rule sensitivity", "sector aggregation robustness", "manual checks for high-emission sectors"]
    referee_risk: "mechanical effects from lossy concordances"
    live_lookup_required: ["current NAICS/NACE/ISIC/HS/CPC/MRIO concordance versions"]

    item: "Domestic versus imported emissions"
    core_issue: "Domestic production emissions and consumption footprints imply different incidence and policy conclusions."
    acceptable_designs: ["report production and consumption accounts", "separate domestic/imported channels", "border-adjustment sensitivity", "trade-reallocation checks"]
    referee_risk: "claiming national decarbonization from territorial emissions while embodied imports rise"
    live_lookup_required: ["current MRIO and emissions inventory vintages"]

    item: "MRIO vintage risk"
    core_issue: "Database releases revise IO tables, trade shares, balancing methods, sector mappings, and satellite emissions."
    acceptable_designs: ["database-version pinning", "cross-MRIO comparison", "release-note audit", "replication archive with concordances"]
    referee_risk: "irreproducible footprint estimates from unpinned MRIO versions"
    live_lookup_required: ["current WIOD, EXIOBASE, Eora, OECD TiVA/ICIO, and GTAP releases"]

    item: "Price versus quantity counterfactuals"
    core_issue: "Monetary IO tables can reflect price changes rather than real input substitution or physical emissions changes."
    acceptable_designs: ["constant-price tables", "physical extensions", "deflator sensitivity", "separate price-model and quantity-model interpretations"]
    referee_risk: "interpreting nominal value-chain changes as physical carbon reductions"
    live_lookup_required: ["current deflator and base-year metadata"]

    item: "Network centrality and carbon propagation"
    core_issue: "IO network centrality, upstreamness, and multiplier measures are accounting metrics that depend on aggregation and normalization."
    acceptable_designs: ["aggregation sensitivity", "weighted directed network definitions", "domestic/import split", "bootstrap or uncertainty propagation"]
    referee_risk: "ranking sectors as causal bottlenecks from centrality alone"
    live_lookup_required: ["current network construction and MRIO uncertainty metadata"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Database pinning"
    - "Are WIOD, EXIOBASE, Eora, OECD TiVA/ICIO, and GTAP releases, years, sectors, countries, and satellite accounts pinned?"
    - "Leontief estimand"
    - "Is the Leontief inverse described as fixed-coefficient accounting unless a causal structural model is explicitly added?"
    - "Concordance"
    - "Are sector, product, country, firm, tariff, and emissions concordances disclosed with many-to-many weighting rules?"
    - "Domestic/import split"
    - "Are domestic embodied emissions, imported embodied emissions, and re-exports separated before policy claims?"
    - "Price/quantity interpretation"
    - "Are nominal, constant-price, physical, price-model, and quantity-model results kept conceptually separate?"
  minimal_empirical_section_checklist:
    - "Database pinning"
    - "Are WIOD, EXIOBASE, Eora, OECD TiVA/ICIO, and GTAP releases, years, sectors, countries, and satellite accounts pinned?"
    - "current database releases and release notes"
    - "Leontief estimand"
    - "Is the Leontief inverse described as fixed-coefficient accounting unless a causal structural model is explicitly added?"
    - "Concordance"
    - "Are sector, product, country, firm, tariff, and emissions concordances disclosed with many-to-many weighting rules?"
    - "current concordance files"
    - "Domestic/import split"
    - "Are domestic embodied emissions, imported embodied emissions, and re-exports separated before policy claims?"
  claims_to_downgrade:
    - "Do not call Leontief inverse multipliers causal effects without a causal model or identifying variation."
    - "Do not mix WIOD, EXIOBASE, Eora, OECD TiVA, and GTAP outputs without pinning releases, sectors, years, countries, and satellite accounts."
    - "Do not infer domestic decarbonization from territorial emissions alone when imported embodied emissions are material."
    - "Do not hide many-to-many sector concordance choices or treat concordance weights as innocuous."
    - "Do not interpret nominal IO changes as physical carbon changes without price/quantity separation."
    - "Do not rank sectors as policy bottlenecks from network centrality alone without aggregation and normalization sensitivity."
    - "Do not make current claims about MRIO releases, satellite accounts, concordances, deflators, national inventories, or database coverage without live lookup."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Database pinning"
    ask: "Are WIOD, EXIOBASE, Eora, OECD TiVA/ICIO, and GTAP releases, years, sectors, countries, and satellite accounts pinned?"
    live_lookup_required: ["current database releases and release notes"]

    check: "Leontief estimand"
    ask: "Is the Leontief inverse described as fixed-coefficient accounting unless a causal structural model is explicitly added?"
    live_lookup_required: []

    check: "Concordance"
    ask: "Are sector, product, country, firm, tariff, and emissions concordances disclosed with many-to-many weighting rules?"
    live_lookup_required: ["current concordance files"]

    check: "Domestic/import split"
    ask: "Are domestic embodied emissions, imported embodied emissions, and re-exports separated before policy claims?"
    live_lookup_required: ["current MRIO and inventory vintages"]

    check: "Price/quantity interpretation"
    ask: "Are nominal, constant-price, physical, price-model, and quantity-model results kept conceptually separate?"
    live_lookup_required: ["current price base and deflators"]

    check: "MRIO robustness"
    ask: "Are headline carbon-network or footprint results compared across at least one alternative MRIO or release when feasible?"
    live_lookup_required: ["current alternative MRIO releases"]

    check: "Uncertainty and aggregation"
    ask: "Are sector aggregation, emissions-factor uncertainty, balancing uncertainty, and high-emission-sector concordance errors propagated or stress-tested?"
    live_lookup_required: ["current uncertainty metadata and satellite-account documentation"]
```

## Forbidden claims

- Do not call Leontief inverse multipliers causal effects without a causal model or identifying variation.
- Do not mix WIOD, EXIOBASE, Eora, OECD TiVA, and GTAP outputs without pinning releases, sectors, years, countries, and satellite accounts.
- Do not infer domestic decarbonization from territorial emissions alone when imported embodied emissions are material.
- Do not hide many-to-many sector concordance choices or treat concordance weights as innocuous.
- Do not interpret nominal IO changes as physical carbon changes without price/quantity separation.
- Do not rank sectors as policy bottlenecks from network centrality alone without aggregation and normalization sensitivity.
- Do not make current claims about MRIO releases, satellite accounts, concordances, deflators, national inventories, or database coverage without live lookup.

## Domain reasoning steps

1. Start with the research object, not the estimator. Define unit, time, outcome, exposure, boundary, and whether the estimand is a descriptive embodied-carbon measure, scenario exposure, causal shock response, or certified accounting claim. Downgrade certified claims unless audited accounting artifacts exist.

2. Classify W. State whether W is IO technical coefficients, MRIO country-sector blocks, product flows, transaction shares, supplier-buyer links, or portfolio-sector exposure. Record orientation, normalization, time variation, and whether rows or columns represent supplying or using sectors.

3. State explicitly: IO/network W is an economic input-output or buyer-supplier network, not a geographic spatial W. Do not use SAR/SDM or spatial indirect-effect language unless a separate spatial model and artifacts exist.

4. Separate direct, indirect, and total emissions. Direct emissions belong to the producing sector, plant, or firm boundary. Upstream indirect emissions are input requirements times carbon intensities. Downstream exposure uses customer sectors, final demand, product use, or pass-through channels.

5. Specify the Leontief construction when used. Define A, final demand or output vector, carbon intensity vector, and whether `(I - A)^(-1)` is computed on domestic IO blocks, MRIO global blocks, or a domestic/import split. Do not use Leontief language for a simple correlation graph.

6. Distinguish production-based intensity, consumption-based embodied carbon, imported embodied carbon, domestic embodied carbon, and sector-country embodied carbon. Every variable needs a numerator, denominator, price basis, currency, deflator, and boundary tag.

7. Require IO/MRIO vintage metadata: table year, release, classification, aggregation, country coverage, price basis, domestic/import treatment, and concordance version. For IO tables, MRIO releases, emission factors, sector/product concordances, firm identifiers, policy coverage, and backend availability, require official/latest lookup at use time.

8. Audit firm-sector and product-sector mapping. A firm assigned to an industry receives a sector-average proxy, not actual firm Scope 3. Flag many-to-many mappings, conglomerates, traders, platforms, outsourced production, multi-product firms, and missing segment shares.

9. Model imports explicitly. State whether imported inputs use domestic technology, proportional imports, MRIO country blocks, customs shares, product sourcing, or a separate imported-input coefficient matrix. Do not ignore imported emissions in CBAM, leakage, or Scope 3 applications.

10. Define upstream versus downstream exposure before construction. Upstream exposure follows suppliers and purchased inputs; downstream exposure follows customers, final demand, use-phase exposure, or revenue risk. Ambiguous W orientation blocks interpretation.

11. Diagnose double counting. Check overlap between direct emissions, purchased electricity, upstream inputs, downstream use, intra-group trade, recycled intermediates, repeated supplier paths, and sector totals already embedded in Leontief requirements.

12. Separate descriptive exposure from causal shock propagation. `W * shock`, `W * treatment`, or network correlation is an exposure construction, not proof of propagation. Causal claims require shock timing, counterfactual, design assumptions, contamination checks, and diagnostics.

13. Use a decision tree, not a method list. Descriptive screen -> IO/MRIO exposure. CBAM or carbon-price exposure -> sector-country exposure plus policy-timing triage. Firm outcome response -> supplier links, pre-shock exposure, FE/design controls, and contamination checks. Structural propagation -> equations, equilibrium assumptions, and artifacts. Geographic spillovers -> spatial skill.

14. Define diagnostics that block claims: missing vintage, missing sector concordance, missing import treatment, unknown W orientation, no boundary tags, no double-counting audit, no shock timing, no counterfactual, no contamination check, missing backend status, or missing `claim_gate.json`.

15. Draft claim language conservatively. Allowed before code: "candidate embodied-carbon exposure", "sector-average upstream exposure", or "MRIO-based scenario measure". Block "actual firm Scope 3", "certified supply-chain emissions", "causal propagation", "carbon leakage effect", and "CBAM compliance impact" unless artifacts support the exact claim.

## Candidate outputs

* `io_carbon_network_plan` YAML or JSON block.
* Research brief separating descriptive exposure, scenario exposure, causal propagation, and certified accounting.
* W construction plan with unit, orientation, normalization, vintage, import treatment, and metadata requirements.
* Leontief inverse or supplier-buyer exposure notes.
* Embodied-carbon variable dictionary with upstream, downstream, direct, indirect, domestic, imported, and total tags.
* Double-counting risk register and diagnostics.
* Method decision tree, not-recommended methods, robustness ranked by risk, and referee objections.
* Claim language with allowed, conditional, and disallowed statements.
* Concrete handoff list for code artifacts and claim gate.

## Output schema

Return YAML or JSON. Do not omit the common fields. Include the domain-specific block exactly as shown, then add `scholarly_depth` and `not_recommended_methods`.

```yaml
skill_name: input_output_carbon_network
user_question_summary: string
research_domain: io_carbon_network | scope3 | cbam | carbon_leakage | supply_chain_risk | mixed
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
  conditional: []
  disallowed: []
uncertainty_notes: []
next_code_actions: []
io_carbon_network_plan:
  network_unit: sector | firm | country_sector | product | unknown
  carbon_intensity_inputs: []
  W_network_candidates: []
  embodied_emissions_variables: []
  shock_propagation_designs: []
  double_counting_risks: []
  forbidden_claims: []
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

* This skill plans design and claims; it does not run estimators, validate backend availability, certify artifacts, or make legal/compliance/audit claims.
* Strong causal, structural, certified, paper-ready, or backend-certified language requires code artifacts plus an allowing `claim_gate.json`.
* IO/MRIO measures depend on table vintage, sector aggregation, price basis, concordance choices, import assumptions, emission factors, and Leontief fixed-coefficient assumptions.
* Official/latest lookup is required at use time for IO tables, MRIO vintages, emission factors, sector/product concordances, firm identifiers, policy definitions, regulation boundaries, package availability, and backend availability.
* Sector-average intensity mapped to a firm is a proxy exposure, not actual firm Scope 3 emissions.
* Descriptive embodied-carbon exposure is not causal shock propagation or certified supply-chain emissions.
* Missing imports, undefined boundaries, unknown W orientation, or unexamined double counting require downgrading total embodied emissions language.
* `model_table.csv` or a coefficient table alone never establishes claim readiness.

## Forbidden claims

* Do not claim industry IO carbon intensity equals actual firm Scope 3 emissions.
* Do not claim certified supply-chain emissions, CBAM compliance, audit assurance, legal violation, fraud, intent, or filing accuracy from IO exposure variables.
* Do not ignore imported emissions, domestic/import splits, boundary definitions, or sector-country sourcing in Scope 3, CBAM, or leakage applications.
* Do not treat network correlation, `W * exposure`, or co-movement along W as causal propagation.
* Do not claim carbon leakage, cost pass-through, or supplier shock effects without shock timing, counterfactual, contamination checks, diagnostics, and `claim_gate.json`.
* Do not call IO W a geographic spatial W or use SAR/SDM language for economic IO W without a separate validated spatial design.
* Do not hardcode stale IO/MRIO vintages, emission factors, concordances, policy coverage, packages, or backends.
* Do not replace unavailable MRIO, PPML, or network backends with ad hoc OLS/log-linear regressions and call the result equivalent.
* Do not bypass diagnostics, reviewer-risk artifacts, backend-discovery artifacts, or claim gates.

## Handoff to code

* Build W manifest: unit, orientation, normalization, source, vintage, release, classification, country coverage, row/column sums, time variation, and domestic/import treatment.
* Build emissions-input manifest: factor source, sector emissions, output denominator, price basis, deflator, currency, boundary, and update date.
* Validate firm-sector, product-sector, sector-country, and supplier-buyer concordances; report unmapped, many-to-many, and ambiguous mappings.
* Compute direct, upstream, downstream, domestic, imported, and total embodied variables only when boundary tags are explicit.
* Record Leontief components: A matrix, output or final-demand vector, inverse method, aggregation, import split, and numerical stability.
* Produce diagnostics for double counting, missingness, import sensitivity, W orientation, W normalization, leverage, support, and timing.
* For causal propagation, require shock source, pre-shock exposure, comparison group, FE/design controls, contamination checks, placebo/pretrend diagnostics, and claim gate.
* Write `diagnostics.json`, `reviewer_risk.json`, `artifact_manifest.json`, `backend_discovery.json`, and `claim_gate.json`.
* Do not ask code to certify Scope 3, legal compliance, CBAM filing accuracy, or audit assurance.

## Handoff from code artifacts

Read `claim_gate.json` first, then `status.json`, `artifact_manifest.json` or `manifest.json`, W metadata, concordance diagnostics, vintage metadata, import-split diagnostics, `diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json`, and finally `model_table.csv`.

Use artifacts to decide claim class: allowed, conditional, partial, exploratory, unknown, or blocked. If any required artifact is missing, state which claim is blocked rather than inferring readiness from coefficients.

## Minimal examples

### Good planning example

User: "Build a firm-year supplier carbon exposure for exporters using IO data and discuss whether CBAM risk transmits through suppliers."

Expected skill output:

```yaml
skill_name: input_output_carbon_network
user_question_summary: firm-year supplier carbon exposure and CBAM risk
research_domain: cbam
research_brief:
  unit: firm_year
  time_frequency: annual
  outcome_candidates: [export_value, input_cost, upstream_embodied_carbon]
  treatment_or_exposure: supplier_sector_embodied_carbon
  estimand_candidates: [descriptive_upstream_exposure, conditional_dynamic_response_to_policy_shock]
  identification_risks: [firm_sector_mapping_error, imported_input_mismeasurement, endogenous_supplier_choice]
candidate_workflows: [io_mrio_exposure_construction, causal_design_triage_for_policy_shock]
candidate_methods: [Leontief_inverse_exposure_for_descriptive_measurement, event_study_or_modern_DID_only_after_timing_validation]
required_diagnostics: [IO_MRIO_vintage_check, W_orientation_check, firm_sector_concordance_check, domestic_import_split_check, double_counting_check, claim_gate_check]
recommended_robustness: [alternative_MRIO_vintage, alternative_sector_aggregation, import_assumption_sensitivity]
forbidden_claims: [actual_firm_scope3, causal_network_transmission_without_design]
claim_language:
  allowed: [candidate firm-year upstream carbon exposure based on sector-average IO intensities]
  conditional: [evidence consistent with supplier-channel exposure if timing and diagnostics pass]
  disallowed: [certified firm Scope 3 emissions, causal CBAM propagation from correlations]
uncertainty_notes: [official latest CBAM scope and MRIO vintage must be checked at use time]
next_code_actions: [build W manifest, construct domestic/imported exposure, write double-counting diagnostics]
io_carbon_network_plan:
  network_unit: firm
  carbon_intensity_inputs: [sector_country_emissions_per_output, imported_input_emission_factors]
  W_network_candidates: [MRIO_technical_coefficients, firm_supplier_sector_links]
  embodied_emissions_variables: [upstream_domestic_embodied_carbon, upstream_imported_embodied_carbon, total_upstream_sector_average_exposure]
  shock_propagation_designs: [policy_timing_event_study_only_if_pre_shock_exposure_is_fixed]
  double_counting_risks: [direct_emissions_counted_inside_total_requirements, repeated_supplier_paths]
  forbidden_claims: [actual_firm_scope3_emissions, certified_supply_chain_emissions]
scholarly_depth:
  estimand_definition: descriptive upstream embodied-carbon exposure; causal response is separate and conditional
  identification_assumptions: [pre_shock_exposure_not_chosen_in_response_to_policy, credible_counterfactual_trends]
  measurement_model: [sector_average_intensity_mapped_to_firms_through_supplier_or_industry_links]
  data_construction_risks: [MRIO_vintage_mismatch, product_sector_concordance_error, import_sourcing_error]
  method_decision_tree: [descriptive_screen_first, causal_design_only_after_timing_and_counterfactual_validation]
  diagnostics_that_block_claims: [missing_import_split, missing_claim_gate]
  robustness_ranked_by_risk: [import_assumption_sensitivity, alternative_MRIO_vintage]
  referee_objections: [sector_average_proxy_may_not_measure_true_firm_supply_chain]
  downgrade_triggers: [no_double_counting_audit, no_pre_policy_exposure_lock]
not_recommended_methods: [treating_W_times_policy_as_causal_propagation_without_design]
```

### Downgrade and overclaim-block example

User: "Use the IO network to prove that my firm's suppliers caused our actual Scope 3 emissions and certify the CBAM compliance impact."

Expected skill output:

```yaml
skill_name: input_output_carbon_network
user_question_summary: requested certified firm Scope 3 and causal CBAM claim
research_domain: scope3
research_brief:
  unit: firm
  time_frequency: unknown
  outcome_candidates: [claimed_actual_scope3]
  treatment_or_exposure: supplier_network
  estimand_candidates: [blocked_certified_accounting_claim, blocked_causal_propagation_claim]
  identification_risks: [no_audited_supplier_activity_data, no_policy_counterfactual, no_import_boundary]
candidate_workflows: [descriptive_sector_proxy_exposure_only]
candidate_methods: [IO_or_MRIO_proxy_construction_with_caveats]
required_diagnostics: [audited_activity_data_presence_check, import_boundary_check, double_counting_check, claim_gate_check]
recommended_robustness: [alternative_sector_mapping_if_descriptive_proxy_is_still_useful]
forbidden_claims: [certified_supply_chain_emissions, causal_supplier_propagation]
claim_language:
  allowed: [sector-average IO exposure may be planned as a non-certified proxy]
  conditional: []
  disallowed: [proof of actual Scope 3 emissions, certified CBAM compliance impact]
uncertainty_notes: [official current policy definitions and accounting boundaries are required at use time]
next_code_actions: [inspect whether audited supplier activity and boundary artifacts exist]
io_carbon_network_plan:
  network_unit: firm
  carbon_intensity_inputs: []
  W_network_candidates: [supplier_buyer_links_if_available, MRIO_sector_proxy_if_available]
  embodied_emissions_variables: [blocked_actual_scope3_claim]
  shock_propagation_designs: []
  double_counting_risks: [unknown_scope_boundary, imported_input_boundary_missing]
  forbidden_claims: [industry_IO_intensity_equals_actual_firm_scope3, network_correlation_is_causal_propagation]
scholarly_depth:
  estimand_definition: certified accounting and causal propagation claims are blocked; only proxy exposure can be planned
  identification_assumptions: []
  measurement_model: [audited_supplier_activity_data_required_for_actual_scope3]
  data_construction_risks: [missing_imports, missing_boundaries, missing_concordance]
  method_decision_tree: [no_audited_activity_data_no_certified_scope3, no_shock_timing_no_causal_propagation]
  diagnostics_that_block_claims: [claim_gate_missing, boundary_missing]
  robustness_ranked_by_risk: [not_applicable_until_measurement_artifacts_exist]
  referee_objections: [sector_IO_proxy_cannot_identify_actual_firm_supply_chain_emissions]
  downgrade_triggers: [no_claim_gate, no_double_counting_audit]
not_recommended_methods: [certifying_scope3_from_sector_IO_intensities]
```

## Completion checklist

* Required section headers are present.
* Shared rules 01-07, including `../_shared/07_scholarly_depth_rules.md`, are cited.
* W is defined as economic IO/MRIO/product/buyer-supplier W, not geographic spatial W.
* Direct, indirect, upstream, downstream, domestic, imported, and total embodied emissions are separated.
* Leontief inverse usage requires A, final demand or output, and import assumptions.
* IO/MRIO vintage, sector aggregation, price basis, firm-sector mapping, product concordance, and import treatment are required.
* Double-counting risks and diagnostics are explicit.
* Descriptive exposure is separated from causal propagation and certified supply-chain emissions.
* Strong claims require code artifacts plus `claim_gate.json`.
* Official/latest lookup is required for volatile tables, factors, policies, concordances, identifiers, packages, and backends.
* Minimal examples include one good planning example and one overclaim block.
