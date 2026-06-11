"""
MetaData Agent - Simple Mode Paper Generation
- **Description**:
    - Generates complete papers from simplified MetaData input
    - Multi-phase generation with persistent ReferencePool:
        0. Planning - core-ref analysis, landscape search, unified research context,
          then paper plan, section reference discovery, utility citation discovery,
          assignment, evidence DAG
        1. Introduction (Leader) - sets tone, extracts contributions
        2. Body Sections - Method, Experiment, Results, Related Work
        3. Synthesis Sections - Abstract and Conclusion from prior sections
        3.5. Review Loop - iterative feedback and revision
        4. PDF Compilation - via Typesetter Agent
    - Two-phase content generation pattern:
        - Phase A (Judgment + Search): LLM judges whether the section needs
          additional references; if yes, PaperSearchTool is called system-side
          and results are merged into the ReferencePool before writing.
        - Phase B (Pure Writing): LLM generates content with all available
          refs (core + discovered) in the prompt, no tools attached.
    - Fixed-sequence review:
        - Mini-review executes citation validation, word count, and key point
          checks in deterministic order (Type 2 tools).
    - ReferencePool accumulates references across all phases:
        user's core refs + discovered refs -> final .bib
    - Independent API, no frontend dependency
"""
import asyncio
import json
import re
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Tuple, Set
from pathlib import Path

import httpx
import yaml

from .progress import ProgressEmitter, ProgressCallback, Phase
from ..shared.llm_client import (
    set_llm_progress_context,
    clear_llm_progress_context,
    set_usage_tracker_context,
    update_usage_tracker_context,
    clear_usage_tracker_context,
)
from ..shared.usage_tracker import UsageTracker
from ..react_base import ReActAgent
from ...config.schema import ModelConfig, SkillsConfig, ToolsConfig
from ..shared.reference_pool import ReferencePool
from ..shared.core_ref_analyzer import CoreRefAnalyzer
from ..shared.research_context_builder import ResearchContextBuilder
from .models import (
    PaperMetaData,
    PaperGenerationResult,
    PlanResult,
    SectionResult,
    SectionGenerationRequest,
    SYNTHESIS_SECTIONS,
    CodeRepoOnError,
)
from ..shared.prompt_compiler import (
    compile_core_prompt,
    compile_citation_prompt,
    apply_citation_edits,
    extract_contributions_from_intro,
)
from ..shared.template_analyzer import TemplateAnalyzer, TemplateWriterGuide
from ..planner_agent.models import (
    PaperPlan,
    ParagraphPlan,
    SectionPlan,
)
from ..shared.table_converter import (
    build_section_table_preview_documents,
    collect_table_layout_review_bundle,
    compile_section_table_preview_documents,
    convert_tables,
    inject_float_refs,
)
from ..shared.session_memory import SessionMemory
from ..shared.code_context import (
    render_code_repository_summary_markdown,
)
from ...evidence.dag_builder import DAGBuilder
from ...models.evidence_graph import EvidenceDAG
from .models import FigureSpec, TableSpec
from .figure_generation import preprocess_generated_figures
from .figure_supplementation import analyze_figure_supplementation_need
from .orchestrator import ReviewOrchestrator
from .revision_executor import RevisionExecutor
from .conflict_resolver import ConflictResolver
from .overflow_manager import OverflowManager
from .artifact_exporter import ArtifactExporter
from .table_restructure import run_table_restructure_loop
from .reporting_helper import ReportingHelper
from .latex_helpers import (
    collect_figure_paths,
    collect_typesetter_figure_ids,
    deduplicate_figure_environments,
    detect_contextless_figure_pages,
    enforce_figure_placement,
    enforce_table_placement,
    escape_latex,
    extract_valid_citation_keys,
    fix_latex_references,
    generate_bib_file,
    normalize_float_placement,
    repair_float_markers,
    repair_hardcoded_figure_references,
    repair_non_owner_figure_references,
    strip_code_path_references,
    validate_assigned_figure_labels_and_refs,
    validate_figure_layout_contract,
    validate_table_layout_contract,
    validate_and_fix_citations,
    validate_main_tex_structure,
)
from .compile_support import (
    build_typesetter_payload,
    ensure_figures_defined,
    ensure_tables_defined,
    normalize_compile_sections,
    parse_typesetter_result,
    post_typesetter_compile,
    save_compile_error_log,
)
from .assembly_helper import (
    assemble_paper,
    validate_and_merge_new_references,
)
from .citation_grounding import (
    CitationGroundingCoordinator,
    sync_sections_results_and_memory,
)
from .metadata_utils import (
    convert_figures_for_latex,
    merge_usage_reports,
    parse_references,
    validate_file_paths,
    validate_ref_usage,
)
from .prompt_support import (
    build_code_repository_context,
    format_research_context_for_prompt,
    get_active_skills,
    retrieve_runtime_code_evidence,
)
from .figure_usage_helper import (
    ensure_paragraph_figure_usages,
    validate_required_figure_usages,
)
from .section_generation import (
    generate_body_section,
    generate_introduction_section,
    generate_synthesis_section,
)
from .local_review import run_local_mini_review
from .decomposed_helper import (
    build_assigned_refs_for_prompt,
    build_subsection_maps,
    prepare_paragraph_generation_inputs,
    run_template_fallback,
)
from .decomposed_verification import (
    handle_local_review_result,
    record_claim_verification_failure,
    verify_claim_and_emit,
)
from .decomposed_runner import run_decomposed_section_generation
from ...prompts import PromptLoader as _PromptLoader

if TYPE_CHECKING:
    from fastapi import APIRouter
    from ..base import BaseAgent

_prompt_loader = _PromptLoader()


def _layout_issue_to_dict(issue: Any) -> Dict[str, Any]:
    if hasattr(issue, "model_dump"):
        return issue.model_dump()
    if isinstance(issue, dict):
        return dict(issue)
    return {"description": str(issue)}


def _final_pdf_table_review_payload(
    *,
    result: Optional[Dict[str, Any]],
    pdf_path: Optional[str],
    source: str,
    reason: str,
) -> Dict[str, Any]:
    if not result:
        return {
            "status": "failed",
            "pdf_path": pdf_path,
            "source": source,
            "reason": reason,
            "all_issues": [],
            "blocking_issues": [],
            "warnings": [],
            "issues": [],
        }
    all_issues = [_layout_issue_to_dict(issue) for issue in (result.get("issues") or [])]
    blocking_issues = [
        _layout_issue_to_dict(issue)
        for issue in (result.get("blocking_layout_issues") or [])
    ]
    blocking_keys = {
        json.dumps(issue, sort_keys=True, default=str) for issue in blocking_issues
    }
    warnings = [
        issue
        for issue in all_issues
        if json.dumps(issue, sort_keys=True, default=str) not in blocking_keys
    ]
    return {
        "status": "passed" if result.get("passed", False) else "failed",
        "pdf_path": pdf_path,
        "source": source,
        "reason": reason,
        "all_issues": all_issues,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "issues": blocking_issues,
        "summary": result.get("summary", ""),
        "passed": bool(result.get("passed", False)),
        "needs_layout_repair": bool(result.get("needs_layout_repair", False)),
    }

# Original inline constant kept as fallback
_GENERATION_SYSTEM_PROMPT_DEFAULT = """\
You are an expert academic writer specializing in research paper composition.
Use present tense for methods, no contractions (it is, do not, cannot),
no possessives on method names (the performance of X, not X's performance).
Place key information at sentence end. Output pure LaTeX only.

CITATION RULES:
- Use ONLY the citation keys listed in the provided references.
- NEVER invent or hallucinate citation keys.
- If a claim needs a reference but none of the provided keys fit, omit the \\cite command.

OUTPUT FORMAT:
Return ONLY the LaTeX content for the section. Do not include explanations outside the LaTeX."""

GENERATION_SYSTEM_PROMPT = _prompt_loader.load(
    "metadata", "generation_system", default=_GENERATION_SYSTEM_PROMPT_DEFAULT
)

_SEARCH_JUDGMENT_PROMPT_DEFAULT = """\
You are an academic research assistant. Your task is to analyze whether the existing \
references are sufficient for writing a specific section of a research paper, or whether \
additional references should be searched.

Given the following section context, analyze whether additional references are needed.

SECTION: {section_type} ({section_title})
PAPER TITLE: {paper_title}
KEY POINTS TO COVER:
{key_points}

EXISTING REFERENCES ({n_refs} papers):
{ref_summaries}

RULES:
- If existing references adequately cover the section's claims, set need_search to false.
- If there are gaps (e.g., missing baselines, no empirical evidence for a claim, \
a sub-topic with zero refs), set need_search to true.
- Provide 1-3 focused search queries using specific keywords, not broad topics.
  Good: "R&D tax credit firm productivity panel data"
  Bad: "innovation economics"
- Each query should target a specific gap you identified.

Respond with ONLY a JSON object, no other text:
{{"need_search": true/false, "reason": "...", "queries": ["...", "..."]}}\
"""

SEARCH_JUDGMENT_PROMPT = _prompt_loader.load(
    "metadata", "search_judgment", default=_SEARCH_JUDGMENT_PROMPT_DEFAULT
)


