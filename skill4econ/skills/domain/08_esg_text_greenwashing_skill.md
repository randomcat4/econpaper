# Skill: esg_disclosure_text

## Purpose

Plan ESG, sustainability, filing, and climate-disclosure text analysis with evidence spans, quality dimensions, greenwashing-risk indicators, and safe claim language. This skill outputs YAML or JSON. It does not make legal, fraud, intent, compliance, or assurance findings.

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

Use for annual reports, sustainability reports, climate reports, filings, disclosure rules, climate targets, transition plans, physical risk, transition risk, governance, capex, assurance, ESG rating divergence, financing-cost links, and greenwashing-risk indicators.

## Do not use when

Do not use to label a firm fraudulent, illegal, intentionally misleading, or legally greenwashing. Do not use keyword frequency alone as disclosure quality. Do not hardcode current standards, filing rules, or regulatory obligations; query official/latest sources at use time.

## Inputs expected

- Document type, issuer, date, jurisdiction, report period, language, and source path or URL.
- Disclosure topics and quality dimensions to code.
- Evidence span requirements: page, section, chunk ID, source quote, and extraction confidence.
- Coding goal: topic flags, quality score, risk indicator, event input, or econometric variable.
- Existing extraction and run artifacts when interpreting completed work.

## Required repo artifacts to inspect

Inspect `skill4econ/README.md`, `skill4econ/registry.yml`, `skill4econ/cli.py`, `skill4econ/core.py`, `skill4econ/python_wrappers.py`, `skill4econ/workflows.py`, `skill4econ/docs/ARTIFACT_CONTRACT.md`, `skill4econ/docs/BACKEND_CONTRACT.md`, `skill4econ/diagnostics/`, `skill4econ/tests/fixtures/`, and `skill4econ/tests/backends/`. For completed work inspect extraction manifests, evidence span tables, `status.json`, `manifest.json`, `artifact_manifest.json`, `reviewer_risk.json`, `diagnostics.json`, `backend_status.json`, `model_table.csv`, and `claim_gate.json` if present.

## Literature anchors

```yaml
literature_anchors:
  canonical_papers_or_authors:
    - "Loughran and McDonald (2011), Journal of Finance, When Is a Liability Not a Liability?"
    - "Matsumura, Prakash, and Vera-Muñoz (2014), The Accounting Review, Firm-Value Effects of Carbon Emissions and Carbon Disclosures"
    - "Cho, Michelon, Patten, and Roberts (2015), Accounting, Organizations and Society, CSR disclosure and impression management"
    - "Delmas and Burbano (2011), California Management Review, The Drivers of Greenwashing"
    - "Marquis, Toffel, and Zhou (2016), Organization Science, Scrutiny, Norms, and Selective Disclosure"
    - "Bingler, Kraus, Leippold, and Webersinke (2022), Finance Research Letters, Cheap Talk and Cherry-Picking"
    - "Sautner, van Lent, Vilkov, and Zhang (2023), Review of Financial Studies, Firm-Level Climate Change Exposure"
  canonical_data_sources:
    - "latest dataset release"
    - "current replication package location"
    - "bad performance is not automatically greenwashing"
    - "greenwashing requires claim-performance mismatch"
    - "controversy databases are selected and media-driven"
    - "current controversy-provider methodology"
    - "current enforcement and violation datasets"
  live_lookup_required_for:
    - "latest dataset release"
    - "current replication package location"
    - "current firm-level exposure data vintage"
    - "current emissions-provider vintage"
    - "current disclosure mandate"
    - "latest restatement files"
    - "current SEC/ISSB/CSRD filing requirements"
    - "current assurance rules"
    - "current controversy-provider methodology"
    - "current enforcement and violation datasets"
  gpt55_pro_patch_notes: |
    literature_anchors:

    citation: "Loughran and McDonald (2011), Journal of Finance, When Is a Liability Not a Liability?"
    use_for: "financial-disclosure text dictionaries, domain-specific word validation, boilerplate caveats"
    live_lookup_required: []

    citation: "Matsumura, Prakash, and Vera-Muñoz (2014), The Accounting Review, Firm-Value Effects of Carbon Emissions and Carbon Disclosures"
    use_for: "disclosure versus emissions-performance separation, voluntary carbon-disclosure valuation"
    live_lookup_required: []

    citation: "Cho, Michelon, Patten, and Roberts (2015), Accounting, Organizations and Society, CSR disclosure and impression management"
    use_for: "symbolic disclosure, impression management, substantive versus rhetorical ESG claims"
    live_lookup_required: []

    citation: "Delmas and Burbano (2011), California Management Review, The Drivers of Greenwashing"
    use_for: "greenwashing conceptual taxonomy, external and internal incentives"
    live_lookup_required: []

    citation: "Marquis, Toffel, and Zhou (2016), Organization Science, Scrutiny, Norms, and Selective Disclosure"
    use_for: "selective environmental disclosure and activist/regulatory scrutiny"
    live_lookup_required: []

    citation: "Bingler, Kraus, Leippold, and Webersinke (2022), Finance Research Letters, Cheap Talk and Cherry-Picking"
    use_for: "climate-disclosure greenwashing, cheap-talk measures, text-performance mismatch"
    live_lookup_required: ["latest dataset release", "current replication package location"]

    citation: "Sautner, van Lent, Vilkov, and Zhang (2023), Review of Financial Studies, Firm-Level Climate Change Exposure"
    use_for: "earnings-call climate text exposure, opportunity/regulatory/physical-risk classifiers"
    live_lookup_required: ["current firm-level exposure data vintage"]
```

