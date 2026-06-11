# AUDIT v3 Patch Spec: Flow Trace and Tier 1.5 Venue/Section Routing

Scope: static/source inspection only. Do not install `easypaper`. Do not apply the code changes below in this audit pass. This document is the construction-ready Tier 1.5 PoC patch spec.

Repo root assumed by line references: `competitor_repos/easypaper-source`.

## A. End-to-end flow trace: `EasyPaper.generate(metadata)` to PDF on disk

### A.1 SDK and agent wiring

| Step | File:lines | Function/class | Passed object/files | LLM call? | Output/side effect |
|---|---:|---|---|---|---|
| 1 | `easypaper/client.py:42-68` | `EasyPaper.__init__` | optional config path/config | no | loads app config; builds agent instances; stores `self._metadata_agent` |
| 2 | `easypaper/client.py:75-94` | `EasyPaper.generate(metadata, **options)` | caller `PaperMetaData` plus options such as `compile_pdf`, `output_dir`, `template_path`, review flags | no | forwards exactly to `MetaDataAgent.generate_paper(...)` |
| 3 | `easypaper/client.py:274-300` | `EasyPaper._build_agents` | `AppConfig` | no | bootstraps skill registry; calls `initialize_agents(...)` |
| 4 | `src/agents/__init__.py:18-28` | `AGENT_DICT` | configured agent names | no | maps `metadata`, `planner`, `writer`, `reviewer`, `typesetter`, `vlm_review` |
| 5 | `src/agents/__init__.py:30-108` | `initialize_agents` | agent configs, skill registry/config, tools config, VLM config | no | instantiates agents and calls `metadata_agent.set_peers(agent_dict)` |
| 6 | `src/agents/metadata_agent/metadata_agent.py:347-362` | `MetaDataAgent.set_peers` | peer dict | no | stores `_writer`, `_reviewer`, `_planner`, `_vlm_reviewer`, `_typesetter` for in-process SDK mode |

### A.2 One-shot generation wrapper

| Step | File:lines | Function/class | Passed object/files | LLM call? | Output/side effect |
|---|---:|---|---|---|---|
| 7 | `src/agents/metadata_agent/metadata_agent.py:1948-2024` | `MetaDataAgent.generate_paper` | `metadata`, `output_dir`, `template_path`, `target_pages`, review/compile options | no direct | calls `prepare_plan(...)`, then `execute_generation(...)`; merges usage |

### A.3 Planning phase

| Step | File:lines | Function/class | Passed object/files | LLM call? | Output/side effect |
|---|---:|---|---|---|---|
| 8 | `src/agents/metadata_agent/metadata_agent.py:529-1240` | `prepare_plan` | `PaperMetaData`; output/paper dir; template path; target pages; skill/style config | optional several | resolves style/template/output dir; prepares refs, figures, code context, research context, evidence DAG; returns `PlanResult` |
| 9 | `src/agents/metadata_agent/metadata_agent.py:610-613` | `ReferencePool` setup | `metadata.references` | no | parsed/citable reference state |
| 10 | `src/agents/metadata_agent/metadata_agent.py:615-657` | figure preprocessing/validation | `metadata.figures`, materials root | no | normalized figure paths and metadata |
| 11 | `src/agents/metadata_agent/metadata_agent.py:661-670` | output directory setup | `output_dir`/timestamp paper dir | no | creates/chooses `paper_dir` |
| 12 | `src/agents/metadata_agent/metadata_agent.py:675-740` | code/Docling enrichment | optional `code_repository`, reference docs | optional external services | attaches code/research input summaries |
| 13 | `src/agents/metadata_agent/metadata_agent.py:742-807` | exemplar analysis | exemplar path/config | yes, if enabled | style/exemplar guidance for prompts |
| 14 | `src/agents/metadata_agent/metadata_agent.py:862-909` | core-ref/landscape/research context | references, metadata, planner peer | yes, if enabled | `research_context` and landscape refs |
| 15 | `src/agents/metadata_agent/metadata_agent.py:969-975` | `ReviewOrchestrator._create_paper_plan` | `metadata`, `target_pages`, `style_guide`, research/code contexts | yes via planner | returns `PaperPlan` |
| 16 | `src/agents/metadata_agent/orchestrator.py:1404-1497` | `_create_paper_plan` | builds `PlanRequest` from legacy fields only: title, idea, method, data, experiments, references, figures, tables, target pages, style | yes via planner | calls `self.host._planner.create_plan(...)` |
| 17 | `src/agents/planner_agent/models.py:517-532` | `PlanRequest` | currently legacy five text fields and assets; no `DocumentInput`/constraints | no | request model limits what planner can read |
| 18 | `src/agents/planner_agent/planner_agent.py:1364-1774` | `PlannerAgent.create_plan` | `PlanRequest` | yes | produces `PaperPlan` with section order, titles, missions, paragraph plans, sources, dependencies |
| 19 | `src/agents/planner_agent/planner_agent.py:1443-1456` | Step 1 structure prompt | title, idea, method, data, experiments, style, pages, research/code summaries | yes | chooses section list; currently venue norms are soft prompt only |
| 20 | `src/agents/planner_agent/planner_agent.py:1475-1506` | section normalization/dedupe | LLM structure output | no | falls back to `DEFAULT_EMPIRICAL_SECTIONS` if weak; inserts abstract |
| 21 | `src/agents/planner_agent/planner_agent.py:1516-1689` | citation/section/paragraph planning | Step 1 sections | yes | assigns budgets, floats, source hints, paragraph plans |
| 22 | `src/agents/metadata_agent/metadata_agent.py:994-1139` | plan export/review/evidence DAG | plan, refs, research context | optional yes | exports planning artifacts; assigns refs; builds evidence DAG |
| 23 | `src/agents/metadata_agent/metadata_agent.py:1191-1214` | `PlanResult` construction | `paper_plan`, `metadata.model_dump()`, `paper_dir`, contexts, refs | no | serialized boundary between planning and execution |

