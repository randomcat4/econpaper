"""
Planner Agent
- **Description**:
    - Creates detailed paper plans before generation
    - Paragraph-level planning with VLM-informed figure/table placement
    - Outputs PaperPlan to guide Writers and Reviewers
"""
import json
import logging
import re
import random
from typing import TYPE_CHECKING, List, Dict, Any, Optional

from ..base import BaseAgent
from ..shared.llm_client import LLMClient
from ..shared.reference_assignment import claim_matrix_refs_for_section
from ...config.schema import ModelConfig
from .models import (
    PaperPlan,
    SectionPlan,
    SubSectionPlan,
    PlanRequest,
    ParagraphPlan,
    FigurePlacement,
    TablePlacement,
    PaperType,
    NarrativeStyle,
    PlanReviewIssue,
    PlanReviewIteration,
    PlanReviewSeverity,
    PlanReviewSummary,
    SentencePlan,
    SentenceRole,
    DEFAULT_EMPIRICAL_SECTIONS,
    WORDS_PER_SENTENCE,
    calculate_total_words,
    estimate_target_paragraphs,
)

if TYPE_CHECKING:
    from fastapi import APIRouter


logger = logging.getLogger("uvicorn.error")
from .prompt_contracts import (
    ELEMENT_ASSIGNMENT_SYSTEM,
    STEP1_STRUCTURE_SYSTEM,
    STEP1_STRUCTURE_USER,
    STEP2_CITATION_SYSTEM,
    STEP2_CITATION_USER,
    STEP6_PLAN_CRITIC_SYSTEM,
    STEP6_PLAN_CRITIC_USER,
    STEP7_PLAN_OPTIMIZER_SYSTEM,
    STEP7_PLAN_OPTIMIZER_USER,
)
from .planner_utils import (
    has_intro_contribution_summary_signal,
    normalize_section_type_name,
    paper_plan_to_json,
    safe_load_json,
)
from .plan_review_rules import (
    classify_figure_semantics,
    classify_intro_table_semantics,
    deterministic_plan_review_issues,
    is_advisory_plan_issue,
    is_intro_like_section,
    is_method_like_section,
    is_related_work_like_section,
)
from .planner_context import (
    format_code_assets_for_planning,
    format_research_context_for_planning,
    gather_plan_candidates,
)
from .planner_elements import (
    assign_figures_to_sections,
    build_assignment_prompt,
    build_figure_placements,
    build_table_placements,
    format_figure_info,
    format_section_figure_info,
    format_table_info,
    parse_element_assignment,
    should_be_wide_figure,
    should_be_wide_table,
)
from .planner_fact_lock import (
    CanonicalFactLock,
    apply_canonical_fact_lock,
    build_canonical_fact_lock,
)
from .planner_citations import (
    distribute_citations_topdown,
    estimate_total_citations,
    infer_section_citation_budget,
    rank_references_for_section,
)
from .planner_defaults import (
    create_default_plan,
    extract_reference_keys,
    get_default_sources,
    get_dependencies,
    get_section_title,
)
from .planner_paragraphs import (
    coerce_bool,
    expand_paragraph_plan,
    generate_default_paragraphs,
    generate_sentence_plans,
    normalize_string_list,
)
from .planner_discovery import (
    assign_papers_to_sections,
    build_context_fallback_payload,
    filter_papers_by_relevance,
    generate_research_context,
    generate_search_queries,
    score_papers_by_relevance,
)
from .planner_query_policy import build_seed_queries
from .planner_sections import (
    decide_section_structure,
    enforce_required_sections,
    enforce_section_structure_contracts,
    normalize_constraints_required_sections,
    parse_paragraph_plans,
    plan_flat_paragraphs,
    plan_subsection_paragraphs,
    collapse_singleton_subsections,
    sanitize_conclusion_like_subsections,
    split_into_subsections,
)
from .planner_references import (
    UTILITY_LITERATURE_TRIGGERS,
    assign_references as assign_references_helper,
    discover_landscape_references as discover_landscape_references_helper,
    discover_references as discover_references_helper,
    discover_utility_references as discover_utility_references_helper,
)
from .planner_build import (
    analyze_figures,
    analyze_tables,
    build_paper_plan,
    enforce_full_paper_plan_invariant,
    format_content_brief_block,
    format_venue_required_sections_block,
    normalize_full_paper_section_items,
)


# =========================================================================
# Planner Agent
# =========================================================================

