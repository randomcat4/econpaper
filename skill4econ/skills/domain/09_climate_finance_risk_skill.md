# Skill: climate_finance_risk

## Purpose

Plan scholar-grade climate finance risk research for physical risk, transition risk, liability risk, portfolio exposure, financed emissions, asset pricing, lending, default risk, event studies, and scenario stress tests.

This skill separates four objects that are often conflated:

1. exposure construction;
2. exposure-outcome association;
3. event response;
4. causal financial effect.

It is a prompt and research-design rubric. It does not run estimators, validate backends, certify artifacts, provide investment advice, forecast realized losses, or issue regulatory, legal, compliance, capital, audit, or assurance conclusions.

Always read these shared rules before using this skill:

* `../_shared/01_claim_language_rules.md`
* `../_shared/02_evidence_lookup_rules.md`
* `../_shared/03_artifact_reading_rules.md`
* `../_shared/04_spec_drafting_rules.md`
* `../_shared/05_forbidden_fallbacks.md`
* `../_shared/06_reviewer_mode_rules.md`
* `../_shared/07_scholarly_depth_rules.md`
* `../_shared/08_domain_literature_anchor_rules.md`

Any causal, paper-ready, backend-certified, legal, fraud, regulatory, audit-grade, or investment-relevant claim must be supported by code artifacts and `claim_gate.json`.

## When to use

Use this skill when climate risk exposure is linked to a financial outcome, including:

* physical risk from flood, wildfire, heat, storms, sea-level rise, drought, or compound hazards;
* asset, facility, mortgage, municipal, sovereign, issuer, loan-book, or portfolio exposure;
* transition risk from carbon prices, climate policy, disclosure rules, technology shifts, sector carbon intensity, stranded-asset proxies, or energy mix;
* portfolio metrics such as weighted average carbon intensity, financed emissions, sector-country exposure, issuer exposure, holdings exposure, or loan-book exposure;
* bond yields, credit spreads, loan spreads, stock returns, default risk, credit ratings, bank lending, insurance pricing, or portfolio weights;
* event studies around policy announcements, disclosure rules, rating changes, disaster events, lawsuits, supervisory communications, or climate news;
* scenario analysis used as stress-test assumptions or exposure mapping, not as forecasts.

## Do not use when

Do not use this skill for pure carbon accounting without a financial outcome; use a carbon accounting or MRV skill instead.

Do not use this skill to:

* recommend buying, selling, shorting, hedging, divesting, or reallocating assets;
* forecast realized losses, returns, defaults, credit events, or regulatory capital needs;
* certify compliance with climate disclosure, prudential, accounting, taxonomic, supervisory, legal, audit, or assurance requirements;
* treat climate scenarios as predictions;
* treat weighted average carbon intensity, financed emissions, or sector-country exposure as complete climate risk;
* treat exposure construction as evidence of financial pricing or causality;
* hardcode current taxonomies, disclosure rules, supervisory rules, scenarios, hazard products, carbon prices, emissions factors, or financial-data definitions.

Volatile facts about policies, regulations, taxonomies, scenarios, standards, satellite or hazard products, financial databases, and reporting rules require official/latest lookup at use time.

## Inputs expected

* Research question, intended contribution, unit of analysis, sample window, and time frequency.
* Climate risk type: physical, transition, liability, mixed, or unknown.
* Exposure target and source: hazard layer, asset geography, issuer-sector mapping, borrower emissions, energy mix, carbon price, policy exposure, financed emissions, or portfolio holdings.
* Financial outcome candidates: bond yield, credit spread, loan spread, stock return, default risk, rating migration, bank lending, insurance premium, or portfolio weight.
* Event definition when relevant: policy announcement, disclosure rule, climate rating change, disaster event, litigation event, or supervisory communication.
* Controls and confounders: sector, country, region, maturity, duration, rating, currency, liquidity, leverage, size, profitability, collateral, borrower risk, lender risk appetite, macro shocks, energy prices, and monetary policy shocks.
* Existing exposure-construction artifacts, scenario manifests, diagnostics, run artifacts, or claim-gate outputs when interpreting completed work.

## Required repo artifacts to inspect

Inspect workspace files first. Do not rely on installed user-level skills as the authority for this repository.

Repository structure and contracts: `README.md`, `registry.yml`, `cli.py`, `core.py`, `python_wrappers.py`, `workflows.py`, `docs/ARTIFACT_CONTRACT.md` when present, `docs/BACKEND_CONTRACT.md` when present, `diagnostics/`, `tests/fixtures/`, and `tests/backends/`.

Shared rules: `skills/_shared/01_claim_language_rules.md`, `skills/_shared/02_evidence_lookup_rules.md`, `skills/_shared/03_artifact_reading_rules.md`, `skills/_shared/04_spec_drafting_rules.md`, `skills/_shared/05_forbidden_fallbacks.md`, `skills/_shared/06_reviewer_mode_rules.md`, and `skills/_shared/07_scholarly_depth_rules.md`.

Run artifacts when a run exists: exposure construction manifest, scenario manifest, portfolio matching manifest, `status.json`, `manifest.json` or `artifact_manifest.json`, `diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json` or `backend_status.json`, `model_table.csv`, and `claim_gate.json`.

