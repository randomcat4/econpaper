# EasyPaper Econ/Finance Fork Baseline

## Upstream

- Upstream repository: https://github.com/PinkGranite/EasyPaper
- Baseline tag: v0.2.4
- Baseline SHA: 8797d4bf9cd8680f4da2d8b322533364d602b82d
- PyPI/local package version: 0.2.4
- Local snapshot path: D:/myproject/EvoScientist/competitor_repos/easypaper-source

## Verification

- `pyproject.toml` declares `name = "easypaper"` and `version = "0.2.4"`.
- `git ls-remote https://github.com/PinkGranite/EasyPaper.git refs/tags/v0.2.4 HEAD` resolves both `HEAD` and `refs/tags/v0.2.4` to `8797d4bf9cd8680f4da2d8b322533364d602b82d`.
- `python -c "import sys; sys.path.insert(0, '.'); import easypaper; print(easypaper.__file__)"` imports the local package from this snapshot.

## Local Snapshot Notes

This directory was present as a local EasyPaper source snapshot before the fork
baseline was established. It includes source-distribution metadata such as
`PKG-INFO`, plus local audit/planning notes named `_AUDIT*.md`. Editable
install/build outputs such as `easypaper.egg-info/` and `__pycache__/` are
ignored so install and import checks do not dirty the fork. The local notes are
kept with the snapshot so later changes are traceable, but the upstream code
baseline remains v0.2.4 at the SHA above.

## Branching Policy

- Fork branch: `evo/econ-finance-tier1`
- Upstream remote name: `upstream`
- Upstream is for manual comparison only. Do not auto-merge floating `master` or
  `main` into this fork.

## Why Not Track Floating Master

The first implementation phase needs deterministic behavior while EasyPaper is
being adapted for economics and finance paper generation. Pinning to v0.2.4
keeps planner, writer, reviewer, and LaTeX assembly changes reviewable against a
stable source tree.

## Current Goal

Turn the EasyPaper pipeline into a local economics/finance paper generation
engine that supports:

- AER/QJE/JFE venue constraints.
- Deterministic economics/finance required sections.
- Metadata fields such as empirical strategy, results, and robustness.
- File-backed empirical figures and tables.
- Local generation of `main.tex` without depending on EvoScientist channels,
  subagent registry, or LangGraph wrappers.