## Measurement regimes

```yaml
measurement_regimes:
  competing_proxy_definitions:
    - "Disclosure text versus actual emissions/performance"
    - "ESG/climate text intensity, target language, risk language, emissions levels, emissions intensity, reductions, capex, abatement, assurance"
    - "Boilerplate versus substantive commitment"
    - "reused language, generic climate risk factors, quantified targets, dated milestones, capex linkage, governance accountability, third-party assurance"
    - "Greenwashing measurement"
    - "gap between positive environmental claims and emissions, toxic releases, controversies, regulatory violations, or subsequent target delivery"
    - "LLM/text classifier validation"
    - "human-labeled holdout sets, inter-annotator agreement, calibration, temporal out-of-sample tests, prompt/model/version logs"
    - "Label leakage"
    - "whether labels, outcomes, firm identity, year, rating-provider fields, or post-treatment text enter features"
  validation_targets:
    - "LLM/text classifier validation"
    - "ESG ratings embedded in training labels can make circular validation"
    - "firm names can proxy sector and style"
    - "future target outcomes can leak into present labels"
    - "Construct definition"
    - "Is greenwashing defined as claim-performance mismatch rather than ESG vocabulary, sentiment, or disclosure length?"
    - "Performance benchmark"
    - "Are claims compared with emissions, intensity, targets, capex, violations, or audited outcomes using consistent scopes and boundaries?"
    - "Boilerplate control"
    - "Does the design separate repeated generic legal language from new, quantified, accountable commitments?"
  known_mismeasurement_channels:
    - "ESG/climate text intensity, target language, risk language, emissions levels, emissions intensity, reductions, capex, abatement, assurance"
    - "text volume is not performance"
    - "emissions may be vendor-estimated"
    - "Scope coverage can change"
    - "firms can disclose more when performance is worse"
    - "reused language, generic climate risk factors, quantified targets, dated milestones, capex linkage, governance accountability, third-party assurance"
    - "generic risk-factor language may be legally driven"
    - "commitment specificity can be mechanically affected by regime shifts"
    - "copy-paste similarity must be benchmarked within filing type"
    - "bad performance is not automatically greenwashing"
  gpt55_pro_patch_notes: |
    measurement_regimes:

    item: "Disclosure text versus actual emissions/performance"
    measure: "ESG/climate text intensity, target language, risk language, emissions levels, emissions intensity, reductions, capex, abatement, assurance"
    pitfalls: ["text volume is not performance", "emissions may be vendor-estimated", "Scope coverage can change", "firms can disclose more when performance is worse"]
    live_lookup_required: ["current emissions-provider vintage", "current disclosure mandate", "latest restatement files"]

    item: "Boilerplate versus substantive commitment"
    measure: "reused language, generic climate risk factors, quantified targets, dated milestones, capex linkage, governance accountability, third-party assurance"
    pitfalls: ["generic risk-factor language may be legally driven", "commitment specificity can be mechanically affected by regime shifts", "copy-paste similarity must be benchmarked within filing type"]
    live_lookup_required: ["current SEC/ISSB/CSRD filing requirements", "current assurance rules"]

    item: "Greenwashing measurement"
    measure: "gap between positive environmental claims and emissions, toxic releases, controversies, regulatory violations, or subsequent target delivery"
    pitfalls: ["bad performance is not automatically greenwashing", "greenwashing requires claim-performance mismatch", "controversy databases are selected and media-driven"]
    live_lookup_required: ["current controversy-provider methodology", "current enforcement and violation datasets"]

    item: "LLM/text classifier validation"
    measure: "human-labeled holdout sets, inter-annotator agreement, calibration, temporal out-of-sample tests, prompt/model/version logs"
    pitfalls: ["LLM labels can encode training-period disclosure norms", "prompt drift breaks reproducibility", "few-shot examples can leak labels", "accuracy on generic ESG text may not transfer to filings"]
    live_lookup_required: ["current model version", "current API behavior", "current benchmark labels"]

    item: "Label leakage"
    measure: "whether labels, outcomes, firm identity, year, rating-provider fields, or post-treatment text enter features"
    pitfalls: ["ESG ratings embedded in training labels can make circular validation", "firm names can proxy sector and style", "future target outcomes can leak into present labels"]
    live_lookup_required: ["current provider label construction", "current train/test split metadata"]

    item: "Firm fixed language style"
    measure: "firm fixed effects, document-template similarity, section fixed effects, auditor/law-firm style, industry-year language norms"
    pitfalls: ["persistent tone can be mistaken for treatment response", "legal counsel changes can create artificial text breaks", "sector vocabulary can proxy climate exposure"]
    live_lookup_required: ["current filing templates and taxonomy tags"]

    item: "Regulator/disclosure regime shifts"
    measure: "mandatory climate-disclosure adoption, taxonomy alignment, assurance mandates, enforcement actions, filing taxonomy changes"
    pitfalls: ["regime shifts change what is said and how it is tagged", "post-mandate comparability may improve mechanically", "pre/post text differences may be compliance, not beliefs"]
    live_lookup_required: ["current SEC, ISSB, ESRS/CSRD, FCA, MAS, HKEX, CSA, and taxonomy requirements"]
```