class PlannerAgent(BaseAgent):
    """
    Planner Agent for paper planning.
    - **Description**:
        - Creates comprehensive paragraph-level plans
        - Optionally uses VLM for intelligent figure/table analysis
        - Directly encapsulates all planning logic (no Strategy pattern)
    """

    def __init__(
        self,
        config: ModelConfig,
        vlm_service: Optional[Any] = None,
    ):
        """
        Initialize the Planner Agent.

        - **Args**:
            - `config` (ModelConfig): LLM configuration
            - `vlm_service` (VLMService, optional): Shared VLM service for figure analysis
        """
        self.config = config
        self.model_name = config.model_name
        self.client = LLMClient(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.vlm_service = vlm_service
        self._last_plan: Optional[PaperPlan] = None
        self._last_plan_review_summary: Optional[PlanReviewSummary] = None
        self._last_plan_evolution: Optional[Dict[str, Any]] = None
        self.enable_plan_review: bool = True
        self.plan_review_max_iterations: int = 2
        self._router = None

        logger.info("PlannerAgent initialized (vlm=%s)", vlm_service is not None)

    @property
    def name(self) -> str:
        return "planner"

    @property
    def description(self) -> str:
        return "Creates detailed paragraph-level paper plans"

    @property
    def router(self) -> "APIRouter":
        if self._router is None:
            self._router = self._create_router()
        return self._router

    @property
    def endpoints_info(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/agent/planner/plan",
                "method": "POST",
                "description": "Create a paper plan from metadata",
            },
            {
                "path": "/agent/planner/health",
                "method": "GET",
                "description": "Health check",
            },
        ]

    def _create_router(self) -> "APIRouter":
        from .router import create_planner_router
        return create_planner_router(self)

    def get_last_plan_review_summary(self) -> Optional[PlanReviewSummary]:
        """
        Return the latest plan-review summary.
        - **Description**:
            - Exposes the reviewer trace for outer orchestration layers.

        - **Returns**:
            - `PlanReviewSummary` or None: Most recent review summary.
        """
        return self._last_plan_review_summary

    def get_last_plan_evolution(self) -> Optional[Dict[str, Any]]:
        """
        Return the latest planner-owned plan-evolution trace.
        - **Returns**:
            - `dict` or None: Review snapshots for artifact export.
        """
        return self._last_plan_evolution

    @staticmethod
    def _build_table_provenance(tables: Optional[List[Any]]) -> Dict[str, Any]:
        """
        Build side-context table metadata keyed by table id for plan review.
        - **Description**:
            - Keeps review semantics out of the paper-plan schema.
        """
        provenance: Dict[str, Any] = {}
        for table in tables or []:
            table_id = str(getattr(table, "id", "") or "")
            if not table_id and isinstance(table, dict):
                table_id = str(table.get("id", "") or "")
            if not table_id:
                continue
            if hasattr(table, "model_dump"):
                provenance[table_id] = table.model_dump()
            elif isinstance(table, dict):
                provenance[table_id] = dict(table)
            else:
                provenance[table_id] = {
                    key: getattr(table, key, "")
                    for key in ("id", "caption", "description", "content", "section")
                    if hasattr(table, key)
                }
        return provenance

    @staticmethod
    def _build_figure_provenance(figures: Optional[List[Any]]) -> Dict[str, Any]:
        """Build side-context figure metadata keyed by figure id."""
        provenance: Dict[str, Any] = {}
        for figure in figures or []:
            figure_id = str(getattr(figure, "id", "") or "")
            if not figure_id and isinstance(figure, dict):
                figure_id = str(figure.get("id", "") or "")
            if not figure_id:
                continue
            if hasattr(figure, "model_dump"):
                provenance[figure_id] = figure.model_dump()
            elif isinstance(figure, dict):
                provenance[figure_id] = dict(figure)
            else:
                provenance[figure_id] = {
                    key: getattr(figure, key, "")
                    for key in (
                        "id",
                        "caption",
                        "description",
                        "section",
                        "semantic_role",
                        "supplementation_rationale",
                        "target_type",
                        "generated_by",
                    )
                    if hasattr(figure, key)
                }
        return provenance

    @staticmethod
    def _section_base_for_table_remap(section_type: str) -> str:
        """
        Normalize a section type for result-table remap decisions.

        This reuses the shared section normalizer and layers duplicate-section
        suffix stripping on top so names such as ``results_2`` map to
        ``result``.
        """
        normalized = normalize_section_type_name(section_type)
        base = re.sub(r"_\d+$", "", normalized)
        return normalize_section_type_name(base)

    @classmethod
    def _is_excluded_table_remap_section(cls, section_type: str) -> bool:
        base = cls._section_base_for_table_remap(section_type)
        return (
            base in {"abstract", "conclusion", "related_work"}
            or is_intro_like_section(section_type)
            or is_intro_like_section(base)
        )

    @classmethod
    def _find_result_table_destination(
        cls,
        paper_plan: PaperPlan,
        current_section_type: str,
    ) -> Optional[SectionPlan]:
        candidates = [
            section for section in paper_plan.sections
            if section.section_type != current_section_type
            and not cls._is_excluded_table_remap_section(section.section_type)
        ]
        priority = ("result", "experiment", "evaluation", "analysis", "method")
        for base in priority:
            for section in candidates:
                if cls._section_base_for_table_remap(section.section_type) == base:
                    return section
        return candidates[0] if candidates else None

    def _table_semantics(
        self,
        table_id: str,
        placement: Optional[Any],
        table_info: Optional[Any],
        table_provenance: Optional[Dict[str, Any]],
        table_analyses: Optional[Dict[str, Any]],
    ) -> str:
        analyses = table_analyses or {}
        return classify_intro_table_semantics(
            table_id,
            placement=placement,
            table_provenance=table_provenance,
            table_info=table_info,
            table_analysis=analyses.get(table_id),
        )

    def _figure_semantics(
        self,
        figure_id: str,
        placement: Optional[Any],
        figure_info: Optional[Any],
        figure_provenance: Optional[Dict[str, Any]],
        figure_analyses: Optional[Dict[str, Any]],
    ) -> str:
        analyses = figure_analyses or {}
        return classify_figure_semantics(
            figure_id,
            placement=placement,
            figure_provenance=figure_provenance,
            figure_info=figure_info,
            figure_analysis=analyses.get(figure_id),
        )

    @classmethod
    def _is_excluded_result_figure_section(cls, section_type: str) -> bool:
        base = cls._section_base_for_table_remap(section_type)
        return (
            base in {"abstract", "conclusion"}
            or is_intro_like_section(section_type)
            or is_related_work_like_section(section_type)
            or is_method_like_section(section_type)
        )

    @classmethod
    def _find_result_figure_destination(
        cls,
        paper_plan: PaperPlan,
        current_section_type: str,
    ) -> Optional[SectionPlan]:
        candidates = [
            section for section in paper_plan.sections
            if section.section_type != current_section_type
            and not cls._is_excluded_result_figure_section(section.section_type)
        ]
        priority = ("result", "results", "evaluation", "experiment", "analysis", "discussion")
        for base in priority:
            for section in candidates:
                if cls._section_base_for_table_remap(section.section_type) == base:
                    return section
        return candidates[0] if candidates else None

    def _sanitize_misplaced_result_figures(
        self,
        paper_plan: PaperPlan,
        figure_infos: Dict[str, Any],
        figure_provenance: Dict[str, Any],
        figure_analyses: Optional[Dict[str, Any]],
    ) -> None:
        """Move or drop pre-populated result-like figures from early sections."""
        moves: List[tuple[SectionPlan, Optional[SectionPlan], FigurePlacement]] = []
        for section in paper_plan.sections:
            if not self._is_excluded_result_figure_section(section.section_type):
                continue
            for placement in list(section.figures):
                figure_id = placement.figure_id
                classification = self._figure_semantics(
                    figure_id,
                    placement,
                    figure_infos.get(figure_id),
                    figure_provenance,
                    figure_analyses,
                )
                if classification != "result_like":
                    continue
                target = self._find_result_figure_destination(
                    paper_plan,
                    section.section_type,
                )
                if not target:
                    logger.warning(
                        "planner.misplaced_result_figure_definition_dropped figure_id=%s",
                        figure_id,
                    )
                moves.append((section, target, placement))

        for source, target, placement in moves:
            source.figures = [
                figure for figure in source.figures
                if figure.figure_id != placement.figure_id
            ]
            if target and all(figure.figure_id != placement.figure_id for figure in target.figures):
                target.figures.append(placement)

    @staticmethod
    def _sanitize_unknown_figures(
        paper_plan: PaperPlan,
        known_figure_ids: Optional[set[str]],
    ) -> None:
        """Drop planner-hallucinated figure ids that do not exist in request metadata."""
        if not known_figure_ids:
            return

        known = {str(fig_id) for fig_id in known_figure_ids if str(fig_id)}
        paper_plan.wide_figures = [
            fig_id for fig_id in paper_plan.wide_figures if fig_id in known
        ]
        for section in paper_plan.sections:
            section.figures = [
                placement
                for placement in section.figures
                if str(placement.figure_id or "") in known
            ]
            section.figures_to_reference = [
                fig_id for fig_id in section.figures_to_reference if fig_id in known
            ]
            for paragraph in section._all_paragraphs():
                paragraph.figures_to_reference = [
                    fig_id for fig_id in paragraph.figures_to_reference if fig_id in known
                ]
                paragraph.figure_usages = [
                    usage
                    for usage in paragraph.figure_usages
                    if str(getattr(usage, "figure_id", "") or "") in known
                ]

    @staticmethod
    def _ensure_figure_usage_contracts(paper_plan: PaperPlan) -> None:
        """Attach each section-defined figure to a paragraph reference contract."""
        for section in paper_plan.sections:
            paragraphs = section._all_paragraphs()
            if not paragraphs:
                continue
            first_paragraph = paragraphs[0]
            for placement in section.figures:
                figure_id = placement.figure_id
                if not figure_id:
                    continue
                section_refs = set(section.figures_to_reference or [])
                paragraph_refs = set(first_paragraph.figures_to_reference or [])
                all_para_refs = {
                    ref
                    for para in paragraphs
                    for ref in (para.figures_to_reference or [])
                }
                if figure_id not in section_refs:
                    section.figures_to_reference.append(figure_id)
                if figure_id not in paragraph_refs and figure_id not in all_para_refs:
                    first_paragraph.figures_to_reference.append(figure_id)

    @staticmethod
    def _enforce_plan_structure_contracts(paper_plan: PaperPlan) -> PaperPlan:
        """Keep sectioning decisions valid after planner optimizer rewrites."""
        paper_plan.sections = [
            enforce_section_structure_contracts(section)
            for section in paper_plan.sections
        ]
        return paper_plan

    @classmethod
    def _preserve_non_result_figure_assignments(
        cls,
        previous_plan: PaperPlan,
        revised_plan: PaperPlan,
        figure_provenance: Optional[Dict[str, Any]],
    ) -> None:
        """
        Keep accepted non-result figure placements from disappearing in review.

        The optimizer may fix missing paragraph usage by removing an assigned
        figure. That is acceptable for misplaced result figures, but not for
        supplemental architecture/pipeline/framework visuals that have already
        passed semantic placement checks.
        """
        provenance = figure_provenance or {}
        revised_defined = {
            placement.figure_id
            for section in revised_plan.sections
            for placement in section.figures
        }
        revised_sections = {section.section_type: section for section in revised_plan.sections}

        for previous_section in previous_plan.sections:
            revised_section = revised_sections.get(previous_section.section_type)
            if not revised_section:
                continue
            for placement in previous_section.figures:
                figure_id = placement.figure_id
                if not figure_id or figure_id in revised_defined:
                    continue
                classification = classify_figure_semantics(
                    figure_id,
                    placement=placement,
                    figure_provenance=provenance,
                )
                if classification == "result_like":
                    continue
                revised_section.figures.append(placement)
                revised_defined.add(figure_id)
                if (
                    figure_id in previous_plan.wide_figures
                    and figure_id not in revised_plan.wide_figures
                ):
                    revised_plan.wide_figures.append(figure_id)

    def _sanitize_intro_result_tables(
        self,
        paper_plan: PaperPlan,
        table_infos: Dict[str, Any],
        table_provenance: Dict[str, Any],
        table_analyses: Optional[Dict[str, Any]],
    ) -> None:
        """Move or drop pre-populated result-like tables from introductions."""
        moves: List[tuple[SectionPlan, Optional[SectionPlan], TablePlacement]] = []
        for section in paper_plan.sections:
            if not is_intro_like_section(section.section_type):
                continue
            for placement in list(section.tables):
                table_id = placement.table_id
                classification = self._table_semantics(
                    table_id,
                    placement,
                    table_infos.get(table_id),
                    table_provenance,
                    table_analyses,
                )
                if classification != "result_like":
                    continue
                target = self._find_result_table_destination(
                    paper_plan,
                    section.section_type,
                )
                if not target:
                    logger.warning(
                        "planner.intro_result_table_definition_dropped table_id=%s",
                        table_id,
                    )
                moves.append((section, target, placement))

        for source, target, placement in moves:
            source.tables = [
                table for table in source.tables
                if table.table_id != placement.table_id
            ]
            if target and all(table.table_id != placement.table_id for table in target.tables):
                target.tables.append(placement)

    _build_figure_placements = staticmethod(build_figure_placements)
    _build_table_placements = staticmethod(build_table_placements)
    _build_assignment_prompt = staticmethod(build_assignment_prompt)
    _parse_element_assignment = staticmethod(parse_element_assignment)
    _assign_figures_to_sections = staticmethod(assign_figures_to_sections)
    _format_section_figure_info = staticmethod(format_section_figure_info)
    _format_figure_info = staticmethod(format_figure_info)
    _format_table_info = staticmethod(format_table_info)
    _should_be_wide_figure = staticmethod(should_be_wide_figure)
    _should_be_wide_table = staticmethod(should_be_wide_table)
    _estimate_total_citations = staticmethod(estimate_total_citations)
    _distribute_citations_topdown = staticmethod(distribute_citations_topdown)
    _rank_references_for_section = staticmethod(rank_references_for_section)
    _infer_section_citation_budget = staticmethod(infer_section_citation_budget)
    _extract_reference_keys = staticmethod(extract_reference_keys)
    _get_section_title = staticmethod(get_section_title)
    _get_default_sources = staticmethod(get_default_sources)
    _get_dependencies = staticmethod(get_dependencies)
    _generate_sentence_plans = staticmethod(generate_sentence_plans)
    _normalize_string_list = staticmethod(normalize_string_list)
    _coerce_bool = staticmethod(coerce_bool)
    _generate_default_paragraphs = staticmethod(generate_default_paragraphs)
    _expand_paragraph_plan = staticmethod(expand_paragraph_plan)
    _assign_papers_to_sections = staticmethod(assign_papers_to_sections)
    _build_context_fallback_payload = staticmethod(build_context_fallback_payload)
    _parse_paragraph_plans = staticmethod(parse_paragraph_plans)
    _split_into_subsections = staticmethod(split_into_subsections)
    _normalize_required_sections = staticmethod(normalize_constraints_required_sections)

    async def _generate_search_queries(
        self,
        section_type: str,
        key_points: List[str],
        existing_refs: List[str],
        paper_title: str,
    ) -> List[str]:
        return await generate_search_queries(
            client=self.client,
            model_name=self.model_name,
            section_type=section_type,
            key_points=key_points,
            existing_refs=existing_refs,
            paper_title=paper_title,
            logger=logger,
        )

    async def _filter_papers_by_relevance(
        self,
        papers: List[Dict[str, Any]],
        section_type: str,
        key_points: List[str],
        paper_title: str,
    ) -> List[Dict[str, Any]]:
        return await filter_papers_by_relevance(
            client=self.client,
            model_name=self.model_name,
            papers=papers,
            section_type=section_type,
            key_points=key_points,
            paper_title=paper_title,
            logger=logger,
        )

    async def _score_papers_by_relevance(
        self,
        research_topic: str,
        papers: List[Dict[str, Any]],
    ) -> List[tuple]:
        return await score_papers_by_relevance(
            client=self.client,
            model_name=self.model_name,
            research_topic=research_topic,
            papers=papers,
            logger=logger,
        )

    async def _generate_research_context(
        self,
        plan: "PaperPlan",
        discovered: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        return await generate_research_context(
            client=self.client,
            model_name=self.model_name,
            plan=plan,
            discovered=discovered,
            logger=logger,
            score_papers_by_relevance_fn=self._score_papers_by_relevance,
            assign_papers_to_sections_fn=assign_papers_to_sections,
        )

    async def _analyze_figures(
        self, figures: List[Any],
    ) -> Dict[str, Any]:
        return await analyze_figures(self.vlm_service, logger, figures)

    async def _analyze_tables(
        self, tables: List[Any],
    ) -> Dict[str, Any]:
        return await analyze_tables(self.vlm_service, logger, tables)

    async def _build_paper_plan(
        self,
        plan_data: Dict[str, Any],
        request: PlanRequest,
        total_words: int,
        figure_analyses: Optional[Dict[str, Any]] = None,
        table_analyses: Optional[Dict[str, Any]] = None,
    ) -> PaperPlan:
        return await build_paper_plan(
            plan_data=plan_data,
            request=request,
            total_words=total_words,
            figure_analyses=figure_analyses,
            table_analyses=table_analyses,
            parse_paragraph_plans_fn=parse_paragraph_plans,
            generate_default_paragraphs_fn=generate_default_paragraphs,
            build_figure_placements_fn=build_figure_placements,
            build_table_placements_fn=build_table_placements,
            get_section_title_fn=get_section_title,
            get_default_sources_fn=get_default_sources,
            get_dependencies_fn=get_dependencies,
            normalize_string_list_fn=normalize_string_list,
            coerce_bool_fn=coerce_bool,
            expand_paragraph_plan_fn=expand_paragraph_plan,
            assign_figure_table_definitions_fn=self._assign_figure_table_definitions,
            logger=logger,
        )

    async def _assign_figure_table_definitions(
        self,
        paper_plan: PaperPlan,
        request: PlanRequest,
        figure_analyses: Optional[Dict[str, Any]] = None,
        table_analyses: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Ensure each figure/table is defined in exactly one section."""
        all_figures = {f.id: f for f in (request.figures or [])}
        all_tables = {t.id: t for t in (request.tables or [])}
        figure_provenance = self._build_figure_provenance(request.figures or [])
        table_provenance = self._build_table_provenance(request.tables or [])

        if (
            not all_figures
            and not all_tables
            and not any(s.tables for s in paper_plan.sections)
            and not any(s.figures for s in paper_plan.sections)
        ):
            return

        self._sanitize_unknown_figures(paper_plan, set(all_figures))

        self._sanitize_misplaced_result_figures(
            paper_plan,
            all_figures,
            figure_provenance,
            figure_analyses,
        )

        self._sanitize_intro_result_tables(
            paper_plan,
            all_tables,
            table_provenance,
            table_analyses,
        )

        figures_defined = set()
        tables_defined = set()
        for section in paper_plan.sections:
            figures_defined.update(f.figure_id for f in section.figures)
            tables_defined.update(t.table_id for t in section.tables)

        fa = figure_analyses or {}
        ta = table_analyses or {}

        for fig_id, fig_info in all_figures.items():
            if should_be_wide_figure(fig_info, fa.get(fig_id)):
                if fig_id not in paper_plan.wide_figures:
                    paper_plan.wide_figures.append(fig_id)

        for tbl_id, tbl_info in all_tables.items():
            if should_be_wide_table(tbl_info):
                if tbl_id not in paper_plan.wide_tables:
                    paper_plan.wide_tables.append(tbl_id)

        unassigned_figs = {
            fid: info for fid, info in all_figures.items()
            if fid not in figures_defined
        }
        unassigned_tbls = {
            tid: info for tid, info in all_tables.items()
            if tid not in tables_defined
        }

        llm_raw: Dict[str, Any] = {}
        if unassigned_figs or unassigned_tbls:
            user_prompt = build_assignment_prompt(
                paper_plan,
                unassigned_figs,
                unassigned_tbls,
                figure_analyses=fa,
                table_analyses=ta,
            )
            try:
                llm_raw = await self._llm_json_call(
                    ELEMENT_ASSIGNMENT_SYSTEM,
                    user_prompt,
                    "element_assignment",
                )
            except Exception as exc:
                logger.warning("planner.element_assignment_failed err=%s", exc)
                llm_raw = {}

        combined: Dict[str, Any] = {**unassigned_figs, **unassigned_tbls}
        assignment = parse_element_assignment(
            json.dumps(llm_raw) if llm_raw else "{}",
            combined,
            paper_plan,
        )
        section_by_type = {s.section_type: s for s in paper_plan.sections}

        for fig_id, fig_info in unassigned_figs.items():
            st = assignment.get(fig_id, "")
            target = section_by_type.get(st)
            if not target:
                continue
            vlm_data = fa.get(fig_id)
            placement = FigurePlacement(
                figure_id=fig_id,
                semantic_role=(
                    getattr(vlm_data, "semantic_role", "")
                    if vlm_data else getattr(fig_info, "semantic_role", "")
                ),
                message=(
                    getattr(vlm_data, "message", "")
                    if vlm_data else getattr(fig_info, "supplementation_rationale", "")
                ),
                is_wide=should_be_wide_figure(fig_info, vlm_data),
                position_hint="mid",
                caption_guidance=getattr(vlm_data, "caption_guidance", "") if vlm_data else "",
            )
            classification = self._figure_semantics(
                fig_id,
                placement,
                fig_info,
                figure_provenance,
                figure_analyses,
            )
            if (
                self._is_excluded_result_figure_section(target.section_type)
                and classification == "result_like"
            ):
                remap_target = self._find_result_figure_destination(
                    paper_plan,
                    target.section_type,
                )
                if remap_target:
                    target = remap_target
                else:
                    logger.warning(
                        "planner.misplaced_result_figure_definition_skipped figure_id=%s",
                        fig_id,
                    )
                    continue
            target.figures.append(placement)

        for tbl_id, tbl_info in unassigned_tbls.items():
            st = assignment.get(tbl_id, "")
            target = section_by_type.get(st)
            if not target:
                continue
            vlm_data = ta.get(tbl_id)
            placement = TablePlacement(
                table_id=tbl_id,
                semantic_role=getattr(vlm_data, "semantic_role", "") if vlm_data else "",
                message=getattr(vlm_data, "message", "") if vlm_data else "",
                is_wide=getattr(vlm_data, "is_wide", False) if vlm_data else should_be_wide_table(tbl_info),
                position_hint="mid",
            )
            classification = self._table_semantics(
                tbl_id,
                placement,
                tbl_info,
                table_provenance,
                table_analyses,
            )
            if (
                is_intro_like_section(target.section_type)
                and classification == "result_like"
            ):
                remap_target = self._find_result_table_destination(
                    paper_plan,
                    target.section_type,
                )
                if remap_target:
                    target = remap_target
                else:
                    logger.warning(
                        "planner.intro_result_table_definition_skipped table_id=%s",
                        tbl_id,
                    )
                    continue
            target.tables.append(placement)

        self._ensure_figure_usage_contracts(paper_plan)

    async def _decide_section_structure(
        self,
        section: SectionPlan,
        paper_type: str,
        contributions: List[str],
        venue: str,
        word_budget: int,
        prior_sections_summary: str,
    ) -> Dict[str, Any]:
        return await decide_section_structure(
            llm_json_call_fn=self._llm_json_call,
            section=section,
            paper_type=paper_type,
            contributions=contributions,
            venue=venue,
            word_budget=word_budget,
            prior_sections_summary=prior_sections_summary,
        )

    async def _plan_flat_paragraphs(
        self,
        section: SectionPlan,
        word_budget: int,
        reference_keys: List[str],
        prior_key_points: str,
        contributions: List[str],
        venue: str = "DEFAULT",
    ) -> List[ParagraphPlan]:
        return await plan_flat_paragraphs(
            llm_json_call_fn=self._llm_json_call,
            parse_paragraph_plans_fn=parse_paragraph_plans,
            section=section,
            word_budget=word_budget,
            reference_keys=reference_keys,
            prior_key_points=prior_key_points,
            contributions=contributions,
            venue=venue,
        )

    async def _plan_subsection_paragraphs(
        self,
        section: SectionPlan,
        subsection_structure: Dict[str, Any],
        reference_keys: List[str],
        contributions: List[str],
    ) -> List[SubSectionPlan]:
        return await plan_subsection_paragraphs(
            llm_json_call_fn=self._llm_json_call,
            parse_paragraph_plans_fn=parse_paragraph_plans,
            section=section,
            subsection_structure=subsection_structure,
            reference_keys=reference_keys,
            contributions=contributions,
        )

    # =====================================================================
    # AskTool consultation interface
    # =====================================================================

    async def answer(self, question: str) -> str:
        """
        Two-stage answer about the paper plan.
        - **Description**:
            - Stage 1: Rule-based keyword filtering over the cached
              PaperPlan to gather compact candidate snippets.
            - Stage 2: LLM refinement — passes the candidates + question
              to ``self.client`` for a concise, semantically precise answer.
            - If the LLM call fails, falls back to Stage 1 output.

        - **Args**:
            - `question` (str): Natural-language question about the plan

        - **Returns**:
            - `result` (str): Precise answer about the plan
        """
        if self._last_plan is None:
            return "No plan available yet."

        candidates = gather_plan_candidates(self._last_plan, question)
        if not candidates:
            return "No matching plan information found."

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a paper-planning assistant. Based on the "
                            "plan context below, answer the question concisely "
                            "and precisely. Keep your response under 200 words."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Plan context:\n{candidates}\n\n"
                            f"Question: {question}"
                        ),
                    },
                ],
                temperature=0.3,
            )
            return response.choices[0].message.content or candidates
        except Exception as e:
            logger.warning("planner.answer LLM refine failed: %s", e)
            return candidates

    # =====================================================================
    # Core planning
    # =====================================================================

    # -----------------------------------------------------------------
    # LLM call helper with retry
    # -----------------------------------------------------------------

    async def _llm_json_call(
        self,
        system_prompt: str,
        user_prompt: str,
        label: str,
        max_retries: int = 2,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        Call LLM and parse the result as JSON, with retry on parse failure.

        - **Args**:
          - `label` (str): Log label for this call (e.g. "step1_structure").
          - `max_retries` (int): Number of retry attempts on JSON parse failure.

        - **Returns**:
          - `Dict[str, Any]`: Parsed JSON object, or empty dict on total failure.
        """
        for attempt in range(1 + max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                )
                text = response.choices[0].message.content.strip()
                parsed = safe_load_json(text, expected=dict)
                if parsed:
                    logger.info("planner.%s ok (attempt=%d)", label, attempt)
                    return parsed
                logger.warning(
                    "planner.%s json_parse_failed attempt=%d raw=%r", label, attempt, text,
                )
            except Exception as e:
                logger.warning(
                    "planner.%s error attempt=%d: %s", label, attempt, e,
                )
        logger.error("planner.%s all_attempts_failed", label)
        return {}

    async def _criticize_plan(
        self,
        plan: PaperPlan,
        iteration: int,
        table_provenance: Optional[Dict[str, Any]] = None,
        figure_provenance: Optional[Dict[str, Any]] = None,
    ) -> PlanReviewIteration:
        """
        Run one critic pass and normalize issues.
        - **Args**:
            - `plan` (PaperPlan): Current plan.
            - `iteration` (int): Iteration index starting from 1.

        - **Returns**:
            - `PlanReviewIteration`: Normalized review result.
        """
        critique = ""
        issues: List[PlanReviewIssue] = []
        try:
            prompt = STEP6_PLAN_CRITIC_USER.format(
                paper_plan_json=paper_plan_to_json(plan),
            )
            payload = await self._llm_json_call(
                STEP6_PLAN_CRITIC_SYSTEM,
                prompt,
                "step6_plan_critic",
                max_retries=1,
                temperature=0.2,
            )
            critique = str(payload.get("critique", "")).strip()
            raw_issues = payload.get("issues", [])
            if isinstance(raw_issues, list):
                for idx, item in enumerate(raw_issues):
                    if not isinstance(item, dict):
                        continue
                    issue_data = dict(item)
                    if not issue_data.get("issue_id"):
                        issue_data["issue_id"] = f"iter-{iteration}-issue-{idx + 1}"
                    issue_data.setdefault("severity", "minor")
                    try:
                        issues.append(PlanReviewIssue.model_validate(issue_data))
                    except Exception:
                        continue
        except Exception as e:
            logger.warning("planner.step6_plan_critic error: %s", e)
            issues.append(
                PlanReviewIssue(
                    issue_id=f"iter-{iteration}-critic-failure",
                    category="review_runtime",
                    severity=PlanReviewSeverity.MAJOR,
                    title="Plan critic runtime failure",
                    description=f"Critic invocation failed: {e}",
                    recommendation=(
                        "Retry plan review and validate critic response before accepting plan."
                    ),
                    expected_plan_change=(
                        "No direct plan patch required; review pass must succeed first."
                    ),
                ),
            )

        # Soft venue-style signal: advisory only, not a blocker.
        if not has_intro_contribution_summary_signal(plan):
            issues.append(
                PlanReviewIssue(
                    issue_id=f"iter-{iteration}-intro-soft-signal",
                    section_type="introduction",
                    category="venue_norm",
                    severity=PlanReviewSeverity.SOFT,
                    title="Introduction contribution-summary signal",
                    description=(
                        "Introduction does not clearly expose a contribution-summary "
                        "intent near its closing flow."
                    ),
                    recommendation=(
                        "Refine mission/key_point in the closing introduction paragraph "
                        "to summarize core contributions."
                    ),
                    expected_plan_change=(
                        "Update introduction final paragraph key_point or supporting_points "
                        "with concise contribution-summary intent."
                    ),
                ),
            )

        issues.extend(
            deterministic_plan_review_issues(
                plan,
                table_provenance=table_provenance,
                figure_provenance=figure_provenance,
            )
        )

        return PlanReviewIteration(
            iteration=iteration,
            critique=critique,
            issues=issues,
            changed=False,
        )

    async def _optimize_plan(
        self,
        plan: PaperPlan,
        issues: List[PlanReviewIssue],
        iteration: int,
    ) -> PaperPlan:
        """
        Run one optimizer pass and return revised plan.
        - **Args**:
            - `plan` (PaperPlan): Current plan.
            - `issues` (List[PlanReviewIssue]): Issues to resolve.
            - `iteration` (int): Iteration index.

        - **Returns**:
            - `PaperPlan`: Revised plan; falls back to input on failure.
        """
        try:
            prompt = STEP7_PLAN_OPTIMIZER_USER.format(
                paper_plan_json=paper_plan_to_json(plan),
                review_issues_json=json.dumps(
                    [issue.model_dump() for issue in issues],
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": STEP7_PLAN_OPTIMIZER_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            raw = response.choices[0].message.content or ""
            parsed = safe_load_json(raw, expected=dict)
            if not parsed:
                logger.warning("planner.step7_plan_optimizer invalid_json iteration=%d", iteration)
                return plan
            if "plan" in parsed and isinstance(parsed["plan"], dict):
                parsed = parsed["plan"]
            return PaperPlan.model_validate(parsed)
        except Exception as e:
            logger.warning("planner.step7_plan_optimizer error iteration=%d: %s", iteration, e)
            return plan

    async def _review_and_refine_plan(
        self,
        plan: PaperPlan,
        max_iterations: int = 2,
        enabled: bool = True,
        table_provenance: Optional[Dict[str, Any]] = None,
        figure_provenance: Optional[Dict[str, Any]] = None,
        fact_lock: Optional[CanonicalFactLock] = None,
    ) -> tuple[PaperPlan, PlanReviewSummary]:
        """
        Run iterative critic-optimizer refinement over a plan.
        - **Args**:
            - `plan` (PaperPlan): Initial plan from planning steps.
            - `max_iterations` (int): Max critic rounds.
            - `enabled` (bool): Whether to run review loop.

        - **Returns**:
            - `tuple[PaperPlan, PlanReviewSummary]`: Final plan and review summary.
        """
        summary = PlanReviewSummary(
            enabled=enabled,
            max_iterations=max(0, int(max_iterations)),
            iterations=[],
            final_status="not_run",
        )
        self._last_plan_evolution = None
        known_figure_ids = set(figure_provenance or {})
        if not enabled or max_iterations <= 0:
            self._sanitize_unknown_figures(plan, known_figure_ids)
            summary.final_status = "skipped"
            return enforce_full_paper_plan_invariant(plan), summary

        current_plan = self._enforce_plan_structure_contracts(
            enforce_full_paper_plan_invariant(plan)
        )
        self._sanitize_unknown_figures(current_plan, known_figure_ids)
        evolution: Dict[str, Any] = {
            "enabled": True,
            "max_iterations": max(0, int(max_iterations)),
            "initial": current_plan.model_dump(mode="json"),
            "iterations": [],
            "final_status": "not_run",
        }
        for iteration in range(1, max_iterations + 1):
            before_snapshot = current_plan.model_dump(mode="json")
            review_iter = await self._criticize_plan(
                current_plan,
                iteration,
                table_provenance=table_provenance,
                figure_provenance=figure_provenance,
            )
            summary.iterations.append(review_iter)
            iteration_trace: Dict[str, Any] = {
                "iteration": iteration,
                "before": before_snapshot,
                "issues": [
                    issue.model_dump(mode="json") for issue in review_iter.issues
                ],
                "changed": False,
                "status": "reviewed",
            }
            evolution["iterations"].append(iteration_trace)

            if not review_iter.issues:
                summary.final_status = "passed"
                iteration_trace["status"] = "passed"
                break

            blocking_issues = [
                issue
                for issue in review_iter.issues
                if issue.is_blocking and not is_advisory_plan_issue(issue)
            ]
            advisory_revision_issues = [
                issue
                for issue in review_iter.issues
                if is_advisory_plan_issue(issue)
            ]
            revision_issues = [*blocking_issues, *advisory_revision_issues]
            if not revision_issues:
                summary.final_status = "pass_with_suggestions"
                iteration_trace["status"] = "pass_with_suggestions"
                break

            revised_plan = await self._optimize_plan(
                current_plan,
                revision_issues,
                iteration,
            )
            revised_plan = self._enforce_plan_structure_contracts(
                enforce_full_paper_plan_invariant(revised_plan)
            )
            fact_lock_issues: List[PlanReviewIssue] = []
            if fact_lock is not None:
                revised_plan, fact_lock_issues = apply_canonical_fact_lock(
                    revised_plan,
                    fact_lock,
                    iteration=iteration,
                )
                revised_plan = self._enforce_plan_structure_contracts(
                    enforce_full_paper_plan_invariant(revised_plan)
                )
                if fact_lock_issues:
                    summary.iterations[-1].issues.extend(fact_lock_issues)
                    iteration_trace["issues"].extend(
                        issue.model_dump(mode="json") for issue in fact_lock_issues
                    )
                    iteration_trace.setdefault("fact_lock_conflicts", []).extend(
                        issue.model_dump(mode="json") for issue in fact_lock_issues
                    )
            changed = revised_plan.model_dump() != current_plan.model_dump()
            summary.iterations[-1].changed = changed
            iteration_trace["changed"] = changed
            if not changed:
                summary.final_status = (
                    "needs_revision" if blocking_issues else "pass_with_suggestions"
                )
                iteration_trace["status"] = "optimizer_unchanged"
                break
            self._preserve_non_result_figure_assignments(
                current_plan,
                revised_plan,
                figure_provenance,
            )
            self._sanitize_unknown_figures(revised_plan, known_figure_ids)
            self._ensure_figure_usage_contracts(revised_plan)
            revised_plan = self._enforce_plan_structure_contracts(
                enforce_full_paper_plan_invariant(revised_plan)
            )
            current_plan = revised_plan
            iteration_trace["after"] = revised_plan.model_dump(mode="json")
            iteration_trace["status"] = "changed"
        else:
            latest_blocking = [
                issue
                for issue in summary._latest_issues()
                if issue.is_blocking and not is_advisory_plan_issue(issue)
            ]
            summary.final_status = "needs_revision" if latest_blocking else "passed"

        if summary.final_status == "not_run":
            latest_blocking = [
                issue
                for issue in summary._latest_issues()
                if issue.is_blocking and not is_advisory_plan_issue(issue)
            ]
            summary.final_status = "needs_revision" if latest_blocking else "passed"
        current_plan = self._enforce_plan_structure_contracts(
            enforce_full_paper_plan_invariant(current_plan)
        )
        evolution["final_status"] = summary.final_status
        evolution["final_plan"] = current_plan.model_dump(mode="json")
        self._last_plan_evolution = evolution
        return current_plan, summary

    # -----------------------------------------------------------------
    # Main entry point — multi-step planning
    # -----------------------------------------------------------------

    async def create_plan(
        self,
        request: PlanRequest,
        review_enabled: Optional[bool] = None,
        review_max_iterations: Optional[int] = None,
    ) -> PaperPlan:
        """
        Create a paper plan from metadata using a multi-step approach.

        - **Description**:
          - Step 1: Structure decision (paper_type, sections, contributions)
          - Step 2: Citation strategy (total target + per-section allocation)
          - Step 3: Figure/table assignment and initial section shells
          - Step 4/5: Per-section structure and paragraph planning
          - Each step produces a small, simple JSON output that is easy for
            the LLM to generate correctly, reducing parse failures.

        - **Args**:
          - `request` (PlanRequest): Planning request with metadata.
          - `review_enabled` (bool, optional): Per-request plan-review switch.
          - `review_max_iterations` (int, optional): Per-request review max rounds.

        - **Returns**:
        - `PaperPlan`: Complete paragraph-level paper plan.
        """
        self._last_plan = None
        self._last_plan_review_summary = None
        self._last_plan_evolution = None

        n_figures = len(request.figures) if request.figures else 0
        n_tables = len(request.tables) if request.tables else 0
        figure_provenance = self._build_figure_provenance(request.figures or [])
        table_provenance = self._build_table_provenance(request.tables or [])

        # VLM analysis before word budget so wide-figure counts use VLM + geometry
        figure_analyses: Dict[str, Any] = {}
        table_analyses: Dict[str, Any] = {}
        if self.vlm_service:
            figure_analyses = await self._analyze_figures(request.figures or [])
            table_analyses = await self._analyze_tables(request.tables or [])

        n_wide_figures = sum(
            1 for f in (request.figures or [])
            if self._should_be_wide_figure(f, figure_analyses.get(getattr(f, "id", "")))
        )
        n_wide_tables = sum(
            1 for t in (request.tables or []) if self._should_be_wide_table(t)
        )

        total_words = calculate_total_words(
            request.target_pages,
            request.style_guide,
            n_figures=n_figures,
            n_tables=n_tables,
            n_wide_figures=n_wide_figures,
            n_wide_tables=n_wide_tables,
        )
        target_pages = request.target_pages or 10
        style_guide = request.style_guide or "DEFAULT"
        total_paragraphs = estimate_target_paragraphs(total_words)
        required_sections = self._normalize_required_sections(request.constraints)
        venue_required_sections_block = format_venue_required_sections_block(
            required_sections
        )
        content_brief_block = format_content_brief_block(
            request.content_brief or {},
            required_sections,
        )

        reference_keys = self._extract_reference_keys(request.references)
        figure_info = self._format_figure_info(request.figures or [], figure_analyses)
        table_info = self._format_table_info(request.tables or [], table_analyses)
        rc_summary = format_research_context_for_planning(request.research_context)
        code_summary = format_code_assets_for_planning(
            code_context=request.code_context,
            code_writing_assets=request.code_writing_assets,
        )

        logger.info(
            "planner.create_plan title=%s words=%d paragraphs=%d vlm=%s required_sections=%s",
            request.title[:30], total_words, total_paragraphs,
            bool(figure_analyses or table_analyses), required_sections,
        )

        # =============================================================
        # STEP 1: Structure Decision
        # =============================================================
        step1_prompt = STEP1_STRUCTURE_USER.format(
            title=request.title,
            idea_hypothesis=request.idea_hypothesis[:2000],
            method=request.method[:1500],
            data=request.data[:1000],
            experiments=request.experiments[:1500],
            style_guide=style_guide,
            target_pages=target_pages,
            research_context_summary=rc_summary,
            code_writing_assets_summary=code_summary,
            venue_required_sections_block=venue_required_sections_block,
            content_brief_block=content_brief_block,
        )
        structure = await self._llm_json_call(
            STEP1_STRUCTURE_SYSTEM, step1_prompt, "step1_structure",
        )

        # Extract structure decisions
        paper_type_str = structure.get("paper_type", "empirical")
        try:
            paper_type = PaperType(paper_type_str.lower())
        except ValueError:
            paper_type = PaperType.EMPIRICAL

        style_str = structure.get("narrative_style", "technical")
        try:
            narrative_style = NarrativeStyle(style_str.lower())
        except ValueError:
            narrative_style = NarrativeStyle.TECHNICAL

        contributions = structure.get("contributions", [])
        structure_rationale = structure.get("structure_rationale", "")
        abstract_focus = structure.get("abstract_focus", "")

        raw_sections = normalize_full_paper_section_items(structure.get("sections", []))
        section_order: List[Dict[str, Any]] = []
        for s in raw_sections:
            if isinstance(s, dict) and s.get("section_type"):
                st = normalize_section_type_name(str(s["section_type"]))
                section_order.append({
                    "section_type": st,
                    "section_title": s.get("section_title", self._get_section_title(st)),
                    "mission": s.get("mission", ""),
                    "key_content": s.get("key_content", []) if isinstance(s.get("key_content"), list) else [],
                })

        if not section_order or len(section_order) < 3:
            section_order = [
                {"section_type": st, "section_title": self._get_section_title(st)}
                for st in DEFAULT_EMPIRICAL_SECTIONS
            ]
            logger.warning("planner.step1_fallback using default sections")

        if not any(s["section_type"] == "abstract" for s in section_order):
            section_order.insert(0, {"section_type": "abstract", "section_title": "Abstract"})

        # Deduplicate section_types: if the LLM produces multiple sections
        # with the same type (e.g. 3 "result" sections), append _2, _3, etc.
        # to create unique keys while preserving semantic meaning.
        type_counts: Dict[str, int] = {}
        for sec in section_order:
            st = sec["section_type"]
            type_counts[st] = type_counts.get(st, 0) + 1
            if type_counts[st] > 1:
                sec["section_type"] = f"{st}_{type_counts[st]}"

        section_types_str = ", ".join(s["section_type"] for s in section_order)
        logger.info(
            "planner.step1_done paper_type=%s sections=[%s]",
            paper_type.value, section_types_str,
        )

        # =============================================================
        # STEP 2: Citation Strategy
        # =============================================================
        step2_prompt = STEP2_CITATION_USER.format(
            title=request.title,
            style_guide=style_guide,
            target_pages=target_pages,
            section_list=section_types_str,
            reference_keys=", ".join(reference_keys) if reference_keys else "None",
        )
        citation_strategy = await self._llm_json_call(
            STEP2_CITATION_SYSTEM, step2_prompt, "step2_citation",
        )

        if not citation_strategy.get("total_target"):
            total_paras = total_paragraphs
            body_count = sum(
                1 for s in section_order
                if s["section_type"] not in ("abstract", "conclusion")
            )
            citation_strategy = {
                "total_target": self._estimate_total_citations(
                    style_guide, body_count, total_paras,
                ),
                "rationale": "Fallback estimation",
                "section_allocation": {},
            }
        logger.info(
            "planner.step2_done total_target=%s",
            citation_strategy.get("total_target"),
        )

        # =============================================================
        # STEP 3: Figure/Table Assignment (unchanged)
        # =============================================================
        n_body = sum(
            1 for s in section_order
            if s["section_type"] not in ("abstract", "conclusion")
        )
        sections: List[SectionPlan] = []

        figure_assignment = self._assign_figures_to_sections(
            request.figures or [], section_order, figure_analyses or {},
        )

        # Build initial SectionPlan shells with mission/key_content from Step 1,
        # plus figure/table placements and citation budgets.
        for order, sec_info in enumerate(section_order):
            section_type = sec_info["section_type"]
            section_title = sec_info["section_title"]

            if section_type in ("abstract", "conclusion"):
                sections.append(SectionPlan(
                    section_type=section_type,
                    section_title=section_title,
                    mission=sec_info.get("mission", ""),
                    key_content=sec_info.get("key_content", []),
                    paragraphs=[],
                    figures=[],
                    tables=[],
                    content_sources=self._get_default_sources(section_type),
                    depends_on=self._get_dependencies(section_type),
                    citation_budget={"target_refs": 0, "min_refs": 0, "max_refs": 0},
                    order=order,
                ))
                continue

            # Allocate word budget per section proportionally
            alloc = (citation_strategy.get("section_allocation") or {}).get(section_type, {})
            if isinstance(alloc, dict) and alloc.get("target_refs"):
                total_target = int(citation_strategy.get("total_target", 1) or 1)
                share = int(alloc.get("target_refs", 0)) / max(1, total_target)
                section_words = max(400, int(total_words * max(share, 0.1)))
            else:
                section_words = max(400, total_words // max(1, n_body))

            # Build figure/table placements for this section
            section_figure_info = self._format_section_figure_info(
                request.figures or [], figure_analyses or {},
                section_type, figure_assignment,
            )
            figure_placements = self._build_figure_placements(
                [{"figure_id": fid} for fid in figure_assignment
                 if figure_assignment.get(fid) == section_type],
                figure_analyses or {},
            )
            table_placements = self._build_table_placements(
                [], table_analyses or {},
            )

            # Citation budget from Step 2
            alloc = (citation_strategy.get("section_allocation") or {}).get(section_type, {})
            if isinstance(alloc, dict):
                citation_budget = {
                    "target_refs": int(alloc.get("target_refs", 0) or 0),
                    "rationale": alloc.get("rationale", ""),
                }
            else:
                citation_budget = {}

            sections.append(SectionPlan(
                section_type=section_type,
                section_title=section_title,
                mission=sec_info.get("mission", ""),
                key_content=sec_info.get("key_content", []),
                paragraphs=[],
                figures=figure_placements,
                tables=table_placements,
                content_sources=self._get_default_sources(section_type),
                depends_on=self._get_dependencies(section_type),
                citation_budget=citation_budget,
                order=order,
            ))

        # =============================================================
        # STEP 4 + 5a/5b: Incremental Per-Section Planning
        # =============================================================
        prior_sections_summary = ""
        prior_key_points = ""

        for idx, section in enumerate(sections):
            if section.section_type in ("abstract", "conclusion"):
                continue

            section_words = max(400, total_words // max(1, n_body))
            alloc = (citation_strategy.get("section_allocation") or {}).get(section.section_type, {})
            if isinstance(alloc, dict) and alloc.get("target_refs"):
                total_target = int(citation_strategy.get("total_target", 1) or 1)
                share = int(alloc.get("target_refs", 0)) / max(1, total_target)
                section_words = max(400, int(total_words * max(share, 0.1)))

            # Step 4: Decide structure
            structure_decision = await self._decide_section_structure(
                section=section,
                paper_type=paper_type.value,
                contributions=contributions,
                venue=style_guide,
                word_budget=section_words,
                prior_sections_summary=prior_sections_summary,
            )

            needs_subs = self._coerce_bool(structure_decision.get("needs_subsections", False))

            if needs_subs:
                # Step 5b: Subsection paragraph plans
                section.subsections = await self._plan_subsection_paragraphs(
                    section=section,
                    subsection_structure=structure_decision,
                    reference_keys=reference_keys,
                    contributions=contributions,
                )
                section = sanitize_conclusion_like_subsections(section)
                section = collapse_singleton_subsections(section)
                sections[idx] = section
                section.sectioning_recommended = bool(section.subsections)
                sub_summary = ", ".join(s.title for s in section.subsections)
                total_paras_in_section = sum(
                    len(s.paragraphs) for s in section.subsections
                )
                prior_sections_summary += (
                    f"{section.section_type}: {total_paras_in_section} paras, "
                    f"{len(section.subsections)} subs ({sub_summary}); "
                )
                for sub in section.subsections:
                    for p in sub.paragraphs:
                        if p.key_point:
                            prior_key_points += f"- [{section.section_type}/{sub.title}] {p.key_point}\n"
            else:
                # Step 5a: Flat paragraph plans
                section.paragraphs = await self._plan_flat_paragraphs(
                    section=section,
                    word_budget=section_words,
                    reference_keys=reference_keys,
                    prior_key_points=prior_key_points,
                    contributions=contributions,
                    venue=style_guide,
                )
                prior_sections_summary += (
                    f"{section.section_type}: {len(section.paragraphs)} paras, flat; "
                )
                for p in section.paragraphs:
                    if p.key_point:
                        prior_key_points += f"- [{section.section_type}] {p.key_point}\n"

            logger.info(
                "planner.step4_5 section=%s subsections=%s paragraphs=%d",
                section.section_type,
                len(section.subsections) if section.subsections else 0,
                len(section._all_paragraphs()),
            )

        # Whole-plan paragraph budget validation
        target_paras = estimate_target_paragraphs(total_words)
        llm_total_paras = sum(len(sp._all_paragraphs()) for sp in sections)
        if llm_total_paras > 0 and llm_total_paras < target_paras * 0.5:
            scale = target_paras / max(1, llm_total_paras)
            for sp in sections:
                if sp.section_type in ("abstract", "conclusion"):
                    continue
                all_paras = sp._all_paragraphs()
                section_target_sents = int(
                    sum(p.approx_sentences for p in all_paras) * scale
                )
                if sp.subsections:
                    # Expand paragraphs within each subsection proportionally
                    for sub in sp.subsections:
                        sub_ratio = len(sub.paragraphs) / max(1, len(all_paras))
                        sub_sents = max(1, int(section_target_sents * sub_ratio))
                        sub.paragraphs = self._expand_paragraph_plan(
                            sub.paragraphs, sub_sents, sp.section_type,
                        )
                else:
                    sp.paragraphs = self._expand_paragraph_plan(
                        sp.paragraphs, section_target_sents, sp.section_type,
                    )
            expanded_total = sum(len(sp._all_paragraphs()) for sp in sections)
            logger.info(
                "planner.plan_budget_expansion llm_paras=%d target=%d expanded=%d",
                llm_total_paras, target_paras, expanded_total,
            )

        paper_plan = PaperPlan(
            title=request.title,
            paper_type=paper_type,
            sections=sections,
            contributions=contributions,
            narrative_style=narrative_style,
            terminology=structure.get("terminology", {}),
            structure_rationale=structure_rationale,
            abstract_focus=abstract_focus,
            citation_strategy=citation_strategy,
        )

        await self._assign_figure_table_definitions(
            paper_plan, request, figure_analyses, table_analyses,
        )

        logger.info(
            "planner.plan_created sections=%d sentences=%d",
            len(paper_plan.sections), paper_plan.get_total_sentences(),
        )
        effective_review_enabled = (
            bool(getattr(self, "enable_plan_review", False))
            if review_enabled is None
            else bool(review_enabled)
        )
        effective_review_max_iterations = (
            int(getattr(self, "plan_review_max_iterations", 2))
            if review_max_iterations is None
            else max(0, int(review_max_iterations))
        )
        paper_plan, review_summary = await self._review_and_refine_plan(
            paper_plan,
            max_iterations=effective_review_max_iterations,
            enabled=effective_review_enabled,
            table_provenance=table_provenance,
            figure_provenance=figure_provenance,
            fact_lock=build_canonical_fact_lock(paper_plan, request),
        )
        paper_plan = enforce_required_sections(paper_plan, required_sections)
        self._last_plan_review_summary = review_summary
        self._last_plan = paper_plan
        return paper_plan

    async def discover_seed_references(
        self,
        title: str,
        idea_hypothesis: str,
        method: str,
        data: str,
        experiments: str,
        existing_ref_keys: List[str],
        paper_search_config: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Discover global references before section-level planning.
        """
        import asyncio
        from ..shared.tools.paper_search import PaperSearchTool

        cfg = paper_search_config or {}
        tool = PaperSearchTool(
            serpapi_api_key=cfg.get("serpapi_api_key"),
            semantic_scholar_api_key=cfg.get("semantic_scholar_api_key"),
            timeout=cfg.get("timeout", 10),
            semantic_scholar_min_results_before_fallback=cfg.get(
                "semantic_scholar_min_results_before_fallback", 3
            ),
            enable_query_cache=cfg.get("enable_query_cache", True),
            cache_ttl_hours=cfg.get("cache_ttl_hours", 24),
        )

        max_queries = max(3, min(6, int(cfg.get("planner_max_queries_per_section", 5))))
        per_round = max(3, int(cfg.get("search_results_per_round", 5)))
        delay_sec = max(0.5, float(cfg.get("planner_inter_round_delay_sec", 1.5)))

        queries = build_seed_queries(
            title=title,
            idea_hypothesis=idea_hypothesis,
            method=method,
            data=data,
            experiments=experiments,
            max_queries=max_queries,
        )
        if not queries:
            logger.info("planner.seed_reference_discovery skipped=no_quality_queries")
            return []

        discovered: List[Dict[str, Any]] = []
        seen_keys = set(existing_ref_keys)
        for i, query in enumerate(queries):
            if i > 0:
                await asyncio.sleep(delay_sec)
            try:
                result = await tool.execute(query=query, max_results=per_round)
                if not result.success:
                    continue
                papers = result.data.get("papers", []) if result.data else []
                for paper in papers:
                    bkey = paper.get("bibtex_key", "")
                    bibtex = paper.get("bibtex", "")
                    if bkey and bibtex and bkey not in seen_keys:
                        seen_keys.add(bkey)
                        discovered.append(
                            {
                                "ref_id": bkey,
                                "bibtex": bibtex,
                                "title": paper.get("title", ""),
                                "year": paper.get("year"),
                                "abstract": paper.get("abstract", ""),
                                "venue": paper.get("venue", ""),
                                "citation_count": paper.get("citation_count"),
                                "source": paper.get("source", ""),
                            }
                        )
            except Exception as e:
                logger.warning("planner.seed_search_error query='%s': %s", query[:80], e)

        logger.info("planner.seed_reference_discovery count=%d", len(discovered))
        return discovered

    async def discover_landscape_references(
        self,
        *,
        core_analysis: Any,
        title: str,
        idea_hypothesis: str,
        paper_search_config: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Broad literature search for research-context construction (pre-plan).

        - **Description**:
            - Queries are derived from core-ref synthesis (gaps, lineage, titles)
              plus the manuscript title and idea — not from section key points.
            - Returns a flat list of papers; callers decide pool membership.
        """
        return await discover_landscape_references_helper(
            core_analysis=core_analysis,
            title=title,
            idea_hypothesis=idea_hypothesis,
            paper_search_config=paper_search_config,
            logger=logger,
        )
        import asyncio
        from ..shared.tools.paper_search import PaperSearchTool

        cfg = paper_search_config or {}
        tool = PaperSearchTool(
            serpapi_api_key=cfg.get("serpapi_api_key"),
            semantic_scholar_api_key=cfg.get("semantic_scholar_api_key"),
            timeout=cfg.get("timeout", 10),
            semantic_scholar_min_results_before_fallback=cfg.get(
                "semantic_scholar_min_results_before_fallback", 3
            ),
            enable_query_cache=cfg.get("enable_query_cache", True),
            cache_ttl_hours=cfg.get("cache_ttl_hours", 24),
        )

        max_queries = max(4, min(10, int(cfg.get("planner_landscape_max_queries", 8))))
        per_round = max(3, int(cfg.get("search_results_per_round", 5)))
        delay_sec = max(0.5, float(cfg.get("planner_inter_round_delay_sec", 1.5)))

        queries: List[str] = []
        seen_q: set = set()

        def _add(q: str) -> None:
            qq = " ".join(str(q).split()).strip()
            if len(qq) < 8 or qq in seen_q:
                return
            seen_q.add(qq)
            queries.append(qq)

        _add(title)
        _add(f"{title} {idea_hypothesis[:220]}")

        gaps = getattr(core_analysis, "shared_gaps", None) or []
        if isinstance(gaps, list):
            for g in gaps[:5]:
                if isinstance(g, str):
                    _add(f"{title} {g[:180]}")

        lineage = getattr(core_analysis, "research_lineage", "") or ""
        if isinstance(lineage, str) and lineage.strip():
            _add(f"{title} {lineage[:200]}")

        pos = getattr(core_analysis, "positioning_statement", "") or ""
        if isinstance(pos, str) and pos.strip():
            _add(f"{title} {pos[:200]}")

        items = getattr(core_analysis, "items", None) or []
        if items:
            for it in items[:4]:
                t = getattr(it, "title", "") if not isinstance(it, dict) else it.get("title", "")
                if t:
                    _add(f"{title} related work {t[:120]}")

        queries = queries[:max_queries]

        discovered: List[Dict[str, Any]] = []
        seen_keys: set = set()
        for i, query in enumerate(queries):
            if i > 0:
                await asyncio.sleep(delay_sec)
            try:
                result = await tool.execute(query=query, max_results=per_round)
                if not result.success:
                    continue
                papers = result.data.get("papers", []) if result.data else []
                for paper in papers:
                    bkey = paper.get("bibtex_key", "")
                    bibtex = paper.get("bibtex", "")
                    if bkey and bibtex and bkey not in seen_keys:
                        seen_keys.add(bkey)
                        discovered.append(
                            {
                                "ref_id": bkey,
                                "bibtex": bibtex,
                                "title": paper.get("title", ""),
                                "year": paper.get("year"),
                                "abstract": paper.get("abstract", ""),
                                "venue": paper.get("venue", ""),
                                "citation_count": paper.get("citation_count"),
                                "source": "landscape_discovery",
                            }
                        )
            except Exception as e:
                logger.warning("planner.landscape_search_error query='%s': %s", query[:80], e)

        logger.info("planner.landscape_reference_discovery count=%d", len(discovered))
        return discovered

    # Known utility / infrastructure mentions -> search query suffixes
    _UTILITY_LITERATURE_TRIGGERS: List[tuple[str, str]] = [
        ("imagenet", "ImageNet large scale visual recognition Deng 2009"),
        ("cifar-10", "CIFAR-10 dataset learning multiple layers"),
        ("cifar-100", "CIFAR-100 dataset"),
        ("pytorch", "PyTorch Paszke automatic differentiation"),
        ("tensorflow", "TensorFlow Abadi machine learning"),
        ("mnist", "MNIST handwritten digit database"),
        ("bleu", "BLEU Papineni machine translation evaluation"),
        ("rouge", "ROUGE Lin summarization evaluation"),
        ("coco dataset", "COCO dataset Lin Microsoft common objects"),
    ]

    async def discover_utility_references(
        self,
        plan: "PaperPlan",
        existing_ref_keys: List[str],
        paper_search_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Targeted search for dataset / metric / framework papers mentioned in the plan.

        - **Description**:
            - Scans section key points and paragraph text for known triggers.
            - Returns section_type -> papers (same shape as ``discover_references``).
        """
        return await discover_utility_references_helper(
            plan=plan,
            existing_ref_keys=existing_ref_keys,
            paper_search_config=paper_search_config,
            logger=logger,
            triggers=self._UTILITY_LITERATURE_TRIGGERS,
        )
        import asyncio
        from ..shared.tools.paper_search import PaperSearchTool

        cfg = paper_search_config or {}
        tool = PaperSearchTool(
            serpapi_api_key=cfg.get("serpapi_api_key"),
            semantic_scholar_api_key=cfg.get("semantic_scholar_api_key"),
            timeout=cfg.get("timeout", 10),
            semantic_scholar_min_results_before_fallback=cfg.get(
                "semantic_scholar_min_results_before_fallback", 3
            ),
            enable_query_cache=cfg.get("enable_query_cache", True),
            cache_ttl_hours=cfg.get("cache_ttl_hours", 24),
        )
        per_round = max(2, int(cfg.get("search_results_per_round", 5)))
        delay_sec = max(0.5, float(cfg.get("planner_inter_round_delay_sec", 1.5)))

        out: Dict[str, List[Dict[str, Any]]] = {}
        seen_keys = set(existing_ref_keys)
        search_count = 0
        max_utility_searches = int(cfg.get("planner_max_utility_searches", 12))

        for sp in plan.sections:
            if sp.section_type in ("abstract", "conclusion"):
                continue
            blobs: List[str] = []
            try:
                blobs.extend(sp.get_key_points())
            except Exception:
                pass
            for para in getattr(sp, "paragraphs", []) or []:
                blobs.append(getattr(para, "key_point", "") or "")
                blobs.extend(getattr(para, "supporting_points", []) or [])
            blob = " ".join(blobs).lower()

            for needle, query in self._UTILITY_LITERATURE_TRIGGERS:
                if search_count >= max_utility_searches:
                    break
                if needle not in blob:
                    continue
                if search_count > 0:
                    await asyncio.sleep(delay_sec)
                search_count += 1
                try:
                    result = await tool.execute(query=query, max_results=per_round)
                    if not result.success:
                        continue
                    papers = result.data.get("papers", []) if result.data else []
                    for paper in papers:
                        bkey = paper.get("bibtex_key", "")
                        bibtex = paper.get("bibtex", "")
                        if not bkey or not bibtex or bkey in seen_keys:
                            continue
                        seen_keys.add(bkey)
                        rec = {
                            "ref_id": bkey,
                            "bibtex": bibtex,
                            "title": paper.get("title", ""),
                            "year": paper.get("year"),
                            "abstract": paper.get("abstract", ""),
                            "venue": paper.get("venue", ""),
                            "citation_count": paper.get("citation_count"),
                            "source": "utility_discovery",
                        }
                        out.setdefault(sp.section_type, []).append(rec)
                        break
                except Exception as e:
                    logger.warning("planner.utility_search_error query='%s': %s", query[:60], e)

        total_u = sum(len(v) for v in out.values())
        if total_u:
            logger.info("planner.utility_reference_discovery total=%d", total_u)
        return out

    # =====================================================================
    # Reference discovery
    # =====================================================================

    async def discover_references(
        self,
        plan: PaperPlan,
        existing_ref_keys: List[str],
        paper_search_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover additional references for each section based on the plan.
        - **Description**:
            - Analyzes each section's key points and generates search queries.
            - Executes multi-round searches via PaperSearchTool.
            - Supports loop searching until target count is reached or no more queries.
            - Returns discovered papers grouped by section_type.
            - Called once during planning, replacing per-section search judgment.

        - **Args**:
            - `plan` (PaperPlan): The paper plan with section structures.
            - `existing_ref_keys` (List[str]): Already-available citation keys.
            - `paper_search_config` (dict, optional): PaperSearchTool config.

        - **Returns**:
            - `Dict[str, List[Dict]]`: section_type -> list of discovered papers
              (each with ref_id, bibtex, title, etc.)
        """
        return await discover_references_helper(
            plan=plan,
            existing_ref_keys=existing_ref_keys,
            paper_search_config=paper_search_config,
            logger=logger,
            generate_search_queries_fn=self._generate_search_queries,
            estimate_total_citations_fn=self._estimate_total_citations,
            distribute_citations_topdown_fn=self._distribute_citations_topdown,
            filter_papers_by_relevance_fn=self._filter_papers_by_relevance,
        )
        import asyncio
        from ..shared.tools.paper_search import PaperSearchTool

        cfg = paper_search_config or {}
        tool = PaperSearchTool(
            serpapi_api_key=cfg.get("serpapi_api_key"),
            semantic_scholar_api_key=cfg.get("semantic_scholar_api_key"),
            timeout=cfg.get("timeout", 10),
            semantic_scholar_min_results_before_fallback=cfg.get(
                "semantic_scholar_min_results_before_fallback", 3
            ),
            enable_query_cache=cfg.get("enable_query_cache", True),
            cache_ttl_hours=cfg.get("cache_ttl_hours", 24),
        )

        # Read configuration for multi-round search
        results_per_round = cfg.get("search_results_per_round", 5)
        max_queries_per_section = cfg.get("planner_max_queries_per_section", 5)
        inter_round_delay = cfg.get("planner_inter_round_delay_sec", 1.5)
        min_target_papers = cfg.get("planner_min_target_papers_per_section", 3)

        # Build search queries from plan — multiple per section for multi-round search
        section_queries: Dict[str, List[str]] = {}
        section_targets: Dict[str, int] = {}  # Target paper count per section

        # --- Top-down citation target computation ---
        # Priority: 1) per-section citation_budget from Planner
        #           2) global citation_strategy from Planner
        #           3) venue-aware estimation + proportional distribution
        body_sections = [
            sp for sp in plan.sections
            if sp.section_type not in ("abstract", "conclusion")
        ]

        strategy = plan.citation_strategy if isinstance(plan.citation_strategy, dict) else {}
        global_total = int(strategy.get("total_target", 0) or 0)
        section_allocation = strategy.get("section_allocation")

        if global_total <= 0:
            # Planner did not provide global strategy; estimate from venue + scale
            total_paras = sum(len(sp.paragraphs) for sp in body_sections)
            global_total = self._estimate_total_citations(
                style_guide=cfg.get("style_guide"),
                n_body_sections=len(body_sections),
                total_paragraphs=total_paras,
            )
            section_allocation = None
            logger.info(
                "planner.citation_strategy fallback: estimated total_target=%d "
                "(venue=%s, body_sections=%d, paragraphs=%d)",
                global_total, cfg.get("style_guide", "unknown"),
                len(body_sections), total_paras,
            )
        else:
            logger.info(
                "planner.citation_strategy from_planner: total_target=%d",
                global_total,
            )

        topdown_targets = self._distribute_citations_topdown(
            total_target=global_total,
            body_sections=body_sections,
            section_allocation=section_allocation,
        )

        for sp in plan.sections:
            if sp.section_type in ("abstract", "conclusion"):
                continue
            key_points = sp.get_key_points()
            if not key_points:
                continue

            # Generate multiple search queries for this section
            queries = await self._generate_search_queries(
                sp.section_type, key_points, existing_ref_keys, plan.title,
            )

            # Store up to N queries per section for multi-round search
            if queries:
                section_queries[sp.section_type] = queries[:max_queries_per_section]
                # Priority: 1) planner per-section budget, 2) top-down allocation
                planner_budget = sp.citation_budget if isinstance(sp.citation_budget, dict) else {}
                planner_target = planner_budget.get("target_refs")
                if planner_target is not None:
                    try:
                        section_targets[sp.section_type] = max(1, int(planner_target))
                    except Exception:
                        section_targets[sp.section_type] = topdown_targets.get(
                            sp.section_type, min_target_papers,
                        )
                else:
                    section_targets[sp.section_type] = topdown_targets.get(
                        sp.section_type, min_target_papers,
                    )

        discovered: Dict[str, List[Dict[str, Any]]] = {}
        seen_keys: set = set(existing_ref_keys)

        for section_type, queries in section_queries.items():
            section_papers: List[Dict[str, Any]] = []
            target_count = section_targets.get(section_type, 3)
            round_num = 0

            # Collect candidates from all planned rounds, then filter/select to target_count.
            while round_num < len(queries):
                query = queries[round_num]

                if round_num > 0:
                    # Rate limiting between rounds with small jitter to reduce burst contention
                    jitter = random.uniform(0, 0.4)
                    await asyncio.sleep(max(0.0, inter_round_delay + jitter))

                try:
                    result = await tool.execute(query=query, max_results=results_per_round)
                    if not result.success:
                        round_num += 1
                        continue

                    papers = result.data.get("papers", []) if result.data else []

                    for paper in papers:
                        bkey = paper.get("bibtex_key", "")
                        bibtex = paper.get("bibtex", "")
                        if bkey and bibtex and bkey not in seen_keys:
                            seen_keys.add(bkey)
                            section_papers.append({
                                "ref_id": bkey,
                                "bibtex": bibtex,
                                "title": paper.get("title", ""),
                                "year": paper.get("year"),
                                "abstract": paper.get("abstract", ""),
                                "venue": paper.get("venue", ""),
                                "citation_count": paper.get("citation_count"),
                            })

                    logger.info(
                        "planner.search_round section=%s round=%d query='%s' found=%d total=%d",
                        section_type, round_num, query[:50], len(papers), len(section_papers),
                    )
                except Exception as e:
                    logger.warning("planner.search_error query='%s': %s", query, e)

                round_num += 1

            # Filter papers by relevance before storing
            if section_papers:
                raw_count = len(section_papers)
                # Get key points for this section from the plan
                section_key_points = []
                for sp in plan.sections:
                    if sp.section_type == section_type:
                        section_key_points = sp.get_key_points()
                        break

                # Filter by relevance using LLM
                filtered_papers = await filter_papers_by_relevance(
                    client=self.client,
                    model_name=self.model_name,
                    logger=logger,
                    papers=section_papers,
                    section_type=section_type,
                    key_points=section_key_points,
                    paper_title=plan.title,
                )
                filtered_count = len(filtered_papers)

                # Keep exactly N when possible: select top target_count by quality.
                filtered_sorted = sorted(
                    filtered_papers,
                    key=lambda p: (
                        float(p.get("relevance_score") or 0.0),
                        int(p.get("citation_count") or 0),
                        int(p.get("year") or 0),
                    ),
                    reverse=True,
                )
                selected_papers = filtered_sorted[:target_count] if target_count > 0 else filtered_sorted

                if selected_papers:
                    discovered[section_type] = selected_papers
                    logger.info(
                        "planner.discovered_refs section=%s target=%d raw=%d filtered=%d selected=%d",
                        section_type, target_count, raw_count, filtered_count, len(selected_papers),
                    )

        total = sum(len(v) for v in discovered.values())
        logger.info("planner.reference_discovery_complete total=%d", total)
        return discovered

    @staticmethod
    def _claim_matrix_refs_for_section(
        research_context: Optional[Dict[str, Any]],
        section_type: str,
    ) -> List[str]:
        """Delegate to shared helper (kept for backward compatibility)."""
        return claim_matrix_refs_for_section(research_context, section_type)

    def assign_references(
        self,
        plan: "PaperPlan",
        discovered: Dict[str, List[Dict[str, Any]]],
        core_ref_keys: List[str],
        paper_search_config: Optional[Dict[str, Any]] = None,
        research_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Distribute references to sections, populating SectionPlan.assigned_refs.

        - **Description**:
            - Discovered refs are assigned to the section they were found for.
            - Core (user-provided) refs are assigned to all body sections
              so every section can cite them.
            - Abstract and conclusion get NO refs (citations forbidden there).
            - A single ref can appear in multiple sections.
            - If research_context is provided with claim_evidence_matrix, use it
              for smarter reference assignment (refs that support claims get priority).

        - **Args**:
            - `plan` (PaperPlan): The paper plan to mutate in-place.
            - `discovered` (Dict[str, List[Dict]]): section_type -> papers from
              discover_references().
            - `core_ref_keys` (List[str]): Citation keys of user-provided refs.
            - `paper_search_config` (Optional[Dict[str, Any]]): Search configuration.
            - `research_context` (Optional[Dict[str, Any]]): Research context with
              ``claim_evidence_matrix`` for claim-aware reference priority.
        """
        return assign_references_helper(
            plan=plan,
            discovered=discovered,
            core_ref_keys=core_ref_keys,
            paper_search_config=paper_search_config,
            research_context=research_context,
            logger=logger,
            estimate_total_citations_fn=self._estimate_total_citations,
            distribute_citations_topdown_fn=self._distribute_citations_topdown,
            rank_references_for_section_fn=self._rank_references_for_section,
            infer_section_citation_budget_fn=self._infer_section_citation_budget,
        )
        cfg = paper_search_config or {}
        budget_enabled = cfg.get("citation_budget_enabled", True)
        soft_cap = cfg.get("citation_budget_soft_cap", True)
        reserve_size = max(1, int(cfg.get("citation_budget_reserve_size", 4)))

        no_cite_sections = {"abstract", "conclusion"}

        # Compute top-down allocation for fallback
        body_sections = [
            sp for sp in plan.sections
            if sp.section_type not in no_cite_sections
        ]
        strategy = plan.citation_strategy if isinstance(plan.citation_strategy, dict) else {}
        global_total = int(strategy.get("total_target", 0) or 0)
        section_allocation = strategy.get("section_allocation")

        if global_total <= 0:
            total_paras = sum(len(sp.paragraphs) for sp in body_sections)
            global_total = self._estimate_total_citations(
                style_guide=cfg.get("style_guide"),
                n_body_sections=len(body_sections),
                total_paragraphs=total_paras,
            )
            section_allocation = None

        topdown_targets = self._distribute_citations_topdown(
            total_target=global_total,
            body_sections=body_sections,
            section_allocation=section_allocation,
        )

        for sp in plan.sections:
            if sp.section_type in no_cite_sections:
                sp.assigned_refs = []
                sp.budget_selected_refs = []
                sp.budget_reserve_refs = []
                sp.budget_must_use_refs = []
                sp.citation_budget = {
                    "enabled": budget_enabled,
                    "min_refs": 0,
                    "target_refs": 0,
                    "max_refs": 0,
                    "candidate_count": 0,
                    "selected_count": 0,
                    "soft_cap": soft_cap,
                }
                continue

            discovered_for_section = discovered.get(sp.section_type, [])
            discovered_ranked = self._rank_references_for_section(discovered_for_section)
            planner_hint_refs = [r for r in sp.get_all_references() if r]
            claim_refs = self._claim_matrix_refs_for_section(
                research_context, sp.section_type,
            )
            budget = self._infer_section_citation_budget(
                section_type=sp.section_type,
                paragraph_count=len(sp.paragraphs),
                candidate_refs=discovered_ranked,
                planner_hint_refs=planner_hint_refs,
                core_ref_keys=core_ref_keys,
                planner_budget=sp.citation_budget if isinstance(sp.citation_budget, dict) else {},
                topdown_target=topdown_targets.get(sp.section_type),
                claim_matrix_refs=claim_refs,
            )

            if not budget_enabled:
                refs: List[str] = []
                for rid in claim_refs:
                    if rid not in refs:
                        refs.append(rid)
                for rid in core_ref_keys:
                    if rid not in refs:
                        refs.append(rid)
                for paper in discovered_ranked:
                    rid = paper.get("ref_id", "")
                    if rid and rid not in refs:
                        refs.append(rid)
                sp.assigned_refs = refs
                sp.budget_selected_refs = refs
                sp.budget_reserve_refs = []
                sp.budget_must_use_refs = planner_hint_refs[:3]
                budget["enabled"] = False
                budget["selected_count"] = len(refs)
                sp.citation_budget = budget
                continue

            selected_refs = list(budget.get("selected_refs", []))
            reserve_refs = list(budget.get("reserve_refs", []))
            must_use_refs = list(budget.get("must_use_refs", []))

            if not selected_refs:
                fallback = [k for k in planner_hint_refs if k in core_ref_keys]
                selected_refs = fallback[: max(1, budget.get("target_refs", 1))]
            sp.assigned_refs = selected_refs
            sp.budget_selected_refs = selected_refs
            sp.budget_reserve_refs = reserve_refs[:reserve_size]
            sp.budget_must_use_refs = must_use_refs
            budget["enabled"] = True
            budget["selected_count"] = len(selected_refs)
            budget["soft_cap"] = soft_cap
            sp.citation_budget = budget

        assigned_counts = {
            sp.section_type: len(sp.assigned_refs)
            for sp in plan.sections if sp.assigned_refs
        }
        logger.info("planner.assign_references result=%s", assigned_counts)

    # =================================================================
    # Incremental Planning: Step 4 -- Per-Section Structure Decision
    # =================================================================

    # =================================================================
    # Incremental Planning: Step 5a -- Flat Paragraph Plan
    # =================================================================

    # =================================================================
    # Incremental Planning: Step 5b -- Subsection Paragraph Plans
    # =================================================================

    async def _create_default_plan(
        self, request: PlanRequest, total_words: int,
    ) -> PaperPlan:
        """Create a default plan when LLM fails."""
        plan = create_default_plan(
            request=request,
            total_words=total_words,
            words_per_sentence=WORDS_PER_SENTENCE,
            generate_default_paragraphs_fn=self._generate_default_paragraphs,
        )
        await self._assign_figure_table_definitions(plan, request, None, None)
        return plan

    # =====================================================================
    # Helpers
    # =====================================================================

    @staticmethod
    def _parse_plan_json(text: str) -> Dict[str, Any]:
        parsed = safe_load_json(text, expected=dict)
        if parsed is None:
            logger.warning("planner.json_parse_error, using defaults")
            return {}
        return parsed

    async def create_plan_from_metadata(
        self,
        title: str,
        idea_hypothesis: str,
        method: str,
        data: str,
        experiments: str,
        references: List[str],
        target_pages: Optional[int] = None,
        style_guide: Optional[str] = None,
    ) -> PaperPlan:
        """Convenience method to create plan from individual fields."""
        request = PlanRequest(
            title=title,
            idea_hypothesis=idea_hypothesis,
            method=method,
            data=data,
            experiments=experiments,
            references=references,
            target_pages=target_pages,
            style_guide=style_guide,
        )
        return await self.create_plan(request)
