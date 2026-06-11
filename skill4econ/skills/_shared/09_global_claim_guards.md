# Skill: global_claim_guards

## Purpose

Define cross-cutting downgrade rules for common applied-micro overclaims. These guards are shared prompt/rubric rules, not estimators or claim certifiers.

## Guarded claim phrases

- "Failure to reject pre-treatment differences" is not evidence that "parallel trends holds"; it is only a diagnostic result that must be interpreted with power, support, anticipation, and design context.
- "A short-run pass-through coefficient" cannot establish "long-run welfare" without quantity, substitution, entry, exit, revenue-use, leakage, and adjustment-margin evidence.

Pretrend non-rejection claim guard

claim_guard:
what_can_be_claimed:
- "Pre-treatment estimates are statistically imprecise and do not provide strong evidence of differential pre-trends in the reported specification."
- "The event-study graph is visually consistent with parallel pre-treatment paths within the available power and pre-period length."
- "The identifying assumption remains conditional parallel trends, supported but not proven by the pre-period diagnostics."
- "Sensitivity checks reduce, but do not eliminate, concern about differential pre-trends."
what_cannot_be_claimed:
- "Do not claim parallel trends are proven because pre-trend coefficients are statistically insignificant."
- "Do not claim no anticipation solely from non-rejected pre-period coefficients."
- "Do not claim treatment and control units are comparable without balance, support, and institutional checks."
- "Do not claim post-treatment effects are causal if pre-period estimates are noisy, sparse, or directionally similar to post effects."
- "Do not use joint pretrend non-rejection as a substitute for design-based identification."
additional_evidence_required:
- "Report event-study coefficients and confidence intervals, not only a joint F-test."
- "Show minimum detectable pre-trend magnitudes or discuss power."
- "Check covariate balance and common support in treatment timing or exposure."
- "Test robustness to alternative control groups, pre-period windows, trends, and estimators."
- "Inspect anticipation windows, policy announcement dates, and pre-treatment behavioral responses."
- "Use placebo outcomes, placebo treatment dates, or negative controls when credible."
common_referee_objections:
- "Insignificant pre-trends may reflect low power rather than valid parallel trends."
- "Pre-period coefficients have the same sign or slope pattern as the treatment effect."
- "The pre-period is too short to diagnose trends."
- "Treatment timing is selected based on prior outcome trajectories."
- "The joint test hides economically meaningful individual pre-period deviations."
- "Controls are outside support or differ in baseline levels and growth potential."
safe_language_examples:
- "We do not reject equality of pre-treatment trends, but this test is not proof of the identifying assumption."
- "The pre-period estimates are small relative to the post-treatment effects, though confidence intervals leave some room for differential trends."
- "The evidence is consistent with, but cannot establish, conditional parallel trends."
- "We therefore interpret the estimates as causal under the maintained parallel-trends assumption and the reported robustness checks."
downgrade_triggers:
- "Wide confidence intervals around pre-period coefficients."
- "Few pre-treatment periods or few treated clusters."
- "Pre-period coefficients trend toward the post-treatment effect."
- "Significant or economically large lead coefficients."
- "Known policy anticipation, announcement effects, or pre-compliance."
- "Treatment assigned based on prior outcomes, capacity, risk, or enforcement targeting."
- "Results sensitive to adding unit trends, changing donors, or changing pre-period windows."

Pass-through welfare claim guard

claim_guard:
what_can_be_claimed:
- "A short-run pass-through estimate measures how much of a cost, tax, allowance price, tariff, or shock is reflected in observed prices over the studied horizon."
- "Pass-through evidence can inform incidence, but only for the measured market, margin, and time horizon."
- "Observed pass-through is consistent with partial-equilibrium price incidence under stated assumptions."
- "Heterogeneous pass-through can reveal market power, contract structure, adjustment frictions, or demand elasticity differences."
what_cannot_be_claimed:
- "Do not infer long-run welfare from short-run pass-through alone."
- "Do not equate statutory liability with economic incidence."
- "Do not claim consumer, producer, worker, taxpayer, or foreign incidence without measuring relevant margins."
- "Do not claim general-equilibrium welfare effects without output, entry, exit, substitution, revenue use, leakage, and market-adjustment evidence."
- "Do not treat complete pass-through as proof that firms are unharmed or incomplete pass-through as proof that consumers benefit."
- "Do not ignore quality adjustment, product switching, contract renegotiation, or market reallocation."
additional_evidence_required:
- "Estimate quantities, output, market shares, entry, exit, margins, profits, wages, and employment when making incidence claims."
- "Measure substitution across products, firms, regions, suppliers, and trade destinations."
- "Account for tax or permit revenue, free allocation, rebates, transfers, and revenue recycling."
- "Distinguish short-run contractual pass-through from long-run equilibrium pass-through."
- "Check downstream and upstream pass-through, not only the first observed price."
- "Use structural demand/supply, sufficient-statistic welfare formulas, or credible partial-equilibrium bounds for welfare claims."
- "For climate or environmental policy, include leakage, abatement, innovation, compliance costs, and external damages before welfare conclusions."
common_referee_objections:
- "The paper estimates price pass-through but labels it welfare or incidence."
- "The observed price is not the final consumer price."
- "Quantities and market shares are missing, so surplus changes cannot be signed."
- "Revenue recycling, free allocation, or rebates are ignored."
- "The time horizon is too short for entry, exit, investment, innovation, or contract adjustment."
- "General-equilibrium substitution and leakage could reverse the partial-equilibrium interpretation."
- "Pass-through differs across exposed and unexposed groups, but distributional effects are not estimated."
safe_language_examples:
- "These estimates identify short-run price pass-through, not full welfare incidence."
- "The results suggest that part of the policy cost was reflected in prices over the sample horizon."
- "Economic incidence depends on additional quantity, profit, wage, substitution, and revenue-use margins that are outside this estimate."
- "We therefore interpret the pass-through estimates as partial-equilibrium evidence on price adjustment."
- "Long-run welfare effects require stronger assumptions and additional outcomes."
downgrade_triggers:
- "Only prices are measured; quantities, margins, or welfare-relevant outcomes are absent."
- "Contracts, regulation, or price controls delay adjustment."
- "Treatment changes product quality, composition, or reporting units."
- "Markets have entry, exit, trade diversion, leakage, or large cross-market substitution."
- "Free allocation, rebates, transfers, or revenue recycling are material."
- "Short post-treatment window relative to investment or contract cycles."
- "Pass-through is estimated for intermediate goods but claims are about final consumers or aggregate welfare."
