"""econpaper v3 product-layer package."""

from .claim_ledger import ClaimLedgerBuildResult, build_claim_ledger, write_claim_ledger
from .evidence import EvidenceBuildResult, build_evidence_ledger, write_evidence_ledger
from .intake import IntakeBuildResult, build_intake_profile, write_intake_profile
from .linting import LintReport, run_lint
from .numeric_renderer import NumericRenderingResult, render_numeric_template, write_numeric_rendering
from .run_validation import RunValidationReport, validate_run_dir, write_run_validation
from .table_generator import TableGenerationResult, generate_publication_table, write_publication_table

__all__ = [
    "ClaimLedgerBuildResult",
    "EvidenceBuildResult",
    "IntakeBuildResult",
    "LintReport",
    "NumericRenderingResult",
    "RunValidationReport",
    "TableGenerationResult",
    "build_claim_ledger",
    "build_evidence_ledger",
    "build_intake_profile",
    "generate_publication_table",
    "render_numeric_template",
    "run_lint",
    "validate_run_dir",
    "write_claim_ledger",
    "write_evidence_ledger",
    "write_intake_profile",
    "write_numeric_rendering",
    "write_publication_table",
    "write_run_validation",
]
