# 00. v3 Executive Changes

## Verdict

v3 is a product reset, not a patch. v2 correctly built a safety layer, but it over-centered "do not say false things" and under-specified why scholars would keep using the product after the first run. v3 defines econpaper as a system for producing a roughly 70% complete submission-oriented draft package, with safety as infrastructure, content quality as the product, and iteration as the retention mechanism.

## Change 1: two P0 product shapes

v3 has two P0 forms.

### Shape A: claim linter

```bash
econpaper lint draft.tex --run-dir path/to/run --refs refs.bib --out lint_pack
```

The linter checks human-written drafts. It produces an annotated manuscript and an `AUTHOR_REPORT.md` with numeric mismatches, missing citations, unsupported causal language, author-asserted claims, and next actions.

Why it is P0:

- It does not require generated prose to be good.
- It establishes trust quickly.
- The value proposition is easy to explain.
- It uses the same evidence ledger, claim ledger, citation safety, and design gates as generation.

### Shape B: generation pipeline

```bash
econpaper write --run-dir path/to/run --intake intake_profile.json --refs refs.bib --out manuscript_pack
```

The generator creates the draft package. It uses the same ledgers and gates, plus the content-layer modules added in v3.

## Change 2: advisor, not arbiter

v2 treated many disputed methodological statements as blocked. v3 keeps strict safety for fabricated numbers, fabricated citations, and mock outputs, but moves most scholarly judgment to `flag-and-confirm`.

### Non-overridable hard-blocks

- fabricated numeric value inconsistent with ledger; overridable: no;
- fabricated citation key not present in `refs.bib` and not marked `CITE_NEEDED`; overridable: no;
- mock output presented as a real manuscript; overridable: no.

### Author override

For every other downgraded or flagged claim, the author can override with:

```json
{
  "author_asserts": true,
  "author_override": {
    "asserted": true,
    "reason": "The institutional design section explains the quasi-random timing; keep the stronger wording for now.",
    "original_status": "flag_and_confirm"
  }
}
```

The system then writes or preserves the author's language, but records the item in `AUTHOR_REPORT.md` under **Author-asserted claims**.

## Change 3: declare-and-confirm intake replaces design guessing

The author usually knows the design. v3 should not frustrate users by forcing the system to infer what the author can declare in seconds.

New flow:

```text
intake_interview
  -> author declares design, treatment timing, estimand, contribution, and context
  -> design_profiler checks consistency against artifacts
  -> contradictions are reported, not silently converted into unknown-design blocks
```

Only when the author skips intake entirely does the system fall back to conservative inference. In that fallback mode, causal writing is not generated automatically, but the author can still assert claims with traceable override records.

## Change 4: three-tier gates replace oversized forbidden-language lists

Every design gate must classify language into exactly three operational tiers.

```text
hard-block        non-overridable; only fabricated numbers, fabricated citations, or mock-as-real
flag-and-confirm  serious reviewer risk; author can override with reason
style-advice      wording preference; never blocks, never enters blocked report
```

Examples:

- TWFE-only staggered DID causal language: `flag-and-confirm`, not non-overridable hard-block.
- IV causal wording without first-stage diagnostics: `flag-and-confirm`.
- RDD causal wording without manipulation tests: `flag-and-confirm`.
- "This is the first paper to ...": `flag-and-confirm`.
- "effect of" in an OLS paper: `style-advice`, because scholars use this phrase in real titles and abstracts.

## Change 5: AUTHOR_REPORT replaces the log pile

The scholar-facing output should not be a folder of reports that must be interpreted like CI logs.

v3 user-readable reporting is:

```text
AUTHOR_REPORT.md
main.pdf                 # if compile succeeds; otherwise markdown fallback with explanation
```

Machine-readable JSON moves to:

```text
reports/internal/
```

`claim_gate_report.md`, `blocked_claims.md`, `cite_needed_report.md`, and `reviewer_risk_memo.md` become sections inside `AUTHOR_REPORT.md`. The standalone reviewer simulator is removed; reviewer questions are fields emitted by design gates and summarized in the report.

## Change 6: success criteria now include quality

A v3 run is not successful merely because it avoids hallucinations. A P0 release must pass negative safety tests and positive quality tests.

### Safety success criteria

1. Unknown run status does not become success-with-warnings.
2. Unknown method does not become paper-ready automatically.
3. Numeric claims map to ledger cells.
4. Citation keys exist or are marked `CITE_NEEDED`.
5. Mock output is visibly watermarked.
6. Reports are consolidated into `AUTHOR_REPORT.md`.

### Content success criteria

1. Each main Results paragraph contains an economic magnitude interpretation.
2. The LLM never writes raw numeric values; numbers are rendered deterministically from placeholders.
3. Publication tables are generated from structured model tables, not treated as arbitrary copied artifacts.
4. Abstract, introduction, results, and conclusion reference the same main numbers.
5. Hedging density is bounded so safety does not become timid writing.
6. At least five real economics / finance scholars run real projects through the system before release; median generated-text retention must be at least 50%, and median self-reported time saved must be meaningfully positive.

## What stays from v2

The following v2 choices remain correct and must not be weakened:

- fail-closed run status and unknown method handling;
- `CITE_NEEDED` instead of hallucinated references;
- failure-as-memo UX;
- do not start implementation with Introduction;
- manuscript as a view over claim ledger;
- no P0 literature search;
- all fifteen false-confidence fixtures, with v3 tier semantics applied.

## Honest endpoint

The endpoint is not "one click to a publishable paper." The endpoint is:

```text
A 70% draft package + deterministic numbers + publication-grade tables + consolidated author report + claim diff across reruns.
```

That is already a product a serious scholar can value. Pretending the remaining 30% can be solved from a run directory alone would be dishonest.