### A.4 Generation phase: section content

| Step | File:lines | Function/class | Passed object/files | LLM call? | Output/side effect |
|---|---:|---|---|---|---|
| 24 | `src/agents/metadata_agent/metadata_agent.py:1244-1930` | `execute_generation` | `PlanResult`; reconstructs `PaperMetaData` and `PaperPlan` | many downstream | generates sections, reviews, compiles, saves artifacts |
| 25 | `src/agents/metadata_agent/metadata_agent.py:1284` | metadata reconstruction | `PaperMetaData(**plan_result.metadata_input)` | no | restores legacy metadata only |
| 26 | `src/agents/metadata_agent/metadata_agent.py:1309-1312` | plan reconstruction | `PaperPlan(**plan_result.paper_plan)` | no | restores dynamic section plan |
| 27 | `src/agents/metadata_agent/metadata_agent.py:1388-1427` | Phase 1 introduction | `paper_plan.get_section("introduction")`, refs, figures, tables, contexts | yes via writer | calls `_generate_introduction`; stores `generated_sections["introduction"]` |
| 28 | `src/agents/metadata_agent/metadata_agent.py:2062-2105` | `_generate_introduction` | same inputs, plus peer helpers | yes via delegated runner | delegates to `section_generation.generate_introduction_section(...)` |
| 29 | `src/agents/metadata_agent/section_generation.py:106-200` | `generate_introduction_section` | `PaperMetaData`, `SectionPlan`, refs, code/research context | yes via decomposed runner | compiles/traces intro prompt from legacy fields; actual content comes from decomposed paragraph generation |
| 30 | `src/agents/metadata_agent/metadata_agent.py:1438-1485` | Phase 2 body loop | `paper_plan.get_body_section_types()` | downstream | loops planned body sections, excluding intro |
| 31 | `src/agents/metadata_agent/metadata_agent.py:2111-2162` | `_generate_body_section` | section type, metadata, intro context, section plan, refs/assets | yes via delegated runner | delegates to `section_generation.generate_body_section(...)` |
| 32 | `src/agents/metadata_agent/section_generation.py:203-325` | `generate_body_section` | `PaperMetaData`, section type, `SectionPlan.content_sources` | yes via decomposed runner | builds prompt metadata by `getattr(metadata, source)`; calls decomposed runner; returns section result |
| 33 | `src/agents/metadata_agent/decomposed_runner.py:11-234` | `run_decomposed_section_generation` | `SectionPlan._all_paragraphs()`, writer peer, prompt/citation/review helpers | yes | for each paragraph: core LLM write, citation LLM pass, local review, claim verification/fallback; returns joined LaTeX |
| 34 | `src/agents/metadata_agent/decomposed_runner.py:101-118` | core paragraph write | paragraph prompt | yes: `writer.generate_core_content` | raw paragraph LaTeX |
| 35 | `src/agents/metadata_agent/decomposed_runner.py:121-135` | citation injection | raw paragraph LaTeX, assigned refs | yes: `writer.inject_citations` | citation-edited LaTeX |
| 36 | `src/agents/metadata_agent/metadata_agent.py:1486-1530` | Phase 3 synthesis | generated sections and contributions | yes | generates abstract and, only if planned, conclusion |
| 37 | `src/agents/metadata_agent/section_generation.py:328-379` | `generate_synthesis_section` | prior sections, contributions, section plan | yes: `writer.generate_core_content` | abstract/conclusion LaTeX |

### A.5 Review, compile, save

