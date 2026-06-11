# Skill: carbon_accounting_mrv

## Purpose

Plan carbon accounting, MRV, Scope 1/2/3, financed emissions, embedded carbon, carbon intensity, activity-data, emission-factor, and data-quality variables for research. This skill outputs YAML or JSON. It does not certify inventories, assure reports, validate compliance, or create audit-grade emissions claims.

Always read these shared rules first:

- `../_shared/01_claim_language_rules.md`
- `../_shared/02_evidence_lookup_rules.md`
- `../_shared/03_artifact_reading_rules.md`
- `../_shared/04_spec_drafting_rules.md`
- `../_shared/05_forbidden_fallbacks.md`
- `../_shared/06_reviewer_mode_rules.md`
- `../_shared/07_scholarly_depth_rules.md`
- `../_shared/08_domain_literature_anchor_rules.md`

Any causal, paper-ready, backend-certified, legal, fraud, or audit-grade claim must be supported by code artifacts and `claim_gate.json`.

## When to use

Use for Scope 1/2/3 boundaries, activity data times emission factor, factor versions, market-based versus location-based electricity, financed-emissions attribution, embedded product carbon, data quality scores, unit conversion, and double counting.

## Do not use when

Do not use for legal or assurance conclusions. Do not use as the main ETS, CBAM, or firm-productivity evaluation skill; hand off after variable construction. Do not hardcode current standards, reporting rules, factor versions, or data-source facts.

## Inputs expected

- Accounting target: firm, facility, product, portfolio, sector, supply chain, or unknown.
- Boundary: organization, operation, Scope categories, product boundary, or financed-emissions attribution.
- Activity data, emission-factor source/version, units, geography, year, and conversion steps.
- Electricity method, product allocation, portfolio weights, and data quality.
- Existing variable-construction or run artifacts when interpreting completed work.

## Required repo artifacts to inspect

