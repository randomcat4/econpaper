"""econpaper v3 product-layer package."""

from .evidence import EvidenceBuildResult, build_evidence_ledger, write_evidence_ledger
from .intake import IntakeBuildResult, build_intake_profile, write_intake_profile
from .linting import LintReport, run_lint
from .numeric_renderer import NumericRenderingResult, render_numeric_template, write_numeric_rendering
from .run_validation import RunValidationReport, validate_run_dir, write_run_validation

__all__ = [
    "EvidenceBuildResult",
    "IntakeBuildResult",
    "LintReport",
    "NumericRenderingResult",
    "RunValidationReport",
    "build_evidence_ledger",
    "build_intake_profile",
    "render_numeric_template",
    "run_lint",
    "validate_run_dir",
    "write_evidence_ledger",
    "write_intake_profile",
    "write_numeric_rendering",
    "write_run_validation",
]
