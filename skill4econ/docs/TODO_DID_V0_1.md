# TODO: DID PaperRun v0.1

Goal: turn existing P0 DID methods into a paper-oriented, reproducible,
reviewer-aware workflow for research faculty. This is not a new estimator.

## Product Boundary

- Workflow name: `did_paper_run`.
- CLI entrypoint:

  ```powershell
  conda run -n base python -m skill4econ.cli workflow --name did_paper_run --spec SPEC --output OUT --run
  ```

- Required design split:
  - `design_type: simple_2x2_did`
  - `design_type: staggered_adoption_did`
- The workflow must not infer the DID design type from a binary treatment
  column.
- Staggered adoption TWFE-only output is not a full PaperRun success.
- Report language must be conservative. Never write:
  - "parallel trends are proven"
  - "passed the parallel trend test"
  - "the policy effect is proven causal"

## Minimum Spec

Required common fields:

- `design_type`
- `data` or `input_path`
- `id`
- `time`
- `y`
- `cluster`, defaulting to `id`
- `x` / `controls`, optional
- `engine_policy: stata_first | stata | python`, default `stata_first`
- `event_window`, default `[-5, 5]`
- `base_period`, default `-1`

Required for `simple_2x2_did`:

- `treat`
- `post`

Required for `staggered_adoption_did`:

- `gvar` or `adoption_time`

## Workflow Status

- `success`: required models and diagnostics ran for the declared design type.
- `degraded`: usable outputs exist, but the selected engine or a requested
  component was substituted or partially unavailable.
- `not_paper_ready`: model output exists, but a core paper-readiness condition
  is missing.
- `failed`: preflight or core estimation blocked the run.

Hard rule: `design_type: staggered_adoption_did` without a successful
csdid/drdid-style alternative is `not_paper_ready`, not `success`.

## Required Artifacts

- `manifest.json`
- `audit.json`
- `dependency_report.json`
- `data_summary.json` and `data_summary.csv`
- `sample_construction.json`
- `treatment_timing_summary.csv`
- `event_study_support.csv`
- `did_diagnostics.json`
- `warnings.json`
- `model_table.csv`
- `event_study_plot.png` when event-study coefficients are available
- `research_report.md`
- `robustness_plan.md`
- `rerun.bat`
- `rerun.sh`
- step-level run directories with Stata do/log or Python artifacts

Do not create `robustness_summary.csv` until real robustness models have run.

## Preflight Checklist

Red conditions:

- Missing `design_type`, `id`, `time`, `y`, or treatment fields.
- `id x time` is not unique.
- Treatment has no variation.
- No pre-treatment period.
- No usable control comparison.
- Event time cannot be constructed.
- A required estimator dependency is unavailable for the declared design.

Yellow conditions:

- Unbalanced panel.
- Few clusters.
- Few treated cohorts.
- No never-treated units.
- Few supported pre-treatment leads.
- Large listwise deletion.
- TWFE used under staggered adoption.
- Python output is used after Stata was requested or preferred.

Green condition:

- The workflow completed diagnostics and recorded all model statuses.
- Green never means the causal design is valid.

## Implementation Tasks

- Add a workflow registry and CLI subcommand.
- Build DID preflight that writes data, sample, treatment timing, event support,
  and warning artifacts before estimation.
- Compile existing `did_twfe_event`, `did_event_study`, and `csdid_staggered`
  method outputs into one run directory.
- Mark every step with actual engine, method, status, and run directory.
- Generate a consolidated `model_table.csv`.
- Generate event-study plot from event coefficients.
- Generate `research_report.md` with explicit limitations.
- Generate rerun scripts with the original spec path and output parent.
- Update smoke tests with at least one workflow run.

## Test Scenarios

- `simple_2x2_did` succeeds with Python-only engine on synthetic panel data.
- Missing `design_type` fails before estimation.
- Duplicate `id x time` fails before estimation and writes duplicate rows.
- Treatment all zero fails before estimation.
- Staggered adoption with `engine_policy: python` is `not_paper_ready`.
- Staggered adoption with Stata csdid/drdid available can become `success`.
- Event support table reports omitted period and supported leads/lags.
- Rerun script points to the original spec and output parent.

## Explicit Non-Goals

- No dynamic spatial Durbin.
- No PSM-DID.
- No SFA integration.
- No DoWhy/CausalML workflow.
- No remote sensing or patent text workflow.
- No LightGBM finance workflow.
- No UI.
- No automatic model selection.
- No automatic causal conclusion generation.
- No hidden engine fallback.