## Identification debate

```yaml
identification_debate:
  core_threats:
    - "calling all optimistic ESG language greenwashing"
    - "confounding fixed language style with time-varying greenwashing"
    - "black-box ESG classifier scores treated as ground truth"
    - "high classifier accuracy driven by leaked labels rather than construct validity"
    - "attributing mandatory-reporting compliance to voluntary greenwashing"
    - "declaring greenwashing before the commitment horizon has elapsed"
  sorting_vs_siting_or_selection_channel:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  why_method_not_magic:
    - "live_lookup_required: GPT-5.5 Pro did not supply a stable item; keep claim blocked until official lookup"
  gpt55_pro_patch_notes: |
    identification_debate:

    item: "Disclosure-performance gap"
    core_issue: "A causal greenwashing claim needs a mismatch between environmental claims and real environmental outcomes, not text positivity alone."
    acceptable_designs: ["claim-performance panels", "target-delivery follow-up", "matched emissions outcomes", "regulatory enforcement validation"]
    referee_risk: "calling all optimistic ESG language greenwashing"
    live_lookup_required: ["current emissions, target, and enforcement data vintages"]

    item: "Boilerplate and firm style"
    core_issue: "Firms have persistent disclosure style, lawyers, templates, and sector vocabularies that can mimic strategic ESG language."
    acceptable_designs: ["firm fixed effects", "section fixed effects", "similarity-to-prior-filing controls", "law-firm/auditor/template controls"]
    referee_risk: "confounding fixed language style with time-varying greenwashing"
    live_lookup_required: ["current filing taxonomy and template changes"]

    item: "Classifier validity"
    core_issue: "Text classifiers and LLM labels must be validated for the filing type, time period, geography, and construct."
    acceptable_designs: ["hand-coded validation", "temporal holdouts", "cross-provider validation", "calibration curves", "model-version logging"]
    referee_risk: "black-box ESG classifier scores treated as ground truth"
    live_lookup_required: ["current model version and provider methodology"]

    item: "Label leakage and circularity"
    core_issue: "If labels are derived from ESG ratings, future controversies, or emissions variables also used as outcomes, validation can be circular."
    acceptable_designs: ["pre-outcome feature windows", "firm-name masking tests", "provider-independent labels", "strict train/test separation by firm and year"]
    referee_risk: "high classifier accuracy driven by leaked labels rather than construct validity"
    live_lookup_required: ["current provider label construction and training data"]

    item: "Disclosure regime shifts"
    core_issue: "New standards and mandates alter disclosure length, structure, vocabulary, and assurance independent of real performance."
    acceptable_designs: ["jurisdiction-by-year controls", "mandate event studies", "unaffected-section placebo tests", "taxonomy-tag fixed effects"]
    referee_risk: "attributing mandatory-reporting compliance to voluntary greenwashing"
    live_lookup_required: ["current disclosure, taxonomy, and assurance requirements"]

    item: "Outcome timing"
    core_issue: "Text may forecast future investment or transition plans, while emissions respond slowly and with measurement lags."
    acceptable_designs: ["pre-specified horizons", "capex and target-interim outcomes", "lagged emissions panels", "survival of commitments"]
    referee_risk: "declaring greenwashing before the commitment horizon has elapsed"
    live_lookup_required: ["current target databases and reported progress updates"]
```

