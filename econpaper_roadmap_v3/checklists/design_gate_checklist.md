# Design Gate Checklist

## Shared checks

- [ ] Gate uses declared design from `intake_profile.json` when available.
- [ ] Gate records `declared_by_author`.
- [ ] Gate checks consistency between declared design and artifacts.
- [ ] Gate emits `reviewer_questions`.
- [ ] Gate emits `next_actions`.
- [ ] Gate classifies every language rule into `hard_block`, `flag_and_confirm`, or `style_advice`.
- [ ] Gate marks every rule with `overridable: yes/no`.
- [ ] Gate uses non-overridable hard-block only for fabricated numbers, fabricated citations, or mock-as-real.
- [ ] Gate supports `author_override` for flag-and-confirm claims.

## DID / staggered DID

- [ ] Treatment timing summary present or requested.
- [ ] Staggered adoption detected or declared.
- [ ] Event-study support checked.
- [ ] Modern estimator availability checked.
- [ ] Anticipation window checked.
- [ ] Parallel-trends language classified as flag-and-confirm when diagnostics are weak.

## IV

- [ ] First stage checked.
- [ ] Weak-IV diagnostic checked.
- [ ] Exclusion restriction statement checked.
- [ ] LATE scope checked.
- [ ] Causal language without diagnostics is flag-and-confirm, not hard-block.

## RDD

- [ ] Running variable and cutoff checked.
- [ ] Bandwidth checked.
- [ ] Manipulation test checked.
- [ ] Covariate continuity checked.
- [ ] Global claims classified as flag-and-confirm.

## Finance

- [ ] Event timing or signal formation checked.
- [ ] Look-ahead leakage checked.
- [ ] Factor model availability checked where alpha is claimed.
- [ ] Multiple-testing issue checked.
- [ ] Tradability language classified as flag-and-confirm unless implementation assumptions are present.

## Mechanism / external validity

- [ ] Mechanism proof language classified as flag-and-confirm.
- [ ] Post-treatment proxy risks checked.
- [ ] Sample scope checked before broad generalization.
- [ ] External-validity overclaim is flag-and-confirm with limitations rewrite.