| Step | File:lines | Function/class | Passed object/files | LLM call? | Output/side effect |
|---|---:|---|---|---|---|
| 38 | `src/agents/metadata_agent/metadata_agent.py:1536-1550` | `_run_review_orchestration` call | generated sections, parsed refs, `PaperPlan`, template path, figures/tables, compile flag, paper dir | yes optional | review/revision/compile loop |
| 39 | `src/agents/metadata_agent/orchestrator.py:226-1087` | `ReviewOrchestrator._run_review_orchestration` | sections, metadata, refs, plan, template/assets | yes | reviewer call, revision planning/apply, iterative compile, optional VLM review, final compile |
| 40 | `src/agents/metadata_agent/orchestrator.py:387-398` | reviewer peer call | draft sections/metadata | yes, if review enabled | reviewer report |
| 41 | `src/agents/metadata_agent/orchestrator.py:408` and `1503-1567` | `_llm_plan_revision_tasks` | review issues | yes | structured revision tasks |
| 42 | `src/agents/metadata_agent/orchestrator.py:474-542` | iteration compile | revised sections | no direct | calls host `_compile_pdf(...)` |
| 43 | `src/agents/metadata_agent/orchestrator.py:572-583` | `_call_vlm_review` | compiled PDF path | yes, if enabled | rendered/layout review |
| 44 | `src/agents/metadata_agent/orchestrator.py:638-679` and `1641-1685` | VLM-to-revision translation | VLM issues | yes | revision plan from rendered review |
| 45 | `src/agents/metadata_agent/orchestrator.py:978-1087` | final compile pass | final sections | no direct | sets `pdf_path` when compile succeeds |
| 46 | `src/agents/metadata_agent/metadata_agent.py:1693-1721` | fallback final compile | final sections and assets | no direct | calls `_compile_pdf` if review loop did not set `pdf_path` |
| 47 | `src/agents/metadata_agent/metadata_agent.py:2392-2645` | `_compile_pdf` | generated sections, references, plan, template, figures/tables, output dir | no direct | normalizes sections; builds typesetter payload; in-process typesetter or HTTP fallback |
| 48 | `src/agents/metadata_agent/metadata_agent.py:2440-2458` | section order/titles for compile | `paper_plan.get_compile_section_order()`, `get_section_titles()` | no | dynamic compile order already exists for PDF path |
| 49 | `src/agents/metadata_agent/metadata_agent.py:2588-2602` | `_build_typesetter_payload` | sections/order/titles/assets | no | payload for typesetter |
| 50 | `src/agents/metadata_agent/metadata_agent.py:2604-2630` | in-process typesetter path | `_typesetter.run(...)` | no | parses result; returns `(pdf_path, latex_path, errors, section_errors)` |
| 51 | `src/agents/metadata_agent/metadata_agent.py:2632-2645` | HTTP typesetter fallback | payload to `/agent/typesetter/compile` | no | same parse result contract |
| 52 | `src/agents/typesetter_agent/typesetter_agent.py:866-1095` | `TypesetterAgent.compile_latex` | work dir containing `main.tex`, `references.bib`, section files | no | runs `pdflatex`, `bibtex`, `pdflatex`, `pdflatex`; copies `main.pdf` to output dir |
| 53 | `src/agents/typesetter_agent/typesetter_agent.py:1022-1051` | PDF success/copy | `main.pdf` | no | sets `result.pdf_path`; copies artifacts to output dir |
| 54 | `src/agents/metadata_agent/metadata_agent.py:1738-1745` | `_assemble_paper` | generated sections and refs | no | assembles root `main.tex` for saved artifacts |
| 55 | `src/agents/metadata_agent/assembly_helper.py:12-84` | `assemble_paper` | section dict and refs | no | currently uses hard-coded ML-ish section order for saved `main.tex` |
| 56 | `src/agents/metadata_agent/artifact_exporter.py:267-277` | `export_generation_core_artifacts` | `latex_content`, bibtex, metadata | no | writes `main.tex`, `references.bib`, `metadata.json` under `paper_dir` |
| 57 | `src/agents/metadata_agent/metadata_agent.py:1901-1908` | `export_artifacts_manifest` | `pdf_path`, warnings/errors, total words | no | writes manifest with final `pdf_path` |
| 58 | `src/agents/metadata_agent/metadata_agent.py:1911-1929` | result construction | section results, output path, pdf path | no | returns `PaperGenerationResult` to SDK caller |

### A.6 Key file relationship: orchestrator vs section_generation vs decomposed_runner

`metadata_agent/orchestrator.py` is not the section writer. It handles planning/review/compile orchestration around the host `MetaDataAgent`. Its `_create_paper_plan` currently narrows the input to the legacy five-field `PlanRequest`; later `_run_review_orchestration` handles reviewer/VLM/revision loops and final compile.

`metadata_agent/section_generation.py` is the section-level adapter. The prior audit's large section-generation area should be treated as routing/glue, not as the planner itself. It receives `PaperMetaData` plus a `SectionPlan`, builds trace prompts and section-specific context, and then delegates actual paragraph writing to the decomposed runner. The body path currently resolves `section_plan.content_sources` or `BODY_SECTION_SOURCES`, then calls `getattr(metadata, source)`. That is the main field-name coupling targeted by E.2.

`metadata_agent/decomposed_runner.py` is the paragraph-level writer loop. It does not know metadata field names. It consumes `SectionPlan` paragraphs and helper functions, then calls the writer LLM for paragraph prose and citation injection. Therefore, the planner's `SectionPlan.mission`, `key_content`, paragraphs, and `content_sources` are the real durable contract between planner and writer. Changing only `section_generation.py` without fixing planner inputs leaves the actual writer paragraph prompts mostly unchanged.

## B. Hidden dependencies and expanded patch scope

Flow tracing finds four dependencies beyond the original E.1/E.2 wording. Tier 1.5 must include them or the venue-required econ plan will be brittle.

1. `PaperMetaData.to_document_input()` has no access to venue skills. Current code only creates `GenerationConstraints(max_pages, style_guide, output_format, citation_format)` at `src/agents/metadata_agent/models.py:208-226`. Add an optional `venue_config` parameter and resolve it in `MetaDataAgent`/orchestrator before calling `to_document_input`.

2. `PlanRequest` has no `content_brief` or `constraints` fields (`src/agents/planner_agent/models.py:517-532`). The planner cannot read `GenerationConstraints.required_sections` until `orchestrator._create_paper_plan` passes a `DocumentInput`-derived payload through `PlanRequest`.

3. Planner normalization is ML-biased. `normalize_section_type_name` maps `"results"` to `"result"` and does not slug `"Empirical Strategy"` (`src/agents/planner_agent/planner_utils.py:12-24`). Planner defaults also lack `data`, `empirical_strategy`, `results`, and `robustness` (`src/agents/planner_agent/planner_defaults.py:21-59`). Add constrained-section normalization and econ defaults.

