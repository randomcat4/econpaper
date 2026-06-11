"""
Typesetter Agent
- **Description**:
    - Handles resource fetching, template injection, and LaTeX compilation
    - Implements self-healing compilation with error recovery
"""
from langchain_core.messages import AnyMessage
from ..shared.llm_client import LLMClient
from typing_extensions import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, START, END
import operator
import os
import re
import shutil
import tempfile
import subprocess
import zipfile
import httpx
import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Any, Set
from jinja2 import Template
from ...config.schema import ModelConfig
from ..base import BaseAgent
from .models import ResourceInfo, BibEntry, CompilationResult, TemplateConfig, TemplateStructureProfile
from ..shared.tex_path_bootstrap import ensure_tex_bin_on_path
from .typesetter_helpers import (
    build_figure_id_map,
    build_preamble_from_config,
    extract_citations_from_content,
    extract_includegraphics_targets,
    generate_bibtex_entry,
    resolve_figure_ids,
    rewrite_includegraphics_targets,
    strip_graphics_extension,
)

if TYPE_CHECKING:
    from fastapi import APIRouter
from .typesetter_sections import (
    apply_citation_style,
    normalize_abstract,
    strip_all_section_commands,
    strip_leading_section_command,
    write_section_files,
)
from .typesetter_template import (
    analyze_template_structure,
    ensure_maketitle_present,
    extract_bib_commands,
    find_brace_end,
    find_bracket_end,
    promote_wide_tables,
    remove_abstract_command,
    replace_abstract_command,
    replace_all_authors,
    smart_inject_content,
    validate_compiled_tex_structure,
)
from .typesetter_diagnostics import (
    build_detection_body,
    copy_to_output_dir,
    extract_document_body,
    extract_errors,
    extract_section_errors,
    extract_warnings,
    expand_tex_includes_for_detection,
    has_tex_command,
    resolve_include_path,
    save_diagnostics_on_failure,
    strip_tex_comments,
)


# Backend API URL for fetching resources
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:9001/api")

# Logger for typesetter agent
logger = logging.getLogger("uvicorn.error")

# Maximum compilation attempts for self-healing
MAX_COMPILE_ATTEMPTS = 3


# Jinja2 template for injecting content into main.tex
MAIN_TEX_TEMPLATE = """{{ preamble }}

\\begin{document}

\\maketitle

{{ content }}

{% if has_bibliography %}
\\bibliographystyle{ {{- bib_style -}} }
\\bibliography{references}
{% endif %}

\\end{document}
"""


class TypesetterAgentState(TypedDict):
    """
    State for Typesetter Agent workflow
    """
    messages: Annotated[list[AnyMessage], operator.add]
    latex_content: Optional[str]  # Legacy single-document path
    sections: Optional[Dict[str, str]]  # Multi-file mode: section_type -> content
    section_order: Optional[List[str]]  # Multi-file mode: body section ordering
    section_titles: Optional[Dict[str, str]]  # Multi-file mode: section_type -> display title
    template_path: Optional[str]
    template_config: Optional[TemplateConfig]  # Template configuration with constraints
    figure_ids: Optional[List[str]]
    citation_ids: Optional[List[str]]
    references: Optional[List[Dict[str, Any]]]
    canonical_bibtex: Optional[str]
    work_id: Optional[str]
    output_dir: Optional[str]  # User-specified output directory for final files
    figures_source_dir: Optional[str]  # Local directory with figure files to copy
    figure_paths: Optional[Dict[str, str]]  # Structured figure paths: id -> file_path
    converted_tables: Optional[Dict[str, str]]  # Pre-converted table LaTeX: id -> latex_code
    work_dir: Optional[str]  # Temporary working directory for compilation
    main_tex_path: Optional[str]  # Path to detected main tex file
    resources: Optional[List[ResourceInfo]]
    bib_entries: Optional[List[BibEntry]]
    compiled_tex: Optional[str]
    section_file_map: Optional[Dict[str, str]]  # Multi-file mode: section_type -> rel path
    compilation_result: Optional[CompilationResult]
    llm_calls: int


