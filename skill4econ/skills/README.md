# Skill4econ Domain Skills

These files are prompt and rubric skills for environmental economics, ESG,
low-carbon, finance, and causal-inference workflows. They are not estimators,
validators, backend installers, or artifact certifiers. They help an agent turn
a research question into a cautious brief, a candidate method set, a draft spec,
and artifact-aware language.

## Boundary

- Skills may propose candidate specs and diagnostics, but code validation owns
  spec validity, backend discovery, artifact completeness, overlap/balance
  checks, W-matrix checks, and run status.
- Skills must not convert a red or missing artifact into a green claim.
- Every causal, structural, paper-ready, legal/fraud, audit-grade, or
  backend-certified statement must be routed through `claim_gate.json`.
- If `claim_gate.json` is absent, the skill must say claim readiness is not
  established.
- For existing runs, inspect `status.json`, `claim_gate.json`, `manifest.json`,
  `artifact_manifest.json`, `reviewer_risk.json`, and relevant diagnostics
  before reading `model_table.csv`.
- Policy, regulation, disclosure-standard, and data-source facts can change.
  Query official/latest sources at use time instead of relying on memory or
  hardcoded facts in these skill files.

## File Index

- `_shared/`: rules that every skill should cite before drafting claims,
  looking up evidence, reading artifacts, drafting specs, choosing fallbacks, or
  writing reviewer summaries. `_shared/07_scholarly_depth_rules.md` is the
  scholar-facing upgrade rule: use it to prevent domain skills from becoming
  generic checklists. `_shared/08_domain_literature_anchor_rules.md` is the
  lintable domain anchor contract for literature, data, measurement,
  identification, and referee-entry fields.
- `intake/`: first-pass research intake, data inventory, policy design
  interpretation, method selection, robustness planning, and draft spec
  generation.
- `domain/`: domain-specific planning skills for environmental policy, climate
  exposure, pollution, spatial exposure, carbon markets, ESG text, and related
  research areas.
- `reporting/`: artifact-to-claim guards and reviewer-facing summaries.

## Recommended Call Order

0. Before editing or auditing a domain skill, read
   `_shared/07_scholarly_depth_rules.md` and keep the current editing scope to
   at most two markdown files.
1. Start with `intake/env_econ_research_intake.md`.
2. Use `intake/data_inventory_and_panel_mapping.md` and
   `intake/policy_design_interpreter.md` to clarify data and treatment design.
3. Use `intake/method_selection_rubric.md` and relevant `domain/` files to
   rank candidate methods without claiming they have run.
4. Use `intake/spec_generation_guide.md` to create a draft spec for code.
5. Run code validation or estimation outside the skill.
6. Read artifacts through `_shared/03_artifact_reading_rules.md`.
7. Use reporting skills only after `claim_gate.json` and supporting artifacts
   allow the requested language.

## Non-Skippable Shared Rules

Before writing any domain or reporting skill output, read:

- `_shared/00_skill_authoring_rules.md`
- `_shared/01_claim_language_rules.md`
- `_shared/02_evidence_lookup_rules.md`
- `_shared/03_artifact_reading_rules.md`
- `_shared/04_spec_drafting_rules.md`
- `_shared/05_forbidden_fallbacks.md`
- `_shared/06_reviewer_mode_rules.md`
- `_shared/07_scholarly_depth_rules.md`
- `_shared/08_domain_literature_anchor_rules.md`

## Scholarly Depth Gate

A skill is not ready just because it has the required headings. For domain
skills, the answer must also be useful to an econometrician:

- define the estimand in words;
- name identification assumptions;
- describe the measurement model and data-construction risks;
- use a method decision tree, not a method list;
- identify diagnostics that block claims;
- rank robustness checks by the risk they address;
- name likely referee objections;
- include downgrade triggers when code artifacts are missing or red.
- expose the lintable `literature_anchors`, `measurement_regimes`,
  `identification_debate`, and `referee_entry_points` contract without
  inventing citations or data sources.

If the editor is not at least 90 percent confident that a domain skill meets
this standard, call GPT-5.5 Pro in a fresh Chrome ChatGPT sidebar conversation.
After at most five back-and-forth exchanges, start a new sidebar conversation to
avoid long-context drift. Each conversation should focus on at most two markdown
files.
