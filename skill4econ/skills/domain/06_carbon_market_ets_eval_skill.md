# Skill: carbon_market_ets_eval

## Purpose

Plan scholar-grade evaluations of carbon markets, emissions trading systems
(ETS), carbon taxes, allowance-price exposure, offset access, and free allocation.
The skill behaves as a research design reviewer and method constraint layer: it
defines the estimand, tests the measurement model, names identification risks,
downgrades unsupported claims, and prepares a concrete handoff to code artifacts.

This skill is not an estimator, validator, backend installer, market monitor,
legal interpreter, compliance certifier, or audit tool. Strong causal,
paper-ready, backend-certified, legal, fraud, compliance, market-manipulation,
or audit-grade claims require completed code artifacts plus `claim_gate.json`.

Read and apply these shared rules before using this skill:

* `../_shared/01_claim_language_rules.md`
* `../_shared/02_evidence_lookup_rules.md`
* `../_shared/03_artifact_reading_rules.md`
* `../_shared/04_spec_drafting_rules.md`
* `../_shared/05_forbidden_fallbacks.md`
* `../_shared/06_reviewer_mode_rules.md`
* `../_shared/07_scholarly_depth_rules.md`
* `../_shared/08_domain_literature_anchor_rules.md`

## When to use

Use this skill when a question involves carbon market policy, ETS inclusion,
carbon taxes, allowance prices, free allocation, auction shares, offsets,
banking, borrowing, compliance obligations, regulated versus unregulated firms,
sector eligibility, innovation responses, output-adjusted emissions, leakage,
or cost pass-through.

Use it for research triage before spec drafting, workflow choice, result
interpretation, or downgrade decisions.

## Do not use when

* The task is only to construct an emissions inventory or MRV ledger; route to a carbon-accounting skill.
* The main object is CBAM, embedded carbon in trade, or border adjustment; route to `14_green_trade_cbam_skill.md`.
* The user asks for legal compliance certification, market manipulation findings, fraud detection, audit assurance, or enforcement conclusions.
* The user only needs backend installation, estimator execution, or code debugging without research-design interpretation.

## Inputs expected

* Research question, policy setting, jurisdiction, study period, unit, time frequency, and target estimand.
* Candidate policy instrument: ETS, carbon tax, allowance price, offset market, free allocation, auction share, or phase change.
* Treatment or exposure definition: coverage dummy, compliance obligation, allowance-price exposure, free-allocation generosity, auction share, tax rate, offset access, or phase-period shift.
* Regulated and unregulated units, sector eligibility rules, size thresholds, baseline emissions, facility-firm links, ownership links, and compliance boundaries.
* Outcome candidates: absolute emissions, output-adjusted emissions, emissions intensity, output, employment, prices, profits, investment, patents, R&D, fuel mix, imports, exports, exits, or relocation.
* Allowance price series, allocation records, auction data, offset-use data, banking/borrowing variables, compliance surrender dates, and reporting-boundary metadata.
* Controls and shock variables: sector-year demand shocks, region-year shocks, energy prices, fuel prices, electricity prices, concurrent policies, macro shocks, and firm trends when justified.
* Leakage and pass-through data: affiliates, plant locations, product prices, input-output links, imports, outsourcing, customer markets, and competitor exposure.
* Existing artifacts when reading results: spec files, status files, diagnostics, reviewer-risk output, model tables, manifests, backend discovery, and `claim_gate.json`.

## Required repo artifacts to inspect

Inspect workspace files first. Do not treat installed user-level skills as
authority for this repository.

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

Also inspect and apply these shared rules:

* `../_shared/01_claim_language_rules.md`
* `../_shared/02_evidence_lookup_rules.md`
* `../_shared/03_artifact_reading_rules.md`
* `../_shared/04_spec_drafting_rules.md`
* `../_shared/05_forbidden_fallbacks.md`
* `../_shared/06_reviewer_mode_rules.md`
* `../_shared/07_scholarly_depth_rules.md`

