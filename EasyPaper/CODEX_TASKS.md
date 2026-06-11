# Codex Tasks for the Econ/Finance Fork

## Common Commands

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
python -m pytest -m "not live_llm and not latex and not slow" -q
python -m pytest tests/test_planner_required_sections.py -q
python -m pytest tests/test_econ_section_generation_content_brief.py -q
python -m pytest tests/test_artifact_manifest_v1.py -q
python -m pytest tests/test_easypaper_app_config_builder.py tests/test_run_econ_paper_script.py -q
```

## Core Econ Invariant Suite

```powershell
python -m pytest `
  tests/test_document_input_econ_constraints.py `
  tests/test_orchestrator_passes_econ_constraints.py `
  tests/test_planner_required_sections.py `
  tests/test_econ_section_generation_content_brief.py `
  tests/test_assembly_order_econ.py `
  tests/test_no_autonomous_result_figures.py `
  -q
```

## Standalone Econ Runner

Mock run, no LLM request:

```powershell
python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml --out outputs/aer_minimal --mock-llm --no-pdf
```

Kimi/Moonshot OpenAI-compatible run:

```powershell
$env:MOONSHOT_API_KEY='<set outside git>'
python scripts/run_econ_paper.py examples/econ/aer_minimal_request.yaml --out outputs/aer_minimal --model kimi-k2.6 --base-url https://api.moonshot.ai/v1 --no-pdf
```

The runner writes:

```text
events.jsonl
request.normalized.json
manifest.normalized.json
venue.normalized.json
config.redacted.yaml
runner.summary.json
main.tex
```

## Working Rules

1. Work on one TODO task or tightly coupled task pair at a time.
2. Before editing, run the related failing or targeted test when practical.
3. After editing, run the targeted test and a nearby regression subset.
4. Do not run live LLM calls in tests.
5. Do not introduce EvoScientist dependencies into this EasyPaper fork.
6. Do not unlock autonomous empirical result figures.
7. Do not commit API keys. Runner keys must come from CLI args or environment variables and saved configs must be redacted.
