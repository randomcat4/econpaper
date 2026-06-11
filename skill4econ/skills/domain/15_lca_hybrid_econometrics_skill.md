# Skill: lca_hybrid_econometrics

## Purpose

Plan life-cycle assessment, hybrid LCA, IO-LCA, and econometric designs that use footprint measures without confusing accounting footprints with causal policy effects.

This skill is a prompt/rubric layer, not an estimator, validator, backend installer, artifact certifier, legal/compliance tool, or substitute for `claim_gate.json`.

## When to use

- The user asks about attributional LCA, consequential LCA, hybrid LCA, IO-LCA, product footprints, functional units, or LCA-based policy evaluation.
- The project combines footprint measures with econometric outcomes or policy claims.
- The user needs claim-safe language distinguishing LCA measurement from causal effects.

## Do not use when

- The user only needs to run an already validated spec.
- The task requires current standards, datasets, package defaults, or policy facts but forbids official/latest lookup.
- The user wants causal, welfare, compliance, audit-grade, or backend-certified claims without artifacts and `claim_gate.json`.

## Inputs expected

- Research question, unit, time period, outcome, exposure or treatment, and intended claim level.
- Data sources, measurement choices, and candidate empirical design.
- Existing `status.json`, `claim_gate.json`, `manifest.json`, diagnostics, reviewer-risk, and model-table artifacts when interpreting results.

## Required repo artifacts to inspect

