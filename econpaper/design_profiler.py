from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DESIGN_PROFILE_VERSION = "v3.0"


@dataclass
class DesignProfileIssue:
    code: str
    tier: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "tier": self.tier, "message": self.message, "path": self.path}


@dataclass
class DesignProfileResult:
    design_profile: dict[str, Any]
    status: str = "passed"
    issues: list[DesignProfileIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.tier == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, tier: str, message: str, path: str | None = None) -> None:
        if tier == "hard_block":
            self.status = "failed"
        self.issues.append(DesignProfileIssue(code=code, tier=tier, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": DESIGN_PROFILE_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "design_profile": self.design_profile,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def build_design_profile(
    *,
    intake_profile_path: str | Path,
    evidence_ledger_path: str | Path | None = None,
    run_validation_path: str | Path | None = None,
    author_amendments_path: str | Path | None = None,
) -> DesignProfileResult:
    result = DesignProfileResult(design_profile={})
    intake = _load_json(Path(intake_profile_path), result, "intake_profile", required=True)
    evidence = _load_json(Path(evidence_ledger_path), result, "evidence_ledger", required=False) if evidence_ledger_path else {}
    run_validation = _load_json(Path(run_validation_path), result, "run_validation", required=False) if run_validation_path else {}
    amendments = _load_json(Path(author_amendments_path), result, "author_amendments", required=False) if author_amendments_path else {}

    declared = intake.get("author_declared_design", {}) if isinstance(intake, dict) else {}
    design_type = str(declared.get("design_type") or "").strip() or "unknown_design"
    declared_by_author = bool(declared.get("declared_by_author")) or design_type != "unknown_design"
    artifacts = _artifact_summary(evidence)
    diagnostics_present, diagnostics_missing = _diagnostics_for_design(design_type, artifacts)
    claim_levels, reviewer_questions, next_actions = _claim_levels_for_design(
        design_type=design_type,
        declared_by_author=declared_by_author,
        diagnostics_present=diagnostics_present,
        diagnostics_missing=diagnostics_missing,
        evidence=evidence,
        amendments=amendments,
    )
    hard_blocks: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []
    style_advice: list[dict[str, Any]] = []

    if run_validation.get("mock_watermark_required") or run_validation.get("public_watermark"):
        hard_blocks.append(
            {
                "code": "mock_output_not_paper_draft",
                "tier": "hard_block",
                "overridable": False,
                "reason": "Mock/smoke output cannot support manuscript design claims.",
            }
        )
        result.add_issue("mock_output_not_paper_draft", "hard_block", "Mock/smoke output cannot support manuscript design claims.", str(run_validation_path))

    for claim_level in claim_levels.values():
        if claim_level["tier"] == "flag_and_confirm":
            flags.append({"code": claim_level["code"], "reason": claim_level["reason"]})
        elif claim_level["tier"] == "style_advice":
            style_advice.append({"code": claim_level["code"], "reason": claim_level["reason"]})

    checked_design = _checked_design(design_type, artifacts)
    consistency_checks = _consistency_checks(design_type, checked_design, declared_by_author, diagnostics_missing)
    result.design_profile = {
        "version": DESIGN_PROFILE_VERSION,
        "status": "failed" if result.has_hard_blocks else "passed",
        "declared_by_author": declared_by_author,
        "declared_design_type": design_type,
        "checked_design_type": checked_design,
        "consistency_checks": consistency_checks,
        "contradicted_or_missing_artifacts": diagnostics_missing,
        "estimand_scope": declared.get("estimand"),
        "assumptions": _assumptions_for_design(design_type),
        "diagnostics_present": diagnostics_present,
        "diagnostics_missing": diagnostics_missing,
        "claim_levels": claim_levels,
        "reviewer_questions": reviewer_questions,
        "next_actions": next_actions,
        "hard_blocks": hard_blocks,
        "flags": flags,
        "style_advice": style_advice,
        "author_override": {"allowed": True, "field": "author_override"},
    }
    result.status = result.design_profile["status"]
    return result


def write_design_profile(
    *,
    intake_profile_path: str | Path,
    out_dir: str | Path,
    evidence_ledger_path: str | Path | None = None,
    run_validation_path: str | Path | None = None,
    author_amendments_path: str | Path | None = None,
) -> DesignProfileResult:
    result = build_design_profile(
        intake_profile_path=intake_profile_path,
        evidence_ledger_path=evidence_ledger_path,
        run_validation_path=run_validation_path,
        author_amendments_path=author_amendments_path,
    )
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result.design_profile, ensure_ascii=False, indent=2)
    (out_path / "design_profile.json").write_text(text, encoding="utf-8")
    (internal / "design_profile.json").write_text(text, encoding="utf-8")
    (internal / "design_profile_build.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _load_json(path: Path, result: DesignProfileResult, label: str, *, required: bool) -> dict[str, Any]:
    if not path.exists():
        tier = "hard_block" if required else "flag_and_confirm"
        result.add_issue(f"{label}_missing", tier, f"{label} file does not exist: {path}", str(path))
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        result.add_issue(f"{label}_invalid_json", "hard_block", f"Could not parse {label}: {exc}", str(path))
        return {}
    return payload if isinstance(payload, dict) else {}


def _artifact_summary(evidence: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for artifact in evidence.get("artifacts", []) if isinstance(evidence, dict) else []:
        if not isinstance(artifact, dict):
            continue
        text = " ".join(str(artifact.get(key) or "") for key in ["artifact_id", "artifact_type", "path"]).lower()
        tokens.add(text)
    for item in evidence.get("evidence_items", []) if isinstance(evidence, dict) else []:
        if not isinstance(item, dict):
            continue
        text = " ".join(str(item.get(key) or "") for key in ["model_id", "statistic", "variable", "diagnostic_status"]).lower()
        tokens.add(text)
    return tokens


def _contains(artifacts: set[str], *needles: str) -> bool:
    return any(all(needle in item for needle in needles) for item in artifacts)


def _contains_any(artifacts: set[str], alternatives: list[tuple[str, ...]]) -> bool:
    return any(_contains(artifacts, *needles) for needles in alternatives)


def _diagnostics_for_design(design_type: str, artifacts: set[str]) -> tuple[list[str], list[str]]:
    design = design_type.lower()
    required: dict[str, list[tuple[str, ...]]] = {}
    if "did" in design:
        required = {
            "event_study": [("event", "study")],
            "pretrend": [("pretrend",), ("pre_trend",)],
            "comparison_group": [("comparison",), ("cohort",), ("never", "treated"), ("control",)],
        }
        if "staggered" in design:
            required["modern_staggered_estimator"] = [
                ("staggered",),
                ("callaway",),
                ("cs_did",),
                ("att_gt",),
                ("differences",),
                ("csdid",),
                ("sun", "abraham"),
                ("did_imputation",),
                ("drdid",),
            ]
    elif "iv" in design:
        required = {
            "first_stage": [("first", "stage")],
            "weak_iv": [("weak", "iv")],
            "reduced_form": [("reduced", "form")],
        }
    elif "rdd" in design or "rd" == design:
        required = {
            "rd_plot": [("rd", "plot")],
            "manipulation_test": [("manipulation",), ("density", "test"), ("rdd", "density")],
            "bandwidth_sensitivity": [("bandwidth",)],
            "covariate_continuity": [("covariate", "continuity")],
        }
    elif "finance" in design or "event_study" in design:
        required = {
            "event_timeline": [("event", "timeline")],
            "leakage_check": [("leakage",)],
            "factor_adjusted": [("factor",)],
        }
    else:
        required = {"structured_model_table": [("model_table",)]}
    present = [name for name, alternatives in required.items() if _contains_any(artifacts, alternatives)]
    missing = [name for name in required if name not in present]
    return present, missing


def _claim_levels_for_design(
    *,
    design_type: str,
    declared_by_author: bool,
    diagnostics_present: list[str],
    diagnostics_missing: list[str],
    evidence: dict[str, Any],
    amendments: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    design = design_type.lower()
    reviewer_questions: list[str] = []
    next_actions: list[str] = []
    claim_levels: dict[str, dict[str, Any]] = {}
    if not declared_by_author:
        claim_levels["causal_language"] = _flag(
            "design_not_declared",
            "No author-declared design is available; causal or identification language needs author confirmation.",
            "State descriptive results or collect an author design declaration.",
            ["What is the intended research design and estimand?"],
            ["Complete intake design declaration."],
        )
    elif diagnostics_missing:
        claim_levels["causal_language"] = _flag(
            f"{design or 'design'}_diagnostics_missing",
            "Declared design is preserved, but required diagnostics/artifacts are missing.",
            "Use assumption-qualified or benchmark language until missing diagnostics are supplied.",
            _questions_for_design(design),
            [f"Add diagnostic/artifact: {item}" for item in diagnostics_missing],
        )
    else:
        claim_levels["causal_language"] = _safe("design_diagnostics_present", "Declared design has the required P0 diagnostic artifacts.")
    if "mechanism" in design or _contains(_artifact_summary(evidence), "mechanism"):
        claim_levels["mechanism_language"] = _flag(
            "mechanism_needs_confirmation",
            "Mechanism language should remain suggestive unless separately identified.",
            "Use 'consistent with' or 'suggestive of' by default.",
            ["Is the mechanism separately identified and timing-compatible?"],
            ["Add mechanism diagnostics or author assertion."],
        )
    if amendments.get("author_override"):
        for level in claim_levels.values():
            if level["tier"] == "flag_and_confirm":
                level["author_override"] = {
                    "asserted": True,
                    "original_status": level["tier"],
                    "reason": str(amendments.get("reason") or "Author amendment supplied."),
                }
                level["tier"] = "author_asserted"
    for item in claim_levels.values():
        reviewer_questions.extend(item.get("reviewer_questions", []))
        next_actions.extend(item.get("next_actions", []))
    return claim_levels, reviewer_questions, next_actions


def _flag(code: str, reason: str, rewrite: str, questions: list[str], actions: list[str]) -> dict[str, Any]:
    return {
        "code": code,
        "tier": "flag_and_confirm",
        "overridable": True,
        "reason": reason,
        "suggested_rewrite": rewrite,
        "reviewer_questions": questions,
        "next_actions": actions,
    }


def _safe(code: str, reason: str) -> dict[str, Any]:
    return {
        "code": code,
        "tier": "safe",
        "overridable": False,
        "reason": reason,
        "suggested_rewrite": "Proceed with ledger-backed, assumption-aware claim language.",
        "reviewer_questions": [],
        "next_actions": [],
    }


def _questions_for_design(design: str) -> list[str]:
    if "did" in design:
        return ["How do results change under Callaway-Sant'Anna, Sun-Abraham, did_imputation, or DRDID equivalents?"]
    if "iv" in design:
        return ["What is the first-stage strength and weak-IV diagnostic evidence?"]
    if "rdd" in design or design == "rd":
        return ["Is there manipulation or covariate discontinuity at the cutoff?"]
    if "finance" in design:
        return ["Are announcement timing, leakage, and factor-adjusted robustness addressed?"]
    return ["What design diagnostics support stronger language?"]


def _checked_design(design_type: str, artifacts: set[str]) -> str:
    if not artifacts:
        return "not_inferred_from_artifacts"
    if _contains(artifacts, "twfe") and "did" in design_type.lower():
        return "declared_did_with_twfe_artifacts"
    if _contains(artifacts, "iv"):
        return "iv_artifacts_present"
    if _contains(artifacts, "rdd"):
        return "rdd_artifacts_present"
    return "structured_artifacts_present"


def _consistency_checks(design_type: str, checked_design: str, declared_by_author: bool, missing: list[str]) -> list[dict[str, Any]]:
    checks = [
        {
            "code": "author_declaration_preserved",
            "status": "passed" if declared_by_author else "needs_author_input",
            "message": "Lack of machine inference does not erase the author's declared design.",
        },
        {
            "code": "artifact_consistency",
            "status": "flag_and_confirm" if missing else "passed",
            "message": f"Declared `{design_type}` checked against `{checked_design}`.",
        },
    ]
    return checks


def _assumptions_for_design(design_type: str) -> list[str]:
    design = design_type.lower()
    if "did" in design:
        return ["parallel trends", "no anticipation unless modeled", "stable comparison group"]
    if "iv" in design:
        return ["instrument relevance", "exclusion restriction", "monotonicity/LATE scope"]
    if "rdd" in design or design == "rd":
        return ["local continuity", "no manipulation at cutoff", "bandwidth robustness"]
    if "finance" in design:
        return ["event timing discipline", "no look-ahead leakage", "appropriate factor adjustment"]
    return ["assumptions require author/design specification"]


def _author_report_text(result: DesignProfileResult) -> str:
    profile = result.design_profile
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Design Profile Status",
        "",
        f"- Status: `{result.status}`",
        f"- Declared design: `{profile.get('declared_design_type')}`",
        f"- Checked design: `{profile.get('checked_design_type')}`",
        "",
        "## Claim Levels",
        "",
    ]
    for name, level in (profile.get("claim_levels") or {}).items():
        lines.append(f"- `{name}`: `{level.get('tier')}` - {level.get('reason')}")
    if not (profile.get("claim_levels") or {}):
        lines.append("- None.")
    lines.extend(["", "## Missing Diagnostics", ""])
    missing = profile.get("diagnostics_missing") or []
    lines.extend([f"- `{item}`" for item in missing] if missing else ["- None."])
    lines.extend(["", "## Non-Overridable Hard Blocks", ""])
    hard_blocks = profile.get("hard_blocks") or []
    lines.extend([f"- `{item['code']}`: {item['reason']}" for item in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Expected Referee Questions", ""])
    questions = profile.get("reviewer_questions") or []
    lines.extend([f"- {item}" for item in questions] if questions else ["- None."])
    lines.extend(["", "## Next Best Actions", ""])
    actions = profile.get("next_actions") or []
    lines.extend([f"- {item}" for item in actions] if actions else ["- Continue to claim-ledger construction."])
    return "\n".join(lines) + "\n"
