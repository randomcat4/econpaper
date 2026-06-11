# 04. Design-Specific Claim Gates

## Why generic claim gates are insufficient

A generic rule like "a claim needs a table reference" is not enough for economics and finance. Different designs fail in different ways. v3 keeps design-aware gates but changes their product role: gates advise, classify, and explain. They do not pretend to be the final referee.

## Shared three-tier gate contract

Every design gate outputs:

```json
{
  "design_type": "staggered_did",
  "declared_by_author": true,
  "paper_ready": false,
  "claim_levels": {
    "causal_language": {
      "tier": "flag_and_confirm",
      "overridable": true,
      "reason": "Declared staggered DID, but no modern staggered estimator is present.",
      "suggested_rewrite": "The estimates are consistent with a decline under the maintained DID assumptions, but modern staggered-DID estimates are still needed.",
      "reviewer_questions": ["How do results change under Callaway-Sant'Anna or Sun-Abraham?"],
      "next_actions": ["Run a modern staggered DID estimator."]
    }
  },
  "hard_blocks": [],
  "flags": [],
  "style_advice": [],
  "author_override": {
    "allowed": true,
    "field": "author_override"
  }
}
```

## Global tier definitions

### Hard-block

Non-overridable. The only hard-block classes are:

1. fabricated numeric value inconsistent with the evidence ledger; overridable: no;
2. fabricated citation key absent from `refs.bib` and not represented as `CITE_NEEDED`; overridable: no;
3. mock output masquerading as a real manuscript; overridable: no.

No design-specific identification dispute belongs in this tier.

### Flag-and-confirm

Overridable: yes.

This tier covers real reviewer risks. The system should not write the stronger language by default, but the author can keep or request it with `author_asserts: true` and a reason. The claim is then listed in `AUTHOR_REPORT.md`.

### Style-advice

Overridable: yes by ignoring advice.

This tier covers taste, tone, and field convention. Style advice never blocks generation and does not enter the hard-block section.

## Gate: OLS / Cross-sectional regression

### Must check

- outcome definition;
- treatment / exposure definition;
- controls;
- sample;
- robust or clustered standard errors;
- omitted-variable risk;
- reverse causality risk;
- variable scaling and magnitude context.

### Language rules

#### Hard-block, overridable: no

- Numeric coefficient, standard error, p-value, N, or percentage inconsistent with ledger.
- Citekey not present in `refs.bib`.
- Mock OLS output represented as a real table.

#### Flag-and-confirm, overridable: yes

- "causes" or "causal effect" from OLS without a declared causal design or credible quasi-experimental source.
- "identifies" without a design-based identification argument.
- "exogenous variation" without author-provided institutional or design support.
- Strong external-validity claims beyond the sample.

#### Style-advice, overridable: yes

- "effect of" in title or prose. The system may suggest "association" if appropriate, but must not block the phrase.
- Generic "significant at the 1% level" prose without economic magnitude.
- Excessive hedging if the claim is already framed as descriptive.

### Reviewer questions

- What omitted variables remain plausible?
- Is the exposure predetermined?
- Are standard errors clustered at the right level?
- Does the magnitude matter economically?

## Gate: Panel fixed effects

### Must check

- unit fixed effects;
- time fixed effects;
- within-unit variation;
- clustering level;
- treatment timing;
- time-varying confounders;
- bad controls;
- sample attrition.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent numbers.
- Missing citekeys.
- Mock-as-real output.

#### Flag-and-confirm, overridable: yes

- "causal effect" without a declared source of quasi-random variation.
- "rules out time-varying confounders" without diagnostics or institutional argument.
- "generalizes" beyond the panel sample.

#### Style-advice, overridable: yes

- "within-unit effect" vs "within-unit association" wording.
- Hedging level around descriptive fixed-effect results.

### Reviewer questions

- Are time-varying shocks correlated with treatment?
- Are controls post-treatment?
- Is clustering consistent with treatment assignment?

## Gate: DID / staggered DID

### Must check

- treatment timing;
- absorbing vs reversible treatment;
- never-treated / not-yet-treated controls;
- cohort support;
- anticipation windows;
- dynamic effects;
- pre-treatment coefficients;
- TWFE role;
- heterogeneous-treatment risk;
- modern estimator availability;
- inference and clustering.

### Required artifacts

