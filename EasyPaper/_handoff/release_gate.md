# EasyPaper Release Gate

## P0 baseline

Command:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
python -m pytest -m "not live_llm and not latex and not slow" -q
```

Result:

- `803 passed`
- `6 failed`
- `6 skipped`
- `4 deselected`

Known failing tests:

- `tests/test_dag_migration.py::TestPromptLoader::test_load_existing_prompt`
- `tests/test_narrative_section_shape_guards.py::test_planner_prompt_policy_requires_dedicated_conclusion`
- `tests/test_plugin_config_template_sync.py::test_plugin_setup_skill_config_template_matches_example_config`
- `tests/test_plugin_config_template_sync.py::test_example_config_matches_current_schema_shape`
- `tests/test_plugin_config_template_sync.py::test_setup_skill_mentions_synchronized_config_template`
- `tests/test_skills_bootstrap.py::test_builtin_packaged_tree_matches_canonical_skills_tree`

Interpretation:

These match roadmap Phase A1: missing packaged prompt/config/plugin skill assets
and a missing canonical `skills/` tree.

## P0 blocker policy

- Live LLM tests remain out of the fast release gate.
- LaTeX/PDF compilation remains manual or optional until the roadmap reaches the
  LaTeX phases.
- Empirical result figures must remain file-backed; autonomous generated result
  figures stay blocked.
- `notes/REVIEW_PROMPT_FOR_LAOGE.md` is a pre-existing unstaged user edit and is
  not part of this release gate.

## Phase A1 result

Command:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
python -m pytest tests/test_dag_migration.py tests/test_narrative_section_shape_guards.py tests/test_plugin_config_template_sync.py tests/test_skills_bootstrap.py -q
python -m pytest -m "not live_llm and not latex and not slow" -q
```

Result:

- Targeted A1 tests: `99 passed`
- Full fast suite: `809 passed, 6 skipped, 4 deselected`

The Phase A1 baseline failures are cleared.
