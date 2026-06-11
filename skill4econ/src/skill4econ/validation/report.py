from __future__ import annotations

from .contract_verifier import ValidationReport


def render_validation_summary(report: ValidationReport) -> str:
    return (
        f"{report.status}: run_dir={report.run_dir} "
        f"errors={len(report.errors)} warnings={len(report.warnings)} strict={report.strict}"
    )