- treatment timing summary;
- event-study plot or table;
- pretrend diagnostic;
- comparison group definition;
- modern staggered DID output when adoption is staggered;
- inference specification.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent treatment effects, standard errors, p-values, or event-study coefficients.
- Missing citekeys.
- Mock DID output presented as real.

#### Flag-and-confirm, overridable: yes

- "causal effect" when only TWFE exists for staggered adoption.
- "TWFE identifies the staggered DID effect" when heterogeneous timing exists and no modern estimator supports it.
- "parallel trends is proven."
- "no anticipation" without anticipation-window diagnostics or author-provided institutional timing.
- Strong claims based on pretrend tests with low power.

#### Style-advice, overridable: yes

- Whether to say "under the parallel trends assumption" in every Results sentence or once per subsection.
- Whether to use ATT terminology in abstract-level prose.

### Reviewer questions

- How sensitive are estimates to Callaway-Sant'Anna, Sun-Abraham, did_imputation, or DRDID equivalents?
- Are event-study pretrends informative with enough support?
- Are never-treated and not-yet-treated controls both examined?
- Is treatment timing possibly anticipated?

### Next actions

- run a modern staggered DID estimator;
- add anticipation windows;
- show cohort support;
- report dynamic effects;
- compare never-treated and not-yet-treated controls.

## Gate: IV

### Must check

- instrument definition;
- endogenous variable;
- first stage;
- weak-IV diagnostics;
- reduced form;
- exclusion restriction statement;
- monotonicity / LATE scope;
- overidentification test where relevant;
- clustered inference.

### Required artifacts

- first-stage table;
- second-stage table;
- reduced-form table if possible;
- weak-IV diagnostic;
- instrument narrative.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent IV coefficients or diagnostics.
- Missing citekeys.
- Mock IV output presented as real.

#### Flag-and-confirm, overridable: yes

- "causal effect" without first-stage and weak-IV diagnostics.
- "the instrument is valid" without exclusion-scope caveat.
- "effect for all units" when the design supports only LATE.
- Overidentification comfort language without the relevant test.

#### Style-advice, overridable: yes

- Whether to lead with "compliers" in abstract vs empirical strategy.
- Degree of hedging around exclusion restriction language.

### Reviewer questions

- What is the first-stage strength?
- Why is the exclusion restriction plausible?
- Who are the compliers?
- Are reduced-form effects consistent with the IV story?

## Gate: RDD

### Must check

- running variable;
- cutoff;
- bandwidth;
- kernel / polynomial order;
- manipulation / sorting;
- covariate continuity;
- donut robustness;
- placebo cutoffs;
- local estimand.

### Required artifacts

- RD plot;
- main bandwidth table;
- bandwidth sensitivity;
- manipulation test;
- covariate balance around cutoff.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent local estimates, bandwidths, or sample sizes.
- Missing citekeys.
- Mock RDD output presented as real.

#### Flag-and-confirm, overridable: yes

- "causal effect" without manipulation and covariate-continuity diagnostics.
- Global treatment-effect language away from the cutoff.
- "no sorting" without a manipulation test or institutional support.
- Strong extrapolation beyond the local estimand.

#### Style-advice, overridable: yes

- Whether to repeatedly say "local" in every sentence.
- Whether to place bandwidth details in text or table notes.

### Reviewer questions

- Is the running variable manipulable?
- How stable are results across bandwidths?
- Do covariates jump at the cutoff?
- What population is local to the cutoff?

## Gate: Finance event study

### Must check

- event date source;
- announcement timing;
- leakage window;
- estimation window;
- event window;
- market model / factor model;
- overlapping events;
- cross-sectional dependence;
- clustering;
- multiple testing.

### Required artifacts

- event timeline;
- CAR or BHAR table;
- pre-event leakage check;
- factor-adjusted robustness where relevant;
- sample construction and filters.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent CAR, BHAR, alpha, t-statistic, or event-window numbers.
- Missing citekeys.
- Mock event-study output presented as real.

#### Flag-and-confirm, overridable: yes

- "investors anticipated" without pre-event tests.
- "profitable strategy" without trading-cost and out-of-sample timing assumptions.
- "predicts returns" without formation and holding-period discipline.
- Market-efficiency conclusions without event-time validity checks.
- Look-ahead leakage in signal construction.