For completed or partial runs, inspect these artifacts before result language:
`claim_gate.json`, `status.json`, `manifest.json`, `artifact_manifest.json`,
`diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json` or equivalent,
and `model_table.csv`. Never rely only on a CLI exit code or a model table.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Ellerman, Convery, and de Perthuis (2010), Pricing Carbon: The European Union Emissions Trading Scheme"
    - "Martin, Muûls, de Preux, and Wagner (2014), American Economic Review, Industry Compensation Under Relocation Risk"
    - "Calel and Dechezleprêtre (2016), Review of Economics and Statistics, Environmental Policy and Directed Technological Change"
    - "Fabra and Reguant (2014), American Economic Review, Pass-Through of Emissions Costs in Electricity Markets"
    - "Bayer and Aklin (2020), Proceedings of the National Academy of Sciences, EU ETS emissions effects"
    - "Dechezleprêtre, Nachtigall, and Venmans (2023), Journal of Environmental Economics and Management, Joint impact of the EU ETS"
    - "Caron, Rausch, and Winchester (2015), The Energy Journal, Leakage from Sub-national Climate Policy"
  canonical_data_sources:
    - "California cap-and-trade leakage, resource shuffling, imported electricity, subnational welfare"
    - "European Commission Union Registry"
    - "European Union Transaction Log / EUTL legacy access"
    - "EEA EU ETS data viewer"
    - "installation-to-firm mapping"
    - "installation openings/closures"
    - "phase breaks"
    - "aviation and maritime scope changes"
    - "registry redactions"
    - "current Union Registry schema"
  live_lookup_required_for:
    - "current Union Registry schema"
    - "latest EEA data-viewer vintage"
    - "current sector coverage"
    - "Phase IV allocation and MSR rules"
    - "current program name and statutory extension"
    - "latest ARB dashboard files"
    - "current allowance budgets"
    - "price-containment and reserve rules"
    - "absolute-cap transition status"
    - "current registry/trading platform files"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Ellerman, Convery, and de Perthuis (2010), Pricing Carbon: The European Union Emissions Trading Scheme"
    use_for: "EU ETS institutional design, allowance allocation, banking, compliance cycle, and early over-allocation"
    live_lookup_required_for: []

    citation: "Martin, Muûls, de Preux, and Wagner (2014), American Economic Review, Industry Compensation Under Relocation Risk"
    use_for: "free allocation, leakage-risk criteria, relocation claims, and firm-level compensation politics"
    live_lookup_required_for: []

    citation: "Calel and Dechezleprêtre (2016), Review of Economics and Statistics, Environmental Policy and Directed Technological Change"
    use_for: "EU ETS innovation response, patent outcomes, regulated-firm treatment assignment"
    live_lookup_required_for: []

    citation: "Fabra and Reguant (2014), American Economic Review, Pass-Through of Emissions Costs in Electricity Markets"
    use_for: "allowance-cost pass-through, electricity-market incidence, consumer-price effects"
    live_lookup_required_for: []

    citation: "Bayer and Aklin (2020), Proceedings of the National Academy of Sciences, EU ETS emissions effects"
    use_for: "aggregate EU ETS counterfactual evaluation and emissions-reduction debate"
    live_lookup_required_for: []

    citation: "Dechezleprêtre, Nachtigall, and Venmans (2023), Journal of Environmental Economics and Management, Joint impact of the EU ETS"
    use_for: "installation-threshold identification, emissions and economic-performance outcomes"
    live_lookup_required_for: []

    citation: "Caron, Rausch, and Winchester (2015), The Energy Journal, Leakage from Sub-national Climate Policy"
    use_for: "California cap-and-trade leakage, resource shuffling, imported electricity, subnational welfare"
    live_lookup_required_for: []
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "EU ETS data entrance"
    - "installation/operator verified emissions, free allocation, surrendered units, account/compliance status, transaction records where public"
    - "California cap-and-trade data entrance"
    - "covered-entity emissions, allowance allocation, auctions, offsets, holding/transfer infrastructure, compliance instruments"
    - "China ETS data entrance"
    - "covered entities, allowance allocation plans, compliance notices, transaction prices/volumes, MRV guidance"
    - "Allowance allocation"
    - "auctioning"
    - "grandfathering"
    - "benchmarking"
  validation_targets:
    - "entity-facility-fuel-supplier mapping"
    - "electricity-import accounting"
    - "resource-shuffling rules"
    - "offset invalidation risk"
    - "Data entrance"
    - "Are EU ETS, California, and China data sources named separately, with registry vintage, coverage, and public-access limits disclosed?"
    - "Allocation and opportunity cost"
    - "Does the design distinguish free allocation from zero marginal compliance cost and separate rents from abatement incentives?"
    - "Dynamic cap accounting"
    - "Are banking, borrowing, reserve mechanisms, and cumulative caps handled before interpreting annual emissions changes?"
  known_mismeasurement_channels:
    - "installation-to-firm mapping"
    - "installation openings/closures"
    - "phase breaks"
    - "aviation and maritime scope changes"
    - "registry redactions"
    - "entity-facility-fuel-supplier mapping"
    - "electricity-import accounting"
    - "resource-shuffling rules"
    - "offset invalidation risk"
    - "limited facility-level public microdata"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "EU ETS data entrance"
    data_entrances: ["European Commission Union Registry", "European Union Transaction Log / EUTL legacy access", "EEA EU ETS data viewer"]
    measure: "installation/operator verified emissions, free allocation, surrendered units, account/compliance status, transaction records where public"
    pitfalls: ["installation-to-firm mapping", "installation openings/closures", "phase breaks", "aviation and maritime scope changes", "registry redactions"]
    live_lookup_required_for: ["current Union Registry schema", "latest EEA data-viewer vintage", "current sector coverage", "Phase IV allocation and MSR rules"]

    item: "California cap-and-trade data entrance"
    data_entrances: ["California Air Resources Board cap-and-trade program data", "ARB allowance allocation and auction reports", "CITSS tracking system public material", "Mandatory GHG Reporting Program facility data"]
    measure: "covered-entity emissions, allowance allocation, auctions, offsets, holding/transfer infrastructure, compliance instruments"
    pitfalls: ["entity-facility-fuel-supplier mapping", "electricity-import accounting", "resource-shuffling rules", "offset invalidation risk"]
    live_lookup_required_for: ["current program name and statutory extension", "latest ARB dashboard files", "current allowance budgets", "price-containment and reserve rules"]

    item: "China ETS data entrance"
    data_entrances: ["Ministry of Ecology and Environment notices", "National Carbon Trading Market materials", "Shanghai Environment and Energy Exchange trading releases", "pilot exchange disclosures"]
    measure: "covered entities, allowance allocation plans, compliance notices, transaction prices/volumes, MRV guidance"
    pitfalls: ["limited facility-level public microdata", "intensity-based allocation", "state-owned enterprise behavior", "pilot-to-national transition"]
    live_lookup_required_for: ["current sector coverage", "absolute-cap transition status", "current registry/trading platform files", "latest allowance-allocation plan"]

    item: "Allowance allocation"
    variants: ["auctioning", "grandfathering", "benchmarking", "output-based allocation", "leakage-risk free allocation"]
    measure: "initial allocation, free-allocation share, benchmark stringency, auction revenue, compensation eligibility"
    pitfalls: ["free allocation is not zero opportunity cost", "allocation can be endogenous to output or leakage status", "rents differ from compliance cost"]
    live_lookup_required_for: ["current benchmark values", "leakage lists", "auction calendars", "sector-specific free-allocation formulas"]

    item: "Banking and borrowing"
    variants: ["inter-period banking", "within-period compliance flexibility", "borrowing restrictions", "price-stability reserves"]
    measure: "banked allowance stock, surrender timing, compliance-period carryover, expectations-driven abatement timing"
    pitfalls: ["short-run emissions may rise while cumulative cap still binds", "banking changes price path", "borrowing rules differ sharply across systems"]
    live_lookup_required_for: ["current banking restrictions", "reserve and market-stability mechanisms", "compliance-deadline rules"]

    item: "Outcome channels"
    channels: ["direct abatement", "output shifting", "carbon leakage", "pass-through", "innovation", "fuel switching", "permit-price capitalization"]
    measure: "verified emissions, production, imports/exports, prices, patents, energy inputs, profits, welfare decomposition"
    pitfalls: ["verified emissions are not global emissions", "production relocation can mimic abatement", "innovation is lagged and selected"]
    live_lookup_required_for: ["current offset eligibility", "current trade-exposure rules", "current linked-market coverage"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "coverage thresholds correlate with size, technology, energy intensity, and regulatory scrutiny"
    - "short-run abatement can be reshuffled across time through banking or across space through leakage"
    - "local emissions outcomes overstate climate benefits when imported embodied emissions are ignored"
    - "confusing accounting cost, opportunity cost, and realized cash outlay"
    - "counting patents without quality, diffusion, or abatement relevance"
    - "assigning all post-treatment emissions movement to the ETS"
  sorting_vs_siting_or_selection_channel:
    - "patents and technology adoption respond with lags and may reflect selection into regulated status."
  why_method_not_magic:
    - "surrender compliance and verified emissions reductions do not by themselves identify welfare or long-run decarbonization."
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Treatment assignment"
    core_issue: "ETS coverage is usually threshold-, sector-, fuel-, or facility-based, not random."
    acceptable_designs: ["threshold RD / fuzzy RD where valid", "matched difference-in-differences", "event studies with credible pre-trends", "synthetic controls for aggregate caps"]
    referee_risk: "coverage thresholds correlate with size, technology, energy intensity, and regulatory scrutiny"
    live_lookup_required_for: []

    item: "Short-run compliance versus long-run welfare"
    core_issue: "surrender compliance and verified emissions reductions do not by themselves identify welfare or long-run decarbonization."
    acceptable_designs: ["cumulative-cap accounting", "dynamic allowance-bank models", "welfare decomposition with pass-through and rents", "innovation-lag analysis"]
    referee_risk: "short-run abatement can be reshuffled across time through banking or across space through leakage"
    live_lookup_required_for: ["current cap trajectory", "current banking stock", "current allowance price path"]

    item: "Leakage and output shifting"
    core_issue: "facility-level emissions may fall because output moves to uncovered regions, suppliers, imports, or electricity sources."
    acceptable_designs: ["production and trade outcomes", "electricity-import tests", "resource-shuffling diagnostics", "sectoral leakage exposure heterogeneity"]
    referee_risk: "local emissions outcomes overstate climate benefits when imported embodied emissions are ignored"
    live_lookup_required_for: ["current import accounting rules", "current CBAM/leakage-compensation interface"]

    item: "Pass-through and incidence"
    core_issue: "allowance prices can pass through to product or electricity prices even under free allocation."
    acceptable_designs: ["marginal-cost pass-through regressions", "hourly electricity-market bidding models", "retail-price incidence tests", "auction/free-allocation rent separation"]
    referee_risk: "confusing accounting cost, opportunity cost, and realized cash outlay"
    live_lookup_required_for: ["current allowance price series", "current auction/free-allocation shares"]

    item: "Innovation response"
    core_issue: "patents and technology adoption respond with lags and may reflect selection into regulated status."
    acceptable_designs: ["firm patent panels", "regulated-versus-unregulated matched firms", "technology-class-specific outcomes", "pre-policy innovation trends"]
    referee_risk: "counting patents without quality, diffusion, or abatement relevance"
    live_lookup_required_for: []

    item: "Overlapping policy contamination"
    core_issue: "renewable mandates, coal retirements, energy-price shocks, COVID, industrial policy, and reporting-rule changes can coincide with ETS phases."
    acceptable_designs: ["policy-stack controls", "sector-by-year shocks", "fuel-price controls", "negative controls", "robust staggered-DID estimators"]
    referee_risk: "assigning all post-treatment emissions movement to the ETS"
    live_lookup_required_for: ["current overlapping climate and energy policies"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Data entrance"
    - "Are EU ETS, California, and China data sources named separately, with registry vintage, coverage, and public-access limits disclosed?"
    - "Allocation and opportunity cost"
    - "Does the design distinguish free allocation from zero marginal compliance cost and separate rents from abatement incentives?"
    - "Dynamic cap accounting"
    - "Are banking, borrowing, reserve mechanisms, and cumulative caps handled before interpreting annual emissions changes?"
    - "Leakage/output shifting"
    - "Are production, imports, electricity sourcing, and uncovered substitutes tested alongside verified emissions?"
    - "Pass-through"
    - "Are product or electricity prices used to estimate incidence rather than assuming firms absorb allowance costs?"
  minimal_empirical_section_checklist:
    - "Data entrance"
    - "Are EU ETS, California, and China data sources named separately, with registry vintage, coverage, and public-access limits disclosed?"
    - "latest registry/data versions"
    - "Allocation and opportunity cost"
    - "Does the design distinguish free allocation from zero marginal compliance cost and separate rents from abatement incentives?"
    - "current allocation formulas"
    - "Dynamic cap accounting"
    - "Are banking, borrowing, reserve mechanisms, and cumulative caps handled before interpreting annual emissions changes?"
    - "current banking/reserve rules"
    - "Leakage/output shifting"
  claims_to_downgrade:
    - "Do not claim an ETS caused emissions reductions from before-after emissions changes without a counterfactual."
    - "Do not treat free allocation as eliminating marginal compliance cost or pass-through."
    - "Do not equate verified covered emissions reductions with global emissions reductions without leakage and output-shifting checks."
    - "Do not pool EU ETS, California, and China ETS as the same treatment without design-specific allocation, banking, MRV, and coverage controls."
    - "Do not make current claims about allowance prices, sector coverage, caps, registry fields, offsets, or reserve rules without live lookup."
    - "Do not infer long-run welfare from short-run compliance or surrender behavior alone."
    - "Do not call innovation response causal unless treatment assignment, pre-trends, patent class relevance, and lag structure are defensible."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Data entrance"
    ask: "Are EU ETS, California, and China data sources named separately, with registry vintage, coverage, and public-access limits disclosed?"
    live_lookup_required_for: ["latest registry/data versions"]

    check: "Allocation and opportunity cost"
    ask: "Does the design distinguish free allocation from zero marginal compliance cost and separate rents from abatement incentives?"
    live_lookup_required_for: ["current allocation formulas"]

    check: "Dynamic cap accounting"
    ask: "Are banking, borrowing, reserve mechanisms, and cumulative caps handled before interpreting annual emissions changes?"
    live_lookup_required_for: ["current banking/reserve rules"]

    check: "Leakage/output shifting"
    ask: "Are production, imports, electricity sourcing, and uncovered substitutes tested alongside verified emissions?"
    live_lookup_required_for: ["current leakage safeguards and import-accounting rules"]

    check: "Pass-through"
    ask: "Are product or electricity prices used to estimate incidence rather than assuming firms absorb allowance costs?"
    live_lookup_required_for: ["current allowance prices and auction data"]

    check: "Identification credibility"
    ask: "Are pre-trends, treatment timing, threshold manipulation, staggered timing, and overlapping policies directly addressed?"
    live_lookup_required_for: []

    check: "Welfare interpretation"
    ask: "Does the paper avoid moving from short-run compliance to long-run welfare without leakage, innovation, rent, revenue, and consumer-incidence terms?"
    live_lookup_required_for: ["current cap path and revenue-use rules"]
```

## Forbidden claims

- Do not claim an ETS caused emissions reductions from before-after emissions changes without a counterfactual.
- Do not treat free allocation as eliminating marginal compliance cost or pass-through.
- Do not equate verified covered emissions reductions with global emissions reductions without leakage and output-shifting checks.
- Do not pool EU ETS, California, and China ETS as the same treatment without design-specific allocation, banking, MRV, and coverage controls.
- Do not make current claims about allowance prices, sector coverage, caps, registry fields, offsets, or reserve rules without live lookup.
- Do not infer long-run welfare from short-run compliance or surrender behavior alone.
- Do not call innovation response causal unless treatment assignment, pre-trends, patent class relevance, and lag structure are defensible.

## Domain reasoning steps

1. Start with the research object: unit, time frequency, outcome, treatment or exposure, estimand, direct effect, indirect effect, and intended population.
2. Classify the policy instrument as ETS, carbon tax, allowance price, offset market, free-allocation reform, auction reform, or unknown mixed policy.
3. Separate regulated from unregulated units and record the compliance boundary: facility, installation, firm, corporate group, sector, region, or product market.
4. Verify sector eligibility, size thresholds, baseline-emission thresholds, opt-in rules, opt-out rules, and phase-period changes from official/latest sources at use time.
5. Distinguish treatment definitions: coverage dummy, compliance obligation, allowance-price exposure, free allocation generosity, auction share, tax rate, offset access, and phase or period changes.
6. Treat ETS inclusion as selected by default; document selection through sector, baseline emissions, fuel mix, size, political economy, trade exposure, or prior regulation.
7. Define the estimand in words: ATT(g,t) for covered cohorts, dynamic ATT after compliance, marginal effect of allowance-price exposure, or descriptive exposure-response when causality is not credible.
8. Do not let the estimator define the estimand; if timing, unit, or exposure is ambiguous, output a clarification need rather than a main method.
9. Build the emissions measurement model: reporting boundary, scope, facility-firm aggregation, emissions factors, fuel switching, missing reporters, and MRV rule changes.
10. Separate absolute emissions decline from true abatement; output decline, outsourcing, relocation, boundary changes, fuel switching, measurement changes, reporting changes, exit, and leakage can all explain lower reported emissions.
11. Require output-adjusted emissions or emissions intensity when claims concern abatement rather than scale contraction, and state the denominator and its measurement risk.
12. Construct allowance-price exposure as an economic dose, not just a market price; exposure may depend on emissions liability, free allocation, auction share, banked allowances, offsets, and output.
13. Treat free allocation intensity and quota allocation as potentially endogenous; allocation may respond to historical emissions, lobbying, output, leakage risk, or sector benchmarks.
14. Model banking and borrowing as intertemporal margins; permit prices may affect current emissions, future abatement, compliance timing, and allowance hoarding differently.
15. Model offset access separately from ETS coverage; offsets can reduce compliance cost without reducing regulated-unit emissions.
16. For innovation response, specify lag structure, technology class, patent quality, R&D accounting, green versus non-green classification, and anticipation before the compliance date.
17. For pass-through, require product prices or output prices, cost exposure, market structure, demand elasticity, and competitor exposure; do not infer pass-through from emissions alone.
18. For leakage, map affiliates, unregulated plants, imports, outsourcing, relocation, product substitution, and sector-level output shifts before claiming system-wide reductions.
19. Require sector-year, industry-year, region-year, energy-price, fuel-price, and demand-shock controls when they are plausible confounders.
20. Diagnose concurrent policies such as renewable mandates, energy-efficiency rules, pollution controls, subsidies, power-market reforms, or trade shocks.
21. For staggered coverage, prefer modern DID estimands that report cohort-time effects; treat TWFE event studies as diagnostics unless artifacts and `claim_gate.json` justify stronger language.
22. For continuous allowance-price or tax-rate exposure, specify whether identifying variation is within sector-year, across sectors, across regulated intensity, or over market-price shocks.
23. If using price shocks, explain why allowance-price movements are plausibly exogenous to unit-level outcomes after controls, or downgrade to descriptive exposure analysis.
24. Check support and overlap between regulated and unregulated units within comparable sectors, baseline emissions, output scale, energy intensity, and pre-policy trends.
25. Check anticipation around announcement, allocation publication, compliance start, allowance surrender, auction design, tax-rate change, and phase transition dates.
26. Report pretrend diagnostics with window length, power concerns, cohort-specific estimates, support, and anticipation caveats; never call a pretrend "passed" by default.
27. Plan heterogeneity only when motivated: free allocation intensity, trade exposure, energy intensity, market power, offset access, banked allowances, sector benchmarks, or baseline abatement cost.
28. Rank robustness by threat: alternative coverage definitions for selection, output denominators for abatement, sector-year trends for confounding, affiliate outcomes for leakage, and price controls for energy shocks.
29. Identify diagnostics that block claims: missing official coverage source, unresolved facility-firm mapping, poor overlap, contaminated controls, unsupported backend, missing leakage check for system-wide claims, or absent `claim_gate.json`.
30. Use official/latest lookup at use time for ETS coverage, allowance rules, price series, free allocation formulas, auction shares, banking/borrowing, offset rules, reporting obligations, tax rates, exemptions, and regulatory timelines.

## Candidate outputs

* A `carbon_market_eval` YAML or JSON block for research planning or result triage.
* An estimand-first research brief distinguishing coverage, compliance, price exposure, allocation generosity, offsets, tax rate, and phase changes.
* A method decision tree that routes to modern DID, event-study diagnostics, continuous-dose designs, pass-through designs, leakage designs, or descriptive measurement.
* A measurement-risk, diagnostic, and robustness plan ranked by identification threat.
* Safe claim language, disallowed claim language, downgrade triggers, and a code-artifact handoff list.

## Output schema

Return YAML by default, or JSON if explicitly requested. Include common fields,
the exact domain block below, `scholarly_depth`, and `not_recommended_methods`.

```yaml
skill_name: carbon_market_ets_eval
user_question_summary: string
research_domain: carbon_market_policy
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: null
  estimand_candidates: []
  identification_risks: []
carbon_market_eval:
  policy_instrument: ETS | carbon_tax | allowance_price | offset_market | unknown
  treatment_definition_candidates: []
  outcome_candidates: []
  main_identification_risks: []
  design_candidates: []
  required_controls: []
  leakage_checks: []
  pass_through_checks: []
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

* ETS coverage, tax exposure, and free allocation are not random by default.
* A fall in reported firm emissions is not evidence of true abatement unless output, leakage, outsourcing, relocation, boundary changes, fuel switching, measurement changes, reporting changes, and exit are addressed.
* Carbon market rules are volatile; use official/latest sources at use time for ETS coverage, allowance rules, price series, free allocation, auction shares, banking, borrowing, offset rules, reporting obligations, tax rates, exemptions, and timelines.
* Legal compliance, fraud, audit assurance, market manipulation, and enforcement conclusions are outside this skill.
* Pass-through claims require price outcomes and a cost-exposure design; leakage claims require outcomes outside the regulated boundary.
* Innovation claims require technology classification, timing, lag structure, and checks for patenting or R&D reporting changes.
* Modern DID, event-study, IV, DML, or pass-through language is not sufficient without design-specific assumptions and diagnostics.
* Code artifacts can establish that a workflow ran and diagnostics were produced; they do not by themselves prove that the policy claim is true.
* If `claim_gate.json` is missing, blocked, or inconsistent with diagnostics, strong claim language is unavailable.

## Forbidden claims

* Do not treat ETS inclusion, free allocation, or compliance obligation as randomly assigned unless the design proves quasi-random assignment.
* Do not ignore industry trends, sector-year shocks, region-year shocks, energy prices, fuel prices, demand shocks, or concurrent policies.
* Do not interpret firm-level emissions decline as true abatement without output, leakage, boundary, reporting, exit, and relocation checks.
* Do not claim system-wide emissions reductions when emissions may have shifted to unregulated affiliates, imports, suppliers, or other jurisdictions.
* Do not claim carbon leakage, pass-through, or innovation effects from an emissions-only regression.
* Do not call allowance-price exposure exogenous merely because market prices vary over time.
* Do not treat free allocation generosity, quota allocation, or auction share as exogenous without a credible allocation rule or design.
* Do not use a missing-dependency, parser-only, diagnostic-only, or unsupported backend result as a live estimator result.
* Do not use TWFE as the default main causal design for staggered ETS adoption without modern DID checks and claim-gate support.
* Do not make legal, compliance, fraud, market manipulation, audit, or enforcement claims.

## Handoff to code

Create a spec that records unit, time, policy instrument, treatment/exposure
definition, outcome definitions, coverage source, allowance price source,
allocation source, offset source, banking/borrowing variables, compliance dates,
fixed effects, clusters, controls, and required diagnostics.

Ask code to verify only code-verifiable items:

* Field validity against the schema.
* Dataset availability and key uniqueness for unit-time or unit-product-time panels.
* Official-source metadata fields, retrieval dates, and version stamps when supplied.
* Facility-firm, firm-group, sector, and region mappings.
* Treatment timing, phase changes, and exposure construction.
* Required controls, fixed effects, clusters, weights, and sample restrictions.
* Backend availability and whether the estimator actually ran.
* Diagnostics for overlap, balance, pretrends, cohort support, anticipation, placebo outcomes, leakage, pass-through, and sensitivity.
* Artifact completeness: manifests, status files, diagnostics, reviewer-risk output, model tables, and `claim_gate.json`.

Do not ask code to certify legal compliance, validate regulatory interpretation,
detect manipulation, or declare a paper-ready finding from model output alone.

## Handoff from code artifacts

Before writing result language, read `claim_gate.json`, `status.json`,
`manifest.json` or `artifact_manifest.json`, `diagnostics.json`,
`reviewer_risk.json`, `backend_discovery.json` or equivalent, and `model_table.csv`.

Use the artifacts as follows:

* If `claim_gate.json` is absent, claim readiness is unknown or blocked.
* If backend discovery shows missing dependencies or parser-only output, downgrade estimator claims.
* If diagnostics show poor overlap, weak pretrends, contaminated controls, unsupported timing, or missing leakage checks, downgrade causal and system-wide claims.
* If official-source metadata are missing for volatile rules or prices, mark exposure construction incomplete.
* If the model table conflicts with diagnostics or claim gate, follow the claim gate and reviewer-risk artifacts.
* If pass-through or leakage artifacts are absent, restrict language to emissions or exposure outcomes actually estimated.
* If compliance or market-integrity language appears in outputs, remove it unless supplied by an authorized legal or regulatory source and still avoid certification.

## Minimal examples

### Good planning input

User: "Did the ETS reduce emissions, or did regulated firms move production to unregulated affiliates?"

### Good planning output

```yaml
skill_name: carbon_market_ets_eval
user_question_summary: "ETS effects on regulated emissions and possible affiliate leakage."
research_domain: carbon_market_policy
research_brief:
  unit: firm_or_facility
  time_frequency: year
  outcome_candidates: [absolute_emissions, output_adjusted_emissions, affiliate_output, affiliate_emissions]
  treatment_or_exposure: ETS_coverage_and_allowance_price_exposure
  estimand_candidates: [covered_unit_ATT_gt, dynamic_ATT, leakage_response]
  identification_risks: [selection_into_coverage, sector_trends, energy_price_shocks, allocation_endogeneity, boundary_changes]
carbon_market_eval:
  policy_instrument: ETS
  treatment_definition_candidates: [coverage_dummy, compliance_obligation, allowance_price_exposure, free_allocation_intensity, offset_access]
  outcome_candidates: [reported_emissions, emissions_intensity, output, affiliate_output, affiliate_emissions, exits]
  main_identification_risks: [nonrandom_coverage, quota_allocation_endogeneity, leakage, reporting_boundary_change]
  design_candidates: [modern_did_for_coverage, continuous_price_exposure_design, affiliate_leakage_event_study]
  required_controls: [sector_year_effects, region_year_effects, energy_prices, output, baseline_emissions, concurrent_policy_indicators]
  leakage_checks: [affiliate_shift, outsourcing_shift, import_substitution, relocation, exits]
  pass_through_checks: [not_available_without_product_prices]
  forbidden_claims: [do_not_equate_reported_decline_with_true_abatement, do_not_treat_ETS_inclusion_as_random]
candidate_workflows: [did_paper_run, leakage_diagnostic_workflow]
candidate_methods: [cs_did_attgt_if_staggered_coverage, did_imputation_if_timing_valid, continuous_dose_event_study_if_price_exposure_constructed]
required_diagnostics: [coverage_timing_audit, support_overlap, cohort_pretrends, anticipation_window, facility_firm_mapping, leakage_outcome_availability]
recommended_robustness: [alternative_coverage_thresholds, output_denominator_variants, sector_year_trends, excluding_boundary_change_units]
forbidden_claims: [paper_ready_effect_without_claim_gate, true_abatement_without_output_and_leakage_checks]
claim_language:
  allowed: ["A design can test whether reported emissions fell and whether activity shifted to unregulated affiliates."]
  disallowed: ["The ETS caused true abatement before leakage, output, boundary, and claim-gate checks."]
uncertainty_notes: [verify_latest_official_coverage_allocation_offset_and_price_sources_at_use_time]
next_code_actions: [draft_spec, build_exposure_variables, validate_mappings, run_diagnostics, produce_claim_gate]
scholarly_depth:
  estimand_definition: "Dynamic ATT for covered units plus auxiliary leakage contrasts for unregulated affiliates."
  identification_assumptions: [parallel_counterfactual_trends_within_sector_year_support, no_unmeasured_concurrent_policy_shock, stable_reporting_boundaries]
  measurement_model: [reported_emissions_vs_output_adjusted_emissions, facility_to_firm_aggregation, allowance_shortfall_price_exposure]
  data_construction_risks: [misclassified_coverage, missing_affiliates, allocation_endogeneity, reporting_rule_change]
  method_decision_tree: [staggered_coverage_to_modern_DID, continuous_price_dose_if_exposure_valid, no_leakage_data_to_downgrade_system_claim]
  diagnostics_that_block_claims: [failed_overlap, weak_pretrend_support, missing_claim_gate, no_leakage_outcomes_for_system_reduction_claim]
  robustness_ranked_by_risk: [alternative_treatment_definitions, output_adjustment, sector_year_controls, affiliate_leakage_checks]
  referee_objections: [regulated_firms_selected_by_baseline_emissions, quota_allocation_rewards_dirty_baselines, reductions_reflect_output_decline]
  downgrade_triggers: [claim_gate_missing, leakage_artifacts_missing, price_exposure_unverifiable]
not_recommended_methods: [default_TWFE_for_staggered_coverage, emissions_only_OLS_as_true_abatement, price_time_series_without_unit_exposure]
```

### Downgrade or overclaim-block input

User: "The regression says covered firms emitted less, so write that the ETS achieved verified abatement and firms complied."

### Downgrade or overclaim-block output

```yaml
skill_name: carbon_market_ets_eval
user_question_summary: "Request to overclaim verified abatement and compliance from an emissions regression."
research_domain: carbon_market_policy
research_brief:
  unit: firm
  time_frequency: year
  outcome_candidates: [reported_emissions]
  treatment_or_exposure: ETS_coverage_dummy
  estimand_candidates: [not_established]
  identification_risks: [selection_into_coverage, output_decline, leakage, reporting_boundary_change, missing_claim_gate]
carbon_market_eval:
  policy_instrument: ETS
  treatment_definition_candidates: [coverage_dummy_only]
  outcome_candidates: [reported_emissions_only]
  main_identification_risks: [nonrandom_coverage, industry_trends, energy_price_shocks, untested_leakage, unverified_output_adjustment]
  design_candidates: [downgrade_to_descriptive_association_until_artifacts_exist]
  required_controls: [sector_year_effects, energy_prices, output_or_sales, boundary_change_flags]
  leakage_checks: [blocked_because_no_affiliate_or_trade_outcomes_provided]
  pass_through_checks: [blocked_because_no_price_outcomes_provided]
  forbidden_claims: [verified_abatement, legal_compliance, market_integrity, random_assignment]
candidate_workflows: [artifact_review_before_claim_language]
candidate_methods: [none_until_spec_and_diagnostics_are_verified]
required_diagnostics: [claim_gate_json, output_adjustment, leakage_outcomes, boundary_audit, pretrend_and_overlap_checks]
recommended_robustness: [not_applicable_until_core_design_exists]
forbidden_claims: [ETS_achieved_verified_abatement, firms_complied, market_manipulation_or_no_manipulation]
claim_language:
  allowed: ["Reported emissions are lower in the estimated specification, but abatement, leakage, and compliance claims are not supported yet."]
  disallowed: ["The ETS achieved verified abatement and firms complied."]
uncertainty_notes: [official_coverage_and_compliance_rules_must_be_checked_at_use_time]
next_code_actions: [inspect_claim_gate, audit_output_adjustment, add_leakage_checks, verify_reporting_boundaries]
scholarly_depth:
  estimand_definition: "Not established; the supplied result is an emissions association, not verified abatement."
  identification_assumptions: [not_satisfied_from_current_artifacts]
  measurement_model: [reported_emissions_only_cannot_distinguish_abatement_from_scale_or_boundary_change]
  data_construction_risks: [coverage_misclassification, missing_output, missing_affiliates, reporting_change]
  method_decision_tree: [missing_core_artifacts_to_downgrade, add_design_before_causal_language]
  diagnostics_that_block_claims: [missing_claim_gate, no_output_adjustment, no_leakage_check, no_compliance_authority]
  robustness_ranked_by_risk: [output_adjustment_first, leakage_second, sector_year_controls_third]
  referee_objections: [selection_into_regulation, reductions_due_to_output_decline, leakage_to_unregulated_units]
  downgrade_triggers: [claim_gate_missing, compliance_claim_requested, legal_language_requested]
not_recommended_methods: [emissions_only_regression_as_compliance_evidence, binary_coverage_OLS_without_sector_year_controls]
```

## Completion checklist

* All required section headers are present exactly once.
* Shared rule files `01` through `07` are cited by relative path.
* The skill starts from estimand, measurement model, identification assumptions, and domain-specific failure modes, not from an estimator.
* Regulated/unregulated units, sector eligibility, compliance boundaries, and reporting boundaries are explicit.
* Treatment definitions distinguish coverage, compliance obligation, allowance-price exposure, free allocation, auction share, tax rate, offset access, and phase changes.
* Absolute emissions decline is separated from true abatement through output, leakage, boundary, reporting, exit, relocation, and fuel-switching checks.
* Banking, borrowing, offsets, free allocation intensity, quota allocation, allowance prices, innovation, pass-through, and leakage are covered.
* Sector-year, industry-year, region-year, energy-price, and concurrent-policy controls are named where relevant.
* Selection into regulation and quota allocation endogeneity are treated as central risks.
* Official/latest lookup is required for volatile ETS and carbon-tax definitions.
* The exact `carbon_market_eval` block, `scholarly_depth`, and `not_recommended_methods` are present in the output schema.
* Forbidden claims block random ETS inclusion, unsupported abatement, ignored trends, and legal/compliance/market-manipulation claims.
* Handoff to code and handoff from artifacts name concrete validations, artifacts, and downgrade rules.
* At least two minimal examples are included: good planning and overclaim blocking.
* No estimator is run, no backend is certified, and no artifact is validated by the skill itself.
