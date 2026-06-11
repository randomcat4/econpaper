# Econpaper Roadmap v3 Merge Log

## 2026-06-11 P0 baseline freeze

- Branch: `codex/econpaper-roadmap-v3`
- Base commit: `c0aae5a`
- Primary roadmap used: `notes/TODO_EasyPaper_EconFinance_Production_v2_HighConcurrency.md`
- Production roadmap supplement: `skill4econ/docs/roadmap/TODO_EasyPaper_EconFinance_Production.md`
- v3 audit constraints: `EasyPaper/_AUDIT_v3_synthesis.md`, `EasyPaper/_AUDIT_v3_patch_spec.md`, `EasyPaper/_AUDIT_v3_integration.md`, `EasyPaper/_AUDIT_v3_risks.md`

The user-specified `D:/myproject/econpaper/econpaper_roadmap_v3` path was not
present in the working tree during baseline discovery. The implementation will
use the checked-in production roadmaps plus the v3 audit documents as the source
of truth unless a more specific roadmap file appears later.

## Working tree notes

- Pre-existing user edit kept unstaged: `notes/REVIEW_PROMPT_FOR_LAOGE.md`
- No API keys or local env files are staged.

## 2026-06-11 Phase A1

- Implemented missing packaged prompt assets:
  - `src/prompts/metadata/generation_system.txt`
  - `src/prompts/planner/step1_structure.txt`
- Added synchronized config templates:
  - `configs/example.yaml`
  - `plugins/easypaper/skills/easypaper-setup-environment/config.example.yaml`
- Added setup skill:
  - `plugins/easypaper/skills/easypaper-setup-environment/SKILL.md`
- Mirrored built-in skill YAML files into canonical `skills/`.
- Added prompt txt files to package data in `pyproject.toml`.

Tests:

- `python -m pytest tests/test_dag_migration.py tests/test_narrative_section_shape_guards.py tests/test_plugin_config_template_sync.py tests/test_skills_bootstrap.py -q`
  - `99 passed`
- `python -m pytest -m "not live_llm and not latex and not slow" -q`
  - `809 passed, 6 skipped, 4 deselected`