## Referee entry points

```yaml
referee_entry_points:
  likely_major_objections:
    - "Construct definition"
    - "Is greenwashing defined as claim-performance mismatch rather than ESG vocabulary, sentiment, or disclosure length?"
    - "Performance benchmark"
    - "Are claims compared with emissions, intensity, targets, capex, violations, or audited outcomes using consistent scopes and boundaries?"
    - "Boilerplate control"
    - "Does the design separate repeated generic legal language from new, quantified, accountable commitments?"
    - "Classifier validation"
    - "Are LLM or ML labels validated on human-coded, out-of-time, filing-type-specific samples with model/version metadata?"
    - "Leakage test"
    - "Are firm identifiers, ESG ratings, future outcomes, and provider-derived labels excluded or stress-tested?"
  minimal_empirical_section_checklist:
    - "Construct definition"
    - "Is greenwashing defined as claim-performance mismatch rather than ESG vocabulary, sentiment, or disclosure length?"
    - "Performance benchmark"
    - "Are claims compared with emissions, intensity, targets, capex, violations, or audited outcomes using consistent scopes and boundaries?"
    - "current emissions-provider vintage"
    - "current assurance status"
    - "Boilerplate control"
    - "Does the design separate repeated generic legal language from new, quantified, accountable commitments?"
    - "current filing templates and regulator language"
    - "Classifier validation"
  claims_to_downgrade:
    - "Do not call ESG or climate word frequency greenwashing without a performance benchmark."
    - "Do not treat longer climate disclosure as better environmental performance."
    - "Do not treat LLM or vendor text scores as ground truth without human validation, model/version logging, and leakage checks."
    - "Do not ignore firm fixed language style, legal templates, filing sections, and industry vocabulary."
    - "Do not use future emissions, ESG ratings, controversy labels, or target outcomes as classifier features for present-period greenwashing labels."
    - "Do not interpret mandatory-regime text changes as voluntary disclosure strategy without regime controls."
    - "Do not make current claims about SEC, ISSB, ESRS/CSRD, taxonomy, assurance, enforcement, or provider datasets without live lookup."
  gpt55_pro_patch_notes: |
    referee_entry_points:

    check: "Construct definition"
    ask: "Is greenwashing defined as claim-performance mismatch rather than ESG vocabulary, sentiment, or disclosure length?"
    live_lookup_required: []

    check: "Performance benchmark"
    ask: "Are claims compared with emissions, intensity, targets, capex, violations, or audited outcomes using consistent scopes and boundaries?"
    live_lookup_required: ["current emissions-provider vintage", "current assurance status"]

    check: "Boilerplate control"
    ask: "Does the design separate repeated generic legal language from new, quantified, accountable commitments?"
    live_lookup_required: ["current filing templates and regulator language"]

    check: "Classifier validation"
    ask: "Are LLM or ML labels validated on human-coded, out-of-time, filing-type-specific samples with model/version metadata?"
    live_lookup_required: ["current LLM/model version", "current classifier methodology"]

    check: "Leakage test"
    ask: "Are firm identifiers, ESG ratings, future outcomes, and provider-derived labels excluded or stress-tested?"
    live_lookup_required: ["current provider label construction"]

    check: "Fixed style and regime shifts"
    ask: "Are firm fixed language style, sector vocabulary, document section, filing regime, and mandate timing explicitly handled?"
    live_lookup_required: ["current disclosure regime and taxonomy status"]

    check: "Causal language"
    ask: "Does the paper avoid causal claims unless disclosure shocks, enforcement shocks, or credible quasi-experimental variation are used?"
    live_lookup_required: ["current regulator enforcement data"]
```

## Forbidden claims

- Do not call ESG or climate word frequency greenwashing without a performance benchmark.
- Do not treat longer climate disclosure as better environmental performance.
- Do not treat LLM or vendor text scores as ground truth without human validation, model/version logging, and leakage checks.
- Do not ignore firm fixed language style, legal templates, filing sections, and industry vocabulary.
- Do not use future emissions, ESG ratings, controversy labels, or target outcomes as classifier features for present-period greenwashing labels.
- Do not interpret mandatory-regime text changes as voluntary disclosure strategy without regime controls.
- Do not make current claims about SEC, ISSB, ESRS/CSRD, taxonomy, assurance, enforcement, or provider datasets without live lookup.