class TypesetterAgent(BaseAgent):
    """
    Typesetter Agent for LaTeX compilation
    - **Description**:
        - Fetches resources from backend
        - Generates BibTeX file
        - Injects content into template
        - Compiles LaTeX with self-healing
    """

    def __init__(self, config: ModelConfig):
        self.client = LLMClient(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.model_name = config.model_name
        self.agent = self.init_agent()

    _extract_includegraphics_targets = staticmethod(extract_includegraphics_targets)
    _strip_graphics_extension = staticmethod(strip_graphics_extension)
    _generate_bibtex_entry = staticmethod(generate_bibtex_entry)
    _build_preamble_from_config = staticmethod(build_preamble_from_config)
    _apply_citation_style = staticmethod(apply_citation_style)
    _normalize_abstract = staticmethod(normalize_abstract)
    _smart_inject_content = staticmethod(smart_inject_content)
    _validate_compiled_tex_structure = staticmethod(validate_compiled_tex_structure)
    _ensure_maketitle_present = staticmethod(ensure_maketitle_present)
    _replace_all_authors = staticmethod(replace_all_authors)
    _replace_abstract_command = staticmethod(replace_abstract_command)
    _remove_abstract_command = staticmethod(remove_abstract_command)
    _extract_bib_commands = staticmethod(extract_bib_commands)
    _find_brace_end = staticmethod(find_brace_end)
    _analyze_template_structure = staticmethod(analyze_template_structure)
    _find_bracket_end = staticmethod(find_bracket_end)
    _promote_wide_tables = staticmethod(promote_wide_tables)
    _strip_tex_comments = staticmethod(strip_tex_comments)
    _extract_document_body = staticmethod(extract_document_body)
    _resolve_include_path = staticmethod(resolve_include_path)
    _has_tex_command = staticmethod(has_tex_command)
    _extract_errors = staticmethod(extract_errors)
    _extract_warnings = staticmethod(extract_warnings)
    _extract_section_errors = staticmethod(extract_section_errors)

    def init_agent(self):
        """
        Initialize the agent workflow graph
        """
        agent_builder = StateGraph(TypesetterAgentState)
        agent_builder.add_node("setup_workspace", self.setup_workspace)
        agent_builder.add_node("fetch_resources", self.fetch_resources)
        agent_builder.add_node("generate_bibtex", self.generate_bibtex)
        agent_builder.add_node("inject_template", self.inject_template)
        agent_builder.add_node("compile_latex", self.compile_latex)

        agent_builder.add_edge(START, "setup_workspace")
        agent_builder.add_edge("setup_workspace", "fetch_resources")
        agent_builder.add_edge("fetch_resources", "generate_bibtex")
        agent_builder.add_edge("generate_bibtex", "inject_template")
        agent_builder.add_edge("inject_template", "compile_latex")
        agent_builder.add_edge("compile_latex", END)

        return agent_builder.compile()

    def _find_main_tex(self, work_dir: str) -> Optional[str]:
        """
        Find the main tex file containing documentclass
        - **Description**:
            - Searches for .tex files with both \\documentclass and \\begin{document}
            - Prefers files named main.tex or containing 'paper' in name

        - **Args**:
            - `work_dir` (str): Directory to search

        - **Returns**:
            - `str`: Path to main tex file, or None if not found
        """
        candidates = []

        for root, dirs, files in os.walk(work_dir):
            for f in files:
                if f.endswith('.tex'):
                    path = os.path.join(root, f)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as file:
                            content = file.read()
                            if '\\documentclass' in content and '\\begin{document}' in content:
                                # Calculate priority: lower is better
                                priority = 10
                                fname_lower = f.lower()
                                if fname_lower == 'main.tex':
                                    priority = 0
                                elif 'paper' in fname_lower:
                                    priority = 1
                                elif 'example' in fname_lower:
                                    priority = 2
                                candidates.append((priority, path))
                    except Exception:
                        continue

        if candidates:
            # Sort by priority and return best match
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

        return None

    @staticmethod
    def _flatten_support_files(work_dir: str) -> None:
        """
        Copy .bst, .cls, .sty files from subdirectories to work_dir root.
        - **Description**:
            - Template zips often nest support files in subdirectories
              (e.g. ``bst/``, ``styles/``). BibTeX and pdflatex only search
              the current directory by default, so these must be at the root.

        - **Args**:
            - `work_dir` (str): The compilation working directory.
        """
        extensions = ('.bst', '.cls', '.sty')
        for root, _dirs, files in os.walk(work_dir):
            if root == work_dir:
                continue
            for fname in files:
                if fname.endswith(extensions):
                    src = os.path.join(root, fname)
                    dst = os.path.join(work_dir, fname)
                    if not os.path.exists(dst):
                        shutil.copy2(src, dst)
                        logger.info("typesetter.flattened_support_file %s", fname)

    async def setup_workspace(self, state: TypesetterAgentState) -> Dict[str, Any]:
        """
        Set up temporary workspace for compilation
        - **Description**:
            - Creates temporary directory structure
            - Extracts template if provided
            - Detects main tex file automatically

        - **Args**:
            - `state` (TypesetterAgentState): Current workflow state

        - **Returns**:
            - `dict`: Updated state with work_dir and main_tex_path
        """
        logger.info("typesetter.setup_workspace start")

        # Create temporary directory
        work_dir = tempfile.mkdtemp(prefix="typesetter_")
        figures_dir = os.path.join(work_dir, "figures")
        os.makedirs(figures_dir, exist_ok=True)
        logger.info("typesetter.setup_workspace work_dir=%s", work_dir)

        # Extract template if provided
        template_path = state.get("template_path")
        main_tex_path = None

        if template_path and os.path.exists(template_path):
            if template_path.endswith('.zip'):
                logger.info("typesetter.extracting_template path=%s", template_path)
                with zipfile.ZipFile(template_path, 'r') as zip_ref:
                    zip_ref.extractall(work_dir)

                # Detect main tex file
                main_tex_path = self._find_main_tex(work_dir)
                if main_tex_path:
                    logger.info("typesetter.detected_main_tex file=%s", os.path.basename(main_tex_path))
                    # Flatten .bst/.cls/.sty files to the work_dir root so
                    # pdflatex/bibtex can find them regardless of zip structure
                    self._flatten_support_files(work_dir)
                else:
                    logger.warning("typesetter.no_main_tex_found")

        # Copy figures from local source directory if provided (legacy)
        figures_source_dir = state.get("figures_source_dir")
        if figures_source_dir and os.path.isdir(figures_source_dir):
            logger.info("typesetter.copying_local_figures source=%s", figures_source_dir)
            copied_count = 0
            for item in os.listdir(figures_source_dir):
                src_path = os.path.join(figures_source_dir, item)
                if os.path.isfile(src_path):
                    # Copy figure file to work_dir/figures/
                    dst_path = os.path.join(figures_dir, item)
                    try:
                        shutil.copy2(src_path, dst_path)
                        copied_count += 1
                    except Exception as e:
                        logger.warning("typesetter.figure_copy_failed file=%s error=%s", item, str(e))
            logger.info("typesetter.local_figures_copied count=%d", copied_count)

        # Copy figures from structured figure_paths (new method)
        figure_paths = state.get("figure_paths", {})
        if figure_paths:
            logger.info("typesetter.copying_structured_figures count=%d", len(figure_paths))
            for fig_id, file_path in figure_paths.items():
                if file_path and os.path.exists(file_path):
                    # Keep original filename for reference
                    filename = os.path.basename(file_path)
                    dst_path = os.path.join(figures_dir, filename)
                    try:
                        shutil.copy2(file_path, dst_path)
                        logger.info("typesetter.figure_copied id=%s path=%s", fig_id, dst_path)
                    except Exception as e:
                        logger.warning("typesetter.figure_copy_failed id=%s error=%s", fig_id, str(e))
                else:
                    logger.warning("typesetter.figure_not_found id=%s path=%s", fig_id, file_path)

        return {"work_dir": work_dir, "main_tex_path": main_tex_path}

    async def fetch_resources(self, state: TypesetterAgentState) -> Dict[str, Any]:
        """
        Fetch figure resources from backend
        - **Description**:
            - Downloads figures referenced in the LaTeX content

        - **Args**:
            - `state` (TypesetterAgentState): Current workflow state

        - **Returns**:
            - `dict`: Updated state with fetched resources
        """
        print(f"INPUT STATE [fetch_resources]: figure_ids={state.get('figure_ids')}")

        work_dir = state.get("work_dir")
        figure_ids = self._resolve_figure_ids(state)
        figures_dir = os.path.join(work_dir, "figures")

        resources = []

        async with httpx.AsyncClient() as client:
            for fig_id in figure_ids:
                resource = ResourceInfo(
                    resource_id=fig_id,
                    resource_type="figure",
                    status="pending"
                )

                try:
                    # Try to fetch figure from backend
                    # Figure path format: figures/{filename}
                    response = await client.get(
                        f"{BACKEND_API_URL}/files/figures/{fig_id}",
                        timeout=30.0
                    )

                    if response.status_code == 200:
                        # Determine file extension from content-type
                        content_type = response.headers.get("content-type", "")
                        ext = ".png"
                        if "pdf" in content_type:
                            ext = ".pdf"
                        elif "jpeg" in content_type or "jpg" in content_type:
                            ext = ".jpg"
                        elif "svg" in content_type:
                            ext = ".svg"

                        local_path = os.path.join(figures_dir, f"{fig_id}{ext}")
                        with open(local_path, "wb") as f:
                            f.write(response.content)

                        resource.local_path = local_path
                        resource.status = "downloaded"
                    else:
                        resource.status = "failed"

                except Exception as e:
                    print(f"Failed to fetch figure {fig_id}: {e}")
                    resource.status = "failed"

                resources.append(resource)

        return {"resources": resources, "figure_ids": figure_ids}

    def _resolve_figure_ids(self, state: TypesetterAgentState) -> List[str]:
        return resolve_figure_ids(state, self._extract_includegraphics_targets)

    def _build_figure_id_map(
        self,
        figure_paths: Dict[str, str],
        work_dir: str,
    ) -> Dict[str, str]:
        return build_figure_id_map(figure_paths, work_dir)

    def _rewrite_includegraphics_targets(
        self,
        content: str,
        work_dir: str,
        id_to_rel_path: Dict[str, str],
    ) -> str:
        return rewrite_includegraphics_targets(content, work_dir, id_to_rel_path)

    def _extract_citations_from_content(self, latex_content: str) -> List[str]:
        return extract_citations_from_content(latex_content)

    def _write_section_files(
        self,
        work_dir: str,
        sections: Dict[str, str],
        section_order: Optional[List[str]] = None,
        section_titles: Optional[Dict[str, str]] = None,
        citation_style: str = "cite",
        use_appendices_env: bool = False,
    ) -> Dict[str, str]:
        return write_section_files(
            work_dir=work_dir,
            sections=sections,
            section_order=section_order,
            section_titles=section_titles,
            citation_style=citation_style,
            use_appendices_env=use_appendices_env,
            strip_leading_section_command_fn=self._strip_leading_section_command,
            apply_citation_style_fn=self._apply_citation_style,
            logger=logger,
        )

    @staticmethod
    def _strip_leading_section_command(content: str) -> str:
        return strip_leading_section_command(content, TypesetterAgent._strip_all_section_commands)

    @staticmethod
    def _strip_all_section_commands(content: str) -> str:
        return strip_all_section_commands(content, TypesetterAgent._find_brace_end)

    def _save_diagnostics_on_failure(self, work_dir: str, output_dir: str) -> None:
        return save_diagnostics_on_failure(work_dir, output_dir, logger)

    def _copy_to_output_dir(self, work_dir: str, output_dir: str) -> Dict[str, str]:
        return copy_to_output_dir(work_dir, output_dir, logger)

    def _expand_tex_includes_for_detection(
        self,
        content: str,
        current_file: str,
        work_dir: str,
        visited: Set[str],
    ) -> str:
        return expand_tex_includes_for_detection(
            content=content,
            current_file=current_file,
            work_dir=work_dir,
            visited=visited,
            logger=logger,
        )

    def _build_detection_body(
        self,
        tex_src: str,
        main_tex: str,
        work_dir: str,
    ) -> str:
        return build_detection_body(
            tex_src=tex_src,
            main_tex=main_tex,
            work_dir=work_dir,
            logger=logger,
        )

    async def generate_bibtex(self, state: TypesetterAgentState) -> Dict[str, Any]:
        """
        Generate BibTeX file from references
        - **Description**:
            - Creates references.bib from provided reference data
            - Prioritizes raw bibtex string if provided
            - Auto-extracts citation keys from section content to find needed refs

        - **Args**:
            - `state` (TypesetterAgentState): Current workflow state

        - **Returns**:
            - `dict`: Updated state with bib_entries
        """
        work_dir = state.get("work_dir")
        references = state.get("references", [])
        canonical_bibtex = state.get("canonical_bibtex")
        sections_dict = state.get("sections") or {}
        latex_content = state.get("latex_content") or ""

        if canonical_bibtex is not None:
            bib_path = os.path.join(work_dir, "references.bib")
            with open(bib_path, "w", encoding="utf-8") as f:
                f.write(canonical_bibtex)
            bib_entries = [
                BibEntry(
                    key=ref.get("ref_id") or ref.get("id") or "unknown",
                    entry_type="article",
                    title=ref.get("title", ""),
                    raw_bibtex=ref.get("bibtex"),
                )
                for ref in references
                if ref.get("bibtex")
            ]
            logger.info(
                "typesetter.written_canonical_bibtex entries=%d path=%s",
                len(bib_entries),
                bib_path,
            )
            return {"bib_entries": bib_entries}

        # Extract citation keys from all section content.
        all_content = "\n".join(sec_content for sec_content in sections_dict.values())
        if not all_content.strip() and latex_content.strip():
            all_content = latex_content
        citation_ids = self._extract_citations_from_content(all_content) if all_content.strip() else []
        logger.info("typesetter.extracted_citations count=%d keys=%s (sections=%d)",
                   len(citation_ids), citation_ids[:5] if len(citation_ids) > 5 else citation_ids,
                   len(sections_dict))

        bib_entries = []
        bib_content_parts = []

        # Build reference map from provided references
        # Support both "id" and "ref_id" keys for flexibility
        ref_map = {}
        for ref in references:
            ref_id = ref.get("ref_id") or ref.get("id")
            if ref_id:
                ref_map[ref_id] = ref

        logger.info("typesetter.provided_references count=%d keys=%s",
                   len(ref_map), list(ref_map.keys())[:5])

        # Generate entries for references we have data for
        for cid in citation_ids:
            ref = ref_map.get(cid)

            if ref:
                # Check if raw bibtex is provided - use it directly
                if ref.get("bibtex"):
                    bib_content_parts.append(ref["bibtex"].strip())
                    # Still create a BibEntry for tracking
                    entry = BibEntry(
                        key=cid,
                        entry_type="article",
                        title=ref.get("title", ""),
                        raw_bibtex=ref["bibtex"],
                    )
                    bib_entries.append(entry)
                else:
                    # Generate from structured data
                    entry = BibEntry(
                        key=cid,
                        entry_type=ref.get("entry_type", "article"),
                        title=ref.get("title", "Untitled"),
                        authors=ref.get("authors"),
                        year=ref.get("year"),
                        doi=ref.get("doi"),
                        url=ref.get("url"),
                        venue=ref.get("venue"),
                        journal=ref.get("journal"),
                        booktitle=ref.get("booktitle"),
                    )
                    bib_entries.append(entry)
                    bib_str = self._generate_bibtex_entry(entry)
                    bib_content_parts.append(bib_str)
            else:
                # Skip - reference data should be provided by upstream
                logger.warning("typesetter.missing_reference key=%s (should be provided by upstream)", cid)

        # Safety fallback: if no citation keys extracted but references exist,
        # write ALL provided references to .bib (ensures bibtex is never empty
        # when references are available)
        if not bib_content_parts and references:
            logger.warning("typesetter.no_citations_extracted_but_refs_exist count=%d — writing all refs as fallback", len(references))
            for ref in references:
                if ref.get("bibtex"):
                    bib_content_parts.append(ref["bibtex"].strip())
                    ref_id = ref.get("ref_id") or ref.get("id") or "unknown"
                    bib_entries.append(BibEntry(
                        key=ref_id,
                        entry_type="article",
                        title=ref.get("title", ""),
                        raw_bibtex=ref["bibtex"],
                    ))

        # Write references.bib
        bib_path = os.path.join(work_dir, "references.bib")
        with open(bib_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(bib_content_parts))

        logger.info("typesetter.written_bibtex entries=%d path=%s", len(bib_entries), bib_path)

        return {"bib_entries": bib_entries}

    # Default section ordering and titles for multi-file mode
    DEFAULT_SECTION_ORDER = [
        "introduction", "related_work", "method", "experiment", "result", "conclusion",
    ]
    DEFAULT_SECTION_TITLES = {
        "introduction": "Introduction",
        "related_work": "Related Work",
        "method": "Methodology",
        "experiment": "Experiments",
        "result": "Results",
        "conclusion": "Conclusion",
        "appendix": "Appendix",
    }

    def _smart_inject_content(self, template_content: str, sections: Dict[str, str],
                              template_config: TemplateConfig, bib_entries: List[BibEntry],
                              profile: Optional[TemplateStructureProfile] = None) -> str:
        return smart_inject_content(
            template_content=template_content,
            sections=sections,
            template_config=template_config,
            bib_entries=bib_entries,
            profile=profile,
        )

    @staticmethod
    def _validate_compiled_tex_structure(compiled_tex: str) -> List[str]:
        return validate_compiled_tex_structure(compiled_tex)

    @staticmethod
    def _ensure_maketitle_present(
        text: str,
        profile: Optional[TemplateStructureProfile] = None,
    ) -> str:
        return ensure_maketitle_present(text, profile=profile)

    @staticmethod
    def _replace_all_authors(text: str, new_author: str) -> str:
        return replace_all_authors(text, new_author)

    @staticmethod
    def _replace_abstract_command(text: str, new_content: str) -> str:
        return replace_abstract_command(text, new_content)

    @staticmethod
    def _remove_abstract_command(text: str) -> str:
        return remove_abstract_command(text)

    @staticmethod
    def _extract_bib_commands(text: str) -> str:
        return extract_bib_commands(text)

    @staticmethod
    def _find_brace_end(text: str, open_brace_pos: int) -> int:
        return find_brace_end(text, open_brace_pos)

    @staticmethod
    def _analyze_template_structure(template_tex: str) -> TemplateStructureProfile:
        return analyze_template_structure(template_tex)

    @staticmethod
    def _find_bracket_end(text: str, open_bracket_pos: int) -> int:
        return find_bracket_end(text, open_bracket_pos)

    @staticmethod
    def _promote_wide_tables(content: str, column_threshold: int = 5) -> str:
        return promote_wide_tables(content, column_threshold=column_threshold)

    async def inject_template(self, state: TypesetterAgentState) -> Dict[str, Any]:
        """
        Inject content into LaTeX template
        - **Description**:
            - Uses sections dict input, writing each section to its own `.tex` file
              while `main.tex` references them with `\\input{sections/xxx}`.
            - Smart injection that handles title, abstract, and sections
            - Uses detected main_tex_path from template
            - Falls back to building from TemplateConfig if no template

        - **Args**:
            - `state` (TypesetterAgentState): Current workflow state

        - **Returns**:
            - `dict`: Updated state with compiled_tex and optionally section_file_map
        """
        logger.info("typesetter.inject_template start")

        work_dir = state.get("work_dir")
        latex_content = state.get("latex_content") or ""
        sections_dict = state.get("sections")
        section_order = state.get("section_order")
        section_titles = state.get("section_titles")
        resources = state.get("resources", [])
        bib_entries = state.get("bib_entries", [])
        template_config = state.get("template_config")
        main_tex_path = state.get("main_tex_path")
        figure_paths = state.get("figure_paths", {}) or {}

        id_to_rel_path: Dict[str, str] = {}
        for resource in resources:
            if resource.status == "downloaded" and resource.local_path:
                rel_path = os.path.relpath(resource.local_path, work_dir)
                id_to_rel_path[str(resource.resource_id)] = self._strip_graphics_extension(rel_path)
        id_to_rel_path.update(self._build_figure_id_map(figure_paths, work_dir))

        # Create default template_config if not provided
        if template_config is None:
            template_config = TemplateConfig()
        if not (template_config.paper_title or "").strip():
            raise ValueError("typesetter.inject_template requires non-empty template_config.paper_title")

        # Determine final main.tex path
        final_main_tex = os.path.join(work_dir, "main.tex")

        if not sections_dict:
            if not latex_content.strip():
                raise ValueError("typesetter.inject_template requires sections content or latex_content")
            compiled_tex = self._rewrite_includegraphics_targets(
                latex_content,
                work_dir=work_dir,
                id_to_rel_path=id_to_rel_path,
            )
            with open(final_main_tex, "w", encoding="utf-8") as f:
                f.write(compiled_tex)
            logger.info("typesetter.inject_template mode=legacy_latex_content chars=%d", len(compiled_tex))
            return {"compiled_tex": compiled_tex, "section_file_map": {}}

        logger.info("typesetter.inject_template mode=multi-file sections=%s",
                    list(sections_dict.keys()))

        # Resolve includegraphics targets in each section.
        for sec_type in list(sections_dict.keys()):
            sections_dict[sec_type] = self._rewrite_includegraphics_targets(
                sections_dict[sec_type],
                work_dir=work_dir,
                id_to_rel_path=id_to_rel_path,
            )

        # Detect whether the template uses the appendix package's
        # \begin{appendices} environment (e.g. Springer Nature templates).
        _use_appendices_env = False
        if main_tex_path and os.path.exists(main_tex_path):
            with open(main_tex_path, "r", encoding="utf-8", errors="ignore") as _tf:
                _tpl_src = _tf.read()
            _use_appendices_env = bool(
                re.search(r'\\usepackage(?:\[.*?\])?\{appendix\}', _tpl_src)
                or r'\begin{appendices}' in _tpl_src
            )
            if _use_appendices_env:
                logger.info("typesetter.appendix_format detected=appendices_env")

        # Write individual section files
        section_file_map = self._write_section_files(
            work_dir=work_dir,
            sections=sections_dict,
            section_order=section_order,
            section_titles=section_titles,
            citation_style=template_config.citation_style,
            use_appendices_env=_use_appendices_env,
        )

        # Build \input{} commands for body sections
        order = section_order or self.DEFAULT_SECTION_ORDER
        input_commands = []
        for sec_type in order:
            if sec_type in section_file_map:
                input_commands.append(f"\\input{{{section_file_map[sec_type]}}}")
        # Add any extra sections not in the order
        for sec_type, rel_path in section_file_map.items():
            if sec_type != "abstract" and sec_type not in order:
                input_commands.append(f"\\input{{{rel_path}}}")

        body_input_text = "\n\n".join(input_commands)

        # Abstract is inlined into main.tex (do not use sections/abstract.tex)
        abstract_inline = ""
        if sections_dict.get("abstract", "").strip():
            abstract_inline = self._normalize_abstract(sections_dict["abstract"])
            # Strip LaTeX boilerplate the LLM may have generated
            abstract_inline = re.sub(r'\\title\{[^}]*\}\s*', '', abstract_inline)
            abstract_inline = re.sub(r'\\maketitle\s*', '', abstract_inline)
            abstract_inline = re.sub(r'\\begin\{abstract\}\s*', '', abstract_inline)
            abstract_inline = re.sub(r'\s*\\end\{abstract\}', '', abstract_inline)
            abstract_inline = self._apply_citation_style(abstract_inline, template_config.citation_style)
            abstract_inline = re.sub(r'(?<!\\)%', r'\\%', abstract_inline).strip()
        if not abstract_inline:
            raise ValueError("typesetter.inject_template missing abstract content in multi-file mode")

        # Conclusion is written as sections/conclusion.tex via
        # _write_section_files and included via \input in body_input_text.

        # Inject into template
        if main_tex_path and os.path.exists(main_tex_path):
            logger.info("typesetter.using_template file=%s", os.path.basename(main_tex_path))
            with open(main_tex_path, "r", encoding="utf-8", errors="ignore") as f:
                template_content = f.read()

            # Build a sections dict compatible with _smart_inject_content
            # but using \input commands instead of inline content
            input_sections = {
                "abstract": abstract_inline,
                "body": body_input_text,
            }
            compiled_tex = self._smart_inject_content(
                template_content, input_sections, template_config, bib_entries
            )
            structure_errors = self._validate_compiled_tex_structure(compiled_tex)
            if structure_errors:
                raise ValueError(
                    f"typesetter.inject_template structure validation failed: {structure_errors}"
                )

            # Copy template directory files if needed
            if main_tex_path != final_main_tex:
                template_dir = os.path.dirname(main_tex_path)
                if template_dir != work_dir:
                    for item in os.listdir(template_dir):
                        src = os.path.join(template_dir, item)
                        dst = os.path.join(work_dir, item)
                        if os.path.isfile(src) and not os.path.exists(dst):
                            shutil.copy2(src, dst)
        else:
            # No template - build from config with \input commands
            logger.info("typesetter.no_template building_from_config mode=multi-file")
            preamble = self._build_preamble_from_config(template_config)

            full_content = ""
            if abstract_inline:
                full_content = f"\\begin{{abstract}}\n{abstract_inline}\n\\end{{abstract}}\n\n"
            full_content += body_input_text

            bib_style = template_config.bib_style or "plain"
            template = Template(MAIN_TEX_TEMPLATE)
            compiled_tex = template.render(
                preamble=preamble,
                content=full_content,
                has_bibliography=len(bib_entries) > 0,
                bib_style=bib_style,
            )
            structure_errors = self._validate_compiled_tex_structure(compiled_tex)
            if structure_errors:
                raise ValueError(
                    f"typesetter.inject_template structure validation failed: {structure_errors}"
                )

        # Write main.tex
        with open(final_main_tex, "w", encoding="utf-8") as f:
            f.write(compiled_tex)
        logger.info("typesetter.written_main_tex chars=%d mode=multi-file", len(compiled_tex))

        return {"compiled_tex": compiled_tex, "section_file_map": section_file_map}

    async def compile_latex(self, state: TypesetterAgentState) -> Dict[str, Any]:
        """
        Compile LaTeX with self-healing
        - **Description**:
            - Runs pdflatex -> bibtex -> pdflatex compilation
            - Copies results to output_dir if specified
            - Attempts to fix common errors automatically

        - **Args**:
            - `state` (TypesetterAgentState): Current workflow state

        - **Returns**:
            - `dict`: Updated state with compilation_result
        """
        logger.info("typesetter.compile_latex start")
        if not ensure_tex_bin_on_path(logger):
            logger.warning(
                "typesetter.tex_path_bootstrap_failed "
                "hint=install_MiKTeX_or_TeXLive_and_add_bin_to_PATH_or_run_scripts/check_toolchain.py"
            )

        work_dir = state.get("work_dir")
        output_dir = state.get("output_dir")
        section_file_map = state.get("section_file_map")  # From inject_template multi-file mode
        main_tex = os.path.join(work_dir, "main.tex")

        result = CompilationResult(
            success=False,
            attempts=0,
            errors=[],
            warnings=[],
        )

        # Populate section_files if we have the mapping
        if section_file_map:
            result.section_files = {
                sec_type: os.path.join(work_dir, rel_path + ".tex")
                for sec_type, rel_path in section_file_map.items()
            }

        # Auto-inject missing packages before compilation
        try:
            from ..shared.template_analyzer import (
                detect_missing_packages as _detect_missing,
                inject_missing_packages as _inject_missing,
                PreambleParser as _PreambleParser,
            )
            if os.path.exists(main_tex):
                with open(main_tex, "r", encoding="utf-8") as f:
                    tex_src = f.read()
                preamble = _PreambleParser.extract_preamble(tex_src)
                loaded_pkgs = set(_PreambleParser.extract_packages(preamble))
                detection_body = self._build_detection_body(tex_src, main_tex, work_dir)

                detected_pkgs = _detect_missing(preamble, detection_body)
                fallback_pkgs: List[str] = []

                # Conservative fallback: inject only when the command is present
                # but command detection/mapping may still miss due template variance.
                if self._has_tex_command(detection_body, "adjustbox") and "adjustbox" not in loaded_pkgs:
                    fallback_pkgs.append("adjustbox")
                if self._has_tex_command(detection_body, "multirow") and "multirow" not in loaded_pkgs:
                    fallback_pkgs.append("multirow")
                if self._has_tex_command(detection_body, "checkmark") and "amssymb" not in loaded_pkgs:
                    fallback_pkgs.append("amssymb")
                if self._has_tex_command(detection_body, "texttimes") and "textcomp" not in loaded_pkgs:
                    fallback_pkgs.append("textcomp")

                final_pkgs: List[str] = []
                for pkg in detected_pkgs + fallback_pkgs:
                    if pkg not in loaded_pkgs and pkg not in final_pkgs:
                        final_pkgs.append(pkg)

                if final_pkgs:
                    logger.info(
                        "typesetter.auto_inject_packages detected=%s fallback=%s final=%s",
                        detected_pkgs,
                        fallback_pkgs,
                        final_pkgs,
                    )
                    patched = _inject_missing(tex_src, final_pkgs)
                    with open(main_tex, "w", encoding="utf-8") as f:
                        f.write(patched)
        except Exception as e:
            logger.warning("typesetter.auto_inject_packages_failed: %s", e)

        for attempt in range(MAX_COMPILE_ATTEMPTS):
            result.attempts = attempt + 1
            logger.info("typesetter.compile attempt=%d/%d", attempt + 1, MAX_COMPILE_ATTEMPTS)

            try:
                # First pdflatex pass
                logger.info("typesetter.pdflatex pass=1")
                proc1 = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", work_dir, main_tex],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",  # Handle non-UTF-8 chars in pdflatex output
                    timeout=60,
                    cwd=work_dir,
                )

                # Run bibtex if references exist
                bib_file = os.path.join(work_dir, "references.bib")
                if os.path.exists(bib_file):
                    logger.info("typesetter.bibtex")
                    # NOTE: bibtex expects the AUX *basename* (without extension) in cwd.
                    # Passing an absolute path can cause bibtex to fail to locate/write files.
                    aux_name = "main"
                    bibtex_proc = subprocess.run(
                        ["bibtex", aux_name],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=30,
                        cwd=work_dir,
                    )
                    if bibtex_proc.returncode != 0:
                        logger.warning(
                            "typesetter.bibtex_failed code=%s stderr=%s",
                            bibtex_proc.returncode,
                            (bibtex_proc.stderr or "").strip()[:2000],
                        )
                    else:
                        logger.info("typesetter.bibtex_ok")

                    bbl_path = os.path.join(work_dir, "main.bbl")
                    if not os.path.exists(bbl_path):
                        logger.warning("typesetter.bbl_missing path=%s", bbl_path)

                # Second pdflatex pass
                logger.info("typesetter.pdflatex pass=2")
                proc2 = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", work_dir, main_tex],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                    cwd=work_dir,
                )

                # Third pass for references
                logger.info("typesetter.pdflatex pass=3")
                proc3 = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-output-directory", work_dir, main_tex],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                    cwd=work_dir,
                )

                # Check for PDF
                pdf_path = os.path.join(work_dir, "main.pdf")
                if os.path.exists(pdf_path):
                    result.success = True
                    result.pdf_path = pdf_path
                    result.source_path = work_dir

                    # Parse log for warnings
                    log_path = os.path.join(work_dir, "main.log")
                    if os.path.exists(log_path):
                        with open(log_path, "r", errors="ignore") as f:
                            log_content = f.read()
                            result.log_content = log_content[-5000:]
                            result.warnings = self._extract_warnings(log_content)
                            # Also extract section-level errors (may exist even on success)
                            if section_file_map:
                                result.errors = self._extract_errors(log_content)
                                result.section_errors = self._extract_section_errors(
                                    log_content, section_file_map
                                )

                    logger.info("typesetter.compile_success")

                    # Copy to output_dir if specified
                    if output_dir:
                        logger.info("typesetter.copying_to_output output_dir=%s", output_dir)
                        output_paths = self._copy_to_output_dir(work_dir, output_dir)
                        result.pdf_path = output_paths["pdf_path"]
                        result.source_path = output_paths["source_path"]
                        logger.info("typesetter.output_complete pdf=%s", result.pdf_path)

                    break
                else:
                    # Parse errors from log
                    log_path = os.path.join(work_dir, "main.log")
                    if os.path.exists(log_path):
                        with open(log_path, "r", errors="ignore") as f:
                            log_content = f.read()
                            result.log_content = log_content[-5000:]
                            result.errors = self._extract_errors(log_content)
                            # Extract per-section errors if multi-file mode
                            if section_file_map:
                                result.section_errors = self._extract_section_errors(
                                    log_content, section_file_map
                                )

                    logger.warning("typesetter.compile_failed errors=%s section_errors=%s",
                                   result.errors[:2],
                                   {k: v[:1] for k, v in result.section_errors.items()} if result.section_errors else {})

                    # Try to fix errors
                    if attempt < MAX_COMPILE_ATTEMPTS - 1:
                        fixed = await self._try_fix_errors(work_dir, main_tex, result.errors)
                        if not fixed:
                            break

            except subprocess.TimeoutExpired:
                result.errors.append("Compilation timed out")
                logger.error("typesetter.compile_timeout")
                break
            except FileNotFoundError:
                result.errors.append("pdflatex not found. Please install TeX distribution.")
                logger.error("typesetter.pdflatex_not_found")
                break
            except Exception as e:
                result.errors.append(f"Compilation error: {str(e)}")
                logger.error("typesetter.compile_error error=%s", str(e))
                break

        if not result.success and output_dir:
            logger.info("typesetter.saving_diagnostics output_dir=%s", output_dir)
            self._save_diagnostics_on_failure(work_dir, output_dir)

        return {"compilation_result": result}

    async def _try_fix_errors(self, work_dir: str, main_tex: str, errors: List[str]) -> bool:
        """
        Try to fix common LaTeX errors
        - **Description**:
            - Uses LLM to suggest fixes for compilation errors

        - **Returns**:
            - `bool`: True if fix was attempted
        """
        if not errors:
            return False

        try:
            with open(main_tex, "r", encoding="utf-8") as f:
                tex_content = f.read()

            # Try simple fixes first
            fixed_content = tex_content

            # Fix common issues
            for error in errors:
                error_lower = error.lower()

                if "undefined control sequence" in error_lower:
                    # Try to comment out problematic command
                    pass
                elif "missing $ inserted" in error_lower:
                    # Math mode issue - hard to auto-fix
                    pass
                elif "file not found" in error_lower:
                    # Missing file - replace with placeholder
                    match = re.search(r"file `([^']+)'", error, re.IGNORECASE)
                    if match:
                        missing_file = match.group(1)
                        fixed_content = fixed_content.replace(
                            f"\\includegraphics{{{missing_file}}}",
                            "% [Figure not available]"
                        )

            if fixed_content != tex_content:
                with open(main_tex, "w", encoding="utf-8") as f:
                    f.write(fixed_content)
                return True

        except Exception as e:
            print(f"Error fixing LaTeX: {e}")

        return False

    async def run(self,
                  latex_content: Optional[str] = None,
                  sections: Optional[Dict[str, str]] = None,
                  section_order: Optional[List[str]] = None,
                  section_titles: Optional[Dict[str, str]] = None,
                  template_path: Optional[str] = None,
                  template_config: Optional[TemplateConfig] = None,
                  figure_ids: Optional[List[str]] = None,
                  citation_ids: Optional[List[str]] = None,
                  references: Optional[List[Dict[str, Any]]] = None,
                  canonical_bibtex: Optional[str] = None,
                  work_id: Optional[str] = None,
                  output_dir: Optional[str] = None,
                  figures_source_dir: Optional[str] = None,
                  figure_paths: Optional[Dict[str, str]] = None,
                  converted_tables: Optional[Dict[str, str]] = None):
        """
        Run the Typesetter Agent
        - **Description**:
            - Compiles per-section LaTeX content into a templated paper output.

        - **Args**:
            - `sections` (Dict[str, str], optional): Per-section content
            - `section_order` (List[str], optional): Body section ordering
            - `section_titles` (Dict[str, str], optional): section_type -> display title
            - `template_path` (str, optional): Path to template zip
            - `template_config` (TemplateConfig, optional): Template configuration with constraints
            - `figure_ids` (List[str], optional): Figure IDs to fetch
            - `citation_ids` (List[str], optional): Citation IDs
            - `references` (List[Dict], optional): Reference metadata
            - `work_id` (str, optional): Work ID for resource lookup
            - `output_dir` (str, optional): Directory to save final output files
            - `figures_source_dir` (str, optional): Local directory with figure files
            - `figure_paths` (Dict[str, str], optional): Structured figure paths (id -> file_path)
            - `converted_tables` (Dict[str, str], optional): Pre-converted table LaTeX (id -> code)

        - **Returns**:
            - `dict`: Compilation result with PDF path
        """
        return await self.agent.ainvoke({
            "latex_content": latex_content,
            "sections": sections,
            "section_order": section_order,
            "section_titles": section_titles,
            "template_path": template_path,
            "template_config": template_config,
            "figure_ids": figure_ids or [],
            "citation_ids": citation_ids or [],
            "references": references or [],
            "canonical_bibtex": canonical_bibtex,
            "work_id": work_id,
            "output_dir": output_dir,
            "figures_source_dir": figures_source_dir,
            "figure_paths": figure_paths or {},
            "converted_tables": converted_tables or {},
            "messages": [],
            "llm_calls": 0,
        })

    @property
    def name(self) -> str:
        """Agent name identifier"""
        return "typesetter"

    @property
    def description(self) -> str:
        """Agent description"""
        return "Handles resource fetching, template injection, and LaTeX compilation with self-healing"

    @property
    def router(self) -> "APIRouter":
        """Return the FastAPI router for this agent"""
        from .router import create_typesetter_router
        return create_typesetter_router(self)

    @property
    def endpoints_info(self) -> List[Dict[str, Any]]:
        """Return endpoint metadata for list_agents"""
        return [
            {
                "path": "/agent/typesetter/compile",
                "method": "POST",
                "description": "Compile LaTeX content into PDF with resource handling",
                "input_model": "TypesetterPayload",
                "output_model": "TypesetterResult"
            }
        ]
