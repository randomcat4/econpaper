# Codex Runbook

This runbook is the repo-local execution entry for `skill4econ`.

## Official Entrypoints

```powershell
conda run -n base python -m skill4econ.cli list
conda run -n base python -m skill4econ.cli run --engine python --method METHOD --spec SPEC --run
conda run -n base python -m skill4econ.cli workflow --name WORKFLOW --spec SPEC --run
conda run -n base python -m skill4econ.cli validate-run --run-dir RUN_DIR --strict
conda run -n base python -m skill4econ.cli smoke --suite all --strict
```

`make` may remain as a convenience wrapper, but it is not a required validation path on Windows.

## Baseline From The Last Audit

- Spatial pytest equivalent: `15 passed`.
- Full smoke pytest equivalent: `32 passed`.
- Full CLI smoke runner: `{"status":"ok","checks":43}`.

Reconfirm these before claiming a major phase is complete.

## Per-Turn Checklist

- Read `TODO.md` for the current phase.
- Read `docs/KNOWN_BUGS.md` before changing claim language.
- Use `rg` to locate existing wrappers/contracts before adding new modules.
- Do not weaken fixture assertions or silently fall back to a different estimator.
- Every new run artifact must be reachable from `artifact_manifest.json`.
- Every new risk code must be registered in `contracts/risk_registry.py`.

## Preferred Smoke Commands

```powershell
conda run -n base python -m skill4econ.cli smoke --suite contracts --strict
conda run -n base python -m skill4econ.cli smoke --suite backend-contract --strict
conda run -n base python -m skill4econ.cli smoke --suite did --strict
conda run -n base python -m skill4econ.cli smoke --suite psm --strict
conda run -n base python -m skill4econ.cli smoke --suite spatial --strict
conda run -n base python -m skill4econ.cli smoke --suite all --strict
```

Smoke reports are written to `artifacts/smoke/latest_smoke_report.json`.
