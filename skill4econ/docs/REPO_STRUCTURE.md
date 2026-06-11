# Repository structure

`skill4econ` keeps the repository root for human-facing entry points and puts
runtime code under `src/skill4econ`.

## Top-level layout

- `src/skill4econ/`: Python package, wrappers, contracts, diagnostics,
  validation, backend adapters, and package-local configuration.
- `skills/`: agent-facing domain, intake, shared, and reporting skill files.
- `examples/`: runnable mini-panel specs and fixture data used by CLI smoke
  tests.
- `tests/`: unit, contract, adapter, golden, and smoke tests.
- `docs/`: operating notes, backend contracts, known bugs, and roadmaps.
- `integrations/`: larger companion projects that should not be mixed into the
  core package tree.
- `vendor_sources/`: source snapshots for Stata or backend wrappers. The
  directory is intentionally mostly ignored except for its README.

## Integrated companion projects

- `integrations/easypaper-econ-finance/`: EasyPaper fork snapshot adapted for
  economics and finance paper generation. It is kept separate from the core
  econometrics package so review and future syncs are easier.

## Running locally

From this repository root:

```powershell
python -m pip install -e .
python -m skill4econ.cli list
python -m skill4econ.cli smoke --suite backend-contract --strict
```

The older workspace-relative spec style such as
`skill4econ/examples/mini_panel/panel_spec.yml` is still accepted. From the repo
root, prefer `examples/mini_panel/panel_spec.yml`.