4. Compile uses dynamic plan order, but saved root `main.tex` does not. `_compile_pdf` already uses `paper_plan.get_compile_section_order()` at `src/agents/metadata_agent/metadata_agent.py:2440-2442`; however `_assemble_paper` calls `assembly_helper.assemble_paper`, whose default order is hard-coded to introduction/related_work/method/experiment/result/discussion/conclusion at `src/agents/metadata_agent/assembly_helper.py:50-63`. Patch assembly to accept plan order/titles so saved artifacts match the generated PDF.

## C. Tier 1.5 patch spec

### C.1 E.1: copy `venue_config.required_sections` into `GenerationConstraints`; planner reads constraints

#### C.1.1 Add venue-aware `DocumentInput` conversion

Edit `src/agents/metadata_agent/models.py:208-234`.

Before:

```diff
-    def to_document_input(self) -> "DocumentInput":
+    def to_document_input(self) -> "DocumentInput":
...
-        constraints = GenerationConstraints(
-            max_pages=self.target_pages,
-            style_guide=self.style_guide,
-            output_format="latex",
-            citation_format="bibtex",
-        )
```

After:

```diff
+    def to_document_input(
+        self,
+        *,
+        venue_config: Optional[Dict[str, Any]] = None,
+    ) -> "DocumentInput":
...
+        venue_config = venue_config or {}
+        required_sections = list(venue_config.get("required_sections") or [])
+        page_limit = venue_config.get("page_limit")
+        max_pages = self.target_pages or page_limit
+        constraints = GenerationConstraints(
+            max_pages=max_pages,
+            style_guide=self.style_guide or venue_config.get("name"),
+            output_format="latex",
+            citation_format=venue_config.get("citation_format", "bibtex"),
+            required_sections=required_sections,
+        )
```

Also expand the returned `content_brief` at `src/agents/metadata_agent/models.py:227-234` so section-specific keys exist for planner and section generation:

```diff
         content_brief={
             "idea_hypothesis": self.idea_hypothesis,
             "method": self.method,
             "data": self.data,
             "experiments": self.experiments,
+            "introduction": self.idea_hypothesis,
+            "empirical_strategy": self.method,
+            "results": self.experiments,
+            "robustness": self.experiments,
+            "conclusion": self.idea_hypothesis,
         },
```

Implementation notes:

- Add `Any`, `Dict`, and `Optional` imports only if not already present in this file.
- Keep `to_document_input()` backward compatible by making `venue_config` optional.
- Do not add `venue_config` to `PaperMetaData` unless a later API change requires serializing it; Tier 1.5 should resolve venue config from active skills.

#### C.1.2 Resolve effective venue config in `MetaDataAgent`

Edit `src/agents/metadata_agent/metadata_agent.py:407-431`.

Add a helper next to `_get_active_skills` and `_effective_style_guide`:

```diff
+    def _effective_venue_config(self, style_guide: Optional[str] = None) -> Dict[str, Any]:
+        active = self._get_active_skills(section_type="document", style_guide=style_guide)
+        for skill in active or []:
+            cfg = getattr(skill, "venue_config", None) or {}
+            if cfg:
+                return dict(cfg)
+        return {}
```

If the skill registry does not return venue skills for `section_type="document"`, use `"introduction"` as fallback because venue profiles usually apply across sections:

```diff
+        active = self._get_active_skills("document", style_guide) or self._get_active_skills("introduction", style_guide)
```

Expected behavior:

- For `style_guide`/configured venue `american-economic-review`, this helper returns the loaded venue skill's `venue_config`.
- If no active venue skill exists, it returns `{}` and current behavior remains unchanged.

#### C.1.3 Pass `DocumentInput` through planning

Edit `src/agents/metadata_agent/orchestrator.py:1404-1497`.

Before:

```diff
             plan_request = PlanRequest(
                 title=metadata.title,
                 idea_hypothesis=metadata.idea_hypothesis,
                 method=metadata.method,
                 data=metadata.data,
                 experiments=metadata.experiments,
...
                 target_pages=target_pages,
                 style_guide=style_guide,
             )
```

After:

```diff
+            venue_config = self.host._effective_venue_config(style_guide)
+            document_input = metadata.to_document_input(venue_config=venue_config)
             plan_request = PlanRequest(
                 title=metadata.title,
                 idea_hypothesis=metadata.idea_hypothesis,
                 method=metadata.method,
                 data=metadata.data,
                 experiments=metadata.experiments,
+                content_brief=document_input.content_brief,
+                constraints=document_input.constraints,
...
-                target_pages=target_pages,
+                target_pages=target_pages or document_input.constraints.max_pages,
-                style_guide=style_guide,
+                style_guide=style_guide or document_input.constraints.style_guide,
             )
```

Edit `src/agents/planner_agent/models.py:517-532`.

Before:

```diff
 class PlanRequest(BaseModel):
     ...
     experiments: str
+    ...
     style_guide: Optional[str] = None
```

After:

```diff
+from ...models.document_spec import GenerationConstraints
 class PlanRequest(BaseModel):
     ...
     experiments: str
+    content_brief: Dict[str, str] = Field(default_factory=dict)
+    constraints: Optional[GenerationConstraints] = None
     ...
     style_guide: Optional[str] = None
```

If importing `GenerationConstraints` causes package-level coupling in tests, use a local planner model:

```python
constraints: Optional[Dict[str, Any]] = None
```

But the preferred Tier 1.5 implementation is to use the existing `GenerationConstraints` type because `src/models/document_spec.py:66-91` already defines `required_sections`.

