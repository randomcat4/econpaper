# EasyPaper Econ/Finance Integration

This folder contains the EasyPaper-derived snapshot for generating
economics and finance manuscript drafts.

## What is included

- AER, QJE, and JFE venue configs.
- Economics/finance metadata fields and section taxonomy.
- Deterministic required sections:
  Introduction, Data, Empirical Strategy, Results, Robustness, Conclusion.
- File-backed empirical artifact manifests.
- Guards that forbid autonomous AI generation of empirical result figures.
- `scripts/run_econ_paper.py` for standalone local runs.
- Mock AER/JFE proof-of-concept outputs through tests.

## Important boundary

This integration is intentionally separate from the `skill4econ` core package.
The core package runs econometric methods and produces auditable artifacts. This
The EasyPaper-derived layer consumes paper requests and file-backed artifacts to assemble
manuscript drafts.

## Smoke commands

```powershell
python -m pytest tests/test_run_econ_paper_script.py tests/test_minimal_poc_runner_outputs.py -q
python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml --out outputs/aer_minimal --mock-llm --no-pdf
```