#### Style-advice, overridable: yes

- Whether to call estimates "abnormal returns" or "market reactions" in nontechnical sections.
- Whether to put multiple-testing caveats in text or report.

### Reviewer questions

- Are announcement times measured before market reaction windows?
- Are overlapping events handled?
- Are results robust to factor adjustment?
- Is multiple testing addressed?

## Gate: Portfolio sorts / asset pricing

### Must check

- signal formation date;
- return measurement window;
- rebalancing frequency;
- breakpoints;
- value-weight vs equal-weight;
- factor model;
- alpha inference;
- transaction costs and microcap filters for performance claims;
- multiple testing.

### Required artifacts

- portfolio sort table;
- long-short returns;
- factor alpha table;
- factor definitions;
- signal timing and lag discipline.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent returns, alphas, t-statistics, or portfolio counts.
- Missing citekeys.
- Mock portfolio output presented as real.

#### Flag-and-confirm, overridable: yes

- "predicts returns" if signal timing is not lagged.
- "alpha" without a factor model.
- "tradable" without trading-cost and implementation assumptions.
- "mispricing" without ruling out risk-based explanations.

#### Style-advice, overridable: yes

- Whether to put sorting mechanics in text vs table notes.
- Whether to use "spread" or "long-short" terminology.

### Reviewer questions

- Are breakpoints NYSE or full sample?
- Are portfolios value-weighted or equal-weighted?
- Are microcaps driving results?
- Are alphas robust across factor models?

## Gate: Fama-MacBeth

### Must check

- per-period cross-sectional regression setup;
- lagged predictors;
- time-series inference;
- Newey-West or other autocorrelation correction;
- factor and control set;
- cross-sectional sample filters;
- multiple testing.

### Required artifacts

- per-period coefficient aggregation;
- average coefficients and t-statistics;
- predictor construction audit;
- inference settings.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent average coefficients or t-statistics.
- Missing citekeys.
- Mock Fama-MacBeth output presented as real.

#### Flag-and-confirm, overridable: yes

- "priced risk factor" without factor model or cross-sectional pricing interpretation.
- "predicts returns" without lagged predictors.
- "robustly priced" without multiple-testing and inference checks.

#### Style-advice, overridable: yes

- Whether to describe coefficients as average slopes or premia.
- How much methodology to repeat outside the table notes.

### Reviewer questions

- Are predictors known at the time of return measurement?
- Is inference corrected for time-series dependence?
- Are results concentrated in one subperiod?

## Gate: Mechanism

Mechanism is not a design by itself. It is a claim type layered over a design.

### Must check

- mechanism proxy;
- timing relative to treatment;
- alternative channels;
- whether mechanism result is separately identified;
- whether mechanism is exploratory;
- whether the main design supports mechanism interpretation.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent mechanism estimates.
- Missing citekeys.
- Mock mechanism output presented as real.

#### Flag-and-confirm, overridable: yes

- "proves the channel."
- "confirms the mechanism."
- Mediation language without a mediation design.
- Mechanism claims using post-treatment bad controls without a clear interpretation.

#### Style-advice, overridable: yes

- "consistent with" vs "suggestive of" wording.
- Whether to put mechanism caveats in the paragraph or section opener.

### Reviewer questions

- Is the mechanism variable itself affected by treatment?
- Are alternative channels ruled out or merely discussed?
- Is the evidence timing-compatible with the proposed mechanism?

## Gate: External validity

External validity is a claim layer, not a standalone design.

### Must check

- sample country / industry / firm / household scope;
- period;
- institutional features;
- treatment scale;
- comparison to target population;
- heterogeneous effects.

### Language rules

#### Hard-block, overridable: no

- Ledger-inconsistent sample size, geography, period, or outcome scope.
- Missing citekeys.
- Mock sample metadata presented as real.

#### Flag-and-confirm, overridable: yes

- "generalizes globally" from a single-country or single-industry sample.
- "applies to all firms / households" when the sample is restricted.
- Broad policy recommendations beyond the institutional context.

#### Style-advice, overridable: yes

- Whether limitations are stated in Results or a separate section.
- Whether external-validity caveats are placed in the abstract.

### Reviewer questions

- What population is actually represented?
- Which institutional features are likely nonportable?
- Do heterogeneity results support broader claims?