#### C.1.4 Planner prompt and enforcement

Edit `src/agents/planner_agent/prompt_contracts.py:15-61`.

Before:

```diff
 **Target pages**: {target_pages}
+**Research Context**: {research_context_summary}
...
 - "abstract" is always required.
 - Choose sections appropriate for {style_guide}. Use your knowledge of venue norms.
```

After:

```diff
 **Target pages**: {target_pages}
+**Venue required sections**: {required_sections_block}
 **Research Context**: {research_context_summary}
...
 - "abstract" is always required.
+- Include every venue required section exactly once, preserving the required order after the abstract.
 - Choose sections appropriate for {style_guide}. Use your knowledge of venue norms.
```

Edit `src/agents/planner_agent/planner_agent.py:1443-1506`.

Before:

```diff
         step1_prompt = STEP1_STRUCTURE_USER.format(
...
             target_pages=target_pages,
             research_context_summary=rc_summary,
             code_writing_assets_summary=code_summary,
         )
```

After:

```diff
+        required_sections = self._normalize_required_sections(
+            getattr(request.constraints, "required_sections", None) or []
+        )
+        required_sections_block = ", ".join(s["section_title"] for s in required_sections) or "None"
         step1_prompt = STEP1_STRUCTURE_USER.format(
...
             target_pages=target_pages,
+            required_sections_block=required_sections_block,
             research_context_summary=rc_summary,
             code_writing_assets_summary=code_summary,
         )
```

Then enforce after LLM parsing and before duplicate suffixing:

```diff
         if not any(s["section_type"] == "abstract" for s in section_order):
             section_order.insert(0, {"section_type": "abstract", "section_title": "Abstract"})
+
+        if required_sections:
+            section_order = self._merge_required_sections(section_order, required_sections)
```

Add helper behavior in `PlannerAgent` or a new planner utility:

- `_normalize_required_sections(required: list[str]) -> list[dict]`:
  - input `"Introduction"` -> `{"section_type": "introduction", "section_title": "Introduction"}`
  - input `"Data"` -> `{"section_type": "data", "section_title": "Data"}`
  - input `"Empirical Strategy"` -> `{"section_type": "empirical_strategy", "section_title": "Empirical Strategy"}`
  - input `"Results"` -> `{"section_type": "results", "section_title": "Results"}`
  - input `"Robustness"` -> `{"section_type": "robustness", "section_title": "Robustness"}`
  - input `"Conclusion"` -> `{"section_type": "conclusion", "section_title": "Conclusion"}`
- `_merge_required_sections(section_order, required_sections)`:
  - Keep abstract first.
  - Remove duplicates of required section types from LLM output.
  - Insert required sections immediately after abstract in required order.
  - Preserve non-required sections after required sections only if they are useful and not duplicates.
  - Guarantee `conclusion` exists if required.

Expected before/after:

```diff
-DEFAULT_EMPIRICAL_SECTIONS fallback:
-  abstract, introduction, related_work, method, experiment, result, conclusion
+AER/QJE/JFE required-section plan:
+  abstract, introduction, data, empirical_strategy, results, robustness, conclusion
```

#### C.1.5 Planner defaults and section ids

Edit `src/agents/planner_agent/planner_utils.py:12-24`.

Before:

```diff
     st = (section_type or "").strip().lower()
     alias_map = {
         "methods": "method",
         "methodology": "method",
         "experiments": "experiment",
         "results": "result",
         "intro": "introduction",
     }
     return alias_map.get(st, st)
```

After:

```diff
+    st = re.sub(r"[\s\-]+", "_", st)
     alias_map = {
         "methods": "method",
         "methodology": "method",
         "experiments": "experiment",
-        "results": "result",
+        "result": "results",
         "intro": "introduction",
+        "empirical_strategy": "empirical_strategy",
+        "robustness_checks": "robustness",
     }
```

Compatibility note: If existing tests require `result`, do not globally remap `result` to `results`. Instead, keep `normalize_section_type_name("results") == "result"` for LLM output, and use a separate `_normalize_required_section_name` for venue constraints. Tier 1.5 preference: add the separate helper to avoid silently changing old ML section ids.

Edit `src/agents/planner_agent/planner_defaults.py:21-59`.

Add econ titles/sources/dependencies:

```diff
         "method": "Method",
+        "data": "Data",
+        "empirical_strategy": "Empirical Strategy",
         "experiment": "Experiments",
         "result": "Results",
+        "results": "Results",
+        "robustness": "Robustness",
...
         "method": ["method"],
+        "data": ["data"],
+        "empirical_strategy": ["empirical_strategy", "method", "data"],
         "experiment": ["experiments", "data"],
         "result": ["experiments"],
+        "results": ["results", "experiments", "data"],
+        "robustness": ["robustness", "experiments", "method"],
...
+        "data": ["introduction"],
+        "empirical_strategy": ["data"],
+        "results": ["empirical_strategy"],
+        "robustness": ["results"],
```

Do not replace ML defaults. Add econ ids as additional recognized ids.

### C.2 E.2: `section_generation` consumes `DocumentInput.content_brief`

#### C.2.1 Thread `DocumentInput` into execution

Edit `src/agents/metadata_agent/metadata_agent.py:1244-1930`.

After metadata reconstruction, add:

```diff
+            venue_config = self._effective_venue_config(effective_style_guide)
+            document_input = metadata.to_document_input(venue_config=venue_config)
```

