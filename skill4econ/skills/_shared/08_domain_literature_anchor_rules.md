# Skill: domain_literature_anchor_rules

## Purpose

Define the lintable scholarly-depth fields that every `skills/domain/*.md`
skill must require when it returns domain guidance.

This shared rule is a contract, not a literature review. It must not fill in
domain-specific citations, papers, authors, datasets, policy facts, standards,
or source URLs. Domain skills or GPT-5.5 Pro patches may populate the fields
only with real anchors they are willing to defend; volatile facts belong in
`live_lookup_required_for`.

## Required fields

Every domain skill must expose these fields either in a dedicated section or in
its output schema.

```yaml
literature_anchors:
  canonical_papers_or_authors: []
  canonical_data_sources: []
  live_lookup_required_for: []

measurement_regimes:
  competing_proxy_definitions: []
  validation_targets: []
  known_mismeasurement_channels: []

identification_debate:
  core_threats: []
  sorting_vs_siting_or_selection_channel: null
  why_method_not_magic: []

referee_entry_points:
  likely_major_objections: []
  minimal_empirical_section_checklist: []
  claims_to_downgrade: []
```

## Operational rules

- `canonical_papers_or_authors` names stable literature entry points only when
  the skill author has high confidence they are real and relevant.
- `canonical_data_sources` names stable source families, not stale URLs,
  access dates, or volatile product coverage.
- `live_lookup_required_for` is mandatory for current rules, product scopes,
  policy timelines, API availability, data-product versions, regulatory facts,
  package defaults, and any source whose details can change.
- `measurement_regimes` must distinguish proxies, validation targets, and
  mismeasurement channels before outcome or exposure claims are strengthened.
- `identification_debate` must name why the proposed method does not solve
  selection, sorting, spillovers, omitted variables, or measurement by itself.
- `referee_entry_points` must turn likely objections into empirical-section
  requirements and downgrade triggers.

## Forbidden fill

- Do not write `see literature`, `standard datasets`, `common objections`, or
  similar placeholders.
- Do not invent citations, data sources, agency products, or policy facts to
  satisfy the schema.
- Do not treat an empty schema scaffold as scholarly completeness.
- Do not hardcode official-current details that must be checked at use time.

## Lint expectations

Document lint may check for the field names above, generic template blocks,
repeated `Domain reasoning steps`, and forbidden claim guards. Passing lint
means the contract is present; it does not certify the scholarly content.
