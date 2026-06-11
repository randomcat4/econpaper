"""econpaper v3 product-layer package."""

from .claim_ledger import ClaimLedgerBuildResult, build_claim_ledger, write_claim_ledger
from .coherence import CoherenceResult, run_global_coherence, write_global_coherence
from .compile_pack import CompileResult, compile_pack
from .design_profiler import DesignProfileResult, build_design_profile, write_design_profile
from .evidence import EvidenceBuildResult, build_evidence_ledger, write_evidence_ledger
from .incremental_rerun import IncrementalRerunResult, run_incremental_rerun, write_incremental_rerun
from .intake import IntakeBuildResult, build_intake_profile, write_intake_profile
from .linting import LintReport, run_lint
from .numeric_renderer import NumericRenderingResult, render_numeric_template, write_numeric_rendering
from .release_gate import ReleaseGateResult, run_release_gate, write_release_gate
from .run_validation import RunValidationReport, validate_run_dir, write_run_validation
from .section_writer import SectionWriterResult, generate_sections, write_sections
from .table_generator import TableGenerationResult, generate_publication_table, write_publication_table
from .venue import VenueProfile, resolve_venue
from .write_pack import WritePackResult, write_manuscript_pack

__all__ = [
    "ClaimLedgerBuildResult",
    "CoherenceResult",
    "CompileResult",
    "DesignProfileResult",
    "EvidenceBuildResult",
    "IncrementalRerunResult",
    "IntakeBuildResult",
    "LintReport",
    "NumericRenderingResult",
    "ReleaseGateResult",
    "RunValidationReport",
    "SectionWriterResult",
    "TableGenerationResult",
    "VenueProfile",
    "WritePackResult",
    "build_claim_ledger",
    "build_design_profile",
    "build_evidence_ledger",
    "build_intake_profile",
    "compile_pack",
    "generate_publication_table",
    "generate_sections",
    "render_numeric_template",
    "resolve_venue",
    "run_global_coherence",
    "run_incremental_rerun",
    "run_lint",
    "run_release_gate",
    "validate_run_dir",
    "write_claim_ledger",
    "write_design_profile",
    "write_evidence_ledger",
    "write_global_coherence",
    "write_incremental_rerun",
    "write_intake_profile",
    "write_manuscript_pack",
    "write_numeric_rendering",
    "write_release_gate",
    "write_publication_table",
    "write_run_validation",
    "write_sections",
]