If `effective_style_guide` is not defined yet at that location, use `self._effective_style_guide(metadata)` and then reuse the existing variable later.

Pass `document_input` into introduction and body helpers:

```diff
             intro_result = await self._generate_introduction(
-                metadata, ref_pool, section_plan=intro_plan,
+                metadata, ref_pool, section_plan=intro_plan, document_input=document_input,
...
                     result = await self._generate_body_section(
                         section_type=section_type, metadata=metadata,
+                        document_input=document_input,
```

Edit helper signatures in `src/agents/metadata_agent/metadata_agent.py:2062-2162`:

```diff
-    async def _generate_introduction(..., metadata: PaperMetaData, ...)
+    async def _generate_introduction(..., metadata: PaperMetaData, document_input=None, ...)
...
-            metadata=metadata,
+            metadata=metadata,
+            document_input=document_input,
```

```diff
-    async def _generate_body_section(..., metadata: PaperMetaData, ...)
+    async def _generate_body_section(..., metadata: PaperMetaData, document_input=None, ...)
...
-            metadata=metadata,
+            metadata=metadata,
+            document_input=document_input,
```

Edit `src/agents/metadata_agent/section_generation.py:106-127` and `203-228` to accept `document_input=None`.

#### C.2.2 Replace body `getattr(metadata, source)` with content-brief lookup

Edit `src/agents/metadata_agent/section_generation.py:235-249`.

Before:

```diff
     content_parts = []
     for source in sources:
         if source == "references":
             continue
         value = getattr(metadata, source, "")
         if value:
             content_parts.append(f"### {source.title()}\n{value}")
     metadata_content = "\n\n".join(content_parts) if content_parts else metadata.method
```

After:

```diff
+    content_brief = (document_input.content_brief if document_input else metadata.to_document_input().content_brief)
+    metadata_content = _metadata_content_for_section(
+        content_brief=content_brief,
+        section_type=section_type,
+        sources=sources,
+    )
+    if not metadata_content:
+        metadata_content = content_brief.get("method") or metadata.method
```

Add helper near the top of `section_generation.py`:

```python
def _metadata_content_for_section(
    *,
    content_brief: Dict[str, str],
    section_type: str,
    sources: List[str],
) -> str:
    parts: List[str] = []
    direct = content_brief.get(section_type)
    if direct:
        parts.append(f"### {section_type.replace('_', ' ').title()}\n{direct}")
    for source in sources:
        if source == "references" or source == section_type:
            continue
        value = content_brief.get(source)
        if value:
            parts.append(f"### {source.replace('_', ' ').title()}\n{value}")
    return "\n\n".join(parts)
```

Expected behavior:

```diff
- section_type="empirical_strategy", sources=["method", "data"]
- metadata_content = getattr(metadata, "method") + getattr(metadata, "data")
+ section_type="empirical_strategy", sources=["empirical_strategy", "method", "data"]
+ metadata_content first uses content_brief["empirical_strategy"], then falls back through "method" and "data"
```

#### C.2.3 Introduction prompt should also read content brief

Edit `src/agents/metadata_agent/section_generation.py:146-166`.

Before:

```diff
        paper_title=metadata.title,
         idea_hypothesis=metadata.idea_hypothesis,
         method_summary=metadata.method,
         data_summary=metadata.data,
         experiments_summary=metadata.experiments,
```

After:

```diff
+    content_brief = (document_input.content_brief if document_input else metadata.to_document_input().content_brief)
         paper_title=metadata.title,
-        idea_hypothesis=metadata.idea_hypothesis,
-        method_summary=metadata.method,
-        data_summary=metadata.data,
-        experiments_summary=metadata.experiments,
+        idea_hypothesis=content_brief.get("introduction") or content_brief.get("idea_hypothesis", ""),
+        method_summary=content_brief.get("method", ""),
+        data_summary=content_brief.get("data", ""),
+        experiments_summary=content_brief.get("results") or content_brief.get("experiments", ""),
```

This keeps the trace prompt consistent with the section-specific content source used by body sections.

### C.3 BODY_SECTION_SOURCES dispatch table handling plan (v2 C.6)

Edit `src/agents/metadata_agent/models.py:667-674`.

Do not remove `BODY_SECTION_SOURCES` in Tier 1.5. Convert it from the primary metadata access path into a compatibility fallback for source keys.

Before:

```diff
 BODY_SECTION_SOURCES: Dict[str, List[str]] = {
     "related_work": ["references"],
     "method": ["method"],
     "experiment": ["data", "experiments"],
     "result": ["experiments"],
     "discussion": ["experiments"],
 }
```

After:

```diff
 BODY_SECTION_SOURCES: Dict[str, List[str]] = {
     "related_work": ["references"],
     "method": ["method"],
+    "data": ["data"],
+    "empirical_strategy": ["empirical_strategy", "method", "data"],
     "experiment": ["data", "experiments"],
     "result": ["experiments"],
+    "results": ["results", "experiments", "data"],
+    "robustness": ["robustness", "experiments", "method"],
     "discussion": ["experiments"],
 }
```

Dispatch precedence in `section_generation.generate_body_section` should be:

1. `DocumentInput.content_brief[section_type]`
2. `SectionPlan.content_sources` values read from `DocumentInput.content_brief`
3. `BODY_SECTION_SOURCES[section_type]` values read from `DocumentInput.content_brief`
4. legacy fallback to `content_brief["method"]`/`metadata.method`

