# Skill: green_innovation_patent_text
## Purpose
Plan scholar-grade green innovation measurement and causal-design triage using patents, patent taxonomies, citations, patent families, assignee matching, green text intensity, R&D measures, and policy or finance exposures.

This skill separates green innovation proxy construction from causal claims about green finance, subsidies, disclosure rules, regulation, carbon pricing, procurement, or industrial policy. It defines what the proxy measures, how matching and classification may fail, which timing and lag structure is defensible, and which claims must be downgraded until code artifacts and `claim_gate.json` allow stronger language.

This skill is a prompt and rubric layer. It does not run estimators, validate backends, certify artifacts, discover patent databases, give legal patent advice, or prove true technology progress.

Always read and apply these shared rules before using this skill:

- `../_shared/01_claim_language_rules.md`
- `../_shared/02_evidence_lookup_rules.md`
- `../_shared/03_artifact_reading_rules.md`
- `../_shared/04_spec_drafting_rules.md`
- `../_shared/05_forbidden_fallbacks.md`
- `../_shared/06_reviewer_mode_rules.md`
- `../_shared/07_scholarly_depth_rules.md`
- `../_shared/08_domain_literature_anchor_rules.md`

Any causal, paper-ready, backend-certified, legal, compliance, audit, assurance, or true-innovation claim must be supported by code artifacts and allowed by `claim_gate.json`.
## When to use
Use this skill when the user asks about:

- green patents, climate patents, low-carbon patents, clean-energy patents, environmental-technology patents, or green innovation proxies;
- IPC, CPC, Y-tag, official taxonomy, database label, keyword, dictionary, embedding, or classifier-based green technology mapping;
- firm-patent, assignee, inventor, subsidiary-parent, legal-identifier, M&A, address, or name-disambiguation matching;
- patent counts, applications, grants, priority filings, publication years, families, forward citations, claims, renewals, family size, or citation-weighted patents;
- green text intensity in patents, annual reports, ESG reports, project descriptions, R&D abstracts, earnings calls, news, or disclosures;
- innovation lags after green finance, green credit, subsidies, regulation, disclosure mandates, carbon markets, environmental enforcement, procurement, industrial policy, or investor pressure;
- whether a completed run can support language about green innovation quantity, quality, direction, timing, or causal policy effects.
## Do not use when
Do not use this skill when:

- the user only needs to run an already validated estimator with no patent, text, taxonomy, matching, lag, or innovation-proxy decision;
- the task is legal patent advice, freedom-to-operate analysis, infringement analysis, valuation certification, IP litigation support, or patentability review;
- the user asks to certify that a patent database is complete or that a taxonomy is legally authoritative without official/latest lookup;
- the user asks to equate patent counts mechanically with true green technology progress;
- the user asks for a causal conclusion without design artifacts, diagnostics, and `claim_gate.json`.
## Inputs expected
Collect or infer these inputs before recommending a main design:

- Research question and intended claim: measurement, descriptive association, predictive text proxy, or causal effect.
- Unit: firm, plant, inventor, assignee, region, industry, bank, portfolio, patent, patent family, technology class, or country.
- Time frequency: application year, grant year, priority year, publication year, filing month, firm-year, region-year, or event time.
- Treatment or exposure: green finance, credit policy, subsidy, regulation, carbon market, disclosure mandate, procurement rule, industrial policy, emissions shock, investor pressure, or enforcement.
- Outcome candidates: green patent count, citation-weighted green patents, green patent share, patent-family count, high-value green patents, claims, renewals, green text intensity, R&D spending, green R&D text, or product releases.
- Patent database, text corpus, coverage window, and access constraints.
- Green patent taxonomy and classification map: IPC, CPC, Y tags, keyword map, official technology taxonomy, database-specific labels, or machine-learning classifier.
- Firm-patent matching approach: assignee names, standardized names, legal identifiers, subsidiaries, parent links, M&A events, addresses, inventor affiliations, or external concordances.
- Timing rules: application vs grant vs priority vs publication year, family aggregation, citation-window length, truncation policy, and innovation-lag assumptions.
- Policy, finance, R&D, subsidy, procurement, regulation, sector-trend, and industrial-policy confounders.
- Existing artifacts if interpreting prior runs.

For volatile definitions, require official/latest lookup at use time. Do not hardcode patent taxonomy vintages, IPC/CPC/Y mappings, official green lists, patent database coverage, legal technology categories, agency definitions, API fields, package availability, or classification maps inside the skill response.
## Required repo artifacts to inspect
Inspect workspace files first. Do not rely on installed user-level skills as authority for this repository.

Required repository files and folders:

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
- existing shared, intake, domain, reporting, schema, and delivery-check files

When a run exists, inspect available artifacts before interpreting results:

- `status.json`, `claim_gate.json`, `manifest.json`, `artifact_manifest.json`
- `diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json` or `backend_status.json`
- patent taxonomy, IPC/CPC/Y mapping, and unmatched-code manifests
- firm-patent matching audit, assignee disambiguation logs, parent-subsidiary and M&A mapping logs
- patent-family construction and duplicate-filing diagnostics
- application, priority, grant, and publication timing diagnostics
- lag-structure, event-time support, citation-window, truncation, and field-year normalization diagnostics
- text dictionary or classifier validation, leakage audit, holdout results, and vocabulary drift artifacts
- overlap, balance, pretrend, R&D, subsidy, regulation, and industrial-policy confounder artifacts
- `model_table.csv`, only after diagnostics and claim gate