## Domain reasoning steps

1. Classify the requested claim before choosing a text pipeline: topic-incidence measurement, disclosure-quality measurement, manual-review risk flag, association with financial outcomes, event-study input, candidate causal design, compliance/legal claim, fraud claim, or assurance claim. This skill supports the first four only as research variables or design inputs. Legal, fraud, intent, definitive greenwashing, compliance, and assurance conclusions are blocked.

2. Define the estimand before extraction. For text-only work, specify whether the estimand is a firm-document-year topic indicator, a topic-dimension score, a document-level disclosure-quality score, a firm-year disclosure index, or a manual-review risk flag. For financing-cost or market-response work, specify separately that the text score is the treatment/exposure/covariate and that the financing or market variable is the outcome.

3. Do not mix the measurement estimand with the econometric estimand. A disclosure-quality score measures text content. A financing-cost regression estimates a conditional association, event response, or candidate causal effect only after the design names outcome, timing, comparison set, identifying variation, controls, and diagnostics.

4. Record document metadata before coding: issuer, issuer identifier such as CIK, LEI, ISIN, or internal ID, document type, source path or URL, publication date, fiscal/report year, jurisdiction, language, filing status, report version, page map, and whether the disclosure environment is mandatory, voluntary, transition-plan specific, annual-report based, sustainability-report based, or filing based.

5. Treat document availability as data, not as zero disclosure. Missing reports, unavailable PDFs, changed URLs, late publication, non-English reports, restated reports, and multiple reports for the same firm-year must be coded separately from absence of a topic within an observed document.

6. Separate topic detection from disclosure quality. A topic mention is not evidence of quantified, bounded, comparable, decision-useful disclosure. Quality dimensions must be pre-specified before scoring: quantified metric, Scope boundary, baseline year, target year, target coverage, time horizon, transition-plan link, capex/opex link, governance owner, scenario analysis, historical consistency, external assurance, and reconciliation with prior disclosures.

7. Use a span-level measurement model. Each topic flag, quality dimension, and review-risk indicator must trace to page, section, chunk ID, short evidence span, extraction confidence, and document metadata. The document-level score must state the aggregation rule from spans to topic-dimension scores and from topic-dimension scores to document-year or firm-year variables.

8. Reject keyword-only scores as main evidence. Require context windows, negation handling, boilerplate detection, duplicate-span handling, table/OCR handling, multilingual or translation treatment, and manual-review samples. Keyword counts can be exploratory features only.

9. Define greenwashing-related outputs only as disclosure-risk indicators or manual-review prompts. They cannot establish deception, fraud, illegality, intent, regulatory non-compliance, or assurance failure from text alone.

10. For financing-cost, valuation, or market-response research, name the econometric design separately: cross-sectional association, panel association, event study, difference-in-differences, instrumental variable, or other candidate design. State the design risks: credit risk, firm size, industry-year shocks, regulatory exposure, rating, leverage, liquidity, analyst coverage, voluntary disclosure selection, reverse causality, and timing between report release and financing outcome.

11. Use the research-design decision tree:
    - If documents and metadata are available, construct span-based measurement variables.
    - If spans are missing or extraction is unreliable, downgrade to corpus-coverage or extraction-quality notes.
    - If the user wants a disclosure-quality score, require a pre-specified rubric and manual-review validation.
    - If the user wants a financing-cost association, treat the text score as exposure and require financial outcome timing, controls, fixed effects, and sample-definition diagnostics.
    - If the user wants causal language, require exogenous timing or rule variation, pre-trends or placebo diagnostics where relevant, and a separate causal-design handoff.
    - If the user wants fraud, illegality, intent, or definitive greenwashing labels, block and downgrade to manual-review risk indicators.

12. Name concrete data-construction risks: issuer matching errors, duplicate reports, multiple document types per firm-year, fiscal-year versus publication-date mismatch, report restatements, PDF extraction failure, OCR errors, table loss, page-number drift, boilerplate repetition, translation error, missing report selection, survivorship bias, jurisdiction mismatch, document-length bias, regulatory changes, and changed disclosure templates.

13. Name diagnostics that block claims: missing evidence spans, missing document metadata, unknown report period, unknown jurisdiction, OCR or extraction failure above threshold, unvalidated classifier, poor inter-coder agreement, missing manual-review protocol, keyword-only score, unexplained aggregation weights, document-type mixing without controls, missing financial-outcome timing, absent `claim_gate.json`, or request for legal/fraud/compliance language.

