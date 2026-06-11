# 06. Quality and False Confidence Tests

These tests are release blockers. v3 keeps the v2 false-confidence fixtures and adds quality tests. The product is not releasable if it is merely safe but produces timid, useless, or non-iterable text.

## Tier semantics for tests

```text
hard-block        fabricated numbers, fabricated citations, mock-as-real only
flag-and-confirm  serious design or reviewer risk; author override allowed
style-advice      wording preference; not a release-blocking claim status by itself
```

When a v2 test used the word "blocked" for an identification dispute, v3 preserves the fixture and expected warning but classifies the claim as `flag_and_confirm` unless it falls into the three hard-block categories.

## Test 1: unknown method cannot become paper-ready

### Fixture

`model_table.json` contains method `my_new_magic_estimator` with a coefficient and p-value.

### Expected

- Design profile status: `unknown_method`.
- Claim status: no automatic verified main result.
- Author may assert the claim, but it becomes `author_asserted` with original status recorded.
- Manuscript must not write a main result as system-verified paper-ready.

## Test 2: unknown run status cannot become success_with_warnings

### Fixture

`status.json` contains `status: weird_completed_state`.

### Expected

- Run validation fails closed.
- Result section is not generated automatically.
- `AUTHOR_REPORT.md` says status is unknown and requires validation.
- Author override, if used, is recorded as author-asserted rather than verified.

## Test 3: table path is not sufficient evidence

### Fixture

A LaTeX table exists, but there is no parsed cell mapping.

### Expected

- Manuscript may reference that a table exists only as an appendix/report artifact.
- No numeric effect sentence is automatically allowed.
- Author can manually assert a table interpretation, recorded as author-asserted.

## Test 4: invented coefficient hard-blocked

### Fixture

Evidence ledger coefficient is `0.03`, draft says `0.30`.

### Expected

- Claim verifier hard-blocks the numeric mismatch.
- Overridable: no.
- `AUTHOR_REPORT.md` includes the mismatch.
- Numeric renderer test explains why this should have been impossible if placeholders were used correctly.

## Test 5: robustness cannot become main result

### Fixture

Robustness table has a stronger estimate than the main table.

### Expected

- Writer cannot lead with robustness as primary result by default.
- Language must say robustness is supportive/sensitivity, not main evidence.
- If the author insists, the claim is `flag_and_confirm` and author-asserted.

## Test 6: mechanism cannot be written as proof

### Fixture

Mechanism artifact is flagged `suggestive_only`.

### Expected

- Default writer avoids "confirms the mechanism" and "proves the channel".
- Allowed default language: "consistent with the mechanism" or "suggestive of".
- Stronger mechanism language is `flag_and_confirm`, not hard-block, unless it contains fabricated numbers or citations.

## Test 7: staggered DID with TWFE-only flagged

### Fixture

Treatment adoption is staggered; only TWFE artifact exists.

### Expected

- Main causal DID claim is `flag_and_confirm`.
- TWFE may be described as a benchmark or preliminary estimate by default.
- Next actions recommend modern staggered DID estimator.
- Author can override with reason; `AUTHOR_REPORT.md` records the assertion.

## Test 8: IV without first stage flagged

### Fixture

Second-stage IV table exists; no first-stage or weak-IV diagnostic.

### Expected

- Causal language is `flag_and_confirm`.
- `AUTHOR_REPORT.md` asks for first stage and weak-IV diagnostics.
- Author override is allowed with reason.

## Test 9: RDD without manipulation test flagged

### Fixture

RDD coefficient exists; no manipulation or covariate-continuity diagnostic.

### Expected

- Causal language is `flag_and_confirm`.
- Local descriptive or assumption-qualified language is allowed.
- Required diagnostics are reported.

## Test 10: finance signal with look-ahead flagged

### Fixture

Signal uses data published after return formation date.

### Expected

- Return predictability or tradable-strategy claim is not written automatically.
- Claim is `flag_and_confirm` with high-severity leakage explanation.
- Author override is allowed, but the report records the leakage concern.

## Test 11: missing bibliography does not create fake citations

