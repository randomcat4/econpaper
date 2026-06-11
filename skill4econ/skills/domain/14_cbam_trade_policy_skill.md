# Skill: green_trade_cbam

## Purpose

Plan scholar-grade research designs for green trade, carbon border adjustment
mechanisms, CBAM exposure, embedded carbon, trade-flow outcomes, leakage, and
rerouting. The skill behaves as a research design reviewer and method constraint
layer: it separates exposure measurement from causal claims, tests product and
country mappings, ranks trade estimators by data structure, and downgrades
unsupported language before code handoff.

This skill is not an estimator, validator, backend installer, legal interpreter,
customs adviser, compliance certifier, or audit tool. Strong causal,
paper-ready, backend-certified, legal, compliance, assurance, or audit-grade
claims require completed code artifacts plus `claim_gate.json`.

Read and apply these shared rules before using this skill:

- `../_shared/01_claim_language_rules.md`
- `../_shared/02_evidence_lookup_rules.md`
- `../_shared/03_artifact_reading_rules.md`
- `../_shared/04_spec_drafting_rules.md`
- `../_shared/05_forbidden_fallbacks.md`
- `../_shared/06_reviewer_mode_rules.md`
- `../_shared/07_scholarly_depth_rules.md`
- `../_shared/08_domain_literature_anchor_rules.md`

## When to use

Use this skill when the question involves CBAM, green trade, embedded carbon in
products, product-level coverage, export or import exposure, carbon-price
differentials, certificates, reporting obligations, default values versus actual
emissions, product-country or firm-product-country trade flows, leakage,
rerouting, destination substitution, sector substitution, or intermediary
countries.

Use it before drafting a trade-flow specification, interpreting a completed run,
or deciding whether a CBAM, leakage, competitiveness, or rerouting claim must be
downgraded.

## Do not use when

- The task is only an ETS, carbon tax, allowance price, or free-allocation evaluation; route to `06_carbon_market_ets_eval_skill.md`.
- The task is only an emissions inventory or MRV ledger without trade exposure or product coverage.
- The user asks for legal advice, customs compliance certification, tax liability, audit assurance, or enforcement conclusions.
- The user only needs code debugging, backend installation, or package instructions without research-design interpretation.
- The user asks to hardcode current CBAM scope, rates, default values, exemptions, or deadlines instead of checking official/latest sources at use time.

## Inputs expected

- Research question, jurisdiction, importer/exporter markets, study period, unit, time frequency, and intended estimand.
- Trade unit: firm-product-country, product-country, sector-country, firm-destination-product, or another explicit panel unit.
- Product identifiers and concordances: HS, CN, product category, customs code, sector code, country-sector mapping, and time-varying revisions.
- Product-level embedded emissions data, emissions-intensity source, default values, actual-emissions measures, and measurement boundary.
- CBAM exposure definition: covered product, reporting phase, certificate obligation, product-specific embedded carbon, carbon-price differential, carbon price offset, exemption, phase-in, or default-value exposure.
- Export and import exposure: exporter country, importer country, origin, destination, re-export, intermediary country, trade regime, and firm or product mapping.
- Outcome candidates: trade value, quantity, unit value, export probability, import probability, market entry, market exit, destination switching, rerouting, embedded-carbon flow, and sector output.
- Data features needed for method choice: zeros, extensive margin, high-dimensional fixed effects, clustering level, product-country support, and balanced or unbalanced panels.
- Existing artifacts when reading results: spec files, status files, diagnostics, reviewer-risk output, model tables, manifests, backend discovery, and `claim_gate.json`.

## Required repo artifacts to inspect

Inspect workspace files first. Do not treat installed user-level skills as
authority for this repository.

- `README.md`
- `registry.yml`
- `cli.py`
- `core.py`
- `python_wrappers.py`
- `workflows.py`
- `docs/ARTIFACT_CONTRACT.md` when present
- `docs/BACKEND_CONTRACT.md` when present
- `diagnostics/`
- `tests/fixtures/`
- `tests/backends/`
- Existing shared, intake, domain, reporting, schema, and delivery-check files.

Also inspect and apply these shared rules:

- `../_shared/01_claim_language_rules.md`
- `../_shared/02_evidence_lookup_rules.md`
- `../_shared/03_artifact_reading_rules.md`
- `../_shared/04_spec_drafting_rules.md`
- `../_shared/05_forbidden_fallbacks.md`
- `../_shared/06_reviewer_mode_rules.md`
- `../_shared/07_scholarly_depth_rules.md`