14. Rank robustness checks by risks most likely to overturn the result: manual label validity and inter-coder agreement; report availability and missing-document selection; issuer-year matching and document timing; boilerplate and document-length adjustment; alternative quality rubric and aggregation weights; document-type restrictions; jurisdiction or regulatory-context splits; industry-year and rating/credit-risk controls; placebo topics or placebo dates; and alternative financing-cost measures.

15. Anticipate referee objections in domain language: disclosure quality may proxy for firm size, resources, governance, rating, analyst coverage, or regulatory exposure; voluntary reporters are selected; boilerplate can inflate topic counts; manual labels are subjective; financing-cost regressions may be confounded by credit risk and liquidity; and report publication may occur after the relevant financing decision.

16. Use downgrade language aggressively. Downgrade to topic incidence, disclosure-quality measurement, corpus-coverage analysis, manual-review risk flag, or association-only whenever spans, metadata, validation, timing, controls, or claim gate are insufficient.

## Candidate outputs

- `esg_disclosure_analysis` YAML or JSON plan.
- Evidence-span extraction requirements.
- Disclosure-quality and risk-indicator variables.
- Safe language for manual-review risk.

## Output schema

Return YAML by default, or JSON if requested. Include at least:

```yaml
skill_name: esg_disclosure_text
user_question_summary: string
research_domain: esg_disclosure_text
research_brief:
  unit: null
  time_frequency: null
  outcome_candidates: []
  treatment_or_exposure: null
  estimand_candidates: []
  identification_risks: []
esg_disclosure_analysis:
  document_type: unknown | annual_report | sustainability_report | climate_report | filing | mixed
  disclosure_topics: []
  evidence_spans_required: true
  quality_dimensions:
    quantified_metrics: unknown | true | false
    scope_boundary: unknown | true | false
    baseline_year: unknown | true | false
    target_year: unknown | true | false
    third_party_assurance: unknown | true | false
  greenwashing_risk_indicators: []
  allowed_claim_level: disclosure_quality_indicator
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

- Text indicators flag disclosure quality or review risk; they do not prove deception, fraud, illegality, or intent.
- Evidence spans are required.
- Report type and regulatory context affect interpretation.
- Current disclosure standards and filing rules require official/latest lookup.

## Forbidden claims

- Do not call a firm fraudulent, illegal, intentionally misleading, or definitively greenwashing.
- Do not treat vague language as proof of misconduct.
- Do not use keyword counts alone as disclosure quality.
- Do not claim compliance with current standards without official/latest source checks, artifacts, and claim gate.

## Handoff to code

Draft a text-analysis spec with metadata, extraction source, span requirements, label definitions, scoring rules, manual-review fields, and output table schema. Ask code to preserve source spans and provenance. Do not output raw Stata or R commands.

## Handoff from code artifacts

Read extraction manifests, span tables, `status.json`, `manifest.json`, `artifact_manifest.json`, `reviewer_risk.json`, and `claim_gate.json` if present. Missing spans block strong text claims. Missing claim gate means claim readiness is not established.

## Minimal examples

### Example 1: Disclosure-quality score for financing-cost research

#### Input

User: Score whether sustainability reports contain credible climate targets or vague promises, then use the score in a financing-cost regression.

#### Expected skill output

```yaml
skill_name: esg_disclosure_text
user_question_summary: "Construct an evidence-span-based climate disclosure quality score for financing-cost research."
research_domain: esg
research_brief:
  unit: firm_document
  time_frequency: report_year
  outcome_candidates: [cost_of_debt, loan_spread, bond_yield_spread, implied_cost_of_equity]
  treatment_or_exposure: span_based_climate_disclosure_quality_score
  estimand_candidates: [document_level_measurement_variable, conditional_financing_cost_association]
  identification_risks:
    - firm_size_and_reporting_resources
    - credit_risk_and_rating_confounding
    - industry_year_shocks
    - regulatory_exposure_selection
    - voluntary_disclosure_selection
    - reverse_causality_from_financing_conditions_to_disclosure
    - report_publication_timing_relative_to_financing_outcome
esg_disclosure_analysis:
  document_type: sustainability_report
  disclosure_topics: [emissions, targets, transition_plan]
  evidence_spans_required: true
  quality_dimensions:
    quantified_metrics: unknown
    scope_boundary: unknown
    baseline_year: unknown
    target_year: unknown
    third_party_assurance: unknown
  greenwashing_risk_indicators: [vague_claim, metric_missing, scope_missing]
  allowed_claim_level: disclosure_quality_indicator
  forbidden_claims: [do_not_call_fraud_or_illegal]
