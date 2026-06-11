# econpaper Roadmap v3

## One-line change from v2

v3 builds on the v2 safety layer, adds a content layer and an iteration layer, and changes the product role from **arbiter** to **advisor**.

v2 asked: "How do we stop the system from saying false things?"

v3 asks: "How do we help a scholar produce a submission-grade draft package while making every risk, override, missing input, and next action explicit?"

Safety is the foundation. It is not the selling point by itself. Scholars will pay for content quality, iteration speed, and trust after revision.

## v3 product definition

The product should produce:

> A roughly 70% complete economics / finance manuscript package plus a precise author task list, not a fully automatic submission-ready paper.

The final 30% is not an engineering bug. Institutional background, research motivation, contribution judgment, and field positioning contain information that is often absent from a run directory. The `intake_interview` reduces this gap, but it cannot eliminate it.

## Three-layer architecture

```text
Safety layer
  - fail-closed run status and unknown method handling
  - evidence ledger and claim ledger
  - citation safety and CITE_NEEDED placeholders
  - design-specific gates

Content layer
  - intake interview
  - economic magnitude interpretation
  - deterministic numeric rendering
  - publication table generation
  - global coherence pass
  - abstract and title writer

Iteration layer
  - incremental rerun
  - claim status diff
  - human-edited region protection
  - LaTeX compile loop with graceful markdown fallback
```

Every module must be clear about which layer it serves. A module that only prevents errors belongs to the safety layer. A module that improves what the paper says belongs to the content layer. A module that protects author work across revisions belongs to the iteration layer.

## Two P0 product shapes

v3 defines two parallel P0 forms. They share the same ledgers and gates, but enter the pipeline differently.

### Shape A: claim linter

```bash
econpaper lint draft.tex \
  --run-dir path/to/skill4econ_run \
  --refs refs.bib \
  --out lint_pack
```

The linter checks a human-written draft. It verifies that every numeric value matches the evidence ledger, every citation key exists, and every causal / mechanism / external-validity phrase is compatible with the design gate or explicitly author-asserted.

This is the best wedge product because it does not depend on generated prose quality. The value proposition is one sentence: "Upload your draft and run directory; econpaper finds unsupported empirical and citation claims before referees do."

### Shape B: generation pipeline

```bash
econpaper write \
  --run-dir path/to/skill4econ_run \
  --intake intake_profile.json \
  --refs refs.bib \
  --venue aea \
  --out manuscript_pack
```

The generator creates a manuscript pack from validated artifacts, an intake profile, a bibliography, and conservative section writers. It should not pretend to be fully automatic. It should produce a strong first draft and a clear author action list.

## Advisor, not arbiter

Except for the three non-overridable hard-block classes, econpaper should advise, flag, downgrade, and explain rather than silently refuse.

The three non-overridable hard-block classes are:

1. fabricated numeric values that disagree with the evidence ledger;
2. fabricated citations where a citekey is absent from `refs.bib` and no `CITE_NEEDED` marker is present;
3. mock output masquerading as a real manuscript.

All other design, identification, contribution, mechanism, and external-validity risks are `flag-and-confirm`. The author may override them by setting `author_asserts: true` with a reason in the claim ledger or by using the CLI override workflow. The final `AUTHOR_REPORT.md` must preserve the system's original judgment and the author's reason.

## Literature policy

v3 keeps the v2 decision: do not build literature search, citation graph discovery, PDF crawling, or literature RAG in P0.

P0 does citation safety. P1/P2 can integrate Zotero, Better BibTeX, OpenAlex, Crossref, Semantic Scholar, NBER metadata, RePEc, PaperQA-style PDF workflows, or other tools through structured notes. External prose is not accepted directly into the manuscript.

## Input scope honesty

P0 supports native structured `skill4econ` output. External Stata / R / Python outputs and manually supplied regression tables are an important P1+ track, not a hidden P0 assumption. Parsing arbitrary LaTeX or text regression tables into cell-level evidence is a research-sized problem, and this track directly affects the size of the addressable user base.

## Package contents

- `00_v3_executive_changes.md` — v2 to v3 changes and positioning corrections.
- `01_product_architecture.md` — three-layer product architecture and object model.
- `02_p0_body_writing_chain.md` — P0 module contracts for safety, content, and iteration.
- `03_citation_safety_not_search.md` — citation policy and external literature notes contract.
- `04_design_specific_claim_gates.md` — three-tier language gates by design.
- `05_todo_rewrite.md` — rewritten P0 / P1 / P2 TODO plan.
- `06_quality_and_false_confidence_tests.md` — release-blocking safety and quality tests.
- `07_user_experience_pack.md` — scholar-facing UX, CLI, output pack, and reporting.
- `08_implementation_order.md` — recommended build order and first PR sequence.
- `schemas/` — draft JSON schemas.
- `examples/` — minimal example ledgers and intake profile.
- `checklists/` — release and lint-mode checklists.
- `DELIVERY_SELF_CHECK.md` — v3 package compliance self-check.

## Most important P0 rule

The manuscript is a view over the claim ledger, not free prose cleaned up after the fact. LLMs may propose wording, but numeric values, citations, design permissions, and author overrides must come from structured objects.
