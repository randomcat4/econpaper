# Spatial Exposure DID

Use this note when an agent runs `spatial_exposure_did`.

## Command

```powershell
conda run -n base python -m skill4econ.cli run --engine python --method spatial_exposure_did --spec SPEC --run
```

## Required Spec

- `data`: CSV/XLSX panel input.
- `weights`, `weight_matrix`, or `w_path`: edge-list CSV with `source`,
  `target`, and optional `weight`.
- `id`: panel unit column.
- `time`: time column.
- `y`: outcome column.
- `treat`: active treatment column. If `post` is supplied, the default local
  treatment and exposure source is `treat*post`; set
  `exposure_uses_raw_treat: true` to use raw `treat`.

Useful optional fields:

- `x` or `covars`: additional controls in the TWFE model.
- `cluster`: cluster column; defaults to `id`.
- `row_standardize`: row-standardize W before constructing exposure; defaults
  to true.
- `distance_rings_km`: boundaries for ring exposure, e.g. `[100, 300]`.
- `near_exposure_threshold` or `buffer_threshold`: threshold for near/far
  controls and buffer-zone deletion.
- `event_window`: event-study window, e.g. `[-3, 3]`.
- `gvar`: first treatment time column for local treatment event-study.

## Core Artifacts

- `spatial_exposure_panel.csv`: panel with `_local_treatment`,
  `_spatial_exposure`, lagged exposure, cumulative exposure, ring exposure
  columns when requested, near/far control indicators, and buffer flags.
- `spatial_exposure_panel_buffered.csv`: same panel after dropping exposed
  controls from the clean-control sample.
- `tables/spatial_exposure_summary.csv`: year-level exposure and contaminated
  control summary.
- `figures/spatial_exposure_distribution.png`: exposure histogram.
- `tables/contaminated_controls.csv`: control observations with exposure above
  the near/buffer threshold.
- `tables/spatial_exposure_twfe.csv`: local treatment and W*treatment exposure
  TWFE coefficients.
- `tables/local_effect.csv`: local treatment coefficient only.
- `tables/spillover_effect.csv`: spillover/exposure coefficient only.
- `tables/spatial_exposure_event_study.csv`: dynamic local and exposure terms
  when the requested event design is estimable.
- `tables/spatial_exposure_event_support.csv`: support counts for event terms.
- `did_common_output.json`: DID common-schema bridge for the local treatment
  coefficient only. It does not include the W*treatment exposure coefficient.

## Reviewer Risks

- `CONTROL_GROUP_CONTAMINATED`: control observations have nonzero spatial
  exposure. Report near/far definitions and consider buffer-zone deletion.
- `EXPOSURE_CONTROL_DEFINITION_WEAK`: no explicit threshold/ring/buffer rule
  was provided, or event-study exposure terms are not estimable.
- `SPATIAL_SE_NOT_USED`: ordinary clustered/HC covariance is being used for the
  exposure DID; run `spatial_se_comparison` before claiming spatially robust
  inference.
- `INDIRECT_EFFECT_WITHOUT_IMPACT_DECOMPOSITION`: the W*treatment coefficient
  has no direct/indirect/total impact decomposition.

## Claim Limits

`spatial_exposure_did` is a reduced-form exposure DID. It separates the local
treatment coefficient from the W*treatment exposure coefficient, but it is not
a SAR/SDM/SAC model and does not provide direct/indirect/total impact
decomposition. Do not report the exposure coefficient as a structural indirect
effect. The `did_common_output.json` file is a common-schema convenience for
local treatment comparison only; it is not a Callaway-Sant'Anna/BJS modern DID
estimate.