For completed or partial runs, inspect these artifacts before result language:
`claim_gate.json`, `status.json`, `manifest.json`, `artifact_manifest.json`,
`diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json` or equivalent,
and `model_table.csv`. Never rely only on a CLI exit code or a model table.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Cosbey, Droege, Fischer, and Munnings (2019), Review of Environmental Economics and Policy, Developing Guidance for Implementing Border Carbon Adjustments"
    - "Böhringer, Carbone, and Rutherford (2012), American Economic Journal: Economic Policy, Unilateral Climate Policy Design"
    - "Böhringer, Carbone, and Rutherford (2018), Journal of Environmental Economics and Management, Embodied Carbon Tariffs"
    - "Monjon and Quirion (2011), Climate Policy, Addressing Leakage in the EU ETS"
    - "Fowlie, Reguant, and Ryan (2016), Journal of Political Economy, Market-Based Emissions Regulation and Industry Dynamics"
    - "European Commission (2021), Impact Assessment Report Accompanying the Proposal for a CBAM Regulation"
    - "Branger and Quirion (2014), Ecological Economics, Would Border Carbon Adjustments Prevent Carbon Leakage and Heavy Industry Competitiveness Losses?"
  canonical_data_sources:
    - "changes in EU import sources, non-EU exports, domestic EU production, downstream substitution, rerouting, resource shuffling"
    - "Embedded-emissions source"
    - "Are EU and non-EU destinations, downstream products, rerouting, and resource shuffling tested?"
  live_lookup_required_for:
    - "current WTO disputes and CBAM implementing rules"
    - "current CBAM regulation, implementing acts, product coverage, timeline, default values"
    - "current CBAM timeline"
    - "current implementing regulation"
    - "current reporting and surrender deadlines"
    - "current CBAM product list"
    - "current CN code coverage"
    - "current precursor and indirect-emissions rules"
    - "current embedded-emissions methodology"
    - "current sector guidance"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Cosbey, Droege, Fischer, and Munnings (2019), Review of Environmental Economics and Policy, Developing Guidance for Implementing Border Carbon Adjustments"
    use_for: "border carbon adjustment design, WTO/legal constraints, default values, embodied emissions"
    live_lookup_required: ["current WTO disputes and CBAM implementing rules"]

    citation: "Böhringer, Carbone, and Rutherford (2012), American Economic Journal: Economic Policy, Unilateral Climate Policy Design"
    use_for: "border carbon adjustment, output-based rebating, leakage and welfare trade-offs"
    live_lookup_required: []

    citation: "Böhringer, Carbone, and Rutherford (2018), Journal of Environmental Economics and Management, Embodied Carbon Tariffs"
    use_for: "embodied-carbon tariffs, leakage reduction, welfare and incidence limits"
    live_lookup_required: []

    citation: "Monjon and Quirion (2011), Climate Policy, Addressing Leakage in the EU ETS"
    use_for: "border adjustment versus free allocation, leakage-risk policy design"
    live_lookup_required: []

    citation: "Fowlie, Reguant, and Ryan (2016), Journal of Political Economy, Market-Based Emissions Regulation and Industry Dynamics"
    use_for: "output-based allocation, leakage, industry dynamics relevant to CBAM counterfactuals"
    live_lookup_required: []

    citation: "European Commission (2021), Impact Assessment Report Accompanying the Proposal for a CBAM Regulation"
    use_for: "CBAM policy rationale, product coverage proposal, leakage and administrative design"
    live_lookup_required: ["current CBAM regulation, implementing acts, product coverage, timeline, default values"]

    citation: "Branger and Quirion (2014), Ecological Economics, Would Border Carbon Adjustments Prevent Carbon Leakage and Heavy Industry Competitiveness Losses?"
    use_for: "sectoral leakage, competitiveness, heavy-industry trade modelling"
    live_lookup_required: []
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "CBAM timeline"
    - "transition period, reporting obligations, certificate purchase phase, free-allocation phase-out interaction, compliance deadlines"
    - "Product coverage"
    - "covered CN codes, sectors, precursors, direct and indirect emissions coverage, exemptions and de minimis rules"
    - "sector labels hide CN-code details"
    - "coverage may expand over time"
    - "downstream products and precursors change exposure"
    - "Embedded emissions"
    - "direct and eligible indirect emissions per imported product, installation-specific data, production route, electricity intensity, input precursors"
    - "Default values versus verified data"
  validation_targets:
    - "Regulatory pinning"
    - "Are CBAM regulation, implementing acts, transition timeline, product CN codes, certificate formula, and reporting obligations pinned to a date?"
    - "Product-code exposure"
    - "Is treatment measured at covered-product or CN-code level rather than broad sector names?"
    - "Embedded-emissions source"
    - "Are default values, verified installation data, indirect emissions, and production-route assumptions separated?"
    - "Exporter exposure"
    - "Does exposure incorporate EU export share, carbon intensity, domestic carbon-price crediting, and verification capacity?"
    - "Trade diversion"
    - "Are EU and non-EU destinations, downstream products, rerouting, and resource shuffling tested?"
  known_mismeasurement_channels:
    - "timeline is regulatory and subject to amendments"
    - "transition reporting differs from financial liability"
    - "implementation dates differ from import shipment dates"
    - "sector labels hide CN-code details"
    - "coverage may expand over time"
    - "downstream products and precursors change exposure"
    - "embedded emissions depend on boundary, production route, allocation rule, and verification"
    - "country averages can mismeasure clean exporters"
    - "indirect emissions rules vary by product"
    - "default values can be punitive or conservative"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "CBAM timeline"
    measure: "transition period, reporting obligations, certificate purchase phase, free-allocation phase-out interaction, compliance deadlines"
    pitfalls: ["timeline is regulatory and subject to amendments", "transition reporting differs from financial liability", "implementation dates differ from import shipment dates"]
    live_lookup_required: ["current CBAM timeline", "current implementing regulation", "current reporting and surrender deadlines"]

    item: "Product coverage"
    measure: "covered CN codes, sectors, precursors, direct and indirect emissions coverage, exemptions and de minimis rules"
    pitfalls: ["sector labels hide CN-code details", "coverage may expand over time", "downstream products and precursors change exposure"]
    live_lookup_required: ["current CBAM product list", "current CN code coverage", "current precursor and indirect-emissions rules"]

    item: "Embedded emissions"
    measure: "direct and eligible indirect emissions per imported product, installation-specific data, production route, electricity intensity, input precursors"
    pitfalls: ["embedded emissions depend on boundary, production route, allocation rule, and verification", "country averages can mismeasure clean exporters", "indirect emissions rules vary by product"]
    live_lookup_required: ["current embedded-emissions methodology", "current sector guidance", "current electricity-factor rules"]

    item: "Default values versus verified data"
    measure: "regulator-specified default values, actual installation-level verified emissions, fallback factors, reporting confidence"
    pitfalls: ["default values can be punitive or conservative", "verified data access varies across exporters", "switching between default and actual data changes treatment intensity"]
    live_lookup_required: ["current default values", "current verifier rules", "current reporting templates"]

    item: "Exporter exposure"
    measure: "exporter-country and firm exposure by covered-product exports to EU, carbon intensity, domestic carbon price, verification capacity, trade dependence"
    pitfalls: ["export exposure is not tariff incidence", "firm-level production routes differ within country-sector", "domestic carbon prices and rebates affect net liability"]
    live_lookup_required: ["current trade data", "current domestic carbon-price recognition rules", "current exporter verification requirements"]

    item: "Trade diversion and leakage"
    measure: "changes in EU import sources, non-EU exports, domestic EU production, downstream substitution, rerouting, resource shuffling"
    pitfalls: ["customs data can miss firm-level rerouting", "trade diversion may reduce EU leakage but not global emissions", "covered-product effects can move to downstream products"]
    live_lookup_required: ["current customs data", "current anti-circumvention rules", "current downstream coverage"]

    item: "Pass-through and incidence"
    measure: "import prices, producer prices, EU downstream prices, exporter margins, consumer incidence, certificate costs, free-allocation phase-out"
    pitfalls: ["statutory liability is not economic incidence", "pass-through differs by market power and substitution elasticity", "welfare claims need terms-of-trade, leakage, revenue, and consumer-surplus components"]
    live_lookup_required: ["current EU ETS price", "current CBAM certificate rules", "current free-allocation phase-out schedule"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "using broad sector exposure as if it were the statutory treatment"
    - "treating default values as true emissions"
    - "claiming emissions reductions from EU import changes alone"
    - "equating legal certificate payer with incidence"
    - "assuming static exporter behavior"
    - "CBAM welfare effects require revenue, free-allocation removal, terms of trade, leakage, administrative cost, retaliation risk, and consumer incidence."
    - "claiming global welfare gains from statutory coverage alone"
  sorting_vs_siting_or_selection_channel:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  why_method_not_magic:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Treatment intensity"
    core_issue: "CBAM exposure depends on product code, embedded emissions, EU ETS price, domestic carbon-price crediting, verification status, and default-value use."
    acceptable_designs: ["CN-code exposure measures", "product-country carbon-intensity cells", "verified-versus-default treatment splits", "domestic carbon-price offsets"]
    referee_risk: "using broad sector exposure as if it were the statutory treatment"
    live_lookup_required: ["current product coverage, default values, verified-data rules, certificate formula"]

    item: "Embedded-emissions measurement"
    core_issue: "Default values and verified installation data identify different treatment intensities and may select different exporters."
    acceptable_designs: ["separate default and verified observations", "installation-route controls", "measurement-error bounds", "verification-capacity interactions"]
    referee_risk: "treating default values as true emissions"
    live_lookup_required: ["current default-value tables and verification guidance"]

    item: "Trade diversion"
    core_issue: "Covered exporters may redirect high-carbon output away from the EU or send lower-carbon output to the EU."
    acceptable_designs: ["EU versus non-EU destination panels", "firm-product-destination data", "resource-shuffling tests", "downstream product leakage checks"]
    referee_risk: "claiming emissions reductions from EU import changes alone"
    live_lookup_required: ["current customs microdata and anti-circumvention rules"]

    item: "Pass-through and incidence"
    core_issue: "Economic burden can fall on exporters, EU importers, downstream firms, consumers, or foreign governments."
    acceptable_designs: ["price and quantity decomposition", "market-power heterogeneity", "exchange-rate and freight controls", "downstream price pass-through"]
    referee_risk: "equating legal certificate payer with incidence"
    live_lookup_required: ["current certificate price and pass-through data"]

    item: "Exporter adaptation"
    core_issue: "Firms can abate, verify cleaner processes, alter product mix, absorb costs, reroute trade, or lobby for domestic carbon pricing."
    acceptable_designs: ["firm-level export panels", "emissions-intensity follow-up", "technology and fuel-switching outcomes", "domestic-policy response controls"]
    referee_risk: "assuming static exporter behavior"
    live_lookup_required: ["current exporter data, verification records, and domestic carbon policies"]

    item: "Welfare and leakage claims"
    core_issue: "CBAM welfare effects require revenue, free-allocation removal, terms of trade, leakage, administrative cost, retaliation risk, and consumer incidence."
    acceptable_designs: ["partial-equilibrium incidence bounds", "structural trade model with emissions", "CGE sensitivity", "leakage and revenue decomposition"]
    referee_risk: "claiming global welfare gains from statutory coverage alone"
    live_lookup_required: ["current EU ETS price path, free-allocation phase-out, trade retaliation, and revenue-use rules"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Regulatory pinning"
    - "Are CBAM regulation, implementing acts, transition timeline, product CN codes, certificate formula, and reporting obligations pinned to a date?"
    - "Product-code exposure"
    - "Is treatment measured at covered-product or CN-code level rather than broad sector names?"
    - "Embedded-emissions source"
    - "Are default values, verified installation data, indirect emissions, and production-route assumptions separated?"
    - "Exporter exposure"
    - "Does exposure incorporate EU export share, carbon intensity, domestic carbon-price crediting, and verification capacity?"
    - "Trade diversion"
    - "Are EU and non-EU destinations, downstream products, rerouting, and resource shuffling tested?"
  minimal_empirical_section_checklist:
    - "Regulatory pinning"
    - "Are CBAM regulation, implementing acts, transition timeline, product CN codes, certificate formula, and reporting obligations pinned to a date?"
    - "current CBAM regulation and implementing acts"
    - "Product-code exposure"
    - "Is treatment measured at covered-product or CN-code level rather than broad sector names?"
    - "current product coverage and CN codes"
    - "Embedded-emissions source"
    - "Are default values, verified installation data, indirect emissions, and production-route assumptions separated?"
    - "current default values and verified-data rules"
    - "Exporter exposure"
  claims_to_downgrade:
    - "Do not state CBAM timeline, coverage, default values, verified-data rules, certificate formulas, or reporting deadlines without live lookup."
    - "Do not treat broad sectors as covered products without CN-code verification."
    - "Do not treat default embedded-emissions values as true exporter emissions."
    - "Do not infer global emissions reductions from reduced EU imports without trade diversion and resource-shuffling checks."
    - "Do not equate statutory CBAM liability with economic incidence."
    - "Do not claim exporter welfare, EU consumer incidence, or global welfare effects from exposure measures alone."
    - "Do not ignore domestic carbon-price crediting, verification capacity, indirect emissions rules, free-allocation phase-out, or downstream l"
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Regulatory pinning"
    ask: "Are CBAM regulation, implementing acts, transition timeline, product CN codes, certificate formula, and reporting obligations pinned to a date?"
    live_lookup_required: ["current CBAM regulation and implementing acts"]

    check: "Product-code exposure"
    ask: "Is treatment measured at covered-product or CN-code level rather than broad sector names?"
    live_lookup_required: ["current product coverage and CN codes"]

    check: "Embedded-emissions source"
    ask: "Are default values, verified installation data, indirect emissions, and production-route assumptions separated?"
    live_lookup_required: ["current default values and verified-data rules"]

    check: "Exporter exposure"
    ask: "Does exposure incorporate EU export share, carbon intensity, domestic carbon-price crediting, and verification capacity?"
    live_lookup_required: ["current trade, carbon-price, and verification data"]

    check: "Trade diversion"
    ask: "Are EU and non-EU destinations, downstream products, rerouting, and resource shuffling tested?"
    live_lookup_required: ["current customs and anti-circumvention data"]

    check: "Pass-through"
    ask: "Are import prices, exporter margins, EU downstream prices, and statutory certificate liability separately analyzed?"
    live_lookup_required: ["current EU ETS/CBAM price and customs-price data"]

    check: "Welfare limits"
    ask: "Are leakage, terms of trade, revenue use, free-allocation phase-out, retaliation risk, and administrative costs included before welfare claims?"
    live_lookup_required: ["current free-allocation, revenue-use, and trade-policy rules"]
```

## Forbidden claims

- Do not state CBAM timeline, coverage, default values, verified-data rules, certificate formulas, or reporting deadlines without live lookup.
- Do not treat broad sectors as covered products without CN-code verification.
- Do not treat default embedded-emissions values as true exporter emissions.
- Do not infer global emissions reductions from reduced EU imports without trade diversion and resource-shuffling checks.
- Do not equate statutory CBAM liability with economic incidence.
- Do not claim exporter welfare, EU consumer incidence, or global welfare effects from exposure measures alone.
- Do not ignore domestic carbon-price crediting, verification capacity, indirect emissions rules, free-allocation phase-out, or downstream l

## Domain reasoning steps

1. Start with the trade research object: unit, time, importer, exporter, product, outcome, exposure, estimand, and target population.
2. Separate CBAM exposure measurement from causal trade, competitiveness, leakage, or emissions claims; a well-built exposure variable is not an identified effect.
3. Verify product and sector coverage from official/latest sources at use time; do not hardcode current scope, timing, exemptions, phase-in rules, default values, certificate rules, reporting obligations, or regulatory deadlines.
4. Define the product mapping before the estimator: HS, CN, national customs code, product category, sector code, and concordance vintage.
5. Audit concordance many-to-one and one-to-many mappings; record whether exposure is assigned at product, product-country, firm-product-country, or sector-country level.
6. Build the country-sector mapping for exporter carbon intensity, domestic carbon price, electricity mix, sector benchmarks, exemptions, and origin-specific offsets.
7. Define embedded emissions at product level: actual emissions, default values, emissions intensity, direct emissions, indirect emissions if relevant, and boundary assumptions.
8. Distinguish default-value exposure from actual-emissions exposure; default values can change measured liability and incentives differently from firm-reported emissions.
9. Define carbon-price differential as a constructed exposure, not a binary policy dummy; account for domestic carbon prices, offsets, free allocation, exemptions, and product-specific embedded carbon.
10. Distinguish certificate/reporting obligations from actual cost incidence; reporting can affect trade behavior even before full financial liability.
11. Specify policy timing using announcement, transition/reporting phase, certificate purchase, surrender, phase-in, revision, and enforcement dates when officially verified.
12. Identify importer and exporter exposure separately; exporter exposure may vary by destination, product coverage, origin carbon intensity, and firm product mix.
13. Specify outcomes for both intensive and extensive margins: trade value, quantity, unit value, positive-flow indicator, entry, exit, destination switching, and rerouting.
14. Treat zeros as data, not a nuisance; zeros and extensive margins make PPMLHDFE or related count/quasi-likelihood trade models relevant for many flow designs.
15. Use gravity-style fixed effects when the estimand is trade-flow response: product-time, origin-time, destination-time, origin-destination, product-destination, or firm-product fixed effects as justified by variation.
16. Do not replace missing PPMLHDFE with OLS on log trade flow plus dropped zeros and call it equivalent; that is a downgrade trigger.
17. Check whether identifying variation remains after fixed effects; if product coverage, timing, and country exposure are collinear with planned FE, revise the estimand or downgrade.
18. Plan leakage and rerouting checks through non-covered products, non-covered destinations, intermediary countries, re-exports, transshipment proxies, sector substitution, and destination substitution.
19. Distinguish trade diversion from emissions leakage; rerouted trade does not prove emissions increased unless embedded-carbon or production-location evidence supports it.
20. Check for anticipation and pretrends around official announcements, reporting starts, certificate obligations, phase-in dates, and product-scope revisions.
21. Diagnose support and overlap across covered and uncovered products, high- and low-carbon origins, export destinations, firm product mixes, and pre-policy trade intensity.
22. Include controls only when they do not absorb the estimand: tariffs, trade agreements, sanctions, energy prices, shipping costs, exchange rates, demand shocks, and concurrent climate or industrial policies.
23. Decide whether the design is causal, quasi-experimental, exposure mapping, scenario measurement, or descriptive decomposition; write the claim language accordingly.
24. Rank robustness by threat: concordance alternatives for mapping error, default versus actual emissions for measurement, FE variants for gravity confounding, and rerouting checks for leakage claims.
25. Identify diagnostics that block claims: missing official coverage source, ambiguous product mapping, unresolved zeros, no PPMLHDFE backend for flow design, no support after FE, missing rerouting outcomes, or absent `claim_gate.json`.
26. Use official/latest lookup at use time for CBAM coverage, product scope, exemptions, default values, actual-emissions rules, certificate/reporting obligations, carbon price offsets, tax rates, and regulatory timelines.

## Candidate outputs

- A `green_trade_cbam_plan` YAML or JSON block for planning or result triage.
- A product-country or firm-product-country exposure map with measurement caveats.
- A method decision tree for PPMLHDFE, event-study, modern DID, decomposition, or descriptive exposure analysis.
- A diagnostic and robustness plan for zeros, fixed effects, support, concordance, timing, leakage, and rerouting.
- Safe claim language, disallowed claim language, downgrade triggers, and code-artifact handoff requirements.

## Output schema

Return YAML by default, or JSON if explicitly requested. Include common fields,
the exact domain block below, `scholarly_depth`, and `not_recommended_methods`.

```yaml
skill_name: green_trade_cbam
user_question_summary: string
research_domain: green_trade_cbam
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: null
  estimand_candidates: []
  identification_risks: []
green_trade_cbam_plan:
  trade_unit: firm_product_country | product_country | sector_country | unknown
  exposure_variables: []
  outcome_candidates: []
  policy_timing_notes: []
  method_candidates: []
  ppmlhdfe_relevance: true | false | unknown
  leakage_checks: []
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

- CBAM exposure is a constructed measurement object; it is not automatically a causal treatment.
- A binary covered-product indicator alone rarely captures exposure because embedded emissions, product coverage, carbon price differential, offsets, exemptions, reporting phase, default values, and actual emissions matter.
- CBAM rules are volatile; use official/latest sources at use time for product scope, sector coverage, exemptions, phase-in, default values, actual-emissions rules, certificate and reporting obligations, carbon price offsets, tax rates, and timelines.
- Trade-flow data commonly contain zeros and extensive-margin responses; dropping zeros for log-linear OLS changes the estimand and is not equivalent to PPMLHDFE.
- Leakage, rerouting, and destination substitution require outcomes outside the directly covered product-destination cell.
- Embedded-carbon leakage claims require emissions-intensity or production-location evidence, not just trade diversion.
- Legal compliance, customs liability, audit assurance, and enforcement conclusions are outside this skill.
- If `claim_gate.json` is missing, blocked, or inconsistent with diagnostics, strong claim language is unavailable.

## Forbidden claims

- Do not treat CBAM effects as driven by one binary policy variable alone.
- Do not ignore product coverage, product concordance, rerouting, carbon price offsets, default values, or actual-emissions differences.
- Do not hardcode current CBAM scope, timing, exemptions, certificate rules, default values, tax rates, or reporting obligations.
- Do not replace missing PPMLHDFE with OLS or log-linear trade-flow estimates and call the result equivalent.
- Do not infer leakage from lower exports to one destination without checking rerouting, destination substitution, sector substitution, intermediary countries, and embedded-carbon flows.
- Do not call a product-country exposure map a causal effect.
- Do not claim customs compliance, legal liability, audit assurance, or enforcement status.
- Do not present parser-only, interface-only, missing-dependency, or unsupported backend output as a live estimator result.
- Do not use TWFE or log-linear OLS as a default main claim for staggered or zero-heavy trade-flow settings without explicit justification and claim-gate support.

## Handoff to code

Create a spec that records unit, time, importer, exporter, origin, destination,
product code, concordance vintage, sector mapping, exposure variables, outcome
variables, timing variables, fixed effects, clusters, weights, sample
restrictions, and required diagnostics.

Ask code to verify only code-verifiable items:

- Field validity against the schema.
- Trade panel key uniqueness and duplicate handling.
- HS/CN/product concordance coverage, many-to-one mappings, and unmapped shares.
- Country-sector mapping and exposure merge rates.
- Positive flows, zeros, entry, exit, and extensive-margin indicators.
- Exposure construction for coverage, embedded emissions, default values, actual emissions, carbon price differential, offsets, exemptions, and phase-in.
- Whether identifying variation remains after planned fixed effects.
- Backend availability and whether PPMLHDFE or another estimator actually ran.
- Diagnostics for separation, convergence, leverage, support, pretrends, anticipation, placebo products, rerouting, and destination substitution.
- Artifact completeness: manifests, status files, diagnostics, reviewer-risk output, model tables, and `claim_gate.json`.

Do not ask code to certify customs compliance, legal liability, regulatory
interpretation, audit assurance, or policy effectiveness from model output alone.

## Handoff from code artifacts

Before writing result language, read `claim_gate.json`, `status.json`,
`manifest.json` or `artifact_manifest.json`, `diagnostics.json`,
`reviewer_risk.json`, `backend_discovery.json` or equivalent, and `model_table.csv`.

Use the artifacts as follows:

- If `claim_gate.json` is absent, claim readiness is unknown or blocked.
- If backend discovery shows missing PPMLHDFE, parser-only output, or unsupported dependencies, downgrade trade-flow estimator claims.
- If diagnostics show separation, non-convergence, no remaining identifying variation after FE, poor support, or dropped zero-heavy cells, downgrade causal claims.
- If product concordance or official-source metadata are missing, mark exposure construction incomplete.
- If rerouting or leakage outcomes are absent, restrict language to direct trade-flow outcomes.
- If model tables conflict with diagnostics or claim gate, follow claim gate and reviewer-risk artifacts.

## Minimal examples

### Good planning input

User: "Does CBAM reduce covered-product imports and cause exporters to reroute to other destinations?"

### Good planning output

```yaml
skill_name: green_trade_cbam
user_question_summary: "CBAM exposure, covered-product imports, and destination rerouting."
research_domain: green_trade_cbam
research_brief:
  unit: product_country
  time_frequency: month_or_year
  outcome_candidates: [import_value, import_quantity, positive_flow, destination_switching, embedded_carbon_flow]
  treatment_or_exposure: CBAM_product_exposure_with_carbon_price_differential
  estimand_candidates: [trade_flow_response, extensive_margin_response, rerouting_response]
  identification_risks: [product_coverage_selection, country_sector_mapping_error, timing_anticipation, concurrent_trade_shocks, rerouting_misclassification]
green_trade_cbam_plan:
  trade_unit: product_country
  exposure_variables: [covered_product_indicator, product_embedded_emissions, carbon_price_differential, default_value_exposure, exemption_indicator, reporting_phase_indicator]
  outcome_candidates: [import_value, import_quantity, unit_value, positive_flow, entry, exit, destination_substitution, embedded_carbon_flow]
  policy_timing_notes: [verify_official_latest_coverage_scope_phase_in_reporting_and_certificate_dates_at_use_time]
  method_candidates: [ppmlhdfe_gravity_flow_design, event_study_for_timing, descriptive_exposure_mapping_for_incomplete_identification]
  ppmlhdfe_relevance: true
  leakage_checks: [rerouting_to_noncovered_destinations, intermediary_country_flows, noncovered_product_substitution, sector_substitution, embedded_carbon_flow_shift]
  forbidden_claims: [binary_policy_only_effect, hardcoded_scope_or_timing, leakage_without_rerouting_and_embedded_carbon_checks]
candidate_workflows: [ppmlhdfe_environmental_flows, trade_panel_mapping, leakage_diagnostic_workflow]
candidate_methods: [ppmlhdfe_with_origin_time_destination_time_product_time_FE, modern_DID_if_timing_and_support_are_valid, descriptive_mapping_if_FE_absorb_variation]
required_diagnostics: [product_concordance_audit, zeros_and_extensive_margin_check, FE_variation_check, separation_and_convergence_check, pretrend_and_anticipation_check, rerouting_outcome_availability]
recommended_robustness: [alternative_concordance_vintages, default_vs_actual_emissions, FE_variant_sensitivity, excluding_intermediary_hubs, placebo_uncovered_products]
forbidden_claims: [CBAM_causal_effect_without_claim_gate, PPMLHDFE_equivalence_from_log_OLS, leakage_without_destination_checks]
claim_language:
  allowed: ["The plan can estimate trade-flow responses and test rerouting if product mapping, zeros, FE variation, and claim gate support the design."]
  disallowed: ["CBAM reduced leakage solely because covered imports fell."]
uncertainty_notes: [official_latest_CBAM_rules_and_product_scope_required_at_use_time]
next_code_actions: [build_product_concordance, construct_exposure, audit_zeros, validate_FE_variation, run_ppmlhdfe_if_available, produce_claim_gate]
scholarly_depth:
  estimand_definition: "Trade-flow response of covered product-country cells plus rerouting contrasts to noncovered destinations or intermediary countries."
  identification_assumptions: [parallel_counterfactual_trade_trends_within_gravity_FE_support, no_uncontrolled_concurrent_trade_shock, stable_product_mapping]
  measurement_model: [product_level_embedded_emissions, default_vs_actual_emissions, carbon_price_differential, product_country_exposure]
  data_construction_risks: [HS_CN_concordance_error, reexports, missing_zero_flows, country_sector_mismatch, scope_revision]
  method_decision_tree: [zero_heavy_flows_to_PPMLHDFE, no_backend_to_downgrade_not_log_OLS_equivalence, insufficient_FE_variation_to_descriptive_mapping]
  diagnostics_that_block_claims: [missing_official_scope_source, unmapped_product_share_high, PPMLHDFE_missing_for_flow_claim, no_rerouting_outcomes, claim_gate_missing]
  robustness_ranked_by_risk: [concordance_variants, default_vs_actual_emissions, FE_variants, rerouting_definitions, placebo_products]
  referee_objections: [coverage_selected_by_dirty_products, exporters_reroute_through_hubs, carbon_price_offsets_reduce_exposure, zeros_drive_results]
  downgrade_triggers: [claim_gate_missing, PPMLHDFE_unavailable, product_scope_unverified, leakage_outcomes_absent]
not_recommended_methods: [single_binary_CBAM_dummy, log_OLS_dropping_zeros_as_PPML_substitute, exposure_map_as_causal_effect]
```

### Downgrade or overclaim-block input

User: "PPMLHDFE is not available, so use log exports OLS and say it proves CBAM caused carbon leakage."

### Downgrade or overclaim-block output

```yaml
skill_name: green_trade_cbam
user_question_summary: "Request to replace missing PPMLHDFE with log OLS and overclaim leakage."
research_domain: green_trade_cbam
research_brief:
  unit: product_country
  time_frequency: year
  outcome_candidates: [exports]
  treatment_or_exposure: binary_CBAM_indicator
  estimand_candidates: [not_established]
  identification_risks: [zeros_dropped, product_scope_unverified, rerouting_unchecked, embedded_carbon_missing, missing_claim_gate]
green_trade_cbam_plan:
  trade_unit: product_country
  exposure_variables: [binary_policy_indicator_only]
  outcome_candidates: [log_exports_only]
  policy_timing_notes: [blocked_until_official_latest_scope_timing_and_phase_rules_are_verified]
  method_candidates: [downgrade_to_descriptive_or_wait_for_supported_flow_estimator]
  ppmlhdfe_relevance: true
  leakage_checks: [blocked_no_destination_substitution_intermediary_country_or_embedded_carbon_outcomes]
  forbidden_claims: [OLS_equivalent_to_PPMLHDFE, CBAM_caused_leakage, binary_policy_sufficient, hardcoded_scope]
candidate_workflows: [artifact_review_before_claim_language]
candidate_methods: [none_for_causal_flow_claim_until_backend_and_exposure_are_valid]
required_diagnostics: [backend_discovery, zeros_share, product_concordance_audit, official_scope_lookup, FE_variation_check, rerouting_outcomes, claim_gate_json]
recommended_robustness: [not_applicable_until_core_design_exists]
forbidden_claims: [log_OLS_equivalent_to_PPMLHDFE, causal_leakage_from_binary_dummy, legal_or_compliance_claim]
claim_language:
  allowed: ["With PPMLHDFE unavailable and leakage outcomes missing, the result can at most be a downgraded descriptive association for observed log-positive flows."]
  disallowed: ["Log OLS proves CBAM caused carbon leakage."]
uncertainty_notes: [official_latest_rules_and_backend_artifacts_required]
next_code_actions: [inspect_backend_discovery, construct_full_exposure, preserve_zero_flows, add_rerouting_outcomes, produce_claim_gate]
scholarly_depth:
  estimand_definition: "Not established; dropped-zero log OLS changes the trade-flow estimand and cannot support leakage."
  identification_assumptions: [not_satisfied_from_current_artifacts]
  measurement_model: [binary_policy_indicator_omits_embedded_emissions_carbon_price_offsets_default_values_and_actual_emissions]
  data_construction_risks: [missing_zero_flows, unverified_product_scope, no_intermediary_country_tracking, no_embedded_carbon_measure]
  method_decision_tree: [PPMLHDFE_missing_to_downgrade, log_OLS_not_equivalent, leakage_claim_blocked_without_rerouting_and_embedded_carbon]
  diagnostics_that_block_claims: [backend_missing, zeros_dropped, claim_gate_missing, rerouting_absent, product_scope_unverified]
  robustness_ranked_by_risk: [restore_zeros_and_flow_estimator_first, verify_scope_second, add_leakage_outcomes_third]
  referee_objections: [selection_of_covered_products, extensive_margin_bias, rerouting_not_observed, carbon_intensity_not_measured]
  downgrade_triggers: [PPMLHDFE_unavailable, binary_exposure_only, leakage_language_requested]
not_recommended_methods: [log_OLS_on_positive_trade_as_equivalent_PPMLHDFE, single_binary_CBAM_dummy, leakage_claim_without_embedded_carbon]
```

## Completion checklist

- All required section headers are present exactly once.
- Shared rule files `01` through `07` are cited by relative path.
- The skill starts from unit, product, country, time, exposure, outcome, and estimand.
- CBAM exposure measurement is separated from causal trade and leakage claims.
- Product-level embedded emissions, default values, actual emissions, sector coverage, and product scope are covered.
- Export/import exposure and firm-product-country or product-country mapping are explicit.
- HS/CN/product concordance and country-sector mapping are required.
- Carbon price differential, offsets, exemptions, phase-in, certificates, and reporting obligations are treated as exposure components.
- Trade-flow outcomes include zeros and extensive margins.
- PPMLHDFE relevance and gravity-style fixed effects are addressed without unsafe OLS fallback.
- Leakage, rerouting, destination substitution, sector substitution, and intermediary countries are covered.
- Official/latest lookup is required for volatile CBAM definitions and timelines.
- The exact `green_trade_cbam_plan` block, `scholarly_depth`, and `not_recommended_methods` are present in the output schema.
- Forbidden claims block binary-only CBAM effects, ignored coverage/rerouting/default-value issues, and PPMLHDFE-to-OLS equivalence.
- Handoff to code and handoff from artifacts name concrete validations, artifacts, and downgrade rules.
- At least two minimal examples are included: good planning and overclaim blocking.
- No estimator is run, no backend is certified, and no artifact is validated by the skill itself.
