"""econpaper v3 product-layer package."""

from .claim_ledger import ClaimLedgerBuildResult, build_claim_ledger, write_claim_ledger
from .coherence import CoherenceResult, run_global_coherence, write_global_coherence
from .evidence import EvidenceBuildResult, build_evidence_ledger, write_evidence_ledger
from .incremental_rerun import IncrementalRerunResult, run_incremental_rerun, write_incremental_rerun
from .intake import IntakeBuildResult, build_intake_profile, write_intake_profile
from .linting import LintReport, run_lint
from .numeric_renderer import NumericRenderingResult, render_numeric_template, write_numeric_rendering
from .run_validation import RunValidationReport, validate_run_dir, write_run_validation
from .section_writer import SectionWriterResult, generate_sections, write_sections
from .table_generator import TableGenerationResult, generate_publication_table, write_publication_table

__all__ = [
    "ClaimLedgerBuildResult",
    "CoherenceResult",
    "EvidenceBuildResult",
    "IncrementalRerunResult",
    "IntakeBuildResult",
    "LintReport",
    "NumericRenderingResult",
    "RunValidationReport",
    "SectionWriterResult",
    "TableGenerationResult",
    "build_claim_ledger",
    "build_evidence_ledger",
    "build_intake_profile",
    "generate_publication_table",
    "generate_sections",
    "render_numeric_template",
    "run_global_coherence",
    "run_incremental_rerun",
    "run_lint",
    "validate_run_dir",
    "write_claim_ledger",
    "write_evidence_ledger",
    "write_global_coherence",
    "write_incremental_rerun",
    "write_intake_profile",
    "write_numeric_rendering",
    "write_publication_table",
    "write_run_validation",
    "write_sections",
]