- `README.md`
- `registry.yml`
- `cli.py`
- `core.py`
- `python_wrappers.py`
- `workflows.py`
- `diagnostics/`
- `tests/fixtures/`
- `tests/backends/`
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
    - "ISO 14040:2006, Environmental Management — Life Cycle Assessment — Principles and Framework"
    - "ISO 14044:2006, Environmental Management — Life Cycle Assessment — Requirements and Guidelines"
    - "Guinée et al. (2002), Handbook on Life Cycle Assessment: Operational Guide to the ISO Standards"
    - "Ekvall and Weidema (2004), International Journal of Life Cycle Assessment, System Boundaries and Input Data in Consequential Life Cycle Inventory Analysis"
    - "Finnveden et al. (2009), Journal of Environmental Management, Recent Developments in Life Cycle Assessment"
    - "Suh et al. (2004), Environmental Science & Technology, System Boundary Selection in Life-Cycle Inventories Using Hybrid Approaches"
    - "Hendrickson, Lave, and Matthews (2006), Environmental Life Cycle Assessment of Goods and Services: An Input-Output Approach"
  canonical_data_sources:
    - "LCA principles, goal and scope, functional unit, system boundary, inventory, impact assessment, interpretation"
    - "classic LCA workflow, inventory construction, allocation and system-boundary practice"
    - "Ekvall and Weidema (2004), International Journal of Life Cycle Assessment, System Boundaries and Input Data in Consequential Life Cycle Inventory Analysis"
    - "describes allocated footprint, not marginal policy response"
    - "database averages may not match study geography or year"
    - "boundary and allocation choices can dominate results"
    - "current marginal grid factors"
    - "current technology supply curves"
    - "current market datasets"
    - "process inventory augmented with input-output sectors or MRIO emissions to reduce truncation"
  live_lookup_required_for:
    - "current ISO 14040 status"
    - "current amendments and adopted national versions"
    - "current ISO 14044 status"
    - "current amendments and sector applications"
    - "current ecoinvent, GaBi/Sphera, openLCA, GREET, Agribalyse, ELCD, USEEIO, and EXIOBASE versions"
    - "current marginal grid factors"
    - "current technology supply curves"
    - "current market datasets"
    - "current product category rules and sector standards"
    - "current PCR/EPD rules"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "ISO 14040:2006, Environmental Management — Life Cycle Assessment — Principles and Framework"
    use_for: "LCA principles, goal and scope, functional unit, system boundary, inventory, impact assessment, interpretation"
    live_lookup_required: ["current ISO 14040 status", "current amendments and adopted national versions"]

    citation: "ISO 14044:2006, Environmental Management — Life Cycle Assessment — Requirements and Guidelines"
    use_for: "allocation hierarchy, data quality, critical review, comparative assertions"
    live_lookup_required: ["current ISO 14044 status", "current amendments and sector applications"]

    citation: "Guinée et al. (2002), Handbook on Life Cycle Assessment: Operational Guide to the ISO Standards"
    use_for: "classic LCA workflow, inventory construction, allocation and system-boundary practice"
    live_lookup_required: []

    citation: "Ekvall and Weidema (2004), International Journal of Life Cycle Assessment, System Boundaries and Input Data in Consequential Life Cycle Inventory Analysis"
    use_for: "consequential LCA, marginal suppliers, system expansion, market-mediated effects"
    live_lookup_required: []

    citation: "Finnveden et al. (2009), Journal of Environmental Management, Recent Developments in Life Cycle Assessment"
    use_for: "attributional versus consequential LCA, uncertainty, weighting, social and economic extensions"
    live_lookup_required: []

    citation: "Suh et al. (2004), Environmental Science & Technology, System Boundary Selection in Life-Cycle Inventories Using Hybrid Approaches"
    use_for: "hybrid LCA, process-LCA truncation error, IO-LCA integration"
    live_lookup_required: []

    citation: "Hendrickson, Lave, and Matthews (2006), Environmental Life Cycle Assessment of Goods and Services: An Input-Output Approach"
    use_for: "IO-LCA, economy-wide embodied impacts, hybrid accounting interpretation"
    live_lookup_required: []
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "Attributional LCA"
    - "average burden assigned to a product, process, organization, or functional unit under a specified system boundary"
    - "Consequential LCA"
    - "change in environmental burden from a decision using marginal suppliers, substitution, avoided products, and market-mediated responses"
    - "Functional unit"
    - "service-normalized denominator such as one kWh delivered, passenger-km, tonne-km, kg product, treatment episode, or building-year"
    - "System boundary"
    - "cradle-to-gate, cradle-to-grave, gate-to-gate, use phase, end-of-life, capital goods, land-use change, maintenance, transport"
    - "Allocation rules"
    - "mass, energy, economic, physical causality, substitution, system expansion, recycled-content, avoided-burden methods"
  validation_targets:
    - "Estimand"
    - "Is the study estimating attributional footprint, consequential footprint, or causal policy effect?"
    - "Functional unit"
    - "Are service, quality, lifetime, utilization, and denominator harmonized across alternatives?"
    - "Boundary"
    - "Are cradle-to-gate/cradle-to-grave, capital goods, use phase, end-of-life, land use, and transport included or excluded explicitly?"
    - "Allocation"
    - "Are co-product, recycling, avoided-burden, and system-expansion rules disclosed with sensitivity?"
    - "Hybrid implementation"
    - "Are process and IO modules, sector concordance, price year, deflators, and double-counting removals pinned?"
  known_mismeasurement_channels:
    - "describes allocated footprint, not marginal policy response"
    - "database averages may not match study geography or year"
    - "boundary and allocation choices can dominate results"
    - "requires behavioral and market assumptions"
    - "marginal technology choice is contestable"
    - "long-run and short-run marginal systems differ"
    - "non-equivalent functional units create false comparisons"
    - "quality, lifetime, utilization, and co-service differences matter"
    - "per-dollar units mix prices and quantities"
    - "truncation can omit upstream capital and services"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "Attributional LCA"
    measure: "average burden assigned to a product, process, organization, or functional unit under a specified system boundary"
    pitfalls: ["describes allocated footprint, not marginal policy response", "database averages may not match study geography or year", "boundary and allocation choices can dominate results"]
    live_lookup_required: ["current ecoinvent, GaBi/Sphera, openLCA, GREET, Agribalyse, ELCD, USEEIO, and EXIOBASE versions"]

    item: "Consequential LCA"
    measure: "change in environmental burden from a decision using marginal suppliers, substitution, avoided products, and market-mediated responses"
    pitfalls: ["requires behavioral and market assumptions", "marginal technology choice is contestable", "long-run and short-run marginal systems differ"]
    live_lookup_required: ["current marginal grid factors", "current technology supply curves", "current market datasets"]

    item: "Functional unit"
    measure: "service-normalized denominator such as one kWh delivered, passenger-km, tonne-km, kg product, treatment episode, or building-year"
    pitfalls: ["non-equivalent functional units create false comparisons", "quality, lifetime, utilization, and co-service differences matter", "per-dollar units mix prices and quantities"]
    live_lookup_required: ["current product category rules and sector standards"]

    item: "System boundary"
    measure: "cradle-to-gate, cradle-to-grave, gate-to-gate, use phase, end-of-life, capital goods, land-use change, maintenance, transport"
    pitfalls: ["truncation can omit upstream capital and services", "end-of-life assumptions can reverse rankings", "temporal boundary affects biogenic carbon and avoided emissions"]
    live_lookup_required: ["current PCR/EPD rules", "current land-use and biogenic-carbon guidance"]

    item: "Allocation rules"
    measure: "mass, energy, economic, physical causality, substitution, system expansion, recycled-content, avoided-burden methods"
    pitfalls: ["co-product allocation is often the largest modelling choice", "economic allocation changes with prices", "allocation rules are not causal incidence estimates"]
    live_lookup_required: ["current ISO, PEF, GHG Protocol Product, PCR, and sector allocation rules"]

    item: "Hybrid LCA and IO-LCA"
    measure: "process inventory augmented with input-output sectors or MRIO emissions to reduce truncation"
    pitfalls: ["sector aggregation error", "double counting between process and IO modules", "price-year and sector-concordance mismatch"]
    live_lookup_required: ["current IO/MRIO tables", "current price base and deflators", "current sector concordances"]

    item: "Uncertainty propagation"
    measure: "parameter uncertainty, scenario uncertainty, pedigree scores, Monte Carlo draws, sensitivity to datasets, allocation, geography, and technology"
    pitfalls: ["point footprints hide ranking uncertainty", "database uncertainty may exclude model-form uncertainty", "correlated inputs cannot be treated as independent"]
    live_lookup_required: ["current database uncertainty fields", "current LCIA method versions", "current software implementation"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "claiming a policy caused emissions reductions because the treated technology has a lower modeled footprint"
    - "mixing average footprints with marginal welfare claims"
    - "ranking products on incomparable denominators"
    - "presenting one allocation rule as objective truth"
    - "Hybrid LCA reduces process truncation but introduces IO sector aggregation, price, and double-counting risks."
    - "calling hybrid estimates strictly more accurate without uncertainty accounting"
    - "using decimal precision in footprints while ignoring model-choice uncertainty"
  sorting_vs_siting_or_selection_channel:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  why_method_not_magic:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "LCA footprint versus causal policy effect"
    core_issue: "An LCA footprint is a modelled accounting burden, not a causal treatment effect unless linked to an identified behavioral or technological counterfactual."
    acceptable_designs: ["separate footprint accounting from policy evaluation", "combine LCA with quasi-experimental adoption variation", "state explicit marginal counterfactuals"]
    referee_risk: "claiming a policy caused emissions reductions because the treated technology has a lower modeled footprint"
    live_lookup_required: ["current emission factors and technology assumptions"]

    item: "Attributional versus consequential estimand"
    core_issue: "Average assigned burdens and marginal system consequences answer different questions."
    acceptable_designs: ["report estimand before model choice", "run attributional and consequential sensitivity", "state short-run versus long-run marginal suppliers"]
    referee_risk: "mixing average footprints with marginal welfare claims"
    live_lookup_required: ["current marginal supply and grid-factor data"]

    item: "Boundary and functional-unit comparability"
    core_issue: "Product comparisons are invalid when service units, lifetimes, quality, utilization, or boundaries differ."
    acceptable_designs: ["harmonized functional units", "lifetime normalization", "use-phase sensitivity", "boundary-expansion checks"]
    referee_risk: "ranking products on incomparable denominators"
    live_lookup_required: ["current PCR/EPD and sector rules"]

    item: "Allocation and co-product sensitivity"
    core_issue: "Multi-output systems can change rankings under mass, energy, economic, substitution, or system-expansion allocation."
    acceptable_designs: ["allocation hierarchy disclosure", "multiple-allocation robustness", "price sensitivity for economic allocation", "avoided-product scenario checks"]
    referee_risk: "presenting one allocation rule as objective truth"
    live_lookup_required: ["current allocation guidance and product rules"]

    item: "Hybrid truncation versus aggregation"
    core_issue: "Hybrid LCA reduces process truncation but introduces IO sector aggregation, price, and double-counting risks."
    acceptable_designs: ["module boundary audit", "concordance transparency", "double-counting removal", "cross-database comparison"]
    referee_risk: "calling hybrid estimates strictly more accurate without uncertainty accounting"
    live_lookup_required: ["current IO tables, MRIO releases, and database concordances"]

    item: "Uncertainty and model-form error"
    core_issue: "LCA uncertainty includes parameters, scenarios, allocation, model structure, LCIA method, geography, and time."
    acceptable_designs: ["Monte Carlo plus scenario analysis", "pedigree uncertainty", "database-version sensitivity", "tornado plots and rank uncertainty"]
    referee_risk: "using decimal precision in footprints while ignoring model-choice uncertainty"
    live_lookup_required: ["current LCIA method and software versions"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Estimand"
    - "Is the study estimating attributional footprint, consequential footprint, or causal policy effect?"
    - "Functional unit"
    - "Are service, quality, lifetime, utilization, and denominator harmonized across alternatives?"
    - "Boundary"
    - "Are cradle-to-gate/cradle-to-grave, capital goods, use phase, end-of-life, land use, and transport included or excluded explicitly?"
    - "Allocation"
    - "Are co-product, recycling, avoided-burden, and system-expansion rules disclosed with sensitivity?"
    - "Hybrid implementation"
    - "Are process and IO modules, sector concordance, price year, deflators, and double-counting removals pinned?"
  minimal_empirical_section_checklist:
    - "Estimand"
    - "Is the study estimating attributional footprint, consequential footprint, or causal policy effect?"
    - "Functional unit"
    - "Are service, quality, lifetime, utilization, and denominator harmonized across alternatives?"
    - "current PCR/EPD and sector rules"
    - "Boundary"
    - "Are cradle-to-gate/cradle-to-grave, capital goods, use phase, end-of-life, land use, and transport included or excluded explicitly?"
    - "current standards and database cut-off rules"
    - "Allocation"
    - "Are co-product, recycling, avoided-burden, and system-expansion rules disclosed with sensitivity?"
  claims_to_downgrade:
    - "Do not call an LCA footprint a causal policy effect without an identified counterfactual."
    - "Do not mix attributional and consequential LCA results without naming the estimand."
    - "Do not compare products with different functional units, lifetimes, quality, utilization, or system boundaries."
    - "Do not present one allocation rule as definitive when co-products, recycling, or avoided burdens drive the result."
    - "Do not claim hybrid LCA eliminates uncertainty; it trades process truncation for IO aggregation, concordance, and price-base risks."
    - "Do not report point estimates without uncertainty, scenario, allocation, and database-version sensitivity."
    - "Do not make current claims about LCA standards, PCRs, LCIA methods, ecoinvent, Sphera/GaBi, openLCA, GREET, USEEIO, EXIOBASE, or emission factors without live lookup."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Estimand"
    ask: "Is the study estimating attributional footprint, consequential footprint, or causal policy effect?"
    live_lookup_required: []

    check: "Functional unit"
    ask: "Are service, quality, lifetime, utilization, and denominator harmonized across alternatives?"
    live_lookup_required: ["current PCR/EPD and sector rules"]

    check: "Boundary"
    ask: "Are cradle-to-gate/cradle-to-grave, capital goods, use phase, end-of-life, land use, and transport included or excluded explicitly?"
    live_lookup_required: ["current standards and database cut-off rules"]

    check: "Allocation"
    ask: "Are co-product, recycling, avoided-burden, and system-expansion rules disclosed with sensitivity?"
    live_lookup_required: ["current ISO, PEF, GHG Protocol Product, and PCR allocation guidance"]

    check: "Hybrid implementation"
    ask: "Are process and IO modules, sector concordance, price year, deflators, and double-counting removals pinned?"
    live_lookup_required: ["current IO/MRIO versions and concordances"]

    check: "Uncertainty"
    ask: "Are parameter, scenario, database-version, LCIA-method, and model-form uncertainty propagated into conclusions?"
    live_lookup_required: ["current LCA database, factor, and software versions"]

    check: "Causal claims"
    ask: "Are policy, adoption, or welfare claims supported by identified behavioral variation rather than footprints alone?"
    live_lookup_required: ["current policy and adoption data"]
```

## Forbidden claims

- Do not call an LCA footprint a causal policy effect without an identified counterfactual.
- Do not mix attributional and consequential LCA results without naming the estimand.
- Do not compare products with different functional units, lifetimes, quality, utilization, or system boundaries.
- Do not present one allocation rule as definitive when co-products, recycling, or avoided burdens drive the result.
- Do not claim hybrid LCA eliminates uncertainty; it trades process truncation for IO aggregation, concordance, and price-base risks.
- Do not report point estimates without uncertainty, scenario, allocation, and database-version sensitivity.
- Do not make current claims about LCA standards, PCRs, LCIA methods, ecoinvent, Sphera/GaBi, openLCA, GREET, USEEIO, EXIOBASE, or emission factors without live lookup.

## Domain reasoning steps

- Define the LCA object before the estimator: functional unit, system boundary, impact category, allocation rule, geography, technology, and time horizon.
- Separate attributional footprint accounting from consequential counterfactual analysis and from econometric causal identification.
- Document hybrid LCA or IO-LCA joins, sector concordances, emission factors, and uncertainty propagation before comparing products or firms.
- Treat LCA footprints as constructed outcomes or exposure variables unless a separate design identifies treatment timing and counterfactual outcomes.
- Downgrade policy, welfare, or product-superiority claims when boundary, allocation, factor, or uncertainty choices drive the result.

## Candidate outputs

- A YAML or JSON planning block with research brief, measurement choices, identification risks, diagnostics, robustness, forbidden claims, and next code actions.
- A claim-safe downgrade note when artifacts or assumptions cannot support the requested language.

## Output schema

```yaml
skill_name: string
user_question_summary: string
research_domain: string
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: null
  estimand_candidates: []
  identification_risks: []
literature_anchors:
  canonical_papers_or_authors: []
  canonical_data_sources: []
  live_lookup_required_for: []
measurement_regimes:
  competing_proxy_definitions: []
  validation_targets: []
  known_mismeasurement_channels: []
identification_debate:
  core_threats: []
  sorting_vs_siting_or_selection_channel: null
  why_method_not_magic: []
referee_entry_points:
  likely_major_objections: []
  minimal_empirical_section_checklist: []
  claims_to_downgrade: []
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
```

## Required caveats

- A skill drafts reasoning and language; it does not validate specs, run backends, or certify artifacts.
- Any strong claim must be allowed by `claim_gate.json` and supported by diagnostics and manifests.
- Volatile standards, source versions, policy rules, package defaults, and data coverage require official/latest lookup at use time.

## Handoff to code

- Ask code to validate specs, inspect artifacts, run diagnostics, and write claim gates.

## Handoff from code artifacts

- Read claim levels, agent status, diagnostics, reviewer risks, backend status, and missing artifact lists before prose.

## Completion checklist

- Literature, data, measurement, identification, referee, and forbidden-claim fields are present and non-empty.
- No causal, welfare, compliance, or backend-certified claim bypasses `claim_gate.json`.
- Current facts are marked for live lookup rather than hardcoded.