If these artifacts are unavailable, the skill may draft design questions and candidate routes, but it must mark capability-dependent claims as unknown, partial, exploratory, or blocked.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Popp (2002), American Economic Review, Induced Innovation and Energy Prices"
    - "Acemoglu, Aghion, Bursztyn, and Hemous (2012), American Economic Review, The Environment and Directed Technical Change"
    - "Johnstone, Haščič, and Popp (2010), Environmental and Resource Economics, Renewable Energy Policies and Technological Innovation"
    - "Dechezleprêtre, Glachant, Haščič, Johnstone, and Ménière (2011), Review of Environmental Economics and Policy, Invention and Transfer of Climate Change-Mitigation Technologies"
    - "Calel and Dechezleprêtre (2016), Review of Economics and Statistics, Environmental Policy and Directed Technological Change"
    - "Veefkind, Hurtado-Albir, Angelucci, Karachalios, and Thumm (2012), World Patent Information, A New EPO Classification Scheme for Climate Change Mitigation Technologies"
    - "OECD (2009), OECD Patent Statistics Manual"
  canonical_data_sources:
    - "Johnstone, Haščič, and Popp (2010), Environmental and Resource Economics, Renewable Energy Policies and Technological Innovation"
    - "current PATSTAT, DOCDB, INPADOC, PatentsView, and OECD patent database vintages"
    - "current full-text database coverage"
    - "current machine-translation fields"
    - "current labeled training set"
    - "current patent-text/vector database version"
    - "current assignee-disambiguation file"
    - "current firm-link table"
    - "current ownership database"
    - "current patent database date-field definitions"
  live_lookup_required_for:
    - "current CPC/Y02/Y04S taxonomy release"
    - "current EPO classification notes"
    - "current PATSTAT, DOCDB, INPADOC, PatentsView, and OECD patent database vintages"
    - "current CPC scheme"
    - "current Y02/Y04S definitions"
    - "current patent-office classification coverage"
    - "current full-text database coverage"
    - "current machine-translation fields"
    - "current labeled training set"
    - "current patent-text/vector database version"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Popp (2002), American Economic Review, Induced Innovation and Energy Prices"
    use_for: "energy-price-induced innovation, patent counts, citation-weighted innovation response"
    live_lookup_required: []

    citation: "Acemoglu, Aghion, Bursztyn, and Hemous (2012), American Economic Review, The Environment and Directed Technical Change"
    use_for: "directed technical change, clean versus dirty innovation, path dependence, policy timing"
    live_lookup_required: []

    citation: "Johnstone, Haščič, and Popp (2010), Environmental and Resource Economics, Renewable Energy Policies and Technological Innovation"
    use_for: "policy-induced renewable-energy patenting, technology-specific policy instruments"
    live_lookup_required: []

    citation: "Dechezleprêtre, Glachant, Haščič, Johnstone, and Ménière (2011), Review of Environmental Economics and Policy, Invention and Transfer of Climate Change-Mitigation Technologies"
    use_for: "international diffusion, patent families, climate-mitigation technology transfer"
    live_lookup_required: []

    citation: "Calel and Dechezleprêtre (2016), Review of Economics and Statistics, Environmental Policy and Directed Technological Change"
    use_for: "EU ETS and low-carbon patenting, regulated-firm treatment assignment"
    live_lookup_required: []

    citation: "Veefkind, Hurtado-Albir, Angelucci, Karachalios, and Thumm (2012), World Patent Information, A New EPO Classification Scheme for Climate Change Mitigation Technologies"
    use_for: "CPC/Y02 green technology taxonomy, classification logic, search precision"
    live_lookup_required: ["current CPC/Y02/Y04S taxonomy release", "current EPO classification notes"]

    citation: "OECD (2009), OECD Patent Statistics Manual"
    use_for: "patent families, priority years, applicant/inventor geography, citation and quality measures"
    live_lookup_required: ["current PATSTAT, DOCDB, INPADOC, PatentsView, and OECD patent database vintages"]
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "CPC/Y02 and Y04S labels"
    - "patents tagged by climate-change mitigation/adaptation and smart-grid classifications"
    - "Keyword dictionary"
    - "green patents identified from title, abstract, claims, or description terms"
    - "Supervised classifier"
    - "trained green/non-green labels using patent text, classifications, citations, or assignee features"
    - "LLM classifier"
    - "prompted or fine-tuned model labels for green relevance, mitigation channel, adaptation channel, or technology class"
    - "Precision, recall, and validation set"
    - "human-coded stratified holdout with precision, recall, F1, calibration, false-positive and false-negative audits"
  validation_targets:
    - "Precision, recall, and validation set"
    - "overall accuracy hides rare-class failure"
    - "validation on easy Y02 positives overstates external validity"
    - "random patent samples underrepresent frontier green technologies"
    - "current validation-label release"
    - "current taxonomy version used by annotators"
    - "Green label provenance"
    - "Is each patent label traced to CPC/Y02, keyword rules, supervised labels, LLM prompts, or human coding?"
    - "Validation"
    - "Are precision, recall, F1, and false-positive/false-negative examples reported on a holdout not used to build labels?"
  known_mismeasurement_channels:
    - "taxonomy updates create artificial trends"
    - "office-specific classification lag"
    - "Y02 precision may miss emerging technologies outside taxonomy"
    - "low precision from generic words"
    - "language and translation effects"
    - "sector-specific jargon"
    - "dictionary drift across cohorts"
    - "training labels often inherit CPC/Y02 errors"
    - "class imbalance inflates accuracy"
    - "features can leak assignee, year, or taxonomy labels"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "CPC/Y02 and Y04S labels"
    measure: "patents tagged by climate-change mitigation/adaptation and smart-grid classifications"
    pitfalls: ["taxonomy updates create artificial trends", "office-specific classification lag", "Y02 precision may miss emerging technologies outside taxonomy"]
    live_lookup_required: ["current CPC scheme", "current Y02/Y04S definitions", "current patent-office classification coverage"]

    item: "Keyword dictionary"
    measure: "green patents identified from title, abstract, claims, or description terms"
    pitfalls: ["low precision from generic words", "language and translation effects", "sector-specific jargon", "dictionary drift across cohorts"]
    live_lookup_required: ["current full-text database coverage", "current machine-translation fields"]

    item: "Supervised classifier"
    measure: "trained green/non-green labels using patent text, classifications, citations, or assignee features"
    pitfalls: ["training labels often inherit CPC/Y02 errors", "class imbalance inflates accuracy", "features can leak assignee, year, or taxonomy labels"]
    live_lookup_required: ["current labeled training set", "current patent-text/vector database version"]

    item: "LLM classifier"
    measure: "prompted or fine-tuned model labels for green relevance, mitigation channel, adaptation channel, or technology class"
    pitfalls: ["model version drift", "prompt sensitivity", "non-reproducible hidden reasoning", "training-data contamination with patent labels"]
    live_lookup_required: ["current model version", "current API behavior", "current patent corpus used for inference"]

    item: "Precision, recall, and validation set"
    measure: "human-coded stratified holdout with precision, recall, F1, calibration, false-positive and false-negative audits"
    pitfalls: ["overall accuracy hides rare-class failure", "validation on easy Y02 positives overstates external validity", "random patent samples underrepresent frontier green technologies"]
    live_lookup_required: ["current validation-label release", "current taxonomy version used by annotators"]

    item: "Assignee disambiguation and firm matching"
    measure: "standardized applicant names linked to firms, ultimate owners, subsidiaries, listed entities, and facilities"
    pitfalls: ["M&A and subsidiary ownership create false trends", "university/government assignees differ from corporate innovators", "name harmonization errors are non-random"]
    live_lookup_required: ["current assignee-disambiguation file", "current firm-link table", "current ownership database"]

    item: "Patent family and priority timing"
    measure: "invention counted by priority application or simple/extended family rather than every jurisdictional filing"
    pitfalls: ["counting family members as separate inventions", "grant-year lag bias", "family size mixes invention value and filing strategy"]
    live_lookup_required: ["current DOCDB/INPADOC family definitions", "current PATSTAT release"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "calling any green-patent increase directed technical change"
    - "treating classifier labels as ground truth"
    - "high validation accuracy driven by leaked labels"
    - "attributing acquired patents to post-treatment R&D"
    - "counting jurisdictional filings as independent inventions"
    - "confounding policy adoption with pre-existing clean-tech momentum"
  sorting_vs_siting_or_selection_channel:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  why_method_not_magic:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Directed technical change"
    core_issue: "Clean patenting can rise because total innovation rises, dirty innovation falls, classification improves, or policy redirects inventive effort."
    acceptable_designs: ["clean-versus-dirty shares", "technology-by-firm panels", "pre-policy innovation trends", "energy-price or policy shocks"]
    referee_risk: "calling any green-patent increase directed technical change"
    live_lookup_required: ["current patent taxonomy and sector concordance"]

    item: "Label validity"
    core_issue: "CPC/Y02, dictionaries, supervised models, and LLM labels estimate different constructs."
    acceptable_designs: ["method triangulation", "human-coded holdouts", "precision/recall by technology class", "false-positive audits"]
    referee_risk: "treating classifier labels as ground truth"
    live_lookup_required: ["current classifier and taxonomy versions"]

    item: "Green patent label leakage"
    core_issue: "Models can learn CPC/Y02 tags, assignee names, years, policy regimes, or downstream outcomes rather than technological greenness."
    acceptable_designs: ["remove taxonomy fields", "mask firm names", "train/test split by firm and year", "out-of-taxonomy validation"]
    referee_risk: "high validation accuracy driven by leaked labels"
    live_lookup_required: ["current feature construction and label provenance"]

    item: "Assignee and ownership dynamics"
    core_issue: "Firm-level innovation treatment effects are biased when assignee names, subsidiaries, mergers, or patent sales are mishandled."
    acceptable_designs: ["ultimate-owner panels", "M&A-adjusted assignee histories", "subsidiary robustness", "inventor-location checks"]
    referee_risk: "attributing acquired patents to post-treatment R&D"
    live_lookup_required: ["current ownership, M&A, and assignee-link versions"]

    item: "Patent families and value"
    core_issue: "Raw patent counts mix duplicate filings, low-value filings, strategic patents, and high-value inventions."
    acceptable_designs: ["priority-year family counts", "citation-weighted outcomes", "claims/family-size robustness", "grant-versus-application checks"]
    referee_risk: "counting jurisdictional filings as independent inventions"
    live_lookup_required: ["current patent-family and citation database vintage"]

    item: "Policy endogeneity"
    core_issue: "Green innovation policies target sectors, regions, and firms already on different innovation trajectories."
    acceptable_designs: ["event studies with pre-trends", "matched firm-sector controls", "instrumented policy exposure", "technology-specific policy variation"]
    referee_risk: "confounding policy adoption with pre-existing clean-tech momentum"
    live_lookup_required: ["current policy database and eligibility rules"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Green label provenance"
    - "Is each patent label traced to CPC/Y02, keyword rules, supervised labels, LLM prompts, or human coding?"
    - "Validation"
    - "Are precision, recall, F1, and false-positive/false-negative examples reported on a holdout not used to build labels?"
    - "Leakage"
    - "Are CPC codes, assignee names, year, policy indicators, citations, and outcome variables excluded or stress-tested when they can leak labels?"
    - "Patent family"
    - "Are applications collapsed to priority-year families before interpreting invention counts?"
    - "Assignee disambiguation"
    - "Are names, subsidiaries, M&A, ultimate owners, and patent transfers handled before firm-level inference?"
  minimal_empirical_section_checklist:
    - "Green label provenance"
    - "Is each patent label traced to CPC/Y02, keyword rules, supervised labels, LLM prompts, or human coding?"
    - "current taxonomy and model versions"
    - "Validation"
    - "Are precision, recall, F1, and false-positive/false-negative examples reported on a holdout not used to build labels?"
    - "current validation-set release"
    - "Leakage"
    - "Are CPC codes, assignee names, year, policy indicators, citations, and outcome variables excluded or stress-tested when they can leak labels?"
    - "current feature set and label metadata"
    - "Patent family"
  claims_to_downgrade:
    - "Do not treat CPC/Y02, keyword, supervised, and LLM green labels as interchangeable."
    - "Do not report classifier accuracy without precision, recall, class balance, and holdout-label provenance."
    - "Do not train or validate green classifiers with leaked CPC/Y02 tags, firm names, policy years, ESG labels, or future outcomes unless explicitly stress-tested."
    - "Do not count patent family members across jurisdictions as separate inventions."
    - "Do not infer directed technical change from green patent counts without clean-versus-dirty, total innovation, and pre-trend evidence."
    - "Do not use firm-level patent outcomes without assignee disambiguation, M&A handling, and ownership timing checks."
    - "Do not make current claims about CPC/Y02 taxonomy, PATSTAT/DOCDB/INPADOC, PatentsView, patent-office APIs, or model/provider versions without live lookup."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Green label provenance"
    ask: "Is each patent label traced to CPC/Y02, keyword rules, supervised labels, LLM prompts, or human coding?"
    live_lookup_required: ["current taxonomy and model versions"]

    check: "Validation"
    ask: "Are precision, recall, F1, and false-positive/false-negative examples reported on a holdout not used to build labels?"
    live_lookup_required: ["current validation-set release"]

    check: "Leakage"
    ask: "Are CPC codes, assignee names, year, policy indicators, citations, and outcome variables excluded or stress-tested when they can leak labels?"
    live_lookup_required: ["current feature set and label metadata"]

    check: "Patent family"
    ask: "Are applications collapsed to priority-year families before interpreting invention counts?"
    live_lookup_required: ["current DOCDB/INPADOC/PATSTAT family version"]

    check: "Assignee disambiguation"
    ask: "Are names, subsidiaries, M&A, ultimate owners, and patent transfers handled before firm-level inference?"
    live_lookup_required: ["current assignee and ownership link files"]

    check: "Directed-change estimand"
    ask: "Does the design separate clean-patent levels, clean shares, dirty-patent displacement, and total R&D?"
    live_lookup_required: []

    check: "Policy timing"
    ask: "Are application, priority, publication, and grant dates separated relative to the policy shock?"
    live_lookup_required: ["current patent database date-field definitions"]
```

## Forbidden claims

- Do not treat CPC/Y02, keyword, supervised, and LLM green labels as interchangeable.
- Do not report classifier accuracy without precision, recall, class balance, and holdout-label provenance.
- Do not train or validate green classifiers with leaked CPC/Y02 tags, firm names, policy years, ESG labels, or future outcomes unless explicitly stress-tested.
- Do not count patent family members across jurisdictions as separate inventions.
- Do not infer directed technical change from green patent counts without clean-versus-dirty, total innovation, and pre-trend evidence.
- Do not use firm-level patent outcomes without assignee disambiguation, M&A handling, and ownership timing checks.
- Do not make current claims about CPC/Y02 taxonomy, PATSTAT/DOCDB/INPADOC, PatentsView, patent-office APIs, or model/provider versions without live lookup.

## Domain reasoning steps
1. Separate proxy construction from causal effect.
   - First define what the patent or text variable measures.
   - Then decide whether the research design can support a causal effect of policy, finance, subsidy, regulation, or disclosure on that proxy.
   - A well-labeled green patent variable does not substitute for identification.

2. Define the innovation estimand in words.
   - Examples: change in green patent applications per firm-year, effect on citation-weighted green patent families, effect on green patent share, effect on high-value green invention proxy, or descriptive green text intensity.
   - State whether the estimand concerns quantity, quality, direction, novelty, commercialization potential, or narrative emphasis.

3. Choose timing deliberately.
   - Application year is often closer to inventive activity; grant year reflects examination delay; priority year places inventions within families; publication year may matter for public information.
   - Lag structure must reflect innovation delay, application-grant delay, policy anticipation, and reporting availability.
   - Do not interpret grant-year changes as invention-timing effects without application or priority-year checks.

4. Audit the green patent taxonomy.
   - Identify taxonomy source and vintage through official/latest lookup at use time.
   - Map IPC, CPC, Y tags, database codes, or text classifications to green technology classes.
   - Record one-to-many mappings, code revisions, broad vs narrow definitions, unmatched codes, and taxonomy changes.
   - Keyword-only classification is measurement-error prone unless validated.

5. Treat firm-patent links as a measurement model.
   - Specify assignee normalization, legal suffix handling, language and transliteration rules, subsidiary-parent mapping, M&A handling, addresses, inventor affiliations, and external identifiers.
   - Require match rates and false-match audits by firm, year, country, industry, and treatment status.
   - Low-quality matching blocks strong firm-level conclusions even when regression coefficients are significant.

6. Define aggregation and de-duplication.
   - Decide whether the unit is application, grant, simple family, extended family, firm-family-year, or firm-year.
   - Avoid double-counting the same invention across jurisdictions unless the estimand is international filing activity.
   - Patent families reduce duplicate filings but change geography, timing, and value interpretation.

7. Distinguish innovation quantity, quality, and commercialization.
   - Counts measure filings, not true technological progress.
   - Quality candidates include forward citations, claims, family size, renewals, international filings, examiner citations, grant status, or high-value thresholds.
   - Citation weighting requires citation-window truncation handling and field-year normalization.

8. Address strategic patenting and disclosure behavior.
   - Policies and finance conditions may change filing incentives, green labels, defensive patenting, continuations, trade-secret choices, or disclosure propensity.
   - Green text intensity may measure communication strategy, reporting pressure, or greenwashing risk rather than technology creation.
   - Treat text intensity as a narrative or classification proxy unless validated against technical outputs.

9. Model confounding from R&D, subsidies, and industrial policy.
   - Green finance exposure may coincide with R&D subsidies, procurement, local industrial policy, environmental regulation, carbon-market exposure, sector trends, or technology booms.
   - Require controls, fixed effects, comparison restrictions, or alternative designs that address these confounders.
   - Do not interpret a finance coefficient as innovation causality without design artifacts and claim gating.

10. Choose estimators by data-generating features.
    - Count outcomes may require PPML or count-compatible designs if supported by the repo and backend; OLS/log counts are not automatically equivalent.
    - Staggered policy timing requires estimand-first modern DID logic, not default TWFE.
    - Firm-level treatment needs overlap in pre-policy innovation, R&D, industry, size, finance access, and patenting propensity.
    - Text classifiers require leakage audits, holdout validation, and vocabulary drift checks before confirmatory use.

11. Rank robustness by measurement failure mode.
    - Alternative taxonomies address classification error.
    - Application, priority, grant, and publication-year outcomes address timing sensitivity.
    - Family aggregation addresses duplicate filings.
    - Citation windows and field-year normalization address quality truncation.
    - Assignee-match thresholds address firm-linkage error.
    - Lag structures address delayed innovation response.
    - Subsidy, R&D, procurement, and industry-year controls address confounding.

12. Gate claims using code artifacts.
    - Strong causal claims require diagnostics plus `claim_gate.json`.
    - Strong firm-level claims require matching audits.
    - Strong green-technology claims require taxonomy and measurement metadata.
    - Strong quality claims require citation-window, field-year, and truncation handling.
    - Missing artifacts force downgrade to proxy construction, descriptive association, or exploratory pattern.
## Candidate outputs
This skill may return:

- a `green_innovation_plan` YAML or JSON plan;
- a patent proxy measurement plan;
- a taxonomy, IPC/CPC/Y mapping, and unmatched-code audit plan;
- a firm-patent matching and assignee-disambiguation checklist;
- a lag-structure and timing decision tree;
- a quality-adjustment plan for citations, claims, renewals, and families;
- a green text intensity validation plan;
- a confounding and identification-risk plan;
- safe claim language with explicit downgrades;
- code handoff instructions for diagnostics, artifacts, and claim gating.
## Output schema
Return YAML by default, or JSON if requested. Do not omit the base fields. Include the domain-specific block exactly as shown, with additions allowed after it. Include `scholarly_depth` and `not_recommended_methods`.

```yaml
skill_name: green_innovation_patent_text
user_question_summary: string
research_domain: green_innovation
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: null
  estimand_candidates: []
  identification_risks: []
green_innovation_plan:
  innovation_proxy_candidates: []
  matching_requirements: []
  lag_structure_candidates: []
  quality_adjustment_candidates: []
  measurement_error_risks: []
  robustness_checks: []
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
- Green patent counts are proxies for green inventive output, not true green technology progress.
- Patent quantity, patent quality, novelty, and commercialization are distinct constructs.
- Application year, grant year, publication year, and priority year answer different timing questions.
- Patent lag and policy anticipation must be modeled before interpreting dynamic effects.
- Patent families reduce duplicate filings but change interpretation of jurisdiction, timing, and value.
- IPC/CPC/Y or other green mappings require official/latest lookup at use time.
- Assignee and firm-name matching errors can bias firm-level treatment effects; low match quality blocks strong firm-level conclusions.
- Forward citations require truncation handling and field-year normalization.
- Green text intensity can reflect disclosure strategy, marketing, reporting pressure, classifier drift, or greenwashing risk rather than innovation.
- R&D, subsidies, procurement, industrial policy, regulation, and sector technology trends are major confounders.
- Code artifacts and `claim_gate.json` control strong causal, paper-ready, policy-ready, or true-innovation claims.
## Forbidden claims
Do not claim or imply:

- green patent count equals true green technology progress;
- citation-weighted patents fully measure quality without truncation, field-year normalization, and citation-window discussion;
- green text intensity proves real low-carbon innovation without validation against technical outputs;
- grant-year changes are invention-timing effects without application, priority, or lag analysis;
- policy effects are immediate unless the innovation-lag structure supports it;
- firm-level innovation conclusions are strong when matching, assignee disambiguation, or parent-subsidiary mapping is low quality;
- green finance, ESG, disclosure, subsidy, or regulation caused innovation without credible design artifacts and `claim_gate.json`;
- a patent taxonomy, IPC/CPC/Y map, database label, API field, or legal technology category is current without official/latest lookup at use time;
- duplicate jurisdictional filings are separate inventions unless the estimand is filing activity;
- PPML, DID, DML, causal forest, or text classifiers are credible by name alone without design-specific diagnostics;
- OLS or log-linear fallback is equivalent to a count model when the intended estimator requires a different backend;
- `model_table.csv` alone authorizes causal, quality, or firm-level innovation claims.
## Handoff to code
Draft a concrete spec and ask code to verify only what code can verify.

Required code handoff fields:

- unit and time key: firm-year, region-year, patent-year, family-year, or other;
- treatment timing, exposure definition, anticipation window, innovation-lag windows, comparison group, controls, fixed effects, clusters, and weights;
- patent database, coverage window, taxonomy source, vintage, and official/latest lookup requirement;
- IPC/CPC/Y mapping table or other green classification map, with broad/narrow definitions and unmatched-code policy;
- outcome timing: application year, grant year, priority year, or publication year;
- patent-family construction rule, jurisdictional de-duplication, and aggregation level;
- assignee normalization, firm identifier, parent-subsidiary mapping, M&A handling, match thresholds, and match-quality scoring;
- citation-window rule, truncation adjustment, field-year normalization, claims, renewals, and high-value thresholds;
- green text dictionary, classifier, embedding, or model source with validation requirements;
- R&D, subsidy, procurement, regulation, industrial-policy, industry-year, region-year, firm-size, and pre-policy patenting confounders;
- count-outcome method requirements and backend constraints.

Ask code to produce or verify:

- patent taxonomy manifest and IPC/CPC/Y mapping coverage report;
- firm-patent matching audit by year, industry, treatment status, country, and firm size;
- assignee disambiguation, parent-subsidiary, and M&A mapping logs;
- patent-family construction and duplicate-filing diagnostics;
- application, priority, grant, and publication timing distributions;
- lag-structure diagnostics and dynamic event-time support;
- citation-window truncation and field-year normalization outputs;
- text classifier validation, leakage audit, holdout results, and vocabulary drift diagnostics;
- overlap and balance diagnostics for treated and comparison firms;
- confounder coverage for R&D, subsidies, procurement, regulation, and industrial policy;
- `diagnostics.json`, `reviewer_risk.json`, `manifest.json` or `artifact_manifest.json`, and `claim_gate.json`.

Do not ask code to certify true technological progress, legal patent status, compliance, audit assurance, or a causal finance effect without claim gating.
## Handoff from code artifacts
Before writing strong language, read the artifacts that establish or block claim readiness:

- `claim_gate.json`, `status.json`, `manifest.json` or `artifact_manifest.json`
- `diagnostics.json`, `reviewer_risk.json`, `backend_discovery.json` or `backend_status.json`
- patent taxonomy, IPC/CPC/Y mapping, unmatched-code, and classification manifests
- firm-patent matching audit, assignee disambiguation, parent-subsidiary, and M&A logs
- patent-family construction and duplicate-filing diagnostics
- application, priority, grant, and publication timing diagnostics
- lag-structure and event-time support diagnostics
- citation-window, truncation, and field-year normalization diagnostics
- text validation, leakage, holdout, and vocabulary drift artifacts
- overlap, balance, pretrend, R&D, subsidy, procurement, regulation, and industrial-policy confounder artifacts
- `model_table.csv`, only after claim gate and diagnostics

Downgrade rules:

- If `claim_gate.json` is missing, mark strong causal and paper-ready claims as unknown or blocked.
- If taxonomy or IPC/CPC/Y metadata is missing, call green classification exploratory.
- If firm-patent matching audit is missing or weak, block strong firm-level conclusions.
- If application, priority, grant, and publication timing are not distinguished, block precise innovation-timing claims.
- If lag diagnostics are missing, block dynamic or immediate-response claims.
- If family de-duplication is missing, avoid invention-count claims.
- If citation-window truncation is missing, avoid quality claims based on citations.
- If text validation is missing, describe green text intensity as a narrative proxy only.
- If R&D, subsidy, regulation, procurement, or industrial-policy confounding is unaddressed, downgrade causal language to association or exploratory evidence.
## Minimal examples
### Good planning example
User: "Did green finance increase the quality of firms' green innovation?"

```yaml
skill_name: green_innovation_patent_text
user_question_summary: "Assess whether green finance exposure changed firm-level green patent quality proxies."
research_domain: green_innovation
research_brief:
  unit: firm_year
  time_frequency: annual
  outcome_candidates: [citation_weighted_green_patent_families, green_patent_family_count, high_value_green_patent_share]
  treatment_or_exposure: green_finance_exposure
  estimand_candidates: [dynamic_ATT_on_green_patent_quality_proxy]
  identification_risks: [selection_into_green_finance, R_and_D_subsidy_confounding, industry_green_trends, matching_error, citation_truncation]
green_innovation_plan:
  innovation_proxy_candidates: [citation_weighted_green_patent_families_by_application_year, green_patent_family_count_by_priority_year, green_patent_share]
  matching_requirements: [assignee_normalization, firm_identifier_crosswalk, parent_subsidiary_mapping, M_and_A_check, match_rate_by_treatment_status]
  lag_structure_candidates: [event_time_lags_0_to_5_application_year, priority_year_sensitivity, grant_year_secondary]
  quality_adjustment_candidates: [fixed_window_forward_citations, field_year_normalized_citations, family_size, claims_or_renewals]
  measurement_error_risks: [IPC_CPC_Y_classification_error, disambiguation_error, application_grant_lag, duplicate_filings, strategic_patenting]
  robustness_checks: [narrow_vs_broad_taxonomy, application_vs_priority_year, family_vs_application_counts, citation_window_sensitivity, high_confidence_matches, subsidy_controls]
  forbidden_claims: [green_patent_count_equals_true_technology_progress, green_finance_caused_innovation_without_claim_gate]
candidate_workflows: [patent_proxy_construction, modern_DID_if_timing_overlap_pretrends_valid, count_model_if_backend_validated]
candidate_methods: [dynamic_ATT_for_firm_year_panel, PPML_or_count_compatible_model_if_supported, citation_weighted_family_outcome]
required_diagnostics: [taxonomy_mapping_manifest, firm_patent_match_audit, timing_diagnostics, family_deduplication, citation_truncation, overlap_in_pre_policy_patenting, claim_gate_json]
recommended_robustness: [narrow_vs_broad_green_taxonomy, family_vs_application_count, alternative_lag_windows, high_confidence_matches_only, subsidy_controls]
forbidden_claims: [do_not_claim_true_green_progress_from_counts, do_not_claim_firm_level_effect_with_low_match_quality, do_not_claim_causality_without_claim_gate]
claim_language:
  allowed: ["The design targets changes in green patent quality proxies, conditional on taxonomy, matching, lag, citation, and claim-gate diagnostics."]
  disallowed: ["Green finance caused real green technology progress."]
uncertainty_notes: ["Official/latest patent taxonomy and IPC/CPC/Y mapping must be checked at use time."]
next_code_actions: [build_taxonomy_manifest, run_matching_audit, construct_family_level_application_and_priority_outcomes, produce_lag_and_citation_diagnostics, inspect_claim_gate]
scholarly_depth:
  estimand_definition: "Dynamic effect of green finance exposure on firm-year green patent quality proxies, mainly citation-weighted green patent families by application or priority year."
  identification_assumptions: [credible_counterfactual_innovation_trends, no_uncontrolled_R_and_D_or_subsidy_shock, nondifferential_matching_error, prespecified_lag_structure]
  measurement_model: [official_latest_green_taxonomy_mapping, audited_assignee_links, family_level_deduplication, field_year_normalized_citations]
  data_construction_risks: [taxonomy_vintage_changes, name_matching_false_links, parent_subsidiary_reallocation, citation_truncation, strategic_patenting]
  method_decision_tree: ["valid firm-year panel and pretrends -> modern DID", "many zero counts and backend support -> count-compatible model", "weak matching -> measurement-only or high-confidence subsample"]
  diagnostics_that_block_claims: [missing_taxonomy_manifest, weak_match_audit, missing_family_deduplication, missing_citation_truncation, missing_claim_gate]
  robustness_ranked_by_risk: [high_confidence_matches, alternative_taxonomies, application_vs_priority_year, citation_window_sensitivity, subsidy_controls]
  referee_objections: [green_finance_selection, citations_truncated_and_field_specific, strategic_patenting, taxonomy_captures_peripheral_green_codes]
  downgrade_triggers: [claim_gate_missing, match_quality_low, lag_not_prespecified, subsidy_confounding_unaddressed]
not_recommended_methods: [raw_green_patent_count_as_true_innovation, grant_year_only_as_invention_timing, firm_level_DID_without_match_audit, OLS_log_count_fallback_when_count_model_required]
```

### Downgrade and overclaim-block example
User: "The regression says green finance raised green patent counts. Write that green finance caused real green technology progress at treated firms."

```yaml
skill_name: green_innovation_patent_text
user_question_summary: "User asks to convert a patent-count result into a strong causal technology-progress claim."
research_domain: green_innovation
research_brief:
  unit: firm_year
  time_frequency: annual
  outcome_candidates: [green_patent_count]
  treatment_or_exposure: green_finance
  estimand_candidates: [unspecified_effect_on_patent_count]
  identification_risks: [patent_count_is_proxy, selection_into_green_finance, patent_lag_ignored, matching_quality_unknown, R_and_D_subsidy_confounding]
green_innovation_plan:
  innovation_proxy_candidates: [green_patent_count_proxy_only]
  matching_requirements: [firm_patent_match_audit_required, assignee_disambiguation_required]
  lag_structure_candidates: [application_year_lag_check_required, priority_year_sensitivity_required, grant_year_not_sufficient]
  quality_adjustment_candidates: [citation_weighting_required_for_quality_claim, family_level_deduplication_required]
  measurement_error_risks: [taxonomy_error, matching_error, strategic_patenting, application_grant_lag, duplicate_filings]
  robustness_checks: [alternative_taxonomy, lag_sensitivity, high_confidence_match_subsample, R_and_D_subsidy_controls]
  forbidden_claims: [green_patent_count_equals_true_green_technology_progress, green_finance_caused_innovation_without_claim_gate]
candidate_workflows: [downgrade_to_patent_proxy_language, request_measurement_and_design_artifacts_before_causal_claim]
candidate_methods: [none_for_true_progress_claim_from_count_only]
required_diagnostics: [claim_gate_json, taxonomy_manifest, matching_audit, lag_diagnostics, family_deduplication, quality_proxy_diagnostics, confounder_assessment]
recommended_robustness: [alternative_green_taxonomy, application_priority_grant_year_sensitivity, high_quality_patent_proxy]
forbidden_claims: [do_not_claim_real_green_progress, do_not_claim_causality_without_claim_gate, do_not_claim_firm_level_effect_without_match_quality]
claim_language:
  allowed: ["If claim-gated, the result may be described as an estimated effect on a green patent-count proxy."]
  disallowed: ["Green finance caused real green technology progress at treated firms."]
uncertainty_notes: ["Patent lag, taxonomy, matching, family de-duplication, and quality adjustment are not established."]
next_code_actions: [inspect_claim_gate, audit_firm_patent_matching, construct_application_or_priority_year_lagged_outcomes, add_quality_adjusted_family_outcomes]
scholarly_depth:
  estimand_definition: "At most an effect on a green patent-count proxy; true technology progress is not validated."
  identification_assumptions: [unidentified_from_prompt]
  measurement_model: [green_patent_count_proxy_with_unverified_taxonomy_and_matching]
  data_construction_risks: [low_quality_assignee_match, patent_lag_ignored, duplicate_filings, strategic_patenting, no_quality_adjustment]
  method_decision_tree: ["count result only -> patent proxy language", "true progress claim requested -> block", "causal finance claim requested -> require design artifacts and claim_gate"]
  diagnostics_that_block_claims: [missing_claim_gate, missing_match_audit, missing_lag_diagnostics, missing_taxonomy_manifest, missing_quality_adjustment]
  robustness_ranked_by_risk: [alternative_taxonomy, high_confidence_matches, application_priority_year, citation_or_family_quality_proxy]
  referee_objections: [counts_reflect_filing_strategy, green_finance_targets_innovators, patent_lags_outside_window, matching_differential_by_size_or_treatment]
  downgrade_triggers: [causal_language_without_claim_gate, true_progress_from_counts, firm_matching_quality_unknown]
not_recommended_methods: [raw_count_to_true_innovation_claim, no_lag_grant_year_regression_as_main_invention_effect, causal_green_finance_claim_without_claim_gate]
```
## Completion checklist
- All required section headers are present exactly.
- Shared rules `01` through `07` are explicitly cited.
- The output schema includes the required `green_innovation_plan` block exactly.
- The output schema includes `scholarly_depth` and `not_recommended_methods`.
- The skill separates patent or text proxy measurement from causal policy effects.
- Green patent taxonomy and IPC/CPC/Y mapping require official/latest lookup at use time.
- Firm-patent matching, assignee disambiguation, parent-subsidiary mapping, M&A handling, and match-rate audits are explicit.
- Application year, grant year, publication year, and priority year are distinguished.
- Innovation lag and anticipation are required before dynamic claims.
- Patent family construction and de-duplication are covered.
- Citation weighting, quality versus quantity, truncation, and field-year normalization are covered.
- Green text intensity is treated as a proxy requiring validation.
- Strategic patenting and disclosure behavior are named as risks.
- R&D, subsidy, regulation, procurement, and industrial-policy confounding are explicit.
- Forbidden claims block patent count equals true green progress, ignoring patent lag, weak firm-name matching, and unsupported green-finance causality.
- Handoff to and from code names concrete artifacts and diagnostics.
- Downgrade rules rely on artifacts and `claim_gate.json`.
