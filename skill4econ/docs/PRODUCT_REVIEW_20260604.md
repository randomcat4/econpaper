# skill4econ Product Review - 2026-06-04

This note preserves the GPT-5.5 Pro product review requested by the user. The
review target was: research faculty in environmental economics, economics,
finance, causal inference, and AI x econometrics.

## Round 1: Product Direction

Verdict: the model layer is already broad enough. The next priority is not more
methods, but trust, reproducibility, paper outputs, reviewer diagnostics, and
low-friction use.

Highest-priority route:

- Freeze model expansion for seven days.
- Upgrade `skill4econ` from an econometric method executor into a paper-grade
  econometric workflow engine.
- Start with `PaperRun DID v0.1` for environmental/applied economics policy
  evaluation panel DID.

Why DID first:

- Target users often work with city-year, firm-year, or province-year policy
  evaluation data.
- Current P0 already includes TWFE DID, event study, reghdfe, csdid/drdid,
  clustering, panel audit, plotting, and Stata/Python backends.
- DID is heavily challenged by reviewers: parallel trends, dynamic effects,
  staggered adoption, heterogeneous treatment effects, clustering, sample
  construction, and treatment timing.
- A solid DID PaperRun can become the product template for IV, RDD, PSM, DEA,
  and DML workflows.

The recommended product shape:

```text
data + research spec
-> preflight / data audit
-> baseline model
-> method-specific diagnostics
-> robustness grid
-> figures + tables
-> human-readable research report
-> replication bundle
```

Core output package:

- `manifest.json`
- `audit.json`
- `dependency_report.json`
- `research_report.md` or HTML
- `model_table.csv`
- paper table in CSV/Markdown/LaTeX/DOCX when available
- `event_study_plot.png`
- `treatment_timing_summary.csv`
- pretrend or balance diagnostics
- warnings
- rerun script
- Stata do/log or Python artifacts

Biggest shortfalls:

- No reviewer-perspective diagnostic layer yet.
- No paper-native outputs yet.
- No low-friction teacher onboarding path yet.

Do not prioritize:

- More long-tail models.
- Interface-only methods that look supported.
- Automatic causal conclusion generation.
- Pretty UI before the run directory is trustworthy.
- Fully automatic model selection.
- Hidden Stata/Python substitution.

One-line product principle:

> Stop proving that `skill4econ` can run models; prove that it can help teachers
> make the econometrics part of a paper credible, inspectable, reproducible, and
> reviewer-challengeable.

## Round 2: DID v0.1 Approval

Verdict: conditional approval.

The direction is right, but the first draft cannot be implemented as-is because
it could package incomplete DID evidence as if it were paper-ready.

Hard conditions:

- `simple_2x2_did` and `staggered_adoption_did` must be explicit
  `design_type` values. The workflow must not guess the research design.
- A staggered adoption DID run that only produces TWFE must not be marked as a
  complete success.
- Workflow status must distinguish `success`, `degraded`, `not_paper_ready`,
  and `failed`.
- Do not generate an empty or placeholder `robustness_summary.csv`.
- Always output sample construction and deletion records.
- Check `id x time` uniqueness as a hard preflight rule.
- Event-study output must report omitted period and support by event time.
- The report must not claim that parallel trends are proven or that causality is
  proven.
- Dependency failure severity must depend on design type and user request.

Pseudo-requirements rejected:

- Empty robustness summaries.
- Over-polished CLI syntax before trustworthy outputs.
- Duplicate `output_intent` fields if `workflow --name did_paper_run` already
  carries the intent.
- Generic diagnostic plots unrelated to the DID paper workflow.
- Complex engine scheduling.

Approved next implementation order:

1. Write this product boundary and a DID v0.1 TODO.
2. Define the DID PaperRun spec schema.
3. Build DID preflight before running models.
4. Compile baseline TWFE and event study into one workflow.
5. Add staggered DID alternative with csdid/drdid and honest degradation.
6. Generate `research_report.md` and machine-readable warnings.
7. Add golden data and boundary tests.
8. Test with real target users.