If these artifacts are absent, exposure, association, event-response, scenario, or causal claims must be marked as unknown, partial, exploratory, or blocked as appropriate.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Bolton and Kacperczyk (2021), Journal of Financial Economics, Do Investors Care about Carbon Risk?"
    - "Bolton and Kacperczyk (2023), Journal of Political Economy, Global Pricing of Carbon-Transition Risk"
    - "Engle, Giglio, Kelly, Lee, and Stroebel (2020), Review of Financial Studies, Hedging Climate Change News"
    - "Painter (2020), Review of Financial Studies, An Inconvenient Cost"
    - "Giglio, Maggiori, Rao, Stroebel, and Weber (2021), Review of Financial Studies, Climate Change and Long-Run Discount Rates"
    - "Murfin and Spiegel (2020), Review of Financial Studies, Is the Risk of Sea Level Rise Capitalized in Residential Real Estate?"
    - "Ilhan, Sautner, and Vilkov (2021), Review of Financial Studies, Carbon Tail Risk"
  canonical_data_sources:
    - "current regulator rules"
    - "current litigation and enforcement datasets"
    - "current taxonomy status"
    - "current factor data"
    - "current bond/credit-spread database vintage"
    - "current ESG index methodology"
    - "current loan-pricing datasets"
    - "current rating-agency criteria"
    - "current insurance filings and reinsurance data"
    - "current reserve disclosures"
  live_lookup_required_for:
    - "current climate-news index data vintage"
    - "current hazard-model provider version"
    - "current FEMA/First Street/NOAA/CMIP data vintage"
    - "current insurance-market rules"
    - "current emissions-provider vintage"
    - "current carbon-price and taxonomy rules"
    - "current NGFS scenario vintage"
    - "current regulator rules"
    - "current litigation and enforcement datasets"
    - "current taxonomy status"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Bolton and Kacperczyk (2021), Journal of Financial Economics, Do Investors Care about Carbon Risk?"
    use_for: "carbon premium, emissions exposure, asset-pricing tests"
    live_lookup_required: []

    citation: "Bolton and Kacperczyk (2023), Journal of Political Economy, Global Pricing of Carbon-Transition Risk"
    use_for: "international carbon-transition risk pricing and cross-country heterogeneity"
    live_lookup_required: []

    citation: "Engle, Giglio, Kelly, Lee, and Stroebel (2020), Review of Financial Studies, Hedging Climate Change News"
    use_for: "climate beta, climate-news hedging portfolios, asset-pricing exposure construction"
    live_lookup_required: ["current climate-news index data vintage"]

    citation: "Painter (2020), Review of Financial Studies, An Inconvenient Cost"
    use_for: "municipal bond pricing of sea-level-rise exposure"
    live_lookup_required: []

    citation: "Giglio, Maggiori, Rao, Stroebel, and Weber (2021), Review of Financial Studies, Climate Change and Long-Run Discount Rates"
    use_for: "real estate, long-horizon climate beliefs, discount rates"
    live_lookup_required: []

    citation: "Murfin and Spiegel (2020), Review of Financial Studies, Is the Risk of Sea Level Rise Capitalized in Residential Real Estate?"
    use_for: "physical risk capitalization debate and housing-market evidence"
    live_lookup_required: []

    citation: "Ilhan, Sautner, and Vilkov (2021), Review of Financial Studies, Carbon Tail Risk"
    use_for: "option-implied carbon tail risk and downside protection"
    live_lookup_required: []
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "Physical risk"
    - "asset-level exposure to flood, wildfire, heat, drought, hurricane, sea-level rise, water stress, and chronic climate hazards"
    - "headquarters location is not asset location"
    - "hazard exposure is not realized damage"
    - "insurance and adaptation alter net exposure"
    - "maps and scenarios have vintages"
    - "Transition risk"
    - "carbon emissions, fossil-fuel reserves, energy intensity, technology exposure, policy exposure, carbon-price sensitivity, green revenue"
    - "emissions data may be estimated"
    - "Scope 3 dominates for some sectors"
  validation_targets:
    - "Channel separation"
    - "Are physical, transition, and regulatory risks measured separately rather than hidden inside one ESG or climate score?"
    - "Location validity"
    - "Does exposure use asset, facility, collateral, or revenue geography rather than headquarters when location matters?"
    - "Pricing specification"
    - "Do tests distinguish risk premium, mispricing, liquidity, ratings, sector composition, and investor clientele?"
    - "Credit and loan mechanisms"
    - "Are spreads, covenants, maturity, collateral, and lender selection modeled jointly?"
    - "Insurance mechanism"
    - "Are insurance repricing, nonrenewal, deductibles, regulation, and reinsurance shocks separated?"
  known_mismeasurement_channels:
    - "Physical risk"
    - "headquarters location is not asset location"
    - "hazard exposure is not realized damage"
    - "insurance and adaptation alter net exposure"
    - "maps and scenarios have vintages"
    - "Transition risk"
    - "emissions data may be estimated"
    - "Scope 3 dominates for some sectors"
    - "brown exposure can be hedged or passed through"
    - "taxonomy definitions differ"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "Physical risk"
    measure: "asset-level exposure to flood, wildfire, heat, drought, hurricane, sea-level rise, water stress, and chronic climate hazards"
    pitfalls: ["headquarters location is not asset location", "hazard exposure is not realized damage", "insurance and adaptation alter net exposure", "maps and scenarios have vintages"]
    live_lookup_required: ["current hazard-model provider version", "current FEMA/First Street/NOAA/CMIP data vintage", "current insurance-market rules"]

    item: "Transition risk"
    measure: "carbon emissions, fossil-fuel reserves, energy intensity, technology exposure, policy exposure, carbon-price sensitivity, green revenue"
    pitfalls: ["emissions data may be estimated", "Scope 3 dominates for some sectors", "brown exposure can be hedged or passed through", "taxonomy definitions differ"]
    live_lookup_required: ["current emissions-provider vintage", "current carbon-price and taxonomy rules", "current NGFS scenario vintage"]

    item: "Regulatory risk"
    measure: "carbon pricing, disclosure mandates, taxonomy eligibility, permitting, litigation, fossil-fuel phaseout, building standards, vehicle standards"
    pitfalls: ["announcements and enforcement differ", "jurisdictional coverage is heterogeneous", "policy anticipation affects pre-trends"]
    live_lookup_required: ["current regulator rules", "current litigation and enforcement datasets", "current taxonomy status"]

    item: "Asset pricing outcomes"
    measure: "climate beta, carbon premium, greenium, abnormal returns, cost of capital, credit spreads, CDS, option-implied tail risk"
    pitfalls: ["risk premium and mispricing are observationally close", "realized returns are noisy", "factor construction choices matter", "greenium can reflect clientele or constraints"]
    live_lookup_required: ["current factor data", "current bond/credit-spread database vintage", "current ESG index methodology"]

    item: "Real-response outcomes"
    measure: "capex, emissions abatement, patenting, divestment, plant closure, siting, relocation, adaptation investment, insurance take-up"
    pitfalls: ["financial repricing need not cause real decarbonization", "firms may sell brown assets to less transparent owners", "adaptation can reduce measured damage without reducing hazard"]
    live_lookup_required: ["current asset-level ownership and plant-location data", "current insurance availability"]

    item: "Loan, rating, and insurance pricing"
    measure: "loan spreads, covenants, maturity, collateral haircuts, credit ratings/outlooks, insurance premia, exclusions, deductibles, withdrawal"
    pitfalls: ["lender and insurer clientele sort endogenously", "ratings may lag market prices", "insurance repricing may reflect regulation or reinsurance costs"]
    live_lookup_required: ["current loan-pricing datasets", "current rating-agency criteria", "current insurance filings and reinsurance data"]

    item: "Stranded assets and capital sorting"
    measure: "reserve impairment, fossil asset write-downs, plant retirements, brown-asset transactions, investor ownership, institutional clientele"
    pitfalls: ["book reserves are not marketable reserves", "asset sales can move emissions outside public markets", "clientele effects can mimic risk premia"]
    live_lookup_required: ["current reserve disclosures", "current transaction data", "current investor-holdings database"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "Physical versus transition versus regulatory risk"
    - "Climate risk channels are correlated but economically distinct; a single climate score rarely identifies which channel is priced."
    - "interpreting a composite ESG score as physical or transition risk"
    - "claiming financial-market pricing caused real decarbonization without real outcomes"
    - "treating a single realized-return estimate as structural climate risk pricing"
    - "Spreads, covenants, maturities, and ratings reflect borrower risk, lender selection, collateral, regulation, and relationship lending."
    - "confusing lender clientele sorting with risk-based repricing"
    - "calling all premium increases climate repricing"
    - "using headquarters county as exposure for globally distributed firms"
    - "Green premia, brown discounts, and ownership changes may reflect tastes, mandates, exclusions, and segmentation rather than priced cash-flow risk."
  sorting_vs_siting_or_selection_channel:
    - "Spreads, covenants, maturities, and ratings reflect borrower risk, lender selection, collateral, regulation, and relationship lending."
    - "confusing lender clientele sorting with risk-based repricing"
    - "Insurance premia and withdrawals can reflect hazard learning, regulation, reinsurance costs, capital constraints, and adverse selection."
    - "Firm siting and asset location"
    - "Investor clientele and sorting of capital"
    - "equating capital-market sorting with aggregate emissions reduction"
  why_method_not_magic:
    - "Observed returns, spreads, or greenia do not by themselves show firms reduce emissions, adapt, or reallocate capital productively."
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Physical versus transition versus regulatory risk"
    core_issue: "Climate risk channels are correlated but economically distinct; a single climate score rarely identifies which channel is priced."
    acceptable_designs: ["separate hazard, emissions, and policy measures", "channel-specific shocks", "asset-location panels", "jurisdiction-by-sector exposure"]
    referee_risk: "interpreting a composite ESG score as physical or transition risk"
    live_lookup_required: ["current provider climate-score methodology"]

    item: "Asset pricing versus real response"
    core_issue: "Observed returns, spreads, or greenia do not by themselves show firms reduce emissions, adapt, or reallocate capital productively."
    acceptable_designs: ["joint pricing and investment outcomes", "capital-raising event studies", "facility-level follow-through", "ownership-transfer tracking"]
    referee_risk: "claiming financial-market pricing caused real decarbonization without real outcomes"
    live_lookup_required: ["current investment, ownership, and emissions data vintages"]

    item: "Climate beta and greenium"
    core_issue: "Climate beta and greenium estimates are sensitive to factor construction, sample window, investor clientele, liquidity, ratings, and sector composition."
    acceptable_designs: ["multiple climate factors", "liquidity/rating/maturity controls", "clientele interactions", "out-of-sample tests", "sector-neutral portfolios"]
    referee_risk: "treating a single realized-return estimate as structural climate risk pricing"
    live_lookup_required: ["current factor, holdings, and bond-index methodology"]

    item: "Credit, loan, and rating channels"
    core_issue: "Spreads, covenants, maturities, and ratings reflect borrower risk, lender selection, collateral, regulation, and relationship lending."
    acceptable_designs: ["borrower-lender fixed effects", "within-borrower loan variation", "rating-agency methodology controls", "collateral-location exposure"]
    referee_risk: "confusing lender clientele sorting with risk-based repricing"
    live_lookup_required: ["current rating criteria and syndicated-loan data vintage"]

    item: "Insurance repricing"
    core_issue: "Insurance premia and withdrawals can reflect hazard learning, regulation, reinsurance costs, capital constraints, and adverse selection."
    acceptable_designs: ["property-level hazard controls", "insurer-by-state fixed effects", "regulatory-boundary designs", "reinsurance shock controls"]
    referee_risk: "calling all premium increases climate repricing"
    live_lookup_required: ["current insurer filings, FAIR plan rules, reinsurance prices"]

    item: "Firm siting and asset location"
    core_issue: "Headquarters, incorporation state, plant locations, collateral, and revenue geography imply different climate exposures."
    acceptable_designs: ["geocoded assets", "facility-level production", "collateral-level mortgage or loan data", "revenue-by-region exposure"]
    referee_risk: "using headquarters county as exposure for globally distributed firms"
    live_lookup_required: ["current asset-location, facility, and subsidiary datasets"]

    item: "Investor clientele and sorting of capital"
    core_issue: "Green premia, brown discounts, and ownership changes may reflect tastes, mandates, exclusions, and segmentation rather than priced cash-flow risk."
    acceptable_designs: ["holdings-based clientele measures", "fund-flow shocks", "mandate/exclusion events", "buyer-seller ownership tracking"]
    referee_risk: "equating capital-market sorting with aggregate emissions reduction"
    live_lookup_required: ["current institutional holdings, fund-flow, and mandate datasets"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Channel separation"
    - "Are physical, transition, and regulatory risks measured separately rather than hidden inside one ESG or climate score?"
    - "Location validity"
    - "Does exposure use asset, facility, collateral, or revenue geography rather than headquarters when location matters?"
    - "Pricing specification"
    - "Do tests distinguish risk premium, mispricing, liquidity, ratings, sector composition, and investor clientele?"
    - "Credit and loan mechanisms"
    - "Are spreads, covenants, maturity, collateral, and lender selection modeled jointly?"
    - "Insurance mechanism"
    - "Are insurance repricing, nonrenewal, deductibles, regulation, and reinsurance shocks separated?"
  minimal_empirical_section_checklist:
    - "Channel separation"
    - "Are physical, transition, and regulatory risks measured separately rather than hidden inside one ESG or climate score?"
    - "current provider methodology"
    - "Location validity"
    - "Does exposure use asset, facility, collateral, or revenue geography rather than headquarters when location matters?"
    - "current asset-location data vintage"
    - "Pricing specification"
    - "Do tests distinguish risk premium, mispricing, liquidity, ratings, sector composition, and investor clientele?"
    - "current factor, holdings, and pricing data vintages"
    - "Credit and loan mechanisms"
  claims_to_downgrade:
    - "Do not treat an ESG score as a validated measure of physical, transition, or regulatory climate risk."
    - "Do not use headquarters location as asset-level physical-risk exposure when plant, property, collateral, or revenue locations are available."
    - "Do not infer real-economy decarbonization from greenium, climate beta, credit spread, or rating results alone."
    - "Do not call a carbon premium a risk premium without addressing mispricing, omitted sector risks, liquidity, clientele, and factor-construction sensitivity."
    - "Do not interpret loan, rating, or insurance price changes as climate repricing without lender/insurer selection and regulatory controls."
    - "Do not claim stranded-asset realization from reserves or emissions exposure alone without impairment, closure, write-down, or transaction evidence."
    - "Do not make current claims about climate-disclosure rules, taxonomies, NGFS scenarios, hazard maps, rating-agency criteria, insurance rules, or provider datasets without live loo"
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Channel separation"
    ask: "Are physical, transition, and regulatory risks measured separately rather than hidden inside one ESG or climate score?"
    live_lookup_required: ["current provider methodology"]

    check: "Location validity"
    ask: "Does exposure use asset, facility, collateral, or revenue geography rather than headquarters when location matters?"
    live_lookup_required: ["current asset-location data vintage"]

    check: "Pricing specification"
    ask: "Do tests distinguish risk premium, mispricing, liquidity, ratings, sector composition, and investor clientele?"
    live_lookup_required: ["current factor, holdings, and pricing data vintages"]

    check: "Credit and loan mechanisms"
    ask: "Are spreads, covenants, maturity, collateral, and lender selection modeled jointly?"
    live_lookup_required: ["current loan and rating datasets"]

    check: "Insurance mechanism"
    ask: "Are insurance repricing, nonrenewal, deductibles, regulation, and reinsurance shocks separated?"
    live_lookup_required: ["current insurance filings and reinsurance data"]

    check: "Real effects"
    ask: "Are repricing results linked to capex, emissions, siting, relocation, adaptation, or stranded-asset outcomes before making real-effect claims?"
    live_lookup_required: ["current firm/asset outcome data"]

    check: "Capital sorting"
    ask: "Does the paper test whether brown assets are retired, decarbonized, or merely transferred to different owners?"
    live_lookup_required: ["current ownership and transaction datasets"]
```

## Forbidden claims

- Do not treat an ESG score as a validated measure of physical, transition, or regulatory climate risk.
- Do not use headquarters location as asset-level physical-risk exposure when plant, property, collateral, or revenue locations are available.
- Do not infer real-economy decarbonization from greenium, climate beta, credit spread, or rating results alone.
- Do not call a carbon premium a risk premium without addressing mispricing, omitted sector risks, liquidity, clientele, and factor-construction sensitivity.
- Do not interpret loan, rating, or insurance price changes as climate repricing without lender/insurer selection and regulatory controls.
- Do not claim stranded-asset realization from reserves or emissions exposure alone without impairment, closure, write-down, or transaction evidence.
- Do not make current claims about climate-disclosure rules, taxonomies, NGFS scenarios, hazard maps, rating-agency criteria, insurance rules, or provider datasets without live loo

## Domain reasoning steps

1. Define the research object before choosing a method: unit, timing, financial outcome, exposure, and target estimand.
2. Classify the channel as physical, transition, liability, mixed, or unknown; mixed cases need separate channel language.
3. Keep exposure construction separate from association, event response, causal effect, and scenario stress-test interpretation.
4. For physical risk, require asset geography, hazard intensity, horizon, spatial resolution, vulnerability, adaptation, protection assumptions, and ownership timing; headquarters exposure is not operating-asset exposure unless explicitly defined.
5. For transition risk, separate sector carbon intensity, borrower or issuer emissions, energy mix, carbon-price sensitivity, policy exposure, technology risk, and demand risk.
6. For liability risk, define the legal or enforcement event, affected entity, disclosure issue, and timing; do not infer legal violation or liability from exposure.
7. For portfolios, distinguish weighted average carbon intensity, financed emissions, sector-country exposure, issuer exposure, and holdings or loan-book exposure; none alone proves loss, pricing, or compliance.
8. Audit exposure-construction risks: geocoding error, parent-subsidiary matching, stale holdings, private-firm emissions missingness, sector drift, scenario mapping, survivorship, and missing provenance.
9. Define financial confounding before estimation: rating, maturity, duration, liquidity, seniority, currency, issue size, callability, benchmark curve, issuer risk, borrower risk, bank balance-sheet conditions, energy prices, macro shocks, and monetary policy.
10. Match method to variation: descriptive mapping for concentration; panel association for conditional correlations; event study for precisely timed shocks; modern DID only with valid treatment timing and comparable controls; IV or shift-share only with defended exclusion restrictions.
11. Event studies require official/latest event timestamps, narrow enough windows, benchmark models, thin-trading checks, and contamination checks for overlapping policy, disaster, rate, or commodity news.
12. Scenario analysis is conditional stress testing or exposure mapping; it is not a forecast of realized losses, returns, defaults, capital needs, or macro paths.
13. Use separate claim language: "modeled exposure," "conditional association," "abnormal event response," and "causal effect if diagnostics and `claim_gate.json` support it."
14. Identify blocking diagnostics: missing exposure provenance, weak match rates, undocumented scenario mapping, missing rating or maturity controls, contaminated events, poor overlap, failed pretrends, anticipation, weak instruments, or missing/blocking `claim_gate.json`.
15. Rank robustness by risk: alternative exposure metrics, geocoding and matching sensitivity, sector-country controls, rating-maturity-liquidity controls, event-window sensitivity, placebo events, scenario-vintage sensitivity, and clustering or fixed-effect checks.
16. Anticipate referee objections: carbon scores may be sector composition; physical exposure may be measured at headquarters; loan spreads may reflect borrower risk; events may be anticipated; financed emissions are accounting allocations; scenarios are assumption-driven.
17. Define downgrade triggers before reviewing results: exposure-only when no financial outcome exists; association-only without credible shock; event-response-only with narrow timing but no causal design; scenario-only when outputs are assumption-based; block strong claims when artifacts or `claim_gate.json` are missing.

## Candidate outputs

* `climate_finance_risk` YAML or JSON plan.
* Exposure-construction, portfolio-exposure, event-study, scenario-analysis, or financial-identification plan.
* Required diagnostics and artifact checklist.
* Robustness plan ranked by measurement and identification risk.
* Safe claim-language block separating exposure, association, event response, causality, and scenario stress tests.
* Downgrade/refusal block for investment, realized-loss, regulatory, compliance, audit, assurance, or capital overclaims.

## Output schema

Return YAML by default, or JSON if requested. Do not omit the base fields.

```yaml
skill_name: climate_finance_risk
user_question_summary: string
research_domain: climate_finance
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: null
  estimand_candidates: []
  identification_risks: []
climate_finance_risk:
  risk_type: physical | transition | liability | mixed | unknown
  exposure_construction_candidates: []
  financial_outcome_candidates: []
  identification_design_candidates: []
  scenario_use: none | stress_test | exposure_mapping | sensitivity_analysis | unknown
  exposure_finance_separation:
    exposure_object: string
    financial_estimand: string
    cannot_infer_from_exposure_alone: []
  portfolio_exposure_candidates:
    weighted_average_carbon_intensity: string
    financed_emissions: string
    sector_country_exposure: string
    holdings_or_loan_book_exposure: string
  event_study_candidates:
    event_types: []
    event_time_definition: string
    event_window_candidates: []
    contamination_risks: []
  data_quality_risks: []
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

* This skill is a planning and review rubric, not an estimator, backend validator, artifact certifier, financial adviser, legal adviser, auditor, regulator, or assurance provider.
* Climate scenarios are stress-test assumptions or exposure mappings, not forecasts of realized losses, returns, defaults, capital needs, or macro paths.
* Weighted average carbon intensity is not complete climate risk.
* Financed emissions are attributed financing-chain exposures, not direct bank operating emissions.
* Sector-country exposure is a concentration measure, not proof of loss, mispricing, or regulatory noncompliance.
* Physical-risk exposure usually requires asset geography; headquarters location is insufficient for operating assets unless the estimand is headquarters exposure.
* Transition-risk exposure must separate sector carbon intensity, energy mix, policy exposure, carbon-price sensitivity, technology exposure, and demand risk.
* Financial outcomes require careful controls for sector, country, maturity, duration, rating, currency, liquidity, macro shocks, and baseline credit or equity risk.
* Event studies require credible event timing, benchmark models, narrow enough windows, and contamination checks.
* Official/latest lookup is required at use time for volatile scenarios, taxonomies, disclosure rules, supervisory rules, carbon-pricing systems, hazard products, financial-data definitions, and emissions-accounting standards.
* `claim_gate.json` and diagnostics control strong claim readiness.

## Forbidden claims

* Do not provide investment advice or recommend portfolio actions.
* Do not forecast realized losses, realized returns, defaults, credit events, or regulatory capital needs from a scenario exercise.
* Do not claim regulatory compliance, taxonomy alignment, prudential adequacy, legal violation, audit assurance, or disclosure sufficiency.
* Do not treat a climate scenario as a prediction.
* Do not treat portfolio carbon intensity, financed emissions, or sector-country exposure as complete climate risk.
* Do not call financed emissions direct bank operating emissions.
* Do not infer causal effects on bond yields, loan spreads, stock returns, default risk, or bank lending without a validated design, diagnostics, code artifacts, and `claim_gate.json`.
* Do not treat exposure construction as financial identification.
* Do not ignore sector, country, maturity, duration, rating, liquidity, currency, macro shocks, or baseline borrower/issuer risk.
* Do not call event-window repricing causal if the event was anticipated, contaminated, or imprecisely timed.
* Do not claim disaster-event losses or returns were caused by climate change unless the design separately identifies attribution and financial response.
* Do not hardcode current policy, regulatory, taxonomy, scenario, data-product, or standard details.

## Handoff to code

Draft a concrete spec for code to validate:

* exposure unit and financial-outcome unit;
* sample window, time frequency, and matching keys;
* physical hazard, transition exposure, liability event, or portfolio exposure source;
* scenario metadata and official/latest lookup requirements when scenarios are used;
* financial outcome definition, event-time definition, event windows, controls, fixed effects, clustering, and benchmark models;
* exposure-construction, panel-integrity, event-contamination, missingness, and sample-selection diagnostics;
* robustness priorities and claim-gate requirements.

Ask code to verify only what code can verify: spec validity, data joins, panel integrity, backend availability, diagnostics, artifact completeness, and claim-gate status. Do not ask code to certify investment, legal, regulatory, audit, assurance, or compliance conclusions.

## Handoff from code artifacts

Before writing strong language, inspect the exposure manifest, scenario manifest, portfolio matching manifest, `status.json`, `manifest.json` or `artifact_manifest.json`, `diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json` or `backend_status.json`, `model_table.csv`, and `claim_gate.json`.

Interpret artifacts conservatively:

* If exposure artifacts exist but financial artifacts do not, report exposure mapping only.
* If model tables exist but diagnostics or claim gate are missing, report exploratory associations only.
* If scenario artifacts exist without realized financial outcome analysis, report scenario exposure or stress-test output only.
* If event windows are not documented, do not report event-response claims.
* If `claim_gate.json` blocks causal language, do not use causal language even when coefficients are significant.

## Minimal examples

### Good planning example

User: "Did banks with higher exposure to carbon-intensive borrowers charge higher loan spreads after a climate policy announcement?"

Expected skill output:

```yaml
skill_name: climate_finance_risk
user_question_summary: loan-spread response to transition-risk policy news
research_domain: climate_finance
research_brief:
  unit: loan_facility_or_borrower_lender_year
  time_frequency: deal_date_or_year
  outcome_candidates: [loan_spread, maturity, loan_amount]
  treatment_or_exposure: pre_announcement_transition_exposure
  estimand_candidates: [event_response_by_exposure, conditional_spread_association]
  identification_risks: [borrower_credit_quality, sector_country_composition, anticipated_news, lender_selection]
climate_finance_risk:
  risk_type: transition
  exposure_construction_candidates: [borrower_emissions_intensity, sector_carbon_intensity, bank_loan_book_weighted_exposure, sector_country_policy_exposure]
  financial_outcome_candidates: [loan_spread, loan_maturity, loan_amount, covenant_presence]
  identification_design_candidates: [narrow_event_study_if_timing_is_precise, panel_association_with_borrower_lender_controls, DID_only_if_counterfactuals_are_validated]
  scenario_use: none
  exposure_finance_separation:
    exposure_object: "Pre-announcement borrower or bank transition exposure."
    financial_estimand: "Differential loan-spread response after the announcement."
    cannot_infer_from_exposure_alone: [pricing_effect, causal_effect, regulatory_capital_effect]
  portfolio_exposure_candidates:
    weighted_average_carbon_intensity: "Candidate loan-book transition exposure metric."
    financed_emissions: "Attribution metric, not bank operating emissions."
    sector_country_exposure: "Needed to separate transition risk from sector-country composition."
    holdings_or_loan_book_exposure: "Use loan-book weights and borrower matching dates."
  event_study_candidates:
    event_types: [policy_announcement]
    event_time_definition: "Use official/latest timestamp at use time."
    event_window_candidates: [narrow_daily_window, deal_level_pre_post_window_if_loans_are_sparse]
    contamination_risks: [overlapping_policy_news, macro_rate_news, energy_price_shocks]
  data_quality_risks: [borrower_emissions_missingness, private_firm_matching_error, loan_spread_definition_changes]
  forbidden_claims: [investment_advice, regulatory_capital_claim, causal_pricing_claim_without_claim_gate]
candidate_workflows: [exposure_construction_audit, finance_event_study_design, loan_panel_association_design]
candidate_methods: [event_study_for_announcement_response, high_dimensional_panel_association, modern_DID_only_with_cohort_diagnostics]
required_diagnostics: [exposure_provenance, borrower_lender_match_rate, event_contamination_check, sector_country_balance, rating_maturity_currency_controls, claim_gate_status]
recommended_robustness: [alternative_transition_exposure_metrics, event_window_sensitivity, placebo_policy_dates, sector_country_and_rating_controls]
claim_language:
  allowed: ["A design for testing differential loan-spread response by pre-announcement transition exposure."]
  disallowed: ["The policy caused loan spreads to rise."]
uncertainty_notes: ["Official/latest policy timestamp and scope must be checked at use time."]
next_code_actions: [validate_borrower_lender_matching, build_pre_announcement_exposure, check_event_contamination]
scholarly_depth:
  estimand_definition: "Differential change in loan spreads for more transition-exposed borrowers after policy news, relative to comparable less exposed borrowers or borrower-lender cells."
  identification_assumptions: [not_fully_anticipated, comparable_controls, no_concurrent_differential_shock, selection_addressed_or_downgraded]
  measurement_model: [transition_exposure_measured_before_event, sector_country_and_carbon_metrics_separated, loan_spread_defined_consistently]
  data_construction_risks: [emissions_missingness, parent_matching_error, stale_financial_controls, sparse_deal_dates]
  method_decision_tree: ["precise announcement and daily securities -> event study", "sparse loan timing -> guarded pre/post panel association", "staggered policy -> modern DID only with diagnostics", "no credible shock -> association only"]
  diagnostics_that_block_claims: [missing_event_timestamp, overlapping_news, low_match_rate, missing_rating_maturity_controls, claim_gate_missing_or_blocking]
  robustness_ranked_by_risk: [alternative_exposure_metrics, event_window_sensitivity, placebo_events, sector_country_controls, alternative_clustering]
  referee_objections: [sector_repricing_not_climate_policy, lender_selection, anticipated_announcement, noisy_private_firm_emissions]
  downgrade_triggers: [unclear_event_timing_to_association, weak_matching_to_feasibility, blocking_claim_gate_to_no_causal_language]
not_recommended_methods: [default_TWFE_without_event_timing_diagnostics, OLS_without_rating_maturity_sector_country_liquidity_controls, scenario_loss_forecast_from_exposure_scores]
```

### Downgrade and overclaim-block example

User: "Use our portfolio carbon intensity and climate scenarios to tell us which bonds will lose money and whether our fund meets regulatory climate requirements."

Expected skill output:

```yaml
skill_name: climate_finance_risk
user_question_summary: investment, realized-loss, and regulatory overclaims from carbon intensity and scenarios
research_domain: climate_finance
research_brief:
  unit: bond_or_portfolio
  time_frequency: scenario_horizon
  outcome_candidates: [modeled_exposure, conditional_stress_metric_if_defined]
  treatment_or_exposure: portfolio_carbon_intensity_and_scenario_assumptions
  estimand_candidates: [scenario_exposure, portfolio_concentration]
  identification_risks: [scenario_not_forecast, exposure_metric_not_complete_risk, no_realized_financial_identification]
climate_finance_risk:
  risk_type: transition
  exposure_construction_candidates: [weighted_average_carbon_intensity, financed_emissions, sector_country_exposure, issuer_mapping]
  financial_outcome_candidates: []
  identification_design_candidates: [exposure_mapping_only, scenario_stress_test_only]
  scenario_use: stress_test
  exposure_finance_separation:
    exposure_object: "Portfolio carbon and sector-country exposure under stated scenario assumptions."
    financial_estimand: "Not identified from the provided inputs."
    cannot_infer_from_exposure_alone: [realized_bond_losses, investment_recommendations, regulatory_compliance, capital_adequacy]
  portfolio_exposure_candidates:
    weighted_average_carbon_intensity: "Partial transition-exposure concentration metric."
    financed_emissions: "Attribution metric requiring accounting-boundary documentation."
    sector_country_exposure: "Required because policy and technology risks differ by sector and country."
    holdings_or_loan_book_exposure: "Requires holdings date, issuer identifiers, and weights."
  event_study_candidates:
    event_types: []
    event_time_definition: "No event design supplied."
    event_window_candidates: []
    contamination_risks: []
  data_quality_risks: [scenario_vintage, emissions_scope_coverage, issuer_mapping_error, holdings_date]
  forbidden_claims: [investment_advice, realized_loss_forecast, regulatory_compliance_claim, capital_adequacy_claim]
candidate_workflows: [portfolio_exposure_mapping, scenario_stress_test_documentation]
candidate_methods: [descriptive_exposure_decomposition, scenario_sensitivity_analysis]
required_diagnostics: [holdings_identifier_match_rate, emissions_scope_check, sector_country_decomposition, official_latest_scenario_lookup, claim_gate_status]
recommended_robustness: [alternative_emissions_scope, alternative_scenario_assumptions, issuer_weight_sensitivity]
claim_language:
  allowed: ["This can be framed as portfolio exposure and conditional scenario stress testing."]
  disallowed: ["These bonds will lose money.", "The fund is compliant or non-compliant."]
uncertainty_notes: ["Regulatory and scenario definitions require official/latest lookup at use time."]
next_code_actions: [document_holdings_date_and_weights, compute_exposure_decomposition, produce_scenario_manifest]
scholarly_depth:
  estimand_definition: "Conditional portfolio scenario exposure under stated transition assumptions, not realized return, capital, or compliance status."
  identification_assumptions: [no_causal_financial_effect_identified, scenario_inputs_are_assumptions_not_forecasts]
  measurement_model: [WACI_is_partial_transition_exposure, financed_emissions_are_attributed_financing_metrics, sector_country_decomposition_required]
  data_construction_risks: [issuer_identifier_mismatch, stale_holdings, emissions_scope_missingness, volatile_regulatory_definitions]
  method_decision_tree: ["holdings plus emissions -> exposure decomposition", "scenario variables plus holdings -> stress-test output", "no realized outcome or shock -> no loss or pricing claim", "regulatory question -> outside this skill"]
  diagnostics_that_block_claims: [missing_holdings_date, missing_scenario_manifest, missing_emissions_scope_documentation, claim_gate_missing_or_blocking]
  robustness_ranked_by_risk: [alternative_scenario_assumptions, alternative_emissions_scopes, sector_country_decomposition, issuer_mapping_sensitivity]
  referee_objections: [scenario_assumptions_drive_results, carbon_intensity_is_not_total_risk, regulatory_conclusions_need_rule_specific_workflow]
  downgrade_triggers: [realized_loss_language_to_scenario_exposure, investment_language_blocked, compliance_certification_blocked]
not_recommended_methods: [ranking_bonds_as_investment_advice_from_carbon_intensity, realized_loss_forecast_from_scenario_exposure, regulatory_capital_or_compliance_certification]
```

## Completion checklist

* Fixed sections are present.
* Shared rules `01` through `07` are cited, especially `../_shared/07_scholarly_depth_rules.md`.
* Output schema includes base fields, `climate_finance_risk`, `scholarly_depth`, and `not_recommended_methods`.
* Physical risk covers flood, fire, heat, storm, sea-level rise, and asset geography.
* Transition risk covers carbon price, policy, sector carbon intensity, and energy mix.
* Portfolio exposure covers weighted average carbon intensity, financed emissions, and sector-country exposure.
* Financial outcomes include bond yield, loan spread, stock return, default risk, and bank lending where relevant.
* Event studies cover policy announcements, disclosure rules, rating changes, and disaster events.
* Scenarios are framed as stress-test assumptions, not forecasts.
* Exposure construction, association, event response, causal effect, and scenario stress-test language are separated.
* Investment advice, realized-loss forecasts, and regulatory capital or compliance claims are blocked.
* Domain reasoning includes estimand, measurement model, identification assumptions, diagnostics that block claims, robustness ranked by risk, referee objections, and downgrade triggers.
* Strong claims require code artifacts and `claim_gate.json`.
* Volatile data sources, regulations, policies, scenarios, taxonomies, standards, and product details require official/latest lookup at use time.