Inspect `skill4econ/README.md`, `skill4econ/registry.yml`, `skill4econ/cli.py`, `skill4econ/core.py`, `skill4econ/python_wrappers.py`, `skill4econ/workflows.py`, `skill4econ/docs/ARTIFACT_CONTRACT.md`, `skill4econ/docs/BACKEND_CONTRACT.md`, `skill4econ/diagnostics/`, `skill4econ/tests/fixtures/`, and `skill4econ/tests/backends/`. For completed work inspect data manifests, conversion logs, factor-version logs, `status.json`, `manifest.json`, `artifact_manifest.json`, `reviewer_risk.json`, `diagnostics.json`, `backend_status.json`, `model_table.csv`, and `claim_gate.json` if present.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "WRI/WBCSD Greenhouse Gas Protocol Corporate Accounting and Reporting Standard, revised edition (2004)"
    - "GHG Protocol Scope 2 Guidance (2015)"
    - "GHG Protocol Corporate Value Chain (Scope 3) Accounting and Reporting Standard (2011)"
    - "GHG Protocol Product Life Cycle Accounting and Reporting Standard (2011)"
    - "PCAF Global GHG Accounting and Reporting Standard Part A: Financed Emissions, second edition (2022); third edition status must be checked live"
    - "Klaaßen and Stoll (2021), Nature Communications, Harmonizing corporate carbon footprints"
    - "Busch, Johnson, and Pioch (2022), Journal of Industrial Ecology, Corporate carbon performance data: Quo vadis?"
  canonical_data_sources:
    - "current Scope 2 guidance"
    - "regional residual-mix datasets"
    - "EAC quality criteria"
    - "assurance scope may cover only selected metrics"
    - "limited assurance is not reasonable assurance"
    - "vendor estimates should carry source and model flags"
    - "current CBAM and product-footprint rules"
    - "current LCA database versions"
    - "sector-specific embedded-emissions methods"
    - "Source provenance"
  live_lookup_required_for:
    - "current GHG Protocol update status"
    - "current Scope 2 revision proposals and final guidance status"
    - "current Scope 3 revision proposals and final guidance status"
    - "current product-standard updates and sector guidance"
    - "latest PCAF edition"
    - "current asset-class coverage"
    - "GHG Protocol review status"
    - "current GHG Protocol corporate-standard update status"
    - "current Scope 3 category guidance and revision status"
    - "current Scope 2 guidance"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "WRI/WBCSD Greenhouse Gas Protocol Corporate Accounting and Reporting Standard, revised edition (2004)"
    use_for: "organizational boundaries, Scope 1 and Scope 2 baseline accounting, consolidation approaches"
    live_lookup_required_for: ["current GHG Protocol update status"]

    citation: "GHG Protocol Scope 2 Guidance (2015)"
    use_for: "market-based versus location-based Scope 2 accounting, contractual instruments, residual mix, dual reporting"
    live_lookup_required_for: ["current Scope 2 revision proposals and final guidance status"]

    citation: "GHG Protocol Corporate Value Chain (Scope 3) Accounting and Reporting Standard (2011)"
    use_for: "15 Scope 3 categories, upstream/downstream boundaries, supplier data versus estimation"
    live_lookup_required_for: ["current Scope 3 revision proposals and final guidance status"]

    citation: "GHG Protocol Product Life Cycle Accounting and Reporting Standard (2011)"
    use_for: "embedded emissions, product footprints, cradle-to-gate/cradle-to-grave boundaries, allocation"
    live_lookup_required_for: ["current product-standard updates and sector guidance"]

    citation: "PCAF Global GHG Accounting and Reporting Standard Part A: Financed Emissions, second edition (2022); third edition status must be checked live"
    use_for: "financed emissions, attribution factors, asset-class methods, data-quality scores"
    live_lookup_required_for: ["latest PCAF edition", "current asset-class coverage", "GHG Protocol review status"]

    citation: "Klaaßen and Stoll (2021), Nature Communications, Harmonizing corporate carbon footprints"
    use_for: "Scope 3 incompleteness, boundary inconsistency, omitted emissions, harmonization"
    live_lookup_required_for: []

    citation: "Busch, Johnson, and Pioch (2022), Journal of Industrial Ecology, Corporate carbon performance data: Quo vadis?"
    use_for: "third-party provider inconsistency, vendor-estimated emissions, Scope 3 disagreement, reported versus estimated data"
    live_lookup_required_for: []
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "GHG Protocol organizational boundary"
    - "equity share, financial control, or operational control consolidation; Scope 1 direct emissions; Scope 2 purchased energy emissions"
    - "Scope 1, 2, and 3 separation"
    - "Scope 1 direct emissions; Scope 2 purchased electricity/steam/heat/cooling; Scope 3 value-chain emissions across 15 categories"
    - "Scope 2 location-based versus market-based"
    - "location-based grid-average emissions; market-based contractual instruments such as PPAs, supplier-specific factors, EACs, and residual mix"
    - "Audited versus estimated emissions"
    - "management-reported, third-party assured, regulator-verified, vendor-modelled, or imputed emissions"
    - "Financed emissions"
    - "attributed investee or borrower emissions using PCAF-style attribution factors and data-quality scores"
  validation_targets:
    - "Source provenance"
    - "Are emissions tagged as reported, assured, regulator-verified, vendor-estimated, imputed, or restated?"
    - "Boundary consistency"
    - "Do firm-year comparisons hold consolidation boundary, fiscal year, Scope coverage, and M&A treatment constant?"
    - "Scope 2 robustness"
    - "Are market-based and location-based Scope 2 results both shown, with claims limited to the accounting regime used?"
    - "Scope 3 materiality"
    - "Are Scope 3 categories identified separately, with supplier primary data distinguished from spend-based or industry-average estimates?"
    - "Financed-emissions formula"
    - "Are attribution factor, denominator, asset-class method, and PCAF data-quality score disclosed?"
  known_mismeasurement_channels:
    - "boundary switches create artificial trends"
    - "subsidiary coverage can differ across vendors"
    - "facility data may not reconcile to corporate data"
    - "Scope 3 is not optional noise when material"
    - "Scope 3 categories vary in data quality"
    - "double counting across firms is expected for value-chain accountability"
    - "market-based reductions can reflect certificate procurement rather than physical grid decarbonization"
    - "residual-mix availability differs by region"
    - "dual reporting may be mandatory under the guidance"
    - "assurance scope may cover only selected metrics"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "GHG Protocol organizational boundary"
    measure: "equity share, financial control, or operational control consolidation; Scope 1 direct emissions; Scope 2 purchased energy emissions"
    pitfalls: ["boundary switches create artificial trends", "subsidiary coverage can differ across vendors", "facility data may not reconcile to corporate data"]
    live_lookup_required_for: ["current GHG Protocol corporate-standard update status"]

    item: "Scope 1, 2, and 3 separation"
    measure: "Scope 1 direct emissions; Scope 2 purchased electricity/steam/heat/cooling; Scope 3 value-chain emissions across 15 categories"
    pitfalls: ["Scope 3 is not optional noise when material", "Scope 3 categories vary in data quality", "double counting across firms is expected for value-chain accountability"]
    live_lookup_required_for: ["current Scope 3 category guidance and revision status"]

    item: "Scope 2 location-based versus market-based"
    measure: "location-based grid-average emissions; market-based contractual instruments such as PPAs, supplier-specific factors, EACs, and residual mix"
    pitfalls: ["market-based reductions can reflect certificate procurement rather than physical grid decarbonization", "residual-mix availability differs by region", "dual reporting may be mandatory under the guidance"]
    live_lookup_required_for: ["current Scope 2 guidance", "regional residual-mix datasets", "EAC quality criteria"]

    item: "Audited versus estimated emissions"
    measure: "management-reported, third-party assured, regulator-verified, vendor-modelled, or imputed emissions"
    pitfalls: ["assurance scope may cover only selected metrics", "limited assurance is not reasonable assurance", "vendor estimates should carry source and model flags"]
    live_lookup_required_for: ["current assurance standard", "current disclosure mandate", "vendor data vintage"]

    item: "Financed emissions"
    measure: "attributed investee or borrower emissions using PCAF-style attribution factors and data-quality scores"
    pitfalls: ["portfolio value changes can move financed emissions without real-economy decarbonization", "EVIC and outstanding amount denominators matter", "asset-class methods are not interchangeable"]
    live_lookup_required_for: ["latest PCAF standard", "current asset-class formulas", "current data-quality scoring"]

    item: "Embedded emissions"
    measure: "product or trade-flow emissions using product carbon footprints, LCA factors, process data, or input-output factors"
    pitfalls: ["cradle-to-gate versus cradle-to-grave boundaries change estimates", "allocation rules can dominate product footprints", "sector-specific rules differ for CBAM-like uses"]
    live_lookup_required_for: ["current CBAM and product-footprint rules", "current LCA database versions", "sector-specific embedded-emissions methods"]

    item: "Vendor-estimated ESG emissions"
    measure: "commercial-provider reported/modelled flags, imputation model, fiscal year, restatements, missingness, Scope 3 coverage"
    pitfalls: ["missingness is often not random", "large firms and regulated sectors disclose differently", "provider estimates can diverge materially for non-reporters and Scope 3"]
    live_lookup_required_for: ["vendor methodology version", "coverage universe", "restatement policy", "latest data vintage"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "attenuation or sign reversal when estimated emissions are treated as audited facts"
    - "claiming physical decarbonization from market-based accounting alone"
    - "using total corporate Scope 1+2+3 sums as if they were additive social emissions"
    - "mistaking disclosure changes for real emissions changes"
    - "claiming portfolio decarbonization from divestment or denominator movements alone"
    - "comparing products or imports with incompatible footprint boundaries"
  sorting_vs_siting_or_selection_channel:
    - "Auditing and disclosure selection"
    - "selection models"
    - "mandate/event controls"
    - "balanced panels"
    - "assurance-status interactions"
    - "MNAR sensitivity"
  why_method_not_magic:
    - "Scope 3 is decision-useful but cannot be aggregated across firms as unique economy-wide emissions without double counting."
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Measurement error"
    core_issue: "Emissions variables can contain classical error, systematic vendor bias, boundary error, and non-random missingness."
    acceptable_designs: ["source-flag controls", "reported-only robustness", "multiple-vendor comparison", "measurement-error sensitivity bounds", "imputation uncertainty"]
    referee_risk: "attenuation or sign reversal when estimated emissions are treated as audited facts"
    live_lookup_required_for: ["current vendor methodology and data vintage"]

    item: "Scope 2 interpretation"
    core_issue: "Market-based Scope 2 may capture procurement strategy; location-based Scope 2 better tracks local grid emissions exposure."
    acceptable_designs: ["dual Scope 2 outcomes", "certificate-procurement controls", "grid-factor robustness", "separate physical and contractual claims"]
    referee_risk: "claiming physical decarbonization from market-based accounting alone"
    live_lookup_required_for: ["current Scope 2 guidance and residual-mix factors"]

    item: "Scope 3 and double counting"
    core_issue: "Scope 3 is decision-useful but cannot be aggregated across firms as unique economy-wide emissions without double counting."
    acceptable_designs: ["category-level Scope 3 analysis", "materiality screens", "supplier/customer network checks", "reported-versus-estimated separation"]
    referee_risk: "using total corporate Scope 1+2+3 sums as if they were additive social emissions"
    live_lookup_required_for: ["current Scope 3 category guidance"]

    item: "Auditing and disclosure selection"
    core_issue: "Assured or disclosed emissions are selected by jurisdiction, firm size, sector, investor pressure, and regulation."
    acceptable_designs: ["selection models", "mandate/event controls", "balanced panels", "assurance-status interactions", "MNAR sensitivity"]
    referee_risk: "mistaking disclosure changes for real emissions changes"
    live_lookup_required_for: ["current disclosure and assurance mandates"]

    item: "Financed-emissions attribution"
    core_issue: "Financed emissions mix investee emissions, attribution denominators, exposure changes, and portfolio composition."
    acceptable_designs: ["decomposition into investee emissions, ownership/exposure, denominator, and portfolio rebalancing", "asset-class-specific formulas"]
    referee_risk: "claiming portfolio decarbonization from divestment or denominator movements alone"
    live_lookup_required_for: ["latest PCAF formulas and data-quality scores"]

    item: "Embedded-emissions modelling"
    core_issue: "Embedded emissions depend on process boundaries, allocation rules, input-output assumptions, geography, and time-varying energy mixes."
    acceptable_designs: ["boundary disclosure", "LCA/input-output sensitivity", "supplier-specific versus default-factor robustness", "sector-rule alignment"]
    referee_risk: "comparing products or imports with incompatible footprint boundaries"
    live_lookup_required_for: ["current sector methods and factor databases"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Source provenance"
    - "Are emissions tagged as reported, assured, regulator-verified, vendor-estimated, imputed, or restated?"
    - "Boundary consistency"
    - "Do firm-year comparisons hold consolidation boundary, fiscal year, Scope coverage, and M&A treatment constant?"
    - "Scope 2 robustness"
    - "Are market-based and location-based Scope 2 results both shown, with claims limited to the accounting regime used?"
    - "Scope 3 materiality"
    - "Are Scope 3 categories identified separately, with supplier primary data distinguished from spend-based or industry-average estimates?"
    - "Financed-emissions formula"
    - "Are attribution factor, denominator, asset-class method, and PCAF data-quality score disclosed?"
  minimal_empirical_section_checklist:
    - "Source provenance"
    - "Are emissions tagged as reported, assured, regulator-verified, vendor-estimated, imputed, or restated?"
    - "vendor methodology version"
    - "assurance-standard status"
    - "Boundary consistency"
    - "Do firm-year comparisons hold consolidation boundary, fiscal year, Scope coverage, and M&A treatment constant?"
    - "current reporting-boundary guidance"
    - "Scope 2 robustness"
    - "Are market-based and location-based Scope 2 results both shown, with claims limited to the accounting regime used?"
    - "current Scope 2 guidance and residual mix"
  claims_to_downgrade:
    - "Do not treat vendor-estimated ESG emissions as audited or regulator-verified facts."
    - "Do not aggregate Scope 3 across firms as economy-wide emissions without a double-counting caveat."
    - "Do not claim market-based Scope 2 reductions prove physical grid decarbonization."
    - "Do not compare firms without checking organizational boundary, fiscal year, consolidation method, and restatement history."
    - "Do not infer real-economy decarbonization from financed-emissions declines without decomposing investee emissions, portfolio weights, attribution denominators, and divestment."
    - "Do not use embedded emissions without stating product boundary, allocation rule, factor source, geography, and vintage."
    - "Do not make current claims about GHG Protocol revisions, PCAF editions, CBAM rules, assurance mandates, SEC/CSRD/SB 253 status, or registry datasets without live lookup."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Source provenance"
    ask: "Are emissions tagged as reported, assured, regulator-verified, vendor-estimated, imputed, or restated?"
    live_lookup_required_for: ["vendor methodology version", "assurance-standard status"]

    check: "Boundary consistency"
    ask: "Do firm-year comparisons hold consolidation boundary, fiscal year, Scope coverage, and M&A treatment constant?"
    live_lookup_required_for: ["current reporting-boundary guidance"]

    check: "Scope 2 robustness"
    ask: "Are market-based and location-based Scope 2 results both shown, with claims limited to the accounting regime used?"
    live_lookup_required_for: ["current Scope 2 guidance and residual mix"]

    check: "Scope 3 materiality"
    ask: "Are Scope 3 categories identified separately, with supplier primary data distinguished from spend-based or industry-average estimates?"
    live_lookup_required_for: ["current Scope 3 category guidance"]

    check: "Financed-emissions formula"
    ask: "Are attribution factor, denominator, asset-class method, and PCAF data-quality score disclosed?"
    live_lookup_required_for: ["latest PCAF edition and formulas"]

    check: "Embedded-emissions boundary"
    ask: "Does the analysis specify cradle-to-gate/cradle-to-grave boundary, allocation rule, factor database, and sector rule?"
    live_lookup_required_for: ["current product-footprint, CBAM, and LCA factor rules"]

    check: "Missingness and vendor error"
    ask: "Are missing emissions treated as potentially non-random, with uncertainty from vendor estimates propagated into inference?"
    live_lookup_required_for: ["current provider coverage and restatement files"]
```

## Forbidden claims

- Do not treat vendor-estimated ESG emissions as audited or regulator-verified facts.
- Do not aggregate Scope 3 across firms as economy-wide emissions without a double-counting caveat.
- Do not claim market-based Scope 2 reductions prove physical grid decarbonization.
- Do not compare firms without checking organizational boundary, fiscal year, consolidation method, and restatement history.
- Do not infer real-economy decarbonization from financed-emissions declines without decomposing investee emissions, portfolio weights, attribution denominators, and divestment.
- Do not use embedded emissions without stating product boundary, allocation rule, factor source, geography, and vintage.
- Do not make current claims about GHG Protocol revisions, PCAF editions, CBAM rules, assurance mandates, SEC/CSRD/SB 253 status, or registry datasets without live lookup.

## Domain reasoning steps

1. Classify the requested claim before variable construction: measurement variable, disclosed-accounting variable, attributed exposure, association, candidate causal effect, compliance/legal claim, or audit/assurance claim. This skill supports measurement variables, disclosed-accounting variables, and attributed exposure metrics. Association or causal claims require a separate econometric design handoff. Compliance, legal, fraud, and audit/assurance claims are blocked unless external authority, code artifacts, and `claim_gate.json` support them.

2. Define the estimand with unit, time period, target population, numerator, denominator, boundary, and aggregation rule before naming any accounting standard. A usable estimand must state whether it is firm-year, facility-year, product-batch, portfolio-year, sector-year, or supply-chain exposure; whether the period is fiscal year, calendar year, or reporting year; and whether the value is physical emissions, disclosed emissions, attributed emissions, embedded carbon, intensity, or exposure proxy.

3. For pure MRV or carbon-accounting variables, treat `identification_assumptions` as measurement-validity assumptions, not causal identification assumptions. Use causal language only after a separate research design specifies treatment, counterfactual, timing, identifying variation, and diagnostics.

4. Set the organizational boundary before the operational boundary. Name whether the design uses operational control, financial control, equity share, facility ownership, consolidated group, product boundary, portfolio holding, loan exposure, or input-output sector boundary. Flag M&A, divestitures, outsourcing, subsidiaries, joint ventures, and facility coverage changes as potential breaks in comparability.

5. Keep Scope 1, Scope 2 location-based, Scope 2 market-based, Scope 3 category-specific variables, financed-emissions attribution, embedded product carbon, and IO-based exposure as separate estimands unless a defensible aggregation rule and double-counting note are explicit. For Scope 1/2 examples, do not introduce Scope 3 supplier, customer, or financed-emissions items.

6. Write the measurement equation for each emissions variable. At minimum, specify:
   - Scope 1: fuel, process, and fugitive activity data by type times source-specific emission factors, with unit conversions and factor year/version.
   - Scope 2 location-based: purchased electricity, steam, heat, or cooling times grid-average or location-specific factors, with geography and year.
   - Scope 2 market-based: contractual instruments, residual mix, supplier-specific factors, or market instruments as separate variables from location-based emissions.
   - Intensity: emissions numerator divided by output, sales, value added, production volume, assets, revenue, or portfolio exposure, with deflator and currency treatment where relevant.

7. Require factor provenance. For every emission factor, name source, version, geography, year, GWP basis if relevant, gas coverage, unit, and whether the factor is fuel-specific, grid-average, supplier-specific, sector-average, spend-based, physical-activity-based, or input-output based.

8. Require activity-data provenance. For every activity input, state whether it comes from metered facility data, invoices, firm disclosures, regulatory filings, production records, supplier reports, portfolio holdings, loan books, customs/product records, or estimated spend. Treat reported totals, estimated activity, and spend-based proxies as different measurement tiers.

9. For Scope 3, name the category, supplier/customer side, physical or spend denominator, sector/product concordance, factor source, missingness mechanism, estimation tier, and whether overlap with Scope 1/2, other Scope 3 categories, or financed emissions is possible.

10. For financed emissions, specify asset class, attribution factor, exposure numerator, denominator such as enterprise value, book value, project value, or loan share, time stamp of exposure, portfolio coverage, and treatment of listed/private firms. State explicitly that the result is an attributed portfolio exposure metric, not the financial institution's direct operating emissions and not proof that financing caused client emissions.

11. For embedded carbon and CBAM-style product exposure, specify product boundary, product-sector concordance, direct versus embodied emissions, domestic/import treatment, allocation rule, physical unit, customs or production data source, and whether product carbon is measured, disclosed, modeled, or inferred from sector averages.

12. Name concrete data-construction risks before methods: incompatible units, fuel-to-energy conversion, electricity kWh versus MWh, mass versus CO2e, currency deflators, fiscal/calendar year mismatch, factor geography mismatch, factor-year mismatch, facility-to-firm merge errors, duplicate firm-year rows, changing corporate boundaries, partial facility coverage, missing activity data, estimated values mixed with observed values, and unresolved double counting.

13. Use the research-design decision tree:
   - If activity data, factors, units, and boundaries are traceable, construct a measurement variable.
   - If only disclosed emissions totals are available, construct a disclosed-emissions variable and do not treat it as physical emissions without caveat.
   - If only spend, sector averages, or IO factors are available, construct an exposure or proxy variable and downgrade any inventory-style claim.
   - If the user wants an association with financial, policy, or real outcomes, hand off after variable construction to an econometric design skill.
   - If the user wants a causal effect, require treatment timing, comparison group, identifying variation, and causal diagnostics outside this skill.
   - If the user wants audit, assurance, compliance, fraud, or legal conclusions, block the claim unless external authority and `claim_gate.json` support it.

14. Name diagnostics that block strong claims: missing activity manifest, missing factor source or version, unresolved unit conversion, unknown geography, unknown reporting period, missing boundary, unobserved denominator, unexplained imputation, duplicate unit-time rows, inconsistent aggregation across subsidiaries, location-based and market-based Scope 2 mixed together, unresolved Scope 1/2/3 overlap, financed emissions treated as direct emissions, or absent `claim_gate.json`.

15. Rank robustness checks by the risks most likely to overturn the conclusion: boundary/consolidation changes; observed versus imputed activity data; factor geography/year/version; denominator choice for intensity; facility or portfolio coverage; double-counting exclusions; alternative factor databases; fiscal versus calendar timing; and exclusion of low-quality observations. Do not present location-based versus market-based Scope 2 as a mere robustness check when they are different estimands.

16. Anticipate referee objections in domain language: estimated emissions are not audited emissions; intensity reductions may reflect output or denominator changes rather than emissions reductions; market-based Scope 2 may reflect procurement instruments rather than physical grid emissions; factor choice may drive cross-country or cross-sector rankings; outsourced production may move emissions across scopes; disclosure incentives can change measured emissions; and financed-emissions attribution is not causal responsibility.

17. Use downgrade language aggressively. Downgrade to descriptive measurement, disclosed-accounting variable, exposure proxy, or association-only whenever boundaries, factors, activity data, units, coverage, double counting, or claim gate are insufficient.

## Candidate outputs

- `carbon_accounting_mrv` YAML or JSON plan.
- Boundary and data-quality checklist.
- Econometric variable candidates.
- Caveated claim-language block.

## Output schema

Return YAML by default, or JSON if requested. Include at least:

```yaml
skill_name: carbon_accounting_mrv
user_question_summary: string
research_domain: carbon_accounting_mrv
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: null
  estimand_candidates: []
  identification_risks: []
carbon_accounting_mrv:
  accounting_target: firm | facility | product | portfolio | sector | supply_chain | unknown
  scope_boundary: []
  required_activity_data: []
  emission_factor_needs: []
  unit_conversion_needs: []
  data_quality_risks: []
  double_counting_risks: []
  variables_for_econometrics: []
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

- Estimated emissions are not audited emissions.
- Scope aggregation is only interpretable with explicit boundary notes.
- Financed emissions are attributed exposure metrics, not direct financial-institution operating emissions.
- Factor versions, standards, and reporting rules are volatile; query official/latest sources.
- Data quality scores are measurement-risk indicators, not proof of truth.

## Forbidden claims

- Do not call estimated emissions audited, verified, assured, or compliance-grade without artifacts and claim gate.
- Do not mix Scope 1/2/3 without boundary and double-counting notes.
- Do not call financed emissions direct bank operating emissions.
- Do not ignore unit conversion, factor version, or factor geography.
- Do not fill missing activity data with arbitrary factors and call it equivalent.

## Handoff to code

Draft a variable-construction spec with target, boundary, activity data, factors, units, conversion formulas, data quality, double-counting checks, and intended econometric variables. Ask code to validate units, merges, duplicate unit-time rows, missingness, and provenance. Do not output raw Stata or R commands.

## Handoff from code artifacts

Read data manifests, factor logs, conversion logs, `status.json`, `manifest.json`, `artifact_manifest.json`, `reviewer_risk.json`, and `claim_gate.json` if present. If `claim_gate.json` is absent, claim readiness is not established. If proxy, missingness, factor, or boundary risk appears, use measurement-limited language.

## Minimal examples

### Example 1: Scope 1/2 intensity construction

#### Input

User: I need Scope 1 and Scope 2 emissions intensity for firms using fuel, electricity, and output data.

#### Expected skill output

```yaml
skill_name: carbon_accounting_mrv
user_question_summary: "Construct firm-year Scope 1 and Scope 2 emissions intensity variables."
research_domain: carbon_accounting
research_brief:
  unit: firm
  time_frequency: year
  outcome_candidates: [scope_1_emissions_intensity, scope_2_location_based_intensity, scope_2_market_based_intensity]
  treatment_or_exposure: emissions_accounting_variable
  estimand_candidates: [measurement_variable]
  identification_risks: [measurement_error, factor_version_choice, output_denominator_choice]
carbon_accounting_mrv:
  accounting_target: firm
  scope_boundary: [Scope_1, Scope_2_location_based, Scope_2_market_based]
  required_activity_data: [fuel_use_by_type, purchased_electricity, output_or_sales_denominator]
  emission_factor_needs: [fuel_factor_source, grid_factor_source, market_instrument_factor_source, factor_year, factor_geography]
  unit_conversion_needs: [fuel_energy_units, electricity_units, mass_units, output_units]
  data_quality_risks: [estimated_fuel_use, missing_metered_electricity, mismatched_factor_geography, denominator_choice]
  double_counting_risks: [purchased_heat_steam_cooling_scope_2_treatment, location_vs_market_based_electricity_confusion]
  variables_for_econometrics: [scope_1_intensity, scope_2_location_based_intensity, scope_2_market_based_intensity]
  forbidden_claims: [do_not_call_estimated_emissions_audit_grade, do_not_mix_location_and_market_based_scope_2]
scholarly_depth:
  estimand_definition: >
    For firm i in reporting year t, construct three separate measurement estimands:
    Scope 1 emissions intensity = Scope 1 emissions from owned or controlled fuel,
    process, and fugitive sources divided by a pre-specified output denominator;
    Scope 2 location-based intensity = purchased electricity, steam, heat, or
    cooling multiplied by location/grid factors divided by the same denominator;
    Scope 2 market-based intensity = contractual or residual-mix electricity
    factors divided by the same denominator. These are constructed measurement
    variables, not audited inventories, compliance findings, or causal effects.
  identification_assumptions:
    - "For this MRV task, these are measurement-validity assumptions rather than causal identification assumptions."
    - "The organizational boundary is stable or boundary changes are explicitly recorded."
    - "Facility-level activity data can be correctly assigned to firm-year observations."
    - "Emission factors match the activity geography, fuel/electricity type, year, unit, and factor version."
    - "The output denominator is measured consistently across firms and years."
  measurement_model:
    - "scope1_it = sum over fuels/process/fugitive sources of activity_iat * emission_factor_a,g,t,v * unit_conversion_a"
    - "scope2_location_it = purchased_energy_igt * grid_or_location_factor_g,t,v * unit_conversion"
    - "scope2_market_it = contracted_or_residual_energy_ikt * market_based_factor_k,t,v * unit_conversion"
    - "intensity_it = emissions_it / denominator_it, where denominator choice is fixed before estimation"
    - "Observed, disclosed, estimated, and imputed activity data must be stored as separate data-quality tiers."
  data_construction_risks:
    - "fuel units such as volume, mass, GJ, therms, and kWh are not harmonized"
    - "electricity, steam, heat, or cooling purchases are assigned to the wrong geography or year"
    - "market-based instruments are mixed with location-based grid factors"
    - "facility records fail to cover all subsidiaries or operating sites"
    - "M&A, divestitures, or outsourcing change the firm boundary over time"
    - "fiscal-year output denominators are merged with calendar-year emissions"
    - "revenue denominators lack currency, inflation, or exchange-rate treatment"
    - "duplicate facility-firm-year rows create double counting"
  method_decision_tree:
    - "If metered activity data, factors, units, and boundaries are traceable, construct Scope 1 and Scope 2 measurement variables."
    - "If only firm-disclosed Scope totals are available, construct disclosed-emissions variables and downgrade physical-emissions language."
    - "If only spend or sector-average activity is available, construct a proxy or exposure variable, not an inventory-style estimate."
    - "If the user asks whether emissions changed because of a policy, financing, or management action, hand off to a causal-design skill after variable construction."
    - "If the user asks for compliance, audit, assurance, or legal conclusions, block the claim without external authority and claim gate."
  diagnostics_that_block_claims:
    - "missing activity-data manifest"
    - "missing emission-factor source, geography, year, or version"
    - "unresolved unit conversion"
    - "unknown organizational or operational boundary"
    - "location-based and market-based Scope 2 combined without an explicit rule"
    - "unexplained imputation or estimated activity share"
    - "duplicate firm-year or facility-year rows"
    - "absent claim_gate.json for strong claims"
  robustness_ranked_by_risk:
    - "restrict to observations with observed rather than imputed activity data"
    - "exclude firms with boundary-changing M&A, divestitures, or major facility coverage breaks"
    - "use alternative factor geography, year, or version where defensible"
    - "test alternative output denominators such as physical output, sales, value added, or assets"
    - "separate location-based and market-based Scope 2 rather than averaging them"
    - "drop low-data-quality observations or report results by data-quality tier"
  referee_objections:
    - "The variables are estimated or disclosed measures, not audited emissions."
    - "Carbon intensity may move because the denominator changes, not because emissions fall."
    - "Market-based Scope 2 may reflect contractual instruments rather than physical electricity consumption."
    - "Cross-firm comparisons may be driven by factor geography or boundary differences."
    - "Corporate restructuring or outsourcing may shift emissions across scopes."
  downgrade_triggers:
    - "only disclosed totals are available without activity data"
    - "factor version or geography is unknown"
    - "organizational boundary is missing or changes without documentation"
    - "activity data are mostly imputed or spend-based"
    - "location-based and market-based electricity are mixed"
    - "no claim_gate.json for audit-grade, compliance, causal, or paper-ready claims"
candidate_workflows: [data_inventory]
candidate_methods: [mrv_variable_construction, sensitivity_to_factors]
required_diagnostics: [unit_conversion_check, provenance_check]
recommended_robustness: [alternative_emission_factors, alternative_output_denominators]
forbidden_claims: [respect_claim_gate]
claim_language:
  allowed: ["Research variable construction plan for Scope 1 and Scope 2 intensity."]
  disallowed: ["Regulatory-compliant or audited emissions inventory."]
uncertainty_notes: [Verify official/latest standards and factors at use time.]
next_code_actions: [build_variable_manifest]
```

### Example 2: Scope 3 and financed-emissions downgrade

#### Input

User: Use supplier spend and loan exposure to prove this bank caused its clients' emissions.

#### Expected skill output

```yaml
skill_name: carbon_accounting_mrv
user_question_summary: "Assess whether supplier spend and loan exposure can form Scope 3 or financed-emissions research variables."
research_domain: carbon_accounting
research_brief:
  unit: bank_or_portfolio
  time_frequency: year
  outcome_candidates: [financed_emissions_exposure, scope_3_supplier_exposure]
  treatment_or_exposure: portfolio_or_supplier_activity
  estimand_candidates: [attributed_exposure_metric]
  identification_risks: [attribution_not_causation, double_counting, missing_client_boundary]
carbon_accounting_mrv:
  accounting_target: portfolio
  scope_boundary: [Scope_3_category_specific, financed_emissions_attribution]
  required_activity_data: [supplier_spend, loan_exposure, client_emissions_or_sector_factors]
  emission_factor_needs: [sector_factor_source, factor_year, factor_geography, asset_class_guidance]
  unit_conversion_needs: [currency_deflator, exposure_denominator, emissions_units]
  data_quality_risks: [estimated_client_emissions, missing_supplier_physical_activity, sector_average_factors]
  double_counting_risks: [supplier_customer_overlap, portfolio_company_overlap, scope_3_and_financed_emissions_overlap]
  variables_for_econometrics: [scope_3_exposure_proxy, financed_emissions_attributed_exposure]
  forbidden_claims: [do_not_claim_bank_caused_client_emissions, do_not_call_financed_emissions_operating_emissions]
scholarly_depth:
  estimand_definition: "Attributed value-chain or portfolio emissions exposure, not a causal effect of lending on emissions."
  identification_assumptions: [none_for_causal_claim_without_separate_design]
  measurement_model: [spend_or_exposure_times_factor_or_client_emissions]
  data_construction_risks: [sector_factor_noise, missing_client_boundary, double_counting]
  method_decision_tree: [construct_exposure_metric_for_descriptive_or_risk_analysis, require_separate_causal_design_for_effect_claims]
  diagnostics_that_block_claims: [no_asset_class_attribution_rule, unknown_factor_version, unresolved_double_counting]
  robustness_ranked_by_risk: [alternative_factors, alternative_attribution_denominators, exclude_low_quality_observations]
  referee_objections: [attribution_is_not_causation, factor_choice_may_dominate, exposure_values_change_with_market_conditions]
  downgrade_triggers: [missing_client_emissions, missing_factor_source, no_claim_gate]
candidate_workflows: [data_inventory, mrv_variable_construction]
candidate_methods: [descriptive_exposure_construction, sensitivity_to_factors]
required_diagnostics: [attribution_rule_check, double_counting_check, provenance_check]
recommended_robustness: [alternative_sector_factors, alternative_exposure_denominators]
forbidden_claims: [respect_claim_gate, no_causal_or_audit_grade_claim]
claim_language:
  allowed: ["Attributed financed-emissions exposure variable for research."]
  disallowed: ["The bank caused or audited these emissions."]
uncertainty_notes: [Check official/latest GHG Protocol, PCAF, IFRS, and factor-source guidance at use time.]
next_code_actions: [build_portfolio_exposure_manifest, run_double_counting_checks]
```

## Completion checklist

- Fixed sections are present.
- YAML or JSON output is required.
- Scope, units, factors, data quality, and double counting are explicit.
- Official/latest sources are required for standards and factors.
- Strong claims route through artifacts and `claim_gate.json`.