scholarly_depth:
  estimand_definition: >
    First-stage estimand: a firm-document-year climate disclosure quality score
    constructed from evidence spans, topic labels, and pre-specified quality
    dimensions. Second-stage econometric estimand, if financing data are used:
    the conditional association between lagged or event-timed disclosure quality
    and financing cost. The text score is the exposure or explanatory variable;
    financing cost is the outcome. Neither stage supports fraud, intent,
    legal greenwashing, compliance, assurance, or causal language without a
    separate design and claim gate.
  identification_assumptions:
    - "For the text score, these are measurement-validity assumptions: spans are correctly extracted, coded, and aggregated."
    - "For the financing-cost association, disclosure quality is compared among firms with similar credit risk, size, industry-year conditions, regulatory exposure, liquidity, and financing timing."
    - "A causal effect claim additionally requires exogenous disclosure variation or a separate quasi-experimental design; ordinary panel controls are not sufficient."
    - "The report publication date must precede the financing-cost outcome window when interpreting disclosure as an exposure."
  measurement_model:
    - "span_level_label = topic, quality_dimension, evidence_text, page, section, chunk_id, confidence, document_metadata"
    - "topic_dimension_score = rubric-weighted aggregation of validated spans within a topic and document"
    - "document_quality_score = pre-specified aggregation across quantified metrics, Scope boundary, baseline year, target year, transition-plan link, governance, assurance, and historical consistency"
    - "firm_year_score = rule-based aggregation across multiple documents, preserving document type and publication date"
    - "keyword counts are exploratory features only and cannot substitute for span-based coding"
  data_construction_risks:
    - "missing sustainability reports are confused with zero disclosure"
    - "issuer identifiers are mismatched across reports and financing data"
    - "publication date, fiscal year, and financing-outcome window are misaligned"
    - "annual reports, filings, sustainability reports, and climate reports are pooled without document-type controls"
    - "PDF extraction, OCR, tables, or page maps lose relevant evidence"
    - "boilerplate or repeated text inflates topic counts"
    - "jurisdiction or mandatory-disclosure context changes the meaning of disclosure quality"
    - "non-English or translated reports are coded inconsistently"
  method_decision_tree:
    - "If documents, metadata, and evidence spans are available, construct a disclosure-quality measurement variable."
    - "If only keyword hits are available, downgrade to exploratory topic-incidence evidence."
    - "If using financing-cost outcomes, define outcome timing, lag structure, controls, fixed effects, and sample restrictions before regression."
    - "If the claim is association, report association-only language and avoid causal wording."
    - "If the claim is causal, require an external shock, rule change, event design, or other identifying variation plus diagnostics."
    - "If the claim is fraud, illegality, intent, compliance, or definitive greenwashing, block and downgrade to manual-review risk indicators."
  diagnostics_that_block_claims:
    - "missing evidence spans"
    - "missing document metadata or publication date"
    - "unknown jurisdiction or report period"
    - "keyword-only score"
    - "unvalidated classifier"
    - "poor inter-coder agreement or no manual-review sample"
    - "unexplained score weights"
    - "document-type mixing without controls"
    - "financing outcome measured before disclosure publication"
    - "absent claim_gate.json for strong claims"
  robustness_ranked_by_risk:
    - "manual-review validation and inter-coder agreement"
    - "report-availability and missing-document selection checks"
    - "issuer-year matching and publication-timing checks"
    - "alternative quality rubrics and aggregation weights"
    - "boilerplate and document-length adjustments"
    - "document-type restrictions such as sustainability reports only versus filings only"
    - "industry-year, jurisdiction-year, rating, leverage, liquidity, and size controls"
    - "alternative financing-cost measures and outcome windows"
    - "placebo topics or placebo publication dates"
  referee_objections:
    - "The score may proxy for firm size, reporting resources, governance quality, or analyst coverage."
    - "Financing cost may be driven by credit risk, rating, leverage, liquidity, or industry shocks rather than disclosure."
    - "Voluntary disclosure creates sample selection."
    - "Boilerplate language may inflate topic incidence without improving decision-useful disclosure."
    - "Manual labels and rubric weights may be subjective."
    - "The financing decision may occur before the relevant report is published."
  downgrade_triggers:
    - "keyword-only evidence"
    - "missing or unverifiable evidence spans"
    - "no manual-review validation"
    - "unknown report period or publication date"
    - "financial outcome timing is inconsistent with disclosure timing"
    - "controls cannot address obvious credit-risk or industry-year confounding"
    - "user requests fraud, intent, legal greenwashing, compliance, or assurance conclusions"
    - "no claim_gate.json for paper-ready, causal, legal, or audit-grade claims"