class MetaDataAgent(ReActAgent):
    """
    MetaData Agent for simple-mode paper generation

    - **Description**:
        - Inherits from ReActAgent for access to react_loop and setup_tools.
        - Accepts 5 natural language fields + BibTeX references.
        - Manages a persistent ReferencePool throughout paper generation:
            - User's core references (~5 papers) initialize the pool.
            - During content generation, LLM may call search_papers (ReAct)
              to discover additional references.
            - Discovered papers undergo two-layer validation (LLM judgment +
              system cross-reference) before being added to the pool.
            - The pool's valid_citation_keys grows across phases.
        - Dual-mode tool invocation:
            - Type 1 (ReAct): _generate_introduction / _generate_body_section
              use react_loop with search_papers for autonomous reference search.
            - Type 2 (Delegated): WriterAgent handles iterative mini-review
              (citation validation, word count, key point coverage) internally.
        - Independent API, can be called directly via curl/Postman.
    """

    def __init__(self, config: ModelConfig, tools_config: Optional[ToolsConfig] = None):
        # Use default tools config if not provided
        if tools_config is None:
            tools_config = ToolsConfig(
                enabled=True,
                available_tools=[
                    "validate_citations",
                    "count_words",
                    "check_key_points",
                    "search_papers",
                ],
                max_react_iterations=3,
            )
        super().__init__(config, tools_config)
        self.results_dir = Path(__file__).parent.parent.parent.parent / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self._router = None
        # Skill registry — injected post-construction by agents/__init__.py
        self._skill_registry = None
        self._skills_config: Optional[SkillsConfig] = None
        # Peer agent references — injected post-construction via set_peers()
        self._writer = None
        self._reviewer = None
        self._planner = None
        self._vlm_reviewer = None
        self._typesetter = None
        # Sub-modules — initialised here; they access peers lazily via self (host)
        self._orchestrator = ReviewOrchestrator(self)
        self._executor = RevisionExecutor(self)
        self._resolver = ConflictResolver(self)
        self._overflow = OverflowManager()
        self._artifacts = ArtifactExporter()
        self._citation_grounding = CitationGroundingCoordinator()
        self._reporting = ReportingHelper(
            citation_validator=self._validate_and_fix_citations,
            paragraph_splitter=self._executor._split_section_paragraphs,
        )

    def set_peers(self, agents: Dict[str, "BaseAgent"]) -> None:
        """
        Inject references to peer agents for direct method calls.
        - **Description**:
            - Called after all agents are initialized in initialize_agents().
            - Enables MetaDataAgent to call WriterAgent, ReviewerAgent, etc.
              directly instead of via HTTP.

        - **Args**:
            - `agents` (Dict[str, BaseAgent]): The full agent dictionary.
        """
        self._writer = agents.get("writer")
        self._reviewer = agents.get("reviewer")
        self._planner = agents.get("planner")
        self._vlm_reviewer = agents.get("vlm_review")
        self._typesetter = agents.get("typesetter")

    @property
    def name(self) -> str:
        """Agent name identifier"""
        return "metadata"

    @property
    def description(self) -> str:
        """Agent description"""
        return "MetaData-based paper generation (Simple Mode) - generates complete papers from 5 natural language fields + BibTeX references"

    _collect_figure_paths = staticmethod(collect_figure_paths)
    _fix_latex_references = staticmethod(fix_latex_references)
    _extract_valid_citation_keys = staticmethod(extract_valid_citation_keys)
    _validate_and_fix_citations = staticmethod(validate_and_fix_citations)
    _deduplicate_figure_environments = staticmethod(deduplicate_figure_environments)
    _detect_contextless_figure_pages = staticmethod(detect_contextless_figure_pages)
    _enforce_figure_placement = staticmethod(enforce_figure_placement)
    _enforce_table_placement = staticmethod(enforce_table_placement)
    _repair_hardcoded_figure_references = staticmethod(repair_hardcoded_figure_references)
    _strip_code_path_references = staticmethod(strip_code_path_references)
    _normalize_float_placement = staticmethod(normalize_float_placement)
    _collect_typesetter_figure_ids = staticmethod(collect_typesetter_figure_ids)
    _generate_bib_file = staticmethod(generate_bib_file)
    _escape_latex = staticmethod(escape_latex)
    _validate_main_tex_structure = staticmethod(validate_main_tex_structure)
    _ensure_figures_defined = staticmethod(ensure_figures_defined)
    _ensure_tables_defined = staticmethod(ensure_tables_defined)
    _normalize_compile_sections = staticmethod(normalize_compile_sections)
    _build_typesetter_payload = staticmethod(build_typesetter_payload)
    _save_compile_error_log = staticmethod(save_compile_error_log)
    _parse_typesetter_result = staticmethod(parse_typesetter_result)
    _validate_and_merge_new_references = staticmethod(validate_and_merge_new_references)
    _merge_usage_reports = staticmethod(merge_usage_reports)
    _parse_references = staticmethod(parse_references)
    _validate_ref_usage = staticmethod(validate_ref_usage)
    _validate_file_paths = staticmethod(validate_file_paths)
    _convert_figures_for_latex = staticmethod(convert_figures_for_latex)
    _build_code_repository_context = staticmethod(build_code_repository_context)
    _retrieve_runtime_code_evidence = staticmethod(retrieve_runtime_code_evidence)
    _format_research_context_for_prompt = staticmethod(format_research_context_for_prompt)
    _validate_required_figure_usages = staticmethod(validate_required_figure_usages)
    _ensure_paragraph_figure_usages = staticmethod(ensure_paragraph_figure_usages)

    def _get_active_skills(
        self,
        section_type: str,
        style_guide: Optional[str] = None,
    ):
        active_names = (
            self._skills_config.active_skills
            if self._skills_config and self._skills_config.enabled
            else None
        )
        effective_style = style_guide or self._configured_venue_profile()
        return get_active_skills(
            self._skill_registry,
            section_type,
            effective_style,
            active_names,
        )

    def _configured_venue_profile(self) -> Optional[str]:
        if self._skills_config and self._skills_config.enabled:
            return self._skills_config.venue_profile
        return None

    def _effective_style_guide(self, metadata: PaperMetaData) -> Optional[str]:
        return metadata.style_guide or self._configured_venue_profile()

    @staticmethod
    def _normalize_venue_key(value: Optional[str]) -> str:
        if not value:
            return ""
        return "-".join(
            token
            for token in re.sub(r"[^a-z0-9]+", " ", str(value).strip().lower()).split()
            if token
        )

    def _effective_venue_config(
        self,
        style_guide: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve an economics/finance venue config without breaking legacy styles.

        Venue takes priority over style_guide. Unknown values return None so
        existing AI/ML generation paths continue to work.
        """
        aliases = {
            "aer": "american-economic-review",
            "american-economic-review": "american-economic-review",
            "american-economics-review": "american-economic-review",
            "qje": "quarterly-journal-of-economics",
            "quarterly-journal-of-economics": "quarterly-journal-of-economics",
            "jfe": "journal-of-financial-economics",
            "journal-of-financial-economics": "journal-of-financial-economics",
        }
        file_names = {
            "american-economic-review": "aer.yaml",
            "quarterly-journal-of-economics": "qje.yaml",
            "journal-of-financial-economics": "jfe.yaml",
        }

        for raw in (venue, style_guide):
            key = self._normalize_venue_key(raw)
            canonical = aliases.get(key)
            if not canonical:
                continue

            if self._skill_registry is not None:
                skill = self._skill_registry.get_venue_profile(canonical)
                if skill and skill.venue_config:
                    return dict(skill.venue_config)

            venue_path = (
                Path(__file__).resolve().parents[2]
                / "skills"
                / "builtin"
                / "venues"
                / file_names[canonical]
            )
            try:
                payload = yaml.safe_load(venue_path.read_text(encoding="utf-8"))
            except Exception as exc:
                print(f"[MetaDataAgent] Warning: venue config lookup failed for {raw}: {exc}")
                return None
            if isinstance(payload, dict) and isinstance(payload.get("venue_config"), dict):
                return dict(payload["venue_config"])
        return None

    @property
    def router(self) -> "APIRouter":
        """Return the FastAPI router for this agent"""
        if self._router is None:
            self._router = self._create_router()
        return self._router

    @property
    def endpoints_info(self) -> List[Dict[str, Any]]:
        """Return endpoint metadata for list_agents"""
        return [
            {
                "path": "/metadata/generate",
                "method": "POST",
                "description": "Generate complete paper from MetaData (5 fields + references)",
            },
            {
                "path": "/metadata/generate/stream",
                "method": "POST",
                "description": "Generate complete paper with SSE progress streaming",
            },
            {
                "path": "/metadata/prepare-plan",
                "method": "POST",
                "description": "Run planning phases only and return a resumable PlanResult",
            },
            {
                "path": "/metadata/generate-from-plan/stream",
                "method": "POST",
                "description": "Resume generation from a serialized PlanResult with SSE progress",
            },
            {
                "path": "/metadata/generate-from-folder",
                "method": "POST",
                "description": "Scan research materials and generate PaperMetaData",
            },
            {
                "path": "/metadata/generate/{task_id}/feedback",
                "method": "POST",
                "description": "Submit feedback to an active streaming generation task",
            },
            {
                "path": "/metadata/generate/{task_id}/cancel",
                "method": "POST",
                "description": "Cancel an active streaming generation task",
            },
            {
                "path": "/metadata/generate/{task_id}/resume",
                "method": "POST",
                "description": "Resume generation from a review checkpoint",
            },
            {
                "path": "/metadata/generate/section",
                "method": "POST",
                "description": "Generate a single section (for debugging or incremental generation)",
            },
            {
                "path": "/metadata/health",
                "method": "GET",
                "description": "Health check endpoint",
            },
            {
                "path": "/metadata/schema",
                "method": "GET",
                "description": "Get input schema for paper generation",
            },
        ]

    def _create_router(self) -> "APIRouter":
        """Create FastAPI router for this agent"""
        from .router import create_metadata_router
        return create_metadata_router(self)

    # ------------------------------------------------------------------
    # prepare_plan: Phase 0 only — returns a serializable PlanResult
    # ------------------------------------------------------------------

    @staticmethod
    def _build_default_no_planning_plan(metadata: PaperMetaData) -> Dict[str, Any]:
        """
        Build a validation-only plan shape that resumes via the planless path.
        """
        plan = PaperPlan(
            title=metadata.title,
            sections=[
                SectionPlan(section_type="introduction", section_title="Introduction"),
                SectionPlan(section_type="related_work", section_title="Related Work"),
                SectionPlan(section_type="method", section_title="Methodology"),
                SectionPlan(section_type="experiment", section_title="Experiments"),
                SectionPlan(section_type="result", section_title="Results"),
            ],
        )
        payload = plan.model_dump()
        payload["_easypaper_no_planning"] = True
        return payload

    async def prepare_plan(
        self,
        metadata: PaperMetaData,
        template_path: Optional[str] = None,
        target_pages: Optional[int] = None,
        enable_planning: bool = True,
        enable_exemplar: bool = False,
        save_output: bool = True,
        output_dir: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
        artifacts_prefix: str = "",
    ) -> PlanResult:
        """
        Execute planning phases (0 through 0.5) and return a serializable snapshot.
        - **Description**:
            - Runs template resolution, reference pool init, file validation,
              figure conversion, planning, DAG construction, code context,
              and table conversion.
            - Does NOT start content generation.
            - The returned PlanResult can be sent to the frontend for review,
              optionally modified, then passed to ``execute_generation()``.

        - **Args**:
            - `metadata` (PaperMetaData): Paper metadata with 5 fields + references.
            - `template_path` (str, optional): Path to .zip template file.
            - `target_pages` (int, optional): Target page count.
            - `enable_planning` (bool): Whether to create a paper plan.
            - `save_output` (bool): Whether to save intermediate files.
            - `output_dir` (str, optional): Directory for output files.
            - `progress_callback` (ProgressCallback, optional): SSE callback.
            - `artifacts_prefix` (str): Storage prefix for artifacts.

        - **Returns**:
            - `PlanResult`: Serializable planning snapshot.
        """
        effective_style_guide = self._effective_style_guide(metadata)
        if template_path is None:
            template_path = metadata.template_path
        if not template_path and not metadata.template_path:
            try:
                from src.default_templates import resolve_default_template
                resolved = resolve_default_template(effective_style_guide)
                if resolved:
                    template_path = resolved
            except ImportError:
                pass
        if target_pages is None:
            target_pages = metadata.target_pages

        emitter = ProgressEmitter(callback=progress_callback)
        set_llm_progress_context(emitter, agent="MetaDataAgent")
        await emitter.generation_started(title=metadata.title, target_pages=target_pages)

        errors: List[str] = []
        warnings: List[str] = []
        figure_supplementation_trace: Optional[Dict[str, Any]] = None
        paper_plan: Optional[PaperPlan] = None
        research_context: Optional[Dict[str, Any]] = None
        code_context: Optional[Dict[str, Any]] = None
        code_summary_markdown: Optional[str] = None
        plan_review_summary: Optional[Dict[str, Any]] = None
        plan_review_iterations: List[Dict[str, Any]] = []
        evidence_dag: Optional[EvidenceDAG] = None
        docling_temp_dir: Optional[Path] = None
        docling_cfg = (
            self.tools_config.docling
            if self.tools_config and getattr(self.tools_config, "docling", None)
            else None
        )

        search_cfg_for_pool = {}
        if self.tools_config and self.tools_config.paper_search:
            ps = self.tools_config.paper_search
            search_cfg_for_pool = {
                "serpapi_api_key": ps.serpapi_api_key,
                "semantic_scholar_api_key": ps.semantic_scholar_api_key,
                "timeout": ps.timeout,
                "semantic_scholar_min_results_before_fallback": ps.semantic_scholar_min_results_before_fallback,
                "enable_query_cache": ps.enable_query_cache,
                "cache_ttl_hours": ps.cache_ttl_hours,
            }
        ref_pool = await ReferencePool.create(
            metadata.references, paper_search_config=search_cfg_for_pool,
        )
        print(f"[MetaDataAgent] Reference pool initialized: {ref_pool.summary()}")

        if metadata.figures:
            openrouter_api_key = getattr(getattr(self, "client", None), "_client", None)
            openrouter_api_key = getattr(openrouter_api_key, "api_key", None)
            try:
                await preprocess_generated_figures(
                    metadata,
                    output_dir=output_dir,
                    results_dir=self.results_dir,
                    style_guide=effective_style_guide,
                    openrouter_api_key=openrouter_api_key,
                )
            except Exception as e:
                msg = f"Figure preprocessing failed: {e}"
                print(f"[MetaDataAgent] {msg}")
                await emitter.error(message=msg, phase="prepare_plan")
                return PlanResult(
                    paper_plan={},
                    metadata_input=metadata.model_dump(),
                    errors=[msg],
                    template_path=template_path,
                    target_pages=target_pages,
                    artifacts_prefix=artifacts_prefix,
                    ref_pool_snapshot=ref_pool.to_dict(),
                    plan_review=plan_review_summary,
                    plan_review_iterations=plan_review_iterations,
                )

        validation_errors = self._validate_file_paths(metadata)
        if validation_errors:
            return PlanResult(
                paper_plan={},
                metadata_input=metadata.model_dump(),
                errors=validation_errors,
                template_path=template_path,
                target_pages=target_pages,
                artifacts_prefix=artifacts_prefix,
                ref_pool_snapshot=ref_pool.to_dict(),
                plan_review=plan_review_summary,
                plan_review_iterations=plan_review_iterations,
            )

        if metadata.figures:
            n_converted = self._convert_figures_for_latex(metadata)
            if n_converted:
                print(f"[MetaDataAgent] Converted {n_converted} figure(s) to LaTeX-compatible format")

        paper_dir_str: Optional[str] = None
        if save_output:
            if output_dir:
                paper_dir = Path(output_dir)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_title = re.sub(r'[^\w\-]', '_', metadata.title)[:50]
                paper_dir = self.results_dir / f"{safe_title}_{timestamp}"
            paper_dir.mkdir(parents=True, exist_ok=True)
            paper_dir_str = str(paper_dir)
        else:
            paper_dir = None

        try:
            # Phase 0e-pre: Code repository context (optional, pre-plan)
            if metadata.code_repository:
                print("[MetaDataAgent] Phase 0e-pre: Building code repository context...")
                await emitter.phase_start(Phase.CODE_CONTEXT, "Building code repository context")
                try:
                    code_context = await self._build_code_repository_context(metadata)
                    if code_context:
                        code_summary_markdown = render_code_repository_summary_markdown(code_context)
                except Exception as e:
                    on_error = metadata.code_repository.on_error
                    msg = f"Code repository ingestion failed: {e}"
                    print(f"[MetaDataAgent] Warning: {msg}")
                    if (
                        metadata.code_repository.type.value == "local_dir"
                        and isinstance(e, (FileNotFoundError, ValueError))
                    ):
                        return PlanResult(
                            paper_plan={}, metadata_input=metadata.model_dump(),
                            errors=[msg], ref_pool_snapshot=ref_pool.to_dict(),
                            template_path=template_path, target_pages=target_pages,
                            artifacts_prefix=artifacts_prefix, paper_dir=paper_dir_str,
                            plan_review=plan_review_summary,
                            plan_review_iterations=plan_review_iterations,
                        )
                    if on_error == CodeRepoOnError.STRICT:
                        return PlanResult(
                            paper_plan={}, metadata_input=metadata.model_dump(),
                            errors=[msg], ref_pool_snapshot=ref_pool.to_dict(),
                            template_path=template_path, target_pages=target_pages,
                            artifacts_prefix=artifacts_prefix, paper_dir=paper_dir_str,
                            plan_review=plan_review_summary,
                            plan_review_iterations=plan_review_iterations,
                        )
                    errors.append(msg)
                    code_context = None
                    code_summary_markdown = None

            # Phase 0-docling: Deep reference analysis via Docling (optional)
            if docling_cfg and docling_cfg.enabled:
                print("[MetaDataAgent] Phase 0-docling: Deep reference analysis with Docling...")
                try:
                    from ..shared.docling_service import DoclingService

                    docling_temp_dir = (paper_dir or Path(tempfile.mkdtemp())) / "_docling_tmp"
                    docling_svc = DoclingService(config=docling_cfg)
                    ref_pool._core_refs = await docling_svc.enrich_refs(
                        ref_pool._core_refs,
                        dest_dir=docling_temp_dir,
                        cleanup=False,
                    )
                    docling_count = sum(
                        1 for r in ref_pool._core_refs if r.get("docling_sections")
                    )
                    print(
                        f"[MetaDataAgent] Docling enriched {docling_count} / "
                        f"{len(ref_pool._core_refs)} core references"
                    )
                except ImportError:
                    print(
                        "[MetaDataAgent] Warning: Docling not installed. "
                        "Install with: pip install easypaper[docling]"
                    )
                    errors.append("Docling enabled but not installed")
                except Exception as e:
                    print(f"[MetaDataAgent] Warning: Docling enrichment failed: {e}")
                    errors.append(f"Docling enrichment failed: {e}")

            # Phase 0-exemplar: Exemplar paper selection and analysis (optional)
            exemplar_analysis_dict: Optional[Dict[str, Any]] = None
            exemplar_cfg = (
                self.tools_config.exemplar
                if self.tools_config and getattr(self.tools_config, "exemplar", None)
                else None
            )
            if enable_exemplar and exemplar_cfg and exemplar_cfg.enabled:
                print("[MetaDataAgent] Phase 0-exemplar: Selecting and analyzing exemplar paper...")
                try:
                    from ..shared.exemplar_selector import ExemplarSelector
                    from ..shared.exemplar_analyzer import ExemplarAnalyzer
                    from ..shared.docling_service import DoclingService as _DocSvc

                    if metadata.exemplar_paper_path:
                        _dsvc = _DocSvc(config=docling_cfg if docling_cfg else None)
                        parsed = _dsvc.parse_pdf(metadata.exemplar_paper_path)
                        exemplar_analyzer = ExemplarAnalyzer(
                            self.client, self.model_name,
                            max_chars=exemplar_cfg.max_analysis_chars,
                        )
                        ref_info = {
                            "ref_id": "user_exemplar",
                            "title": metadata.title + " (user-provided exemplar)",
                            "venue": effective_style_guide or "",
                            "year": 0,
                        }
                        ea = await exemplar_analyzer.analyze(
                            full_text=parsed.full_text,
                            sections=parsed.sections,
                            metadata=metadata,
                            ref_info=ref_info,
                        )
                        exemplar_analysis_dict = ea.model_dump(mode="json")
                        print(f"[MetaDataAgent] Exemplar analysis from user-provided PDF: {len(ea.section_blueprint)} sections")
                    else:
                        selector = ExemplarSelector(self.client, self.model_name)
                        selected = await selector.select(
                            core_refs=list(ref_pool.core_refs),
                            metadata=metadata,
                            config=exemplar_cfg,
                            paper_search_config=search_cfg_for_pool,
                        )
                        if selected:
                            exemplar_analyzer = ExemplarAnalyzer(
                                self.client, self.model_name,
                                max_chars=exemplar_cfg.max_analysis_chars,
                            )
                            ea = await exemplar_analyzer.analyze(
                                full_text=selected.get("docling_full_text", ""),
                                sections=selected.get("docling_sections", {}),
                                metadata=metadata,
                                ref_info={
                                    "ref_id": selected.get("ref_id", ""),
                                    "title": selected.get("title", ""),
                                    "venue": selected.get("venue", ""),
                                    "year": selected.get("year", 0),
                                },
                            )
                            exemplar_analysis_dict = ea.model_dump(mode="json")
                            print(f"[MetaDataAgent] Exemplar selected: {selected.get('ref_id', '')} ({len(ea.section_blueprint)} sections)")
                        else:
                            print("[MetaDataAgent] No suitable exemplar found among core refs")
                except Exception as e:
                    print(f"[MetaDataAgent] Warning: Exemplar analysis failed: {e}")
                    errors.append(f"Exemplar analysis failed: {e}")

            # Phase 0: Planning
            if enable_planning:
                print("[MetaDataAgent] Phase 0: Creating Paper Plan...")
                await emitter.phase_start(Phase.PLANNING, "Creating paper plan")
                search_cfg = {}
                if self.tools_config and self.tools_config.paper_search:
                    ps = self.tools_config.paper_search
                    search_cfg = {
                        "serpapi_api_key": ps.serpapi_api_key,
                        "semantic_scholar_api_key": ps.semantic_scholar_api_key,
                        "timeout": ps.timeout,
                        "search_results_per_round": ps.search_results_per_round,
                        "planner_max_queries_per_section": ps.planner_max_queries_per_section,
                        "planner_inter_round_delay_sec": ps.planner_inter_round_delay_sec,
                        "planner_min_target_papers_per_section": ps.planner_min_target_papers_per_section,
                        "semantic_scholar_min_results_before_fallback": ps.semantic_scholar_min_results_before_fallback,
                        "enable_query_cache": ps.enable_query_cache,
                        "cache_ttl_hours": ps.cache_ttl_hours,
                        "citation_budget_enabled": ps.citation_budget_enabled,
                        "citation_budget_soft_cap": ps.citation_budget_soft_cap,
                        "citation_budget_export": ps.citation_budget_export,
                        "citation_budget_reserve_size": ps.citation_budget_reserve_size,
                        "style_guide": effective_style_guide,
                        "planner_landscape_max_queries": getattr(
                            ps, "planner_landscape_max_queries", 8,
                        ),
                        "planner_max_utility_searches": getattr(
                            ps, "planner_max_utility_searches", 12,
                        ),
                    }

                rc_cfg = (
                    self.tools_config.research_context
                    if self.tools_config and self.tools_config.research_context
                    else None
                )
                rc_enabled = rc_cfg.enabled if rc_cfg else False
                planner_review_enabled = (
                    bool(getattr(self.tools_config, "planner_plan_review_enabled", True))
                    if self.tools_config else True
                )
                planner_review_max_iterations = max(
                    0,
                    int(
                        getattr(self.tools_config, "planner_plan_review_max_iterations", 2)
                        if self.tools_config else 2
                    ),
                )

                # Phase 0-core + 0-ctx: core ref analysis, landscape search, unified research context (pre-plan)
                if rc_enabled:
                    print("[MetaDataAgent] Phase 0-core: Analyzing core references...")
                    try:
                        _analyzer = CoreRefAnalyzer.from_tools_config(
                            self.client, self.model_name, self.tools_config,
                        )
                        _core_analysis = await _analyzer.analyze(
                            list(ref_pool.core_refs), metadata,
                        )
                    except Exception as e:
                        print(f"[MetaDataAgent] Warning: Core ref analysis failed: {e}")
                        from .models import CoreRefAnalysis as _CoreRefAnalysis
                        _core_analysis = _CoreRefAnalysis()

                    print("[MetaDataAgent] Phase 0-ctx: Landscape discovery + research context...")
                    landscape_papers: List[Dict[str, Any]] = []
                    try:
                        landscape_papers = await self._planner.discover_landscape_references(
                            core_analysis=_core_analysis,
                            title=metadata.title,
                            idea_hypothesis=metadata.idea_hypothesis,
                            paper_search_config=search_cfg,
                        )
                        for paper in landscape_papers:
                            ref_pool.add_discovered(
                                paper.get("ref_id", ""),
                                paper.get("bibtex", ""),
                                source="landscape_discovery",
                                validation=paper.get("validation"),
                                metadata=paper,
                            )
                    except Exception as e:
                        print(f"[MetaDataAgent] Warning: Landscape discovery failed: {e}")

                    try:
                        _builder = ResearchContextBuilder(self.client, self.model_name)
                        _landscape_top_k = 24
                        if rc_cfg is not None and getattr(rc_cfg, "top_k_key_papers", None):
                            _landscape_top_k = max(8, int(rc_cfg.top_k_key_papers))

                        async def _score_landscape(topic: str, papers: List[Dict[str, Any]]):
                            return await self._planner._score_papers_by_relevance(topic, papers)

                        _rc_model = await _builder.build(
                            core_analysis=_core_analysis,
                            landscape_papers=landscape_papers,
                            paper_metadata=metadata,
                            score_papers_fn=_score_landscape if landscape_papers else None,
                            top_k_landscape=_landscape_top_k,
                        )
                        research_context = _rc_model.to_research_context_dict()
                    except Exception as e:
                        print(f"[MetaDataAgent] Warning: Research context build failed: {e}")

                if getattr(metadata, "enable_figure_supplementation", False):
                    print("[MetaDataAgent] Phase 0-fig: Evaluating figure supplementation...")
                    supplemental_figures: List[FigureSpec] = []
                    try:
                        supplemental_figures, figure_supplementation_trace = (
                            analyze_figure_supplementation_need(
                                metadata,
                                research_context=research_context,
                                code_context=code_context,
                                style_guide=effective_style_guide,
                            )
                        )
                        if supplemental_figures:
                            metadata.figures.extend(supplemental_figures)
                            openrouter_api_key = getattr(getattr(self, "client", None), "_client", None)
                            openrouter_api_key = getattr(openrouter_api_key, "api_key", None)
                            await preprocess_generated_figures(
                                metadata,
                                output_dir=output_dir,
                                results_dir=self.results_dir,
                                style_guide=effective_style_guide,
                                openrouter_api_key=openrouter_api_key,
                            )
                            validation_errors = self._validate_file_paths(metadata)
                            if validation_errors:
                                raise ValueError("; ".join(validation_errors))
                            n_converted = self._convert_figures_for_latex(metadata)
                            if n_converted:
                                print(
                                    f"[MetaDataAgent] Converted {n_converted} supplemented figure(s)"
                                )
                            figure_supplementation_trace["generated_count"] = len(
                                supplemental_figures
                            )
                    except Exception as e:
                        supplemental_ids = {
                            fig.id for fig in supplemental_figures
                        }
                        if supplemental_ids:
                            metadata.figures = [
                                fig for fig in metadata.figures
                                if fig.id not in supplemental_ids
                            ]
                        msg = f"Figure supplementation skipped after generation failure: {e}"
                        print(f"[MetaDataAgent] Warning: {msg}")
                        warnings.append(msg)
                        if figure_supplementation_trace is None:
                            figure_supplementation_trace = {
                                "enabled": True,
                                "status": "failed",
                                "warnings": [msg],
                            }
                        else:
                            figure_supplementation_trace["status"] = "failed"
                            figure_supplementation_trace.setdefault("warnings", []).append(msg)

                paper_plan = await self._orchestrator._create_paper_plan(
                    metadata=metadata, target_pages=target_pages,
                    style_guide=effective_style_guide, research_context=research_context,
                    code_context=code_context,
                    planner_review_enabled=planner_review_enabled,
                    planner_review_max_iterations=planner_review_max_iterations,
                )
                if paper_plan:
                    if self.tools_config and not getattr(
                        self.tools_config, "planner_structure_signals_enabled", True,
                    ):
                        for sp in paper_plan.sections:
                            sp.topic_clusters = []
                            sp.transition_intents = []
                            sp.sectioning_recommended = False

                    if paper_plan.wide_figures:
                        for fig in metadata.figures:
                            if fig.id in paper_plan.wide_figures and not fig.wide:
                                fig.wide = True
                    if paper_plan.wide_tables:
                        for tbl in metadata.tables:
                            if tbl.id in paper_plan.wide_tables and not tbl.wide:
                                tbl.wide = True

                    if save_output and paper_dir:
                        self._artifacts.export_plan_artifacts(
                            paper_dir=paper_dir,
                            paper_plan=paper_plan,
                            figure_supplementation_trace=figure_supplementation_trace,
                        )

                    plan_review_obj = None
                    plan_evolution = None
                    if self._planner and hasattr(self._planner, "get_last_plan_review_summary"):
                        try:
                            plan_review_obj = self._planner.get_last_plan_review_summary()
                        except Exception as e:
                            print(f"[MetaDataAgent] Warning: failed to collect plan review summary: {e}")
                    if self._planner and hasattr(self._planner, "get_last_plan_evolution"):
                        try:
                            plan_evolution = self._planner.get_last_plan_evolution()
                        except Exception as e:
                            print(f"[MetaDataAgent] Warning: failed to collect plan evolution: {e}")
                    if plan_review_obj is not None:
                        plan_review_summary = plan_review_obj.model_dump(mode="json")
                        plan_review_iterations = list(plan_review_summary.get("iterations", []) or [])
                        if save_output and paper_dir:
                            self._artifacts.export_plan_artifacts(
                                paper_dir=paper_dir,
                                plan_review_summary=plan_review_summary,
                                plan_evolution=plan_evolution,
                                figure_supplementation_trace=figure_supplementation_trace,
                            )

                    # Phase 0b: Reference discovery
                    print("[MetaDataAgent] Phase 0b: Discovering references...")
                    discovered = await self._planner.discover_references(
                        plan=paper_plan,
                        existing_ref_keys=list(ref_pool.known_keys),
                        paper_search_config=search_cfg,
                    )
                    disc_count = 0
                    for sec_type, papers in discovered.items():
                        for paper in papers:
                            if ref_pool.add_discovered(
                                paper["ref_id"],
                                paper["bibtex"],
                                source="planner_discovery",
                                validation=paper.get("validation"),
                                metadata=paper,
                            ):
                                disc_count += 1
                    if disc_count:
                        print(f"[MetaDataAgent] Discovered {disc_count} new references")

                    # Phase 0b-utility: dataset / metric / framework papers mentioned in plan text
                    try:
                        utility_refs = await self._planner.discover_utility_references(
                            plan=paper_plan,
                            existing_ref_keys=list(ref_pool.known_keys),
                            paper_search_config=search_cfg,
                        )
                        util_added = 0
                        for sec_type, papers in utility_refs.items():
                            for paper in papers:
                                if ref_pool.add_discovered(
                                    paper.get("ref_id", ""),
                                    paper.get("bibtex", ""),
                                    source="utility_discovery",
                                    validation=paper.get("validation"),
                                    metadata=paper,
                                ):
                                    discovered.setdefault(sec_type, []).append(paper)
                                    util_added += 1
                        if util_added:
                            print(f"[MetaDataAgent] Utility discovery added {util_added} reference(s)")
                    except Exception as e:
                        print(f"[MetaDataAgent] Warning: Utility reference discovery failed: {e}")

                    # Merge section-level paper assignments into pre-plan research context
                    if rc_enabled and research_context is not None:
                        research_context = dict(research_context)
                        research_context["paper_assignments"] = (
                            self._planner._assign_papers_to_sections(paper_plan, discovered)
                        )

                    # Phase 0c: Assign references to sections
                    print("[MetaDataAgent] Phase 0c: Assigning references to sections...")
                    self._planner.assign_references(
                        plan=paper_plan,
                        discovered=discovered,
                        core_ref_keys=[ref["ref_id"] for ref in ref_pool.core_refs if ref.get("ref_id")],
                        paper_search_config=search_cfg,
                        research_context=research_context,
                    )
                    for sp in paper_plan.sections:
                        if sp.assigned_refs:
                            print(f"  [{sp.section_type}] {len(sp.assigned_refs)} refs assigned")
                    await emitter.plan_created(
                        sections=len(paper_plan.sections),
                        estimated_words=paper_plan.get_total_estimated_words(),
                    )
                    await emitter.phase_complete(Phase.PLANNING, f"Plan created with {len(paper_plan.sections)} sections")
                else:
                    print("[MetaDataAgent] Planning skipped or failed, using defaults")

            # Phase 0d.5: Build Evidence DAG
            if paper_plan:
                try:
                    dag_builder = DAGBuilder(llm_client=self.client, model_name=self.model_name)
                    evidence_dag = await dag_builder.build(
                        code_context=code_context,
                        research_context=research_context,
                        figures=metadata.figures,
                        tables=metadata.tables,
                        paper_plan=paper_plan,
                        graph_structure=metadata.graph_structure,
                    )
                    paper_plan.evidence_dag = evidence_dag.to_serializable()

                    for sp in paper_plan.sections:
                        for pidx, para in enumerate(sp.paragraphs):
                            if not para.claim_id:
                                for claim in evidence_dag.claim_nodes.values():
                                    meta = claim.metadata
                                    if meta.get("section_type") == sp.section_type and meta.get("paragraph_index") == pidx:
                                        para.claim_id = claim.node_id
                                        para.bound_evidence_ids = evidence_dag.get_bound_evidence_ids_for_claim(claim.node_id)
                                        break

                    from ..planner_agent.planner_agent import PlannerAgent as _PA
                    total_sp = 0
                    for sp in paper_plan.sections:
                        for pidx, para in enumerate(sp.paragraphs):
                            if para.claim_id and not para.sentence_plans:
                                para.sentence_plans = _PA._generate_sentence_plans(para, evidence_dag=evidence_dag)
                                total_sp += len(para.sentence_plans)
                    if total_sp:
                        print(f"[MetaDataAgent] Generated {total_sp} sentence plans from DAG bindings")

                    if save_output and paper_dir:
                        self._artifacts.export_plan_artifacts(
                            paper_dir=paper_dir,
                            evidence_dag=evidence_dag,
                            figure_supplementation_trace=figure_supplementation_trace,
                        )
                except Exception as e:
                    print(f"[MetaDataAgent] Warning: Evidence DAG construction failed: {e}")
                    evidence_dag = None

            # Phase 0e: Code repository context (post-plan fallback)
            if metadata.code_repository and not code_context:
                try:
                    code_context = await self._build_code_repository_context(metadata)
                    if code_context:
                        code_summary_markdown = render_code_repository_summary_markdown(code_context)
                except Exception as e:
                    on_error = metadata.code_repository.on_error
                    msg = f"Code repository ingestion failed: {e}"
                    if (
                        metadata.code_repository.type.value == "local_dir"
                        and isinstance(e, (FileNotFoundError, ValueError))
                    ):
                        return PlanResult(
                            paper_plan=paper_plan.model_dump() if paper_plan else {},
                            metadata_input=metadata.model_dump(), errors=[msg],
                            ref_pool_snapshot=ref_pool.to_dict(),
                            template_path=template_path, target_pages=target_pages,
                            artifacts_prefix=artifacts_prefix, paper_dir=paper_dir_str,
                            plan_review=plan_review_summary,
                            plan_review_iterations=plan_review_iterations,
                        )
                    if on_error == CodeRepoOnError.STRICT:
                        return PlanResult(
                            paper_plan=paper_plan.model_dump() if paper_plan else {},
                            metadata_input=metadata.model_dump(), errors=[msg],
                            ref_pool_snapshot=ref_pool.to_dict(),
                            template_path=template_path, target_pages=target_pages,
                            artifacts_prefix=artifacts_prefix, paper_dir=paper_dir_str,
                            plan_review=plan_review_summary,
                            plan_review_iterations=plan_review_iterations,
                        )
                    errors.append(msg)
                    code_context = None
                    code_summary_markdown = None

            # Phase 0.5: Convert tables
            converted_tables: Dict[str, str] = {}
            if metadata.tables:
                print(f"[MetaDataAgent] Phase 0.5: Converting {len(metadata.tables)} tables...")
                await emitter.phase_start(Phase.TABLE_CONVERSION, f"Converting {len(metadata.tables)} tables to LaTeX")
                base_path = getattr(metadata, "materials_root", None) or (
                    str(paper_dir.parent) if (save_output and paper_dir) else None
                )
                fallback_base_path = str(paper_dir.parent) if (save_output and paper_dir) else None
                converted_tables = await convert_tables(
                    tables=metadata.tables, llm_client=self.client,
                    model_name=self.model_name, base_path=base_path,
                    fallback_base_path=fallback_base_path,
                )

            result_plan_payload = paper_plan.model_dump() if paper_plan else {}
            if not result_plan_payload and not errors:
                result_plan_payload = self._build_default_no_planning_plan(metadata)

            return PlanResult(
                paper_plan=result_plan_payload,
                evidence_dag=evidence_dag.to_serializable() if evidence_dag else None,
                research_context=research_context,
                code_context=code_context,
                code_summary_markdown=code_summary_markdown,
                ref_pool_snapshot=ref_pool.to_dict(),
                converted_tables=converted_tables,
                metadata_input=metadata.model_dump(),
                errors=errors,
                warnings=warnings,
                template_path=template_path,
                target_pages=target_pages,
                exemplar_analysis=exemplar_analysis_dict,
                artifacts_prefix=artifacts_prefix,
                paper_dir=paper_dir_str,
                plan_review=plan_review_summary,
                plan_review_iterations=plan_review_iterations,
                figure_supplementation_trace=figure_supplementation_trace,
            )

        except Exception as e:
            print(f"[MetaDataAgent] prepare_plan error: {e}")
            await emitter.error(message=str(e), phase="prepare_plan")
            return PlanResult(
                paper_plan={}, metadata_input=metadata.model_dump(),
                errors=[str(e)], ref_pool_snapshot=ref_pool.to_dict(),
                warnings=warnings,
                template_path=template_path, target_pages=target_pages,
                artifacts_prefix=artifacts_prefix, paper_dir=paper_dir_str,
                plan_review=plan_review_summary,
                plan_review_iterations=plan_review_iterations,
                figure_supplementation_trace=figure_supplementation_trace,
            )
        finally:
            # Docling temp file cleanup
            if docling_temp_dir and docling_temp_dir.exists():
                if docling_cfg and docling_cfg.move_to_output and paper_dir:
                    dest = paper_dir / "reference_pdfs"
                    if not dest.exists():
                        shutil.move(str(docling_temp_dir), str(dest))
                elif docling_cfg and docling_cfg.cleanup_after_analysis:
                    shutil.rmtree(docling_temp_dir, ignore_errors=True)
            clear_llm_progress_context()

    # ------------------------------------------------------------------
    # execute_generation: Phases 1-5 from a PlanResult
    # ------------------------------------------------------------------

    async def execute_generation(
        self,
        plan_result: PlanResult,
        enable_review: bool = True,
        max_review_iterations: int = 3,
        compile_pdf: bool = True,
        enable_vlm_review: bool = False,
        enable_user_feedback: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
        feedback_queue: Optional[asyncio.Queue] = None,
        feedback_timeout: float = 300.0,
        save_output: bool = True,
        output_dir: Optional[str] = None,
        figures_source_dir: Optional[str] = None,
    ) -> PaperGenerationResult:
        """
        Execute content generation from a previously computed PlanResult.
        - **Description**:
            - Deserializes PlanResult, reconstructs PaperPlan/EvidenceDAG/ReferencePool,
              then runs Phases 1 through 5 (introduction, body, synthesis, review,
              compilation, assembly).

        - **Args**:
            - `plan_result` (PlanResult): Output of ``prepare_plan()`` (possibly user-modified).
            - `enable_review` (bool): Whether to enable the review loop.
            - `max_review_iterations` (int): Maximum review iterations.
            - `compile_pdf` (bool): Whether to compile to PDF.
            - `enable_vlm_review` (bool): Whether to run VLM review.
            - `enable_user_feedback` (bool): Pause at review for user feedback.
            - `progress_callback` (ProgressCallback, optional): SSE callback.
            - `feedback_queue` (asyncio.Queue, optional): User feedback queue.
            - `feedback_timeout` (float): Seconds to wait for feedback.
            - `save_output` (bool): Whether to save output files.
            - `output_dir` (str, optional): Override output directory.
            - `figures_source_dir` (str, optional): Directory with figure files.

        - **Returns**:
            - `PaperGenerationResult`: Complete generation result.
        """
        # Reconstruct state from PlanResult
        metadata = PaperMetaData(**plan_result.metadata_input)
        effective_style_guide = self._effective_style_guide(metadata)
        venue_config = self._effective_venue_config(
            style_guide=getattr(metadata, "style_guide", None),
            venue=getattr(metadata, "venue", None),
        )
        document_input = metadata.to_document_input(venue_config=venue_config)
        content_brief = document_input.content_brief
        ref_pool = ReferencePool.from_dict(plan_result.ref_pool_snapshot)
        template_path = plan_result.template_path
        target_pages = plan_result.target_pages
        artifacts_prefix = plan_result.artifacts_prefix
        converted_tables = plan_result.converted_tables
        research_context = plan_result.research_context
        code_context = plan_result.code_context
        code_summary_markdown = plan_result.code_summary_markdown
        errors = list(plan_result.errors)
        generation_warnings = list(plan_result.warnings)

        # Analyze template for Writer constraints
        template_guide: Optional[TemplateWriterGuide] = None
        if template_path:
            template_guide = TemplateAnalyzer.analyze_zip(template_path)
            if template_guide.available_packages:
                print(
                    f"[MetaDataAgent] Template analyzed: "
                    f"{len(template_guide.available_packages)} packages, "
                    f"column={template_guide.column_format}, "
                    f"citation={template_guide.citation_style}"
                )

        paper_plan: Optional[PaperPlan] = None
        if plan_result.paper_plan and not plan_result.paper_plan.get("_easypaper_no_planning"):
            paper_plan = PaperPlan(**plan_result.paper_plan)

        evidence_dag: Optional[EvidenceDAG] = None
        if plan_result.evidence_dag:
            evidence_dag = EvidenceDAG.from_serializable(plan_result.evidence_dag)

        # Reconstruct ExemplarAnalysis for prompt guidance
        from .models import ExemplarAnalysis as _ExemplarAnalysis
        from ..shared.exemplar_analyzer import ExemplarAnalyzer as _ExemplarAnalyzerCls
        _exemplar_analysis: Optional[_ExemplarAnalysis] = None
        if plan_result.exemplar_analysis:
            try:
                _exemplar_analysis = _ExemplarAnalysis(**plan_result.exemplar_analysis)
            except Exception:
                _exemplar_analysis = None

        # Resolve output directory
        if output_dir:
            paper_dir: Optional[Path] = Path(output_dir)
        elif plan_result.paper_dir:
            paper_dir = Path(plan_result.paper_dir)
        else:
            paper_dir = None
        if paper_dir and save_output:
            paper_dir.mkdir(parents=True, exist_ok=True)

        emitter = ProgressEmitter(callback=progress_callback)
        set_llm_progress_context(emitter, agent="MetaDataAgent")
        await emitter.generation_started(title=metadata.title, target_pages=target_pages)

        usage_tracker = UsageTracker()
        set_usage_tracker_context(usage_tracker, agent="MetaDataAgent", phase="generation")

        _sa = partial(self._artifacts.save_artifact, artifacts_prefix=artifacts_prefix)

        sections_results: List[SectionResult] = []
        generated_sections: Dict[str, str] = {}
        review_iterations = 0
        target_word_count = None
        prompt_traces: List[Dict[str, Any]] = []
        citation_budget_usage: List[Dict[str, Any]] = []
        pdf_path: Optional[str] = None
        parsed_refs = ref_pool.exportable_refs()
        citation_audit_payload: Optional[Dict[str, Any]] = None
        citation_audit_markdown: Optional[str] = None
        citation_audit_path: Optional[str] = None
        citation_warnings: List[str] = []

        memory = SessionMemory()
        memory.log(
            "metadata", "init", "session_started",
            narrative=f"Resumed generation for '{metadata.title}' targeting {target_pages} pages.",
            title=metadata.title, target_pages=target_pages,
        )
        if paper_plan:
            memory.plan = paper_plan

        def _sec_filename(section_type: str) -> str:
            if paper_plan:
                titles = paper_plan.get_section_titles()
                if section_type in titles:
                    return titles[section_type]
            return section_type.replace("_", " ").title()

        try:
            if metadata.figures:
                run_output_dir = str(paper_dir) if paper_dir else output_dir
                openrouter_api_key = getattr(getattr(self, "client", None), "_client", None)
                openrouter_api_key = getattr(openrouter_api_key, "api_key", None)
                await preprocess_generated_figures(
                    metadata,
                    output_dir=run_output_dir,
                    results_dir=self.results_dir,
                    style_guide=effective_style_guide,
                    openrouter_api_key=openrouter_api_key,
                )

            # Phase 1: Introduction
            print("[MetaDataAgent] Phase 1: Generating Introduction...")
            update_usage_tracker_context(agent="WriterAgent", phase="introduction")
            await emitter.phase_start(Phase.INTRODUCTION, "Generating introduction")
            await emitter.section_start("introduction", phase=Phase.INTRODUCTION)
            await emitter.agent_step(agent="WriterAgent", description="Generating introduction section", section="introduction", phase=Phase.INTRODUCTION)
            intro_plan = paper_plan.get_section("introduction") if paper_plan else None
            intro_result = await self._generate_introduction(
                metadata, ref_pool, section_plan=intro_plan,
                figures=metadata.figures, tables=metadata.tables,
                code_context=code_context, research_context=research_context,
                prompt_traces=prompt_traces, memory=memory, evidence_dag=evidence_dag,
                template_guide=template_guide,
                exemplar_guidance=_ExemplarAnalyzerCls.format_for_prompt(_exemplar_analysis, "introduction"),
                content_brief=content_brief,
            )
            sections_results.append(intro_result)
            print(f"[MetaDataAgent] After introduction: {ref_pool.summary()}")

            if intro_result.status == "ok":
                generated_sections["introduction"] = intro_result.latex_content
                memory.update_section("introduction", intro_result.latex_content)
                memory.log("metadata", "phase1", "introduction_generated",
                           narrative=f"Writer completed the introduction section ({intro_result.word_count} words).",
                           word_count=intro_result.word_count)
                await emitter.section_content(
                    section_type="introduction", content=intro_result.latex_content,
                    word_count=intro_result.word_count, phase=Phase.INTRODUCTION,
                )
                if intro_plan:
                    intro_valid_keys = list(ref_pool.citable_keys("introduction"))
                    intro_budget_usage = self._reporting.collect_section_citation_budget_usage(
                        section_type="introduction", content=intro_result.latex_content,
                        section_plan=intro_plan, writer_valid_keys=intro_valid_keys,
                    )
                    self._reporting.upsert_section_budget_usage(citation_budget_usage, intro_budget_usage)
                contributions = extract_contributions_from_intro(intro_result.latex_content)
                if not contributions:
                    contributions = [f"We propose {metadata.title}", f"Novel approach: {metadata.method[:100]}..."]
            else:
                errors.append(f"Introduction generation failed: {intro_result.error}")
                return PaperGenerationResult(
                    status="error", paper_title=metadata.title,
                    sections=sections_results, errors=errors,
                    usage=usage_tracker.to_dict(),
                )

            if paper_plan and paper_plan.contributions:
                contributions = paper_plan.contributions
            memory.contributions = contributions

            # Phase 2: Body Sections
            print("[MetaDataAgent] Phase 2: Generating Body Sections...")
            update_usage_tracker_context(agent="WriterAgent", phase="body_sections")
            await emitter.phase_start(Phase.BODY_SECTIONS, "Generating body sections")
            body_section_types = paper_plan.get_body_section_types() if paper_plan else ["related_work", "method", "experiment", "result"]
            # Skip introduction — already generated in Phase 1 via _generate_introduction
            body_section_types = [s for s in body_section_types if s != "introduction"]
            for section_type in body_section_types:
                section_plan = paper_plan.get_section(section_type) if paper_plan else None
                section_figures = list(metadata.figures)
                section_tables = list(metadata.tables)
                update_usage_tracker_context(section=section_type)
                try:
                    result = await self._generate_body_section(
                        section_type=section_type, metadata=metadata,
                        intro_context=generated_sections.get("introduction", ""),
                        contributions=contributions, ref_pool=ref_pool,
                        section_plan=section_plan, figures=section_figures,
                        tables=section_tables, converted_tables=converted_tables,
                        code_context=code_context, research_context=research_context,
                        prompt_traces=prompt_traces, memory=memory, evidence_dag=evidence_dag,
                        emitter=emitter, template_guide=template_guide,
                        exemplar_guidance=_ExemplarAnalyzerCls.format_for_prompt(_exemplar_analysis, section_type),
                        content_brief=content_brief,
                    )
                except Exception as e:
                    result = SectionResult(section_type=section_type, status="error", error=str(e))

                sections_results.append(result)
                if result.status == "ok":
                    generated_sections[section_type] = result.latex_content
                    memory.update_section(section_type, result.latex_content)
                    memory.log("metadata", "phase2", f"{section_type}_generated",
                               narrative=f"Writer completed the {section_type} section ({result.word_count} words).",
                               word_count=result.word_count)
                    await emitter.section_content(
                        section_type=section_type, content=result.latex_content,
                        word_count=result.word_count, phase=Phase.BODY_SECTIONS,
                    )
                    if section_plan:
                        section_valid_keys = list(ref_pool.citable_keys(section_type))
                        section_budget_usage = self._reporting.collect_section_citation_budget_usage(
                            section_type=section_type, content=result.latex_content,
                            section_plan=section_plan, writer_valid_keys=section_valid_keys,
                        )
                        self._reporting.upsert_section_budget_usage(citation_budget_usage, section_budget_usage)
                else:
                    errors.append(f"{section_type} generation failed: {result.error}")

            # Phase 3: Synthesis Sections
            print("[MetaDataAgent] Phase 3: Generating Synthesis Sections...")
            update_usage_tracker_context(agent="WriterAgent", phase="synthesis")
            await emitter.phase_start(Phase.SYNTHESIS, "Generating synthesis sections (abstract, conclusion)")
            abstract_result = await self._generate_synthesis_section(
                section_type="abstract", paper_title=metadata.title,
                prior_sections=generated_sections, contributions=contributions,
                style_guide=effective_style_guide,
                section_plan=paper_plan.get_section("abstract") if paper_plan else None,
                prompt_traces=prompt_traces, memory=memory,
                template_guide=template_guide,
                exemplar_guidance=_ExemplarAnalyzerCls.format_for_prompt(_exemplar_analysis, "abstract"),
            )
            sections_results.insert(0, abstract_result)
            if abstract_result.status == "ok":
                generated_sections["abstract"] = abstract_result.latex_content
                memory.update_section("abstract", abstract_result.latex_content)
                await emitter.section_content(
                    section_type="abstract", content=abstract_result.latex_content,
                    word_count=abstract_result.word_count, phase=Phase.SYNTHESIS,
                )
            else:
                errors.append(f"Abstract generation failed: {abstract_result.error}")

            should_generate_conclusion = bool(paper_plan and paper_plan.get_section("conclusion") is not None)
            if should_generate_conclusion:
                conclusion_result = await self._generate_synthesis_section(
                    section_type="conclusion", paper_title=metadata.title,
                    prior_sections=generated_sections, contributions=contributions,
                    style_guide=effective_style_guide,
                    section_plan=paper_plan.get_section("conclusion") if paper_plan else None,
                    prompt_traces=prompt_traces, memory=memory,
                    template_guide=template_guide,
                    exemplar_guidance=_ExemplarAnalyzerCls.format_for_prompt(_exemplar_analysis, "conclusion"),
                )
                sections_results.append(conclusion_result)
                if conclusion_result.status == "ok":
                    generated_sections["conclusion"] = conclusion_result.latex_content
                    memory.update_section("conclusion", conclusion_result.latex_content)
                    await emitter.section_content(
                        section_type="conclusion", content=conclusion_result.latex_content,
                        word_count=conclusion_result.word_count, phase=Phase.SYNTHESIS,
                    )
                else:
                    errors.append(f"Conclusion generation failed: {conclusion_result.error}")

            # Reference Usage Validation
            self._validate_ref_usage(generated_sections, ref_pool)
            orchestration_canonical_bibtex = ref_pool.to_bibtex()

            # Review Orchestration
            update_usage_tracker_context(agent="ReviewerAgent", phase="review")
            if enable_review:
                await emitter.phase_start(Phase.REVIEW_LOOP, "Starting review loop")
            orchestration_result = await self._orchestrator._run_review_orchestration(
                generated_sections=generated_sections, sections_results=sections_results,
                metadata=metadata, parsed_refs=ref_pool.exportable_refs(),
                paper_plan=paper_plan, template_path=template_path,
                figures_source_dir=figures_source_dir, converted_tables=converted_tables,
                max_review_iterations=max_review_iterations, enable_review=enable_review,
                compile_pdf=compile_pdf, enable_vlm_review=enable_vlm_review,
                target_pages=target_pages, paper_dir=paper_dir,
                memory=memory, evidence_dag=evidence_dag, template_guide=template_guide,
                canonical_bibtex=orchestration_canonical_bibtex,
            )
            generated_sections = orchestration_result.generated_sections
            sections_results = orchestration_result.sections_results
            review_iterations = orchestration_result.review_iterations
            target_word_count = orchestration_result.target_word_count
            pdf_path = orchestration_result.final_pdf_path
            orchestration_errors = orchestration_result.errors
            if orchestration_errors:
                errors.extend(orchestration_errors)
            if orchestration_result.warnings:
                generation_warnings.extend(orchestration_result.warnings)
            if enable_review:
                await emitter.phase_complete(Phase.REVIEW_LOOP, f"Review completed ({review_iterations} iterations)")

            final_vlm_result_stale = False
            table_review_bundle: Dict[str, Any] = {
                "status": "not_run",
                "reviews": [],
                "paper_level_findings": [],
            }
            table_review_evolution: Dict[str, Any] = {
                "enabled": bool(getattr(self.tools_config, "table_critic_enabled", False)),
                "max_iterations": int(
                    getattr(self.tools_config, "table_critic_max_iterations", 2)
                ),
                "final_status": "not_run",
                "reason": "critic-gated table restructuring was not invoked",
                "iterations": [],
            }
            table_restructure_iterations: List[Dict[str, Any]] = []

            if paper_plan:
                generated_sections = self._ensure_figures_defined(
                    generated_sections,
                    paper_plan,
                    metadata.figures,
                    template_guide=template_guide,
                )
                generated_sections, figure_repair_errors = self._repair_hardcoded_figure_references(
                    generated_sections,
                    paper_plan,
                )
                generated_sections, float_marker_errors = repair_float_markers(
                    generated_sections,
                    paper_plan,
                )
                generated_sections, non_owner_figure_errors = repair_non_owner_figure_references(
                    generated_sections,
                    paper_plan,
                )
                figure_repair_errors.extend(float_marker_errors)
                figure_repair_errors.extend(non_owner_figure_errors)
                if figure_repair_errors:
                    errors.extend(figure_repair_errors)
                figure_contract_errors = validate_assigned_figure_labels_and_refs(
                    generated_sections,
                    paper_plan,
                    metadata.figures,
                )
                figure_contract_errors.extend(
                    validate_figure_layout_contract(
                        generated_sections,
                        paper_plan,
                        metadata.figures,
                        template_guide=template_guide,
                    )
                )
                if figure_contract_errors:
                    errors.extend(figure_contract_errors)
                table_contract_errors = validate_table_layout_contract(
                    generated_sections,
                    paper_plan,
                    metadata.tables,
                    template_guide=template_guide,
                )
                if table_contract_errors:
                    errors.extend(table_contract_errors)

            table_review_bundle = collect_table_layout_review_bundle(
                generated_sections,
                paper_plan=paper_plan,
                tables=metadata.tables,
            )
            table_restructure_result = await run_table_restructure_loop(
                client=self.client,
                model_name=self.model_name,
                generated_sections=generated_sections,
                converted_tables=converted_tables,
                table_review_bundle=table_review_bundle,
                enabled=bool(getattr(self.tools_config, "table_critic_enabled", False)),
                max_iterations=int(getattr(self.tools_config, "table_critic_max_iterations", 2)),
            )
            table_review_evolution = table_restructure_result.evolution
            table_restructure_iterations = table_restructure_result.iterations
            if table_restructure_result.approved_rewrite_count:
                generated_sections = table_restructure_result.generated_sections
                converted_tables = table_restructure_result.converted_tables
                pdf_path = None
                final_vlm_result_stale = True
                table_review_bundle = collect_table_layout_review_bundle(
                    generated_sections,
                    paper_plan=paper_plan,
                    tables=metadata.tables,
                )
                sync_sections_results_and_memory(
                    generated_sections=generated_sections,
                    sections_results=sections_results,
                    memory=memory,
                )

            figure_page_warnings = self._detect_contextless_figure_pages(
                pdf_path=pdf_path,
                latex_dir=str(Path(pdf_path).parent) if pdf_path else None,
                figure_ids=[fig.id for fig in (metadata.figures or []) if getattr(fig, "id", None)],
            )
            if figure_page_warnings:
                generation_warnings.extend(figure_page_warnings)

            citation_audit = self._citation_grounding.run(
                ref_pool=ref_pool,
                generated_sections=generated_sections,
                sections_results=sections_results,
                paper_plan=paper_plan,
                plan_review=plan_result.plan_review,
                plan_review_iterations=plan_result.plan_review_iterations,
                citation_budget_usage=citation_budget_usage,
                memory=memory,
                paper_dir=paper_dir,
            )
            citation_audit_payload = citation_audit.to_dict()
            citation_audit_markdown = citation_audit.to_markdown()
            if paper_dir:
                citation_audit_path = str(
                    paper_dir / "analysis" / "citations" / "citation_grounding_audit.json"
                )
            if citation_audit.unresolved_findings:
                citation_warnings.append(
                    f"Citation grounding audit has {len(citation_audit.unresolved_findings)} unresolved finding(s)."
                )

            parsed_refs = ref_pool.exportable_refs()
            canonical_references_bibtex = ref_pool.to_bibtex()

            if compile_pdf and paper_dir and not pdf_path:
                final_dir = paper_dir / f"iteration_{review_iterations:02d}_final"
                final_dir.mkdir(parents=True, exist_ok=True)
                figure_base_path = getattr(metadata, "materials_root", None) or os.getcwd()
                figure_paths = self._collect_figure_paths(metadata.figures, base_path=figure_base_path)
                final_pdf, _, final_errors, _ = await self._compile_pdf(
                    generated_sections=generated_sections,
                    template_path=template_path,
                    references=parsed_refs,
                    output_dir=final_dir,
                    paper_title=metadata.title,
                    figures_source_dir=figures_source_dir,
                    figure_paths=figure_paths,
                    converted_tables=converted_tables,
                    paper_plan=paper_plan,
                    figures=metadata.figures,
                    metadata_tables=metadata.tables,
                    template_guide=template_guide,
                    canonical_bibtex=canonical_references_bibtex,
                )
                sync_sections_results_and_memory(
                    generated_sections=generated_sections,
                    sections_results=sections_results,
                    memory=memory,
                )
                if final_errors:
                    errors.extend(final_errors)
                if final_pdf:
                    pdf_path = final_pdf
                citation_audit.compile_bib_snapshots.append(
                    {
                        "path": str(final_dir / "references.bib"),
                        "canonical": False,
                        "relationship": "compile_snapshot_of_root_references_bib",
                    }
                )
                citation_audit_payload = citation_audit.to_dict()
                citation_audit_markdown = citation_audit.to_markdown()

            if paper_plan:
                citation_budget_usage = self._reporting.rebuild_citation_budget_usage_from_final_sections(
                    paper_plan=paper_plan, generated_sections=generated_sections,
                    valid_citation_keys=ref_pool.valid_citation_keys,
                )

            # Assemble Paper
            update_usage_tracker_context(agent="MetaDataAgent", phase="assembly")
            print("[MetaDataAgent] Assembling paper...")
            latex_content = self._assemble_paper(
                title=metadata.title, sections=generated_sections,
                references=ref_pool.exportable_refs(),
                valid_citation_keys=ref_pool.valid_citation_keys,
                section_order=paper_plan.get_compile_section_order() if paper_plan else None,
                section_titles=paper_plan.get_section_titles() if paper_plan else None,
                venue_config=venue_config,
            )
            total_words = sum(r.word_count for r in sections_results if r.word_count)

            # Save output
            output_path = None
            if save_output and paper_dir:
                output_path = str(paper_dir)
                usage_report = usage_tracker.to_dict()
                self._artifacts.export_generation_core_artifacts(
                    paper_dir=paper_dir,
                    latex_content=latex_content,
                    references_bibtex=canonical_references_bibtex,
                    metadata=metadata.model_dump(),
                )
                self._artifacts.export_analysis_artifacts(
                    paper_dir=paper_dir,
                    research_context=research_context,
                    code_context=code_context,
                    code_summary_markdown=code_summary_markdown,
                    ref_pool_snapshot=ref_pool.to_dict(),
                    citation_budget_usage=citation_budget_usage,
                    paper_plan=paper_plan,
                    generated_sections=generated_sections,
                    citation_audit=citation_audit_payload,
                    citation_audit_markdown=citation_audit_markdown,
                )
                table_review_bundle = collect_table_layout_review_bundle(
                    generated_sections,
                    paper_plan=paper_plan,
                    tables=metadata.tables,
                )
                table_rendered_review_enabled = bool(
                    getattr(self.tools_config, "table_rendered_review_enabled", False)
                )
                final_pdf_table_review = {
                    "status": "not_run",
                    "pdf_path": pdf_path,
                    "reason": "final rendered table-specific VLM review was not enabled",
                    "all_issues": [],
                    "blocking_issues": [],
                    "warnings": [],
                    "issues": [],
                }
                if table_rendered_review_enabled:
                    existing_vlm_result = (
                        orchestration_result.final_vlm_result
                        or orchestration_result.last_vlm_result
                    ) if not final_vlm_result_stale else None
                    if existing_vlm_result:
                        final_pdf_table_review = _final_pdf_table_review_payload(
                            result=existing_vlm_result,
                            pdf_path=pdf_path,
                            source="vlm_review",
                            reason="reused final VLM layout review result",
                        )
                    elif not pdf_path:
                        final_pdf_table_review = {
                            "status": "not_run",
                            "pdf_path": None,
                            "reason": (
                                "no final PDF available for rendered table review"
                                if not final_vlm_result_stale
                                else "table rewrite invalidated cached VLM review and final PDF is unavailable"
                            ),
                            "all_issues": [],
                            "blocking_issues": [],
                            "warnings": [],
                            "issues": [],
                        }
                    elif self._vlm_reviewer is None:
                        final_pdf_table_review = {
                            "status": "skipped",
                            "pdf_path": pdf_path,
                            "reason": "VLM Review Agent not available",
                            "all_issues": [],
                            "blocking_issues": [],
                            "warnings": [],
                            "issues": [],
                        }
                    else:
                        rendered_vlm_result = await self._call_vlm_review(
                            pdf_path=pdf_path,
                            page_limit=target_pages or 8,
                            template_type=getattr(template_guide, "template_type", "ICML"),
                            sections_info={
                                r.section_type: {"word_count": r.word_count}
                                for r in sections_results
                            },
                            memory=memory,
                        )
                        if rendered_vlm_result:
                            final_pdf_table_review = _final_pdf_table_review_payload(
                                result=rendered_vlm_result,
                                pdf_path=pdf_path,
                                source="vlm_review",
                                reason="ran final rendered VLM layout review",
                            )
                        else:
                            final_pdf_table_review = {
                                "status": "failed",
                                "pdf_path": pdf_path,
                                "reason": "final rendered VLM layout review returned no result",
                                "all_issues": [],
                                "blocking_issues": [],
                                "warnings": [],
                                "issues": [],
                            }
                section_preview_docs = build_section_table_preview_documents(
                    generated_sections,
                    column_format=getattr(template_guide, "column_format", "single"),
                )
                section_preview_artifacts = {
                    section: {"tex": tex}
                    for section, tex in section_preview_docs.items()
                }
                if section_preview_docs:
                    preview_compile_dir = (
                        paper_dir / "analysis" / "tables" / "section_preview"
                    )
                    compile_results = compile_section_table_preview_documents(
                        section_preview_docs,
                        output_dir=str(preview_compile_dir),
                        max_passes=2,
                        timeout_seconds=60,
                    )
                    for section, result in compile_results.items():
                        section_preview_artifacts.setdefault(section, {})
                        section_preview_artifacts[section].update(
                            {
                                "tex_path": str(result.get("tex_path") or ""),
                                "pdf_path": str(result.get("pdf_path") or ""),
                                "compile_success": bool(result.get("success")),
                                "compile_errors": result.get("errors") or [],
                                "compile_warnings": result.get("warnings") or [],
                            }
                        )
                self._artifacts.export_table_artifacts(
                    paper_dir=paper_dir,
                    table_review=table_review_bundle,
                    table_review_evolution=table_review_evolution,
                    restructure_iterations=table_restructure_iterations,
                    section_preview_artifacts=section_preview_artifacts,
                    final_pdf_table_review={
                        **final_pdf_table_review,
                    },
                )
                self._artifacts.export_trace_artifacts(
                    paper_dir=paper_dir,
                    prompt_traces=prompt_traces,
                    usage_report=usage_report,
                    export_prompt_traces=bool(metadata.export_prompt_traces),
                )
                memory.log("metadata", "final", "paper_assembled",
                           narrative=f"Paper assembled successfully with {total_words} total words.",
                           total_words=total_words, status="assembled")
                memory.persist_all(paper_dir)
                self._artifacts.export_artifacts_manifest(
                    paper_dir,
                    paper_title=metadata.title,
                    errors=list(errors),
                    warnings=[*generation_warnings, *citation_warnings],
                    review_iterations=review_iterations,
                    pdf_path=pdf_path,
                    total_words=total_words,
                )

            status = "ok" if not errors else ("partial" if len(errors) < len(sections_results) else "error")
            result = PaperGenerationResult(
                status=status, paper_title=metadata.title,
                sections=sections_results, latex_content=latex_content,
                output_path=output_path, pdf_path=pdf_path,
                total_word_count=total_words, target_word_count=target_word_count,
                review_iterations=review_iterations, errors=errors,
                warnings=[*generation_warnings, *citation_warnings],
                citation_audit=citation_audit_payload,
                citation_audit_path=citation_audit_path,
                usage=usage_tracker.to_dict(),
            )
            await emitter.completed(
                status=status, total_words=total_words,
                review_iterations=review_iterations,
                sections_count=len([s for s in sections_results if s.status == "ok"]),
                pdf_path=pdf_path,
                paper_dir=str(paper_dir) if paper_dir else None,
            )
            return result

        except Exception as e:
            print(f"[MetaDataAgent] execute_generation error: {e}")
            await emitter.error(message=str(e), phase="execute_generation")
            return PaperGenerationResult(
                status="error", paper_title=metadata.title,
                sections=sections_results, errors=[str(e)],
                usage=usage_tracker.to_dict(),
            )
        finally:
            clear_usage_tracker_context()
            clear_llm_progress_context()

    # ------------------------------------------------------------------
    # generate_paper: backward-compatible wrapper
    # ------------------------------------------------------------------

    async def generate_paper(
        self,
        metadata: PaperMetaData,
        output_dir: Optional[str] = None,
        save_output: bool = True,
        compile_pdf: bool = True,
        template_path: Optional[str] = None,
        figures_source_dir: Optional[str] = None,
        target_pages: Optional[int] = None,
        enable_review: bool = True,
        max_review_iterations: int = 3,
        enable_planning: bool = True,
        enable_exemplar: bool = False,
        enable_vlm_review: bool = False,
        enable_user_feedback: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
        feedback_queue: Optional[asyncio.Queue] = None,
        feedback_timeout: float = 300.0,
        artifacts_prefix: str = "",
    ) -> PaperGenerationResult:
        """
        Generate complete paper from MetaData (backward-compatible wrapper).
        - **Description**:
            - Calls ``prepare_plan()`` then ``execute_generation()`` sequentially.
            - Preserves the original single-call interface used by
              ``/metadata/generate/stream`` and ``/metadata/generate``.
        """
        import time as _time
        _t0 = _time.monotonic()

        _gp_tracker = UsageTracker()
        set_usage_tracker_context(_gp_tracker, agent="PlannerAgent", phase="planning")

        plan_result = await self.prepare_plan(
            metadata=metadata,
            template_path=template_path,
            target_pages=target_pages,
            enable_planning=enable_planning,
            enable_exemplar=enable_exemplar,
            save_output=save_output,
            output_dir=output_dir,
            progress_callback=progress_callback,
            artifacts_prefix=artifacts_prefix,
        )

        if plan_result.errors and not plan_result.paper_plan:
            clear_usage_tracker_context()
            _gp_tracker.set_elapsed_time(round(_time.monotonic() - _t0, 2))
            return PaperGenerationResult(
                status="error",
                paper_title=metadata.title,
                errors=plan_result.errors,
                usage=_gp_tracker.to_dict(),
            )

        clear_usage_tracker_context()

        result = await self.execute_generation(
            plan_result=plan_result,
            enable_review=enable_review,
            max_review_iterations=max_review_iterations,
            compile_pdf=compile_pdf,
            enable_vlm_review=enable_vlm_review,
            enable_user_feedback=enable_user_feedback,
            progress_callback=progress_callback,
            feedback_queue=feedback_queue,
            feedback_timeout=feedback_timeout,
            save_output=save_output,
            output_dir=output_dir,
            figures_source_dir=figures_source_dir,
        )

        elapsed = round(_time.monotonic() - _t0, 2)
        merged_usage = self._merge_usage_reports(_gp_tracker.to_dict(), result.usage or {})
        merged_usage.setdefault("summary", {})["elapsed_seconds"] = elapsed
        result.usage = merged_usage
        return result

    async def generate_single_section(
        self,
        request: SectionGenerationRequest,
    ) -> SectionResult:
        """Generate a single section (for debugging or incremental generation)"""
        metadata = request.metadata
        ref_pool = ReferencePool(metadata.references)

        if request.section_type == "introduction":
            return await self._generate_introduction(metadata, ref_pool)
        elif request.section_type in SYNTHESIS_SECTIONS:
            prior = request.prior_sections or {}
            contributions = extract_contributions_from_intro(prior.get("introduction", ""))
            return await self._generate_synthesis_section(
                section_type=request.section_type,
                paper_title=metadata.title,
                prior_sections=prior,
                contributions=contributions,
                style_guide=self._effective_style_guide(metadata),
            )
        else:
            contributions = []
            if request.intro_context:
                contributions = extract_contributions_from_intro(request.intro_context)
            return await self._generate_body_section(
                section_type=request.section_type,
                metadata=metadata,
                intro_context=request.intro_context or "",
                contributions=contributions,
                ref_pool=ref_pool,
            )

    # =========================================================================
    # Phase 1: Introduction Generation
    # =========================================================================

    async def _generate_introduction(
        self,
        metadata: PaperMetaData,
        ref_pool: ReferencePool,
        section_plan: Optional[SectionPlan] = None,
        figures: Optional[List[FigureSpec]] = None,
        tables: Optional[List[TableSpec]] = None,
        code_context: Optional[Dict[str, Any]] = None,
        research_context: Optional[Dict[str, Any]] = None,
        prompt_traces: Optional[List[Dict[str, Any]]] = None,
        memory: Optional[SessionMemory] = None,
        evidence_dag: Optional[EvidenceDAG] = None,
        template_guide: Optional[TemplateWriterGuide] = None,
        exemplar_guidance: Optional[str] = None,
        content_brief: Optional[Dict[str, str]] = None,
        emitter: Optional[ProgressEmitter] = None,
    ) -> SectionResult:
        try:
            return await generate_introduction_section(
                metadata=metadata,
                ref_pool=ref_pool,
                section_plan=section_plan,
                figures=figures,
                tables=tables,
                code_context=code_context,
                research_context=research_context,
                prompt_traces=prompt_traces,
                memory=memory,
                evidence_dag=evidence_dag,
                template_guide=template_guide,
                exemplar_guidance=exemplar_guidance,
                emitter=emitter,
                tools_config=self.tools_config,
                retrieve_runtime_code_evidence_fn=self._retrieve_runtime_code_evidence,
                format_research_context_for_prompt_fn=self._format_research_context_for_prompt,
                get_active_skills_fn=self._get_active_skills,
                generate_section_decomposed_fn=self._generate_section_decomposed,
                content_brief=content_brief,
                effective_style_guide=self._effective_style_guide(metadata),
            )
        except Exception as e:
            return SectionResult(
                section_type="introduction",
                status="error",
                error=str(e),
            )

    # =========================================================================
    # Phase 2: Body Section Generation
    # =========================================================================

    async def _generate_body_section(
        self,
        section_type: str,
        metadata: PaperMetaData,
        intro_context: str,
        contributions: List[str],
        ref_pool: ReferencePool,
        section_plan: Optional[SectionPlan] = None,
        figures: Optional[List[FigureSpec]] = None,
        tables: Optional[List[TableSpec]] = None,
        converted_tables: Optional[Dict[str, str]] = None,
        code_context: Optional[Dict[str, Any]] = None,
        research_context: Optional[Dict[str, Any]] = None,
        prompt_traces: Optional[List[Dict[str, Any]]] = None,
        memory: Optional[SessionMemory] = None,
        evidence_dag: Optional[EvidenceDAG] = None,
        template_guide: Optional[TemplateWriterGuide] = None,
        emitter: Optional[ProgressEmitter] = None,
        exemplar_guidance: Optional[str] = None,
        content_brief: Optional[Dict[str, str]] = None,
    ) -> SectionResult:
        try:
            return await generate_body_section(
                section_type=section_type,
                metadata=metadata,
                intro_context=intro_context,
                contributions=contributions,
                ref_pool=ref_pool,
                section_plan=section_plan,
                figures=figures,
                tables=tables,
                converted_tables=converted_tables,
                code_context=code_context,
                research_context=research_context,
                prompt_traces=prompt_traces,
                memory=memory,
                evidence_dag=evidence_dag,
                template_guide=template_guide,
                emitter=emitter,
                exemplar_guidance=exemplar_guidance,
                tools_config=self.tools_config,
                retrieve_runtime_code_evidence_fn=self._retrieve_runtime_code_evidence,
                format_research_context_for_prompt_fn=self._format_research_context_for_prompt,
                get_active_skills_fn=self._get_active_skills,
                generate_section_decomposed_fn=self._generate_section_decomposed,
                content_brief=content_brief,
                effective_style_guide=self._effective_style_guide(metadata),
            )
        except Exception as e:
            return SectionResult(
                section_type=section_type,
                status="error",
                error=str(e),
            )

    # =========================================================================
    # Decomposed (claim-level) generation helper
    # =========================================================================

    async def _run_local_mini_review(
        self,
        *,
        section_type: str,
        paragraph_index: int,
        paragraph_plan: ParagraphPlan,
        raw_latex: str,
        final_latex: str,
        figs_to_ref: List[str],
        tables_to_ref: List[str],
        attempt: int,
        max_attempts: int,
        memory: Optional[SessionMemory] = None,
    ) -> Dict[str, Any]:
        return await run_local_mini_review(
            section_type=section_type,
            paragraph_index=paragraph_index,
            paragraph_plan=paragraph_plan,
            raw_latex=raw_latex,
            final_latex=final_latex,
            figs_to_ref=figs_to_ref,
            tables_to_ref=tables_to_ref,
            attempt=attempt,
            max_attempts=max_attempts,
            memory=memory,
            validate_required_figure_usages_fn=self._validate_required_figure_usages,
            rewrite_content_fn=self._writer.rewrite_content,
        )

    async def _generate_section_decomposed(
        self,
        section_type: str,
        section_plan: SectionPlan,
        writer_valid_keys: List[str],
        section_title_str: str = "",
        figures: Optional[List[FigureSpec]] = None,
        evidence_dag: Optional[EvidenceDAG] = None,
        memory: Optional[SessionMemory] = None,
        emitter: Optional[ProgressEmitter] = None,
        template_guide: Optional[TemplateWriterGuide] = None,
        exemplar_guidance: Optional[str] = None,
    ) -> str:
        """
        Generate a section paragraph-by-paragraph via the 3-stage pipeline.
        - **Description**:
            - Iterates over ``section_plan._all_paragraphs()`` (flat + subsection).
            - For each paragraph runs: Stage 1 core content -> Stage 2 citation
              injection -> Stage 3 float ref injection.
            - When ``claim_id`` is present and ``evidence_dag`` is available,
              gathers evidence and runs ``ClaimVerifier`` with retry/degrade.
            - When ``claim_id`` is empty, runs the 3-stage pipeline without
              evidence context and skips claim verification.

        - **Args**:
            - ``section_type`` (str): Section identifier.
            - ``section_plan`` (SectionPlan): Plan with paragraph-level structure.
            - ``writer_valid_keys`` (List[str]): Superset of allowed citation keys.
            - ``section_title_str`` (str): Display title for prompt context.
            - ``evidence_dag`` (EvidenceDAG, optional): The evidence graph.
            - ``memory`` (SessionMemory, optional): Shared memory.
            - ``emitter`` (ProgressEmitter, optional): Emits paragraph-level SSE events.

        - **Returns**:
            - ``str``: Assembled LaTeX content for the entire section.
        """
        from ...generation.claim_verifier import (
            ClaimVerifier,
            MAX_CLAIM_RETRIES,
            TEMPLATE_FALLBACK_ENABLED,
        )
        from ...generation.template_slots import ParagraphTemplate
        from ...generation.template_slots import build_template_fill_prompt

        return await run_decomposed_section_generation(
            section_type=section_type,
            section_plan=section_plan,
            writer_valid_keys=writer_valid_keys,
            section_title_str=section_title_str,
            figures=figures,
            evidence_dag=evidence_dag,
            memory=memory,
            emitter=emitter,
            writer=self._writer,
            ensure_paragraph_figure_usages_fn=self._ensure_paragraph_figure_usages,
            build_subsection_maps_fn=build_subsection_maps,
            prepare_paragraph_generation_inputs_fn=prepare_paragraph_generation_inputs,
            build_assigned_refs_for_prompt_fn=build_assigned_refs_for_prompt,
            compile_core_prompt_fn=compile_core_prompt,
            compile_citation_prompt_fn=compile_citation_prompt,
            apply_citation_edits_fn=apply_citation_edits,
            inject_float_refs_fn=inject_float_refs,
            run_local_mini_review_fn=self._run_local_mini_review,
            handle_local_review_result_fn=handle_local_review_result,
            verify_claim_and_emit_fn=verify_claim_and_emit,
            record_claim_verification_failure_fn=record_claim_verification_failure,
            run_template_fallback_fn=run_template_fallback,
            claim_verifier_cls=ClaimVerifier,
            max_claim_retries=MAX_CLAIM_RETRIES,
            template_fallback_enabled=TEMPLATE_FALLBACK_ENABLED,
            paragraph_template_cls=ParagraphTemplate,
            build_template_fill_prompt_fn=build_template_fill_prompt,
        )

    # =========================================================================
    # Phase 3: Synthesis Section Generation
    # =========================================================================

    async def _generate_synthesis_section(
        self,
        section_type: str,
        paper_title: str,
        prior_sections: Dict[str, str],
        contributions: List[str],
        style_guide: Optional[str] = None,
        section_plan: Optional[SectionPlan] = None,
        prompt_traces: Optional[List[Dict[str, Any]]] = None,
        memory: Optional[SessionMemory] = None,
        template_guide: Optional[TemplateWriterGuide] = None,
        exemplar_guidance: Optional[str] = None,
    ) -> SectionResult:
        """Generate synthesis section (Abstract or Conclusion) via WriterAgent."""
        try:
            return await generate_synthesis_section(
                section_type=section_type,
                paper_title=paper_title,
                prior_sections=prior_sections,
                contributions=contributions,
                style_guide=style_guide,
                section_plan=section_plan,
                prompt_traces=prompt_traces,
                memory=memory,
                template_guide=template_guide,
                exemplar_guidance=exemplar_guidance,
                writer=self._writer,
                get_active_skills_fn=self._get_active_skills,
            )
        except Exception as e:
            return SectionResult(
                section_type=section_type,
                status="error",
                error=str(e),
            )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _enforce_reference_coverage(
        self,
        generated_sections: Dict[str, str],
        sections_results: List[SectionResult],
        paper_plan: Optional[PaperPlan],
        metadata: PaperMetaData,
        valid_ref_keys: Set[str],
        memory: Optional[SessionMemory] = None,
        max_sections_to_revise: int = 2,
    ) -> Set[str]:
        """Delegation stub — see orchestrator.py."""
        return await self._orchestrator._enforce_reference_coverage(
            generated_sections=generated_sections,
            sections_results=sections_results,
            paper_plan=paper_plan,
            metadata=metadata,
            valid_ref_keys=valid_ref_keys,
            memory=memory,
            max_sections_to_revise=max_sections_to_revise,
        )

    def _assemble_paper(
        self,
        title: str,
        sections: Dict[str, str],
        references: List[Dict[str, Any]],
        valid_citation_keys: set = None,
        section_order: Optional[List[str]] = None,
        section_titles: Optional[Dict[str, str]] = None,
        venue_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Assemble complete LaTeX document with final citation validation"""
        if valid_citation_keys is None:
            valid_citation_keys = self._extract_valid_citation_keys(references)
        return assemble_paper(
            title=title,
            sections=sections,
            references=references,
            valid_citation_keys=valid_citation_keys,
            escape_latex_fn=self._escape_latex,
            fix_latex_references_fn=self._fix_latex_references,
            validate_and_fix_citations_fn=self._validate_and_fix_citations,
            section_order=section_order,
            section_titles=section_titles,
            venue_config=venue_config,
        )

    # =========================================================================
    # Pre-Generation Search Judgment (Phase A)
    # =========================================================================

    async def _judge_search_need(
        self,
        section_type: str,
        section_title: str,
        paper_title: str,
        key_points: List[str],
        ref_pool: ReferencePool,
    ) -> Dict[str, Any]:
        """Delegation stub — see orchestrator.py."""
        return await self._orchestrator._judge_search_need(
            section_type=section_type,
            section_title=section_title,
            paper_title=paper_title,
            key_points=key_points,
            ref_pool=ref_pool,
        )

    async def _execute_pre_searches(
        self,
        queries: List[str],
        ref_pool: ReferencePool,
    ) -> int:
        """Delegation stub — see orchestrator.py."""
        return await self._orchestrator._execute_pre_searches(
            queries=queries,
            ref_pool=ref_pool,
        )

    # =========================================================================
    # Phase 4: PDF Compilation
    # =========================================================================

    async def _compile_pdf(
        self,
        generated_sections: Dict[str, str],
        template_path: Optional[str],
        references: List[Dict[str, Any]],
        output_dir: Path,
        paper_title: str,
        figures_source_dir: Optional[str] = None,
        figure_paths: Optional[Dict[str, str]] = None,
        converted_tables: Optional[Dict[str, str]] = None,
        paper_plan: Optional[PaperPlan] = None,
        figures: Optional[List[FigureSpec]] = None,
        metadata_tables: Optional[List[TableSpec]] = None,
        template_guide: Optional[TemplateWriterGuide] = None,
        canonical_bibtex: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str], List[str], Dict[str, List[str]]]:
        """
        Compile PDF using Typesetter Agent (multi-file mode).
        - **Description**:
            - Passes sections as a dict to the TypesetterAgent, which writes each
              section to its own .tex file and uses \\input{} in main.tex
            - This enables precise error-to-section mapping from LaTeX logs

        - **Args**:
            - `generated_sections` (Dict[str, str]): Section contents
            - `template_path` (Optional[str]): Path to .zip template file
            - `references` (List[Dict[str, Any]]): Parsed reference list
            - `output_dir` (Path): Output directory
            - `paper_title` (str): Paper title
            - `figures_source_dir` (Optional[str]): Directory with figure files (legacy)
            - `figure_paths` (Optional[Dict[str, str]]): figure_id -> file_path
            - `converted_tables` (Optional[Dict[str, str]]): table_id -> LaTeX table code
            - `paper_plan` (Optional[PaperPlan]): Paper plan with figure/table assignments
            - `figures` (Optional[List[FigureSpec]]): Figure specifications
            - `metadata_tables` (Optional[List[TableSpec]]): Table specifications

        - **Returns**:
            - Tuple of (pdf_path, latex_path, compile_errors, section_errors)
            - On success: (pdf_path, latex_path, [], {})
            - On failure: (None, None, [error1, ...], {"section_type": [errors]})
        """
        print(f"[MetaDataAgent] Phase 4: Compiling PDF with template: {template_path}")
        if not (paper_title or "").strip():
            return None, None, ["missing_or_empty_paper_title"], {}

        try:
            canonical_sections = generated_sections
            # Dynamic: read section order and titles from the plan
            if paper_plan:
                section_order = paper_plan.get_compile_section_order()
                section_titles = paper_plan.get_section_titles()
            else:
                section_order = ["introduction", "related_work", "method", "experiment", "result", "conclusion"]
                section_titles = {
                    "introduction": "Introduction",
                    "related_work": "Related Work",
                    "method": "Methodology",
                    "experiment": "Experiments",
                    "result": "Results",
                    "conclusion": "Conclusion",
                }
            # Include any generated sections not in plan (e.g. appendix from review loop)
            for st in generated_sections:
                if st != "abstract" and st not in section_order:
                    section_order.append(st)
                if st not in section_titles:
                    section_titles[st] = st.replace("_", " ").title()
            detected_column_format = "single"
            if template_guide and template_guide.column_format:
                detected_column_format = template_guide.column_format
            elif template_path:
                try:
                    tg = TemplateAnalyzer.analyze_zip(template_path)
                    detected_column_format = tg.column_format or "single"
                except Exception:
                    pass
            if paper_plan and figures:
                generated_sections, figure_repair_errors = self._repair_hardcoded_figure_references(
                    generated_sections,
                    paper_plan,
                )
                generated_sections, float_marker_errors = repair_float_markers(
                    generated_sections,
                    paper_plan,
                )
                generated_sections, non_owner_figure_errors = repair_non_owner_figure_references(
                    generated_sections,
                    paper_plan,
                )
                figure_repair_errors.extend(float_marker_errors)
                figure_repair_errors.extend(non_owner_figure_errors)
                if figure_repair_errors:
                    save_compile_error_log(output_dir, figure_repair_errors)
                    return None, None, figure_repair_errors, {}
                figure_assignments: Dict[str, str] = {}
                for sec in paper_plan.sections:
                    for fdef in getattr(sec, "figures", []) or []:
                        label = getattr(fdef, "figure_id", None)
                        if label:
                            figure_assignments[label] = sec.section_type
                if figure_assignments:
                    generated_sections = self._enforce_figure_placement(
                        generated_sections,
                        figure_assignments,
                    )
                # Ensure assigned floats exist before cross-section \ref{} cleanup.
                # Otherwise planned refs look undefined and get stripped before
                # direct injection can use them as placement anchors.
                generated_sections = self._ensure_figures_defined(
                    generated_sections=generated_sections,
                    paper_plan=paper_plan,
                    figures=figures,
                    template_guide=template_guide,
                    column_format=detected_column_format,
                )

            # Enforce table placement according to planner assignments
            if paper_plan:
                table_assignments: Dict[str, str] = {}
                for sec in paper_plan.sections:
                    if sec.tables:
                        for tdef in sec.tables:
                            label = getattr(tdef, "label", None) or getattr(tdef, "table_id", None)
                            if label:
                                table_assignments[label] = sec.section_type
                if table_assignments:
                    generated_sections = self._enforce_table_placement(
                        generated_sections, table_assignments,
                    )

            # Ensure all assigned tables have their environments created
            if paper_plan and metadata_tables:
                generated_sections = self._ensure_tables_defined(
                    generated_sections=generated_sections,
                    paper_plan=paper_plan,
                    tables=metadata_tables,
                    converted_tables=converted_tables,
                )

            generated_sections = self._normalize_compile_sections(
                generated_sections=generated_sections,
                references=references,
                section_order=section_order,
                strip_code_path_references_fn=self._strip_code_path_references,
                fix_latex_references_fn=self._fix_latex_references,
                normalize_float_placement_fn=self._normalize_float_placement,
                validate_and_fix_citations_fn=self._validate_and_fix_citations,
                deduplicate_figure_environments_fn=self._deduplicate_figure_environments,
            )
            figure_ids = self._collect_typesetter_figure_ids(
                generated_sections=generated_sections,
                figures=figures,
                figure_paths=figure_paths,
            )

            from ..typesetter_agent.models import TemplateConfig
            ts_template_config = TemplateConfig(
                paper_title=paper_title,
                paper_authors="EasyPaper",
                column_format=detected_column_format,
            )

            if paper_plan and figures:
                figure_layout_errors = validate_figure_layout_contract(
                    generated_sections,
                    paper_plan,
                    figures,
                    template_guide=template_guide,
                    column_format=detected_column_format,
                )
                if figure_layout_errors:
                    save_compile_error_log(output_dir, figure_layout_errors)
                    return None, None, figure_layout_errors, {}

            from ..shared.table_converter import (
                add_adjustbox_safety,
                rebalance_adjacent_table_star_floats,
                smart_promote_wide_tables,
            )
            # Promote wide tables to table* only in double-column templates
            if detected_column_format == "double":
                for sec_type in list(generated_sections.keys()):
                    generated_sections[sec_type] = smart_promote_wide_tables(
                        generated_sections[sec_type]
                    )
                    generated_sections[sec_type] = rebalance_adjacent_table_star_floats(
                        generated_sections[sec_type]
                    )
            # Always apply adjustbox safety to prevent overflow in any layout
            for sec_type in list(generated_sections.keys()):
                generated_sections[sec_type] = add_adjustbox_safety(
                    generated_sections[sec_type]
                )
            canonical_sections.clear()
            canonical_sections.update(generated_sections)

            payload = self._build_typesetter_payload(
                generated_sections=generated_sections,
                references=references,
                paper_title=paper_title,
                output_dir=output_dir,
                template_path=template_path,
                figures_source_dir=figures_source_dir,
                figure_paths=figure_paths,
                converted_tables=converted_tables,
                figure_ids=figure_ids,
                section_order=section_order,
                section_titles=section_titles,
                detected_column_format=detected_column_format,
                canonical_bibtex=canonical_bibtex,
            )

            # Prefer in-process peer TypesetterAgent (SDK mode); fall back to HTTP.
            if self._typesetter is not None:
                print("[MetaDataAgent] Using in-process Typesetter Agent")
                ts_state = await self._typesetter.run(
                    sections=payload["sections"],
                    section_order=payload["section_order"],
                    section_titles=payload["section_titles"],
                    template_path=payload["template_path"],
                    template_config=ts_template_config,
                    references=payload["references"],
                    canonical_bibtex=payload.get("canonical_bibtex"),
                    figure_ids=payload["figure_ids"],
                    output_dir=payload["output_dir"],
                    figures_source_dir=payload["figures_source_dir"],
                    figure_paths=payload["figure_paths"],
                    converted_tables=payload["converted_tables"],
                )
                parsed = self._parse_typesetter_result(ts_state, output_dir)
                if canonical_bibtex and parsed[1]:
                    Path(parsed[1], "references.bib").write_text(canonical_bibtex, encoding="utf-8")
                if parsed[1]:
                    from ..typesetter_agent.typesetter_helpers import validate_resolved_figure_includes

                    include_errors = validate_resolved_figure_includes(parsed[1], figure_paths or {})
                    if include_errors:
                        return parsed[0], parsed[1], [*parsed[2], *include_errors], parsed[3]
                return parsed

            # HTTP fallback (server mode — TypesetterAgent running as a separate service)
            parsed = await post_typesetter_compile(
                payload=payload,
                request_id=str(uuid.uuid4()),
            )
            if canonical_bibtex and parsed[1]:
                Path(parsed[1], "references.bib").write_text(canonical_bibtex, encoding="utf-8")
            if parsed[1]:
                from ..typesetter_agent.typesetter_helpers import validate_resolved_figure_includes

                include_errors = validate_resolved_figure_includes(parsed[1], figure_paths or {})
                if include_errors:
                    return parsed[0], parsed[1], [*parsed[2], *include_errors], parsed[3]
            return parsed

        except httpx.ConnectError:
            print("[MetaDataAgent] Error: Could not connect to Typesetter Agent")
            self._save_compile_error_log(output_dir, ["Could not connect to Typesetter Agent"])
            return None, None, ["Could not connect to Typesetter Agent"], {}
        except Exception as e:
            print(f"[MetaDataAgent] PDF compilation error: {e}")
            self._save_compile_error_log(output_dir, [str(e)])
            return None, None, [str(e)], {}

    # =========================================================================
    # Phase 5: VLM Review
    # =========================================================================

    async def _call_vlm_review(
        self,
        pdf_path: str,
        page_limit: int = 8,
        template_type: str = "ICML",
        sections_info: Optional[Dict[str, Any]] = None,
        memory: Optional[SessionMemory] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Call VLM Review Agent directly (no HTTP) to check the PDF.
        - **Description**:
            - Builds a VLMReviewRequest and calls self._vlm_reviewer.review().
            - Memory context is injected automatically inside review().

        - **Args**:
            - `pdf_path` (str): Path to compiled PDF
            - `page_limit` (int): Maximum allowed pages
            - `template_type` (str): Template type for context
            - `sections_info` (Dict, optional): Section word counts
            - `memory` (SessionMemory, optional): Shared session memory

        - **Returns**:
            - VLM review result dict or None on failure
        """
        if self._vlm_reviewer is None:
            print("[MetaDataAgent] VLM Review Agent not available, skipping")
            return None
        try:
            from ..vlm_review_agent.models import VLMReviewRequest

            request = VLMReviewRequest(
                pdf_path=pdf_path,
                page_limit=page_limit,
                template_type=template_type,
                check_overflow=True,
                check_underfill=True,
                check_layout=True,
                sections_info=sections_info or {},
            )

            result = await self._vlm_reviewer.review(request, memory=memory)
            return result.model_dump()

        except Exception as e:
            print(f"[MetaDataAgent] VLM Review error: {e}")
            return None