Explicitly avoid `getattr(metadata, source)` for new section ids. `PaperMetaData` does not have `empirical_strategy`, `results`, or `robustness` fields, so attribute lookup is the wrong abstraction.

### C.4 Assembly artifact order must follow `PaperPlan`

Edit `src/agents/metadata_agent/metadata_agent.py:1738-1745`.

Before:

```diff
             latex_content = self._assemble_paper(
                 title=metadata.title, sections=generated_sections,
                 references=ref_pool.exportable_refs(),
                 valid_citation_keys=ref_pool.valid_citation_keys,
             )
```

After:

```diff
+            assembly_section_order = paper_plan.get_compile_section_order() if paper_plan else None
+            assembly_section_titles = paper_plan.get_section_titles() if paper_plan else None
             latex_content = self._assemble_paper(
                 title=metadata.title, sections=generated_sections,
                 references=ref_pool.exportable_refs(),
                 valid_citation_keys=ref_pool.valid_citation_keys,
+                section_order=assembly_section_order,
+                section_titles=assembly_section_titles,
             )
```

Edit wrapper static method if needed, then edit `src/agents/metadata_agent/assembly_helper.py:12-84`.

Before:

```diff
 def assemble_paper(...):
...
     _default_order = ["introduction", "related_work", "method", "experiment", "result", "discussion", "conclusion"]
...
     section_order = [s for s in _default_order if s in sections]
```

After:

```diff
 def assemble_paper(
     *,
     title: str,
     sections: Dict[str, str],
     references: List[Dict[str, Any]],
     valid_citation_keys: Set[str],
+    section_order: Optional[List[str]] = None,
+    section_titles: Optional[Dict[str, str]] = None,
...
 ):
...
-    section_order = [s for s in _default_order if s in sections]
+    requested_order = section_order or _default_order
+    section_order = [s for s in requested_order if s in sections and s != "abstract"]
...
-            sec_title = _default_titles.get(section_type, section_type.replace("_", " ").title())
+            sec_title = (section_titles or {}).get(
+                section_type,
+                _default_titles.get(section_type, section_type.replace("_", " ").title()),
+            )
```

Expected result: both compiled PDF source and exported root `main.tex` preserve `abstract, introduction, data, empirical_strategy, results, robustness, conclusion`.

### C.5 Minimum test plan

Do not run these in this audit pass. Add/update tests when implementing the patch.

1. `tests/test_dag_migration.py::test_paper_metadata_to_document_input`
   - call `metadata.to_document_input(venue_config={"name": "american-economic-review", "page_limit": 40, "required_sections": [...]})`
   - assert `constraints.required_sections == ["Introduction", "Data", "Empirical Strategy", "Results", "Robustness", "Conclusion"]`
   - assert `constraints.max_pages == 40` when `target_pages` is unset
   - assert `content_brief["empirical_strategy"] == metadata.method`

2. New planner unit test, e.g. `tests/test_planner_required_sections.py`
   - instantiate `PlanRequest(..., content_brief=..., constraints=GenerationConstraints(required_sections=[...]))`
   - stub `_llm_json_call` to return an ML-ish or incomplete section list
   - assert `PaperPlan.sections` includes `abstract, introduction, data, empirical_strategy, results, robustness, conclusion` in that order

3. Extend existing body generation test, likely `tests/test_bugfix_body_section_generation.py`
   - section type `empirical_strategy`
   - `DocumentInput.content_brief["empirical_strategy"] = "Identification comes from ..."`
   - assert prompt trace/body metadata includes that string
   - assert no `getattr(metadata, "empirical_strategy")` path is needed

4. New assembly test
   - call `assemble_paper(..., section_order=["introduction", "data", "empirical_strategy", "results", "robustness", "conclusion"], section_titles=...)`
   - assert `\section{Data}` precedes `\section{Empirical Strategy}` and no default `Methodology` section is introduced

5. Regression check
   - existing ML/default plan without `required_sections` remains `abstract, introduction, related_work, method, experiment, result, conclusion` or whatever the LLM returns.

## D. Draft econ venue YAML specs

These are drafts only. Do not create YAML files in this audit pass.

### D.1 `aer.yaml`

Sources checked:

- AER submissions: https://www.aeaweb.org/journals/aer/submissions
- AER style guide: https://www.aeaweb.org/journals/aer/style-guide

Public guide facts used: AER recommends manuscripts not exceed the equivalent of 40 pages at 11-point font, 1.5 spacing, 1-inch margins, or 45 pages at 12-point font, including figures, tables, references, and appendices. AER abstracts should not exceed 100 words. AER style guide says the introduction conventionally does not receive a heading.

```yaml
name: american-economic-review
description: American Economic Review empirical economics venue profile
version: 0.1.0
tags: [economics, empirical, aer]
type: venue_profile
target_sections: [Introduction, Data, Empirical Strategy, Results, Robustness, Conclusion]
priority: 100
venue_config:
  name: american-economic-review
  page_limit: 40
  page_limit_alt_12pt: 45
  abstract_limit: 100
  words_per_page: 600
  required_sections: [Introduction, Data, Empirical Strategy, Results, Robustness, Conclusion]
  optional_sections: [Related Literature, Model, Appendix]
  citation_format: bibtex
  anonymous: false
  manuscript_notes:
    - AER recommends no more than the equivalent of 40 pages at 11-point font, 1.5 spacing, 1-inch margins, inclusive of figures, tables, references, and appendices.
    - AER permits an equivalent 45-page guide at 12-point font, 1.5 spacing, 1-inch margins.
    - AER abstract limit is 100 words.
    - AER style convention: Introduction usually has no displayed heading; keep the internal section id for planning and let typesetting/style adaptation suppress the heading if supported.
system_prompt_append: >
  Write as an empirical economics paper for the American Economic Review:
  clear research question, economic mechanism, identification, data credibility,
  quantitative results, robustness, and concise policy/economic interpretation.
```