### Fixture

No `refs.bib`; writer asked for Introduction and Related Literature.

### Expected

- No fake `\citep{...}`.
- Literature claims replaced with `[CITE_NEEDED]`, `[AUTHOR_INPUT_NEEDED]`, or author-asserted placeholders.

## Test 12: unknown citation key hard-blocks cite command

### Fixture

Manuscript contains `\citep{nonexistent2025}`; `refs.bib` lacks that key.

### Expected

- Citation safety gate hard-blocks the cite command.
- Overridable: no for using the nonexistent cite command.
- The writer may replace it with `[CITE_NEEDED: source for claim]`.

## Test 13: absolute path leakage blocked from public output

### Fixture

Artifact path is `/Users/alice/private/project/data/table1.tex`.

### Expected

- Public manuscript uses relative path.
- Internal path appears only in redacted/internal provenance, not in `main.tex` or `AUTHOR_REPORT.md`.

## Test 14: mock output cannot masquerade as real draft

### Fixture

`--mock-runner` enabled.

### Expected

- All manuscript files contain `SMOKE TEST ONLY -- NOT A PAPER DRAFT`.
- Output status cannot be `paper_ready`.
- Overridable: no.

## Test 15: external validity overclaim flagged

### Fixture

Single-country sample; draft says results generalize globally.

### Expected

- Claim is `flag_and_confirm`, not non-overridable hard-block.
- Limitations section states sample scope.
- Author can override with reason; the report records the original external-validity concern.

## Q1: economic magnitude required in main Results

### Fixture

Main result paragraph says: "The coefficient is 0.03 and statistically significant."

### Expected

- Quality test fails.
- Paragraph is incomplete until it explains units, standard-deviation equivalent, mean-relative change, or another meaningful benchmark.
- If magnitude context is missing, `AUTHOR_REPORT.md` asks for the missing unit / mean / standard deviation.

## Q2: deterministic numeric rendering required

### Fixture

LLM output contains raw numeric prose rather than placeholders.

### Expected

- Quality test fails before publication.
- Prose must be rewritten with placeholders such as `{{coef:claim_main_001}}`.
- Test 4 remains a fallback mismatch detector, not the primary control.

## Q3: hedging density bounded

### Fixture

A Results paragraph contains "may," "suggestive," "consistent with," and "could" in nearly every sentence.

### Expected

- Quality test flags timid writing.
- Writer must consolidate caveats and state safe claims directly.
- Threshold is configurable, but default maximum is two hedge phrases per paragraph unless the section is explicitly limitations or mechanism.

## Q4: global numeric consistency

### Fixture

Abstract says coefficient is `0.03`, Results says `0.04`, and Conclusion says `3 percentage points` for the same claim id.

### Expected

- Coherence pass fails.
- All references to the same claim id must render from the same numeric slot and compatible unit conversions.

## Q5: abstract and body consistency

### Fixture

Abstract claims a mechanism result, but the body contains only main outcome and robustness claims.

### Expected

- Coherence pass flags unsupported abstract content.
- Abstract must be rewritten or the missing body section must be added.

## Q6: override trace completeness

### Fixture

Author overrides a flagged DID causal claim.

### Expected

- Claim ledger contains `author_override.asserted: true`.
- `original_status` is preserved.
- Author reason is non-empty.
- `AUTHOR_REPORT.md` includes the claim under Author-asserted claims.

## Q7: publication table quality

### Fixture

`model_table.json` is valid but generated LaTeX table lacks table notes, sample rows, or inference notes.

### Expected

- Quality test fails.
- Table must include model/sample mapping, inference convention, fixed effects where relevant, star/no-star policy, and provenance note.

## Q8: human evaluation release gate

### Fixture

Pre-release candidate passes automated tests.

### Expected

At least five real economics / finance scholars must run real projects. Release passes only if:

- median generated-text retention is at least 50%;
- at least four of five users report meaningful time saved;
- no user reports that the system silently fabricated a number or citation;
- at least three users say the `AUTHOR_REPORT.md` made next actions clearer than raw logs;
- all feedback is attached to the release notes.
