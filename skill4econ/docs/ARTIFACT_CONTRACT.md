# Artifact Contract

Every `run` and `workflow` must leave a machine-checkable run directory.

## Required Files

```text
manifest.json
audit.json
reviewer_risk.json
artifact_manifest.json
run_config_resolved.yaml
run_config_resolved.json
run_log.md
run_log.txt
status.json
model_table.csv
```

Methods that do not produce coefficient estimates must still write a minimal `model_table.csv` explaining that the run is diagnostic or adapter-only.

## Status

`status.json.status` uses this normalized enum:

```text
success
success_with_warnings
partial_success
skipped
failed
```

`manifest.json.status` may retain legacy method statuses such as `ok`, `degraded`, `not_paper_ready`, `missing_dependency`, or `interface_only`.

## Claim Level

```text
main_estimate
diagnostic
sensitivity_only
adapter_only
exploratory_only
failed
skipped
```

Reduced-form spatial exposure, W sensitivity, and spatial SE comparison must not be labeled structural main estimates. Dependency-gated adapters must remain `adapter_only` unless a real backend has run successfully.

## Paper Readiness

```text
paper_ready
supplementary_only
exploratory_only
not_for_claim
not_available
```

`paper_ready` is forbidden when dependencies are missing, claim-degrading risk codes are present, or the run is adapter-only/sensitivity-only/failed/skipped.

## Reviewer Risk

Each risk item includes:

```json
{
  "code": "SPATIAL_SE_NOT_USED",
  "severity": "medium",
  "scope": "spatial",
  "message": "...",
  "claim_degradation": "supplementary_only"
}
```

All risk codes must be registered through `contracts/risk_registry.py`.

## Validator

```powershell
conda run -n base python -m skill4econ.cli validate-run --run-dir RUN_DIR
conda run -n base python -m skill4econ.cli validate-run --run-dir RUN_DIR --strict
```

The validator checks required files, JSON parseability, registered risk codes, status/risk consistency, artifact existence, rerun command presence, child workflow run contracts, and `model_table.csv` source paths. It writes `validation_report.json` into the run directory.

## Downstream EasyPaper Export

EasyPaper consumes run artifacts through the `export/adapter` bundle boundary.
Do not hand EasyPaper ad hoc tables or prose claims that bypass
`artifact_manifest.json`, `status.json`, `manifest.json`, `reviewer_risk.json`,
`audit.json`, `model_table.csv`, and the validated source paths those files
declare. When `validation_report.json` is present, the export bundle must carry
it as the downstream contract check.

`failed`, `missing_dependency`, `interface_only`, and parser-only/backend
parser statuses are handoff risks, not empirical claims. The export adapter may
preserve them so EasyPaper can show blocked evidence, missing backends, parser
coverage, or revision requirements, but it must not promote them to
`paper_ready`, `main_estimate`, or claimable status.

Finance tier-1 gaps remain adapter specs unless backed by validated artifacts
from a real run. For example, green-finance templates, count-outcome finance
models, ML finance audits, PPML/LightGBM-style methods, or backend-dependent
finance wrappers are specifications until their run directories validate under
this contract.