candidate_workflows: [esg_text_evidence_span_pipeline, disclosure_quality_text_pipeline]
candidate_methods:
  - span_based_text_measurement
  - rubric_based_disclosure_quality_scoring
  - manual_review_validation
  - financing_cost_panel_association_design
required_diagnostics:
  - evidence_span_audit
  - document_metadata_check
  - issuer_year_match_check
  - publication_timing_check
  - classifier_or_coder_validation
  - inter_coder_agreement_or_manual_review_sample
recommended_robustness:
  - alternative_quality_rubric
  - alternative_score_weights
  - document_type_restrictions
  - boilerplate_and_length_adjustment
  - industry_year_and_jurisdiction_year_controls
  - rating_leverage_liquidity_size_controls
  - alternative_financing_cost_measures
  - placebo_topics_or_dates
forbidden_claims: [respect_claim_gate]
claim_language:
  allowed:
    - "Span-based disclosure-quality indicator."
    - "Conditional association between disclosure quality and financing cost, subject to stated design limits."
  disallowed:
    - "The firm committed fraud."
    - "The firm legally engaged in greenwashing."
    - "Disclosure quality caused lower financing costs without a separate causal design."
    - "The disclosure complies with current law or standards without official/latest checks, artifacts, and claim gate."
uncertainty_notes: [Verify latest reporting rules at use time.]
next_code_actions: [extract_evidence_spans]
```

### Example 2: Fraud or greenwashing overclaim downgrade

#### Input

User: Use sustainability reports to prove which firms committed greenwashing fraud.

#### Expected skill output

```yaml
skill_name: esg_disclosure_text
user_question_summary: "Downgrade a request for fraud conclusions from ESG disclosure text."
research_domain: esg
research_brief:
  unit: firm_document
  time_frequency: report_year
  outcome_candidates: [manual_review_risk_indicator]
  treatment_or_exposure: ESG_disclosure_text
  estimand_candidates: [review_flag_not_legal_finding]
  identification_risks: [legal_intent_not_observable_from_text, disclosure_context_selection]
esg_disclosure_analysis:
  document_type: mixed
  disclosure_topics: [emissions_claims, targets, transition_plan]
  evidence_spans_required: true
  quality_dimensions:
    quantified_metrics: unknown
    scope_boundary: unknown
    baseline_year: unknown
    target_year: unknown
    third_party_assurance: unknown
  greenwashing_risk_indicators: [vague_claim, missing_metric, inconsistent_target_language]
  allowed_claim_level: manual_review_risk_indicator
  forbidden_claims: [do_not_call_fraud_or_illegal, do_not_infer_intent_from_text]
scholarly_depth:
  estimand_definition: "Manual-review disclosure-risk flag, not a legal or fraud finding."
  identification_assumptions: [none_for_fraud_claim_from_text_alone]
  measurement_model: [evidence_span_flags, manual_review_queue]
  data_construction_risks: [missing_context, boilerplate, translation_or_OCR_error]
  method_decision_tree: [risk_indicator_allowed, legal_or_fraud_claim_blocked]
  diagnostics_that_block_claims: [missing_spans, no_manual_review, no_claim_gate]
  robustness_ranked_by_risk: [manual_review_sample, alternative_rubric, document_type_split]
  referee_objections: [text_indicator_cannot_establish_intent, legal_compliance_requires_external_adjudication]
  downgrade_triggers: [user_requests_fraud_label, keyword_only_evidence, absent_claim_gate]
candidate_workflows: [esg_text_evidence_span_pipeline, manual_review_queue]
candidate_methods: [risk_indicator_coding, evidence_span_audit]
required_diagnostics: [span_presence_check, manual_review_protocol]
recommended_robustness: [alternative_risk_rubric, second_coder_review]
forbidden_claims: [no_fraud_or_legal_conclusion, respect_claim_gate]
claim_language:
  allowed: ["The text contains indicators that warrant manual review."]
  disallowed: ["The firm committed fraud or illegal greenwashing."]
uncertainty_notes: [Legal, compliance, and assurance conclusions require external authority and supporting artifacts.]
next_code_actions: [extract_evidence_spans, create_manual_review_flags]
```

## Completion checklist

- Fixed sections are present.
- YAML or JSON output is required.
- Evidence spans are mandatory.
- Official/latest sources are required for standards and regulations.
- Strong claims route through artifacts and `claim_gate.json`.
