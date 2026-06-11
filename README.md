# econpaper

`econpaper` is an independent economics and finance paper-generation workspace.
It borrows the EasyPaper skeleton, but it is not maintained as an upstream
EasyPaper fork workflow. Future changes are expected to diverge substantially.

## Layout

- `EasyPaper/`: manuscript generation layer with econ/finance artifact gates,
  strict runner flags, narrative checks, and reviewer attack checks.
- `skill4econ/`: econometrics and finance artifact producer, contracts, docs,
  and the EasyPaper integration snapshot.
- `notes/`: local planning notes and implementation TODOs.

## Current Baseline

EasyPaper source imported from:

- Former remote: `https://github.com/randomcat4/EasyPaper.git`
- Former branch: `evo/econ-finance-tier1`
- Commit: `9d43889cbbdffb05deedc4812d4b8e3afb6f0257`

skill4econ source imported from:

- Former remote: `https://github.com/randomcat4/skill4econ.git`
- Former branch: `main`
- Commit: `a4476f5bc853c0d93fe540f5d3b3da4aa19aa685`

## Design Boundary

EasyPaper must not implement OLS, FE, DID, IV, RDD, DML, spatial, DEA,
Fama-MacBeth, or other estimators. It consumes file-backed `skill4econ`
artifacts, applies claim gates, and generates manuscript/reporting outputs.

Empirical claims are allowed only when upstream `skill4econ` outputs are
claimable, paper-ready, have a main claim available, and have no blocking
reviewer risk.

## Useful Commands

From `EasyPaper/`:

```powershell
python -m pytest tests/test_econ_claim_gates.py tests/test_econ_narrative_bridge.py tests/test_econ_reviewer_attack_pack.py tests/test_artifact_manifest_v1.py tests/test_artifact_path_validation.py tests/test_run_econ_paper_script.py tests/test_econ_output_reports.py tests/test_skill4econ_export_bundle.py -q
python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml --out outputs/final_aer --mock-llm --no-pdf --strict-artifacts --claim-gate-strict
```

From `skill4econ/`:

```powershell
$env:PYTHONPATH='D:\myproject\econpaper\skill4econ\src'
conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict
conda run -n base python -m pytest tests\contracts tests\docs tests\test_skill_docs_contract.py -q
```