### D.2 `qje.yaml`

Source checked:

- QJE Instructions to Authors: https://academic.oup.com/qje/pages/Instructions_To_Authors

Public guide facts used: QJE requires the first page to include title, author information, and total word count. Abstracts may not exceed 250 words and should not contain reference citations. The required manuscript order is title page with abstract/acknowledgment footnote, text, affiliations, appendix, references, notes, tables, then figures. No hard public full-manuscript page or word cap was found on the instruction page, so leave `page_limit` null.

```yaml
name: quarterly-journal-of-economics
description: Quarterly Journal of Economics empirical economics venue profile
version: 0.1.0
tags: [economics, empirical, qje]
type: venue_profile
target_sections: [Introduction, Data, Empirical Strategy, Results, Robustness, Conclusion]
priority: 100
venue_config:
  name: quarterly-journal-of-economics
  page_limit: null
  abstract_limit: 250
  words_per_page: 600
  required_sections: [Introduction, Data, Empirical Strategy, Results, Robustness, Conclusion]
  optional_sections: [Related Literature, Model, Appendix]
  citation_format: bibtex
  anonymous: false
  require_total_word_count: true
  manuscript_order:
    - title_page_with_abstract
    - text
    - affiliations
    - appendix
    - references
    - notes
    - tables
    - figures
  manuscript_notes:
    - QJE first page must include title, author names, addresses, email addresses, and total word count.
    - QJE abstract limit is 250 words and abstracts should not contain reference citations.
    - JEL codes follow the abstract.
    - Public author instructions do not state a hard full-manuscript page or word cap.
system_prompt_append: >
  Write as an empirical economics paper for the Quarterly Journal of Economics:
  foreground the economic question and contribution, make identification and
  mechanisms explicit, and keep exposition polished, selective, and evidence-led.
```

### D.3 `jfe.yaml`

Sources checked:

- JFE submissions: https://www.jfinec.com/submissions
- JFE data and code sharing policy: https://www.jfinec.com/data-and-code-sharing-policy

Public guide facts used: JFE submissions require an anonymous manuscript PDF with no author information or acknowledgments. The title page should show the title and an abstract of 100 words or less. Manuscripts should be double-spaced, 12-point or larger, with at least 1-inch margins. Online appendix material should be attached to the end of the main manuscript file and anonymized. Accepted empirical/simulation/experimental papers must make data, programs, and replication details available.

```yaml
name: journal-of-financial-economics
description: Journal of Financial Economics empirical finance venue profile
version: 0.1.0
tags: [economics, finance, empirical, jfe]
type: venue_profile
target_sections: [Introduction, Data, Empirical Strategy, Results, Robustness, Conclusion]
priority: 100
venue_config:
  name: journal-of-financial-economics
  page_limit: null
  abstract_limit: 100
  words_per_page: 500
  required_sections: [Introduction, Data, Empirical Strategy, Results, Robustness, Conclusion]
  optional_sections: [Related Literature, Institutional Background, Model, Appendix]
  citation_format: bibtex
  anonymous: true
  double_spacing: true
  min_font_pt: 12
  min_margin_in: 1.0
  online_appendix_in_main_file: true
  data_code_policy: required_after_acceptance_for_empirical_simulation_experimental_work
  manuscript_notes:
    - JFE initial submission manuscript must be an anonymous PDF with no author information or acknowledgments.
    - JFE title page should contain title and abstract of 100 words or less.
    - JFE manuscript should be double-spaced, 12-point or larger, with at least 1-inch margins.
    - Online appendix should be attached to the end of the main manuscript file and anonymized.
system_prompt_append: >
  Write as an empirical finance paper for the Journal of Financial Economics:
  emphasize identification, institutional detail, economically meaningful
  magnitudes, robustness, and transparent data/replication implications.
```

## E. Implementation order

1. Add venue-aware `PaperMetaData.to_document_input(venue_config=...)`.
2. Add `MetaDataAgent._effective_venue_config(...)`.
3. Extend `PlanRequest` with `content_brief` and `constraints`.
4. Pass `document_input` from orchestrator into `PlanRequest`.
5. Add planner required-section normalization, prompt slot, and post-LLM enforcement.
6. Add econ section titles/sources/dependencies without removing ML defaults.
7. Thread `document_input` into `section_generation` and replace body `getattr(metadata, source)` lookup with `content_brief`.
8. Keep and expand `BODY_SECTION_SOURCES` as fallback dispatch.
9. Patch assembly artifact order/titles to use `PaperPlan`.
10. Add tests listed in C.5.

## F. Acceptance criteria

- With an active venue config containing `required_sections: [Introduction, Data, Empirical Strategy, Results, Robustness, Conclusion]`, planner output contains exactly those body/synthesis sections in that order after abstract.
- No new section id requires a matching `PaperMetaData` attribute.
- `section_generation.generate_body_section(section_type="empirical_strategy")` can build metadata content from `DocumentInput.content_brief["empirical_strategy"]`.
- Compiled PDF source and exported root `main.tex` use the same plan-derived section order.
- Default non-venue/ML generation remains backward compatible.
