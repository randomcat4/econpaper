from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .evidence_pack import load_evidence_pack
from .linting import extract_numeric_uses


CLAIM_LEDGER_VERSION = "v3.0"
AUTHOR_INPUT_NEEDED = "[AUTHOR_INPUT_NEEDED]"


@dataclass
class ClaimLedgerIssue:
    code: str
    severity: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class ClaimLedgerBuildResult:
    claim_ledger: dict[str, Any]
    slot_map: dict[str, Any]
    status: str = "passed"
    issues: list[ClaimLedgerIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(ClaimLedgerIssue(code=code, severity=severity, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": CLAIM_LEDGER_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "claim_ledger": self.claim_ledger,
            "slot_map": self.slot_map,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def build_claim_ledger(
    *,
    evidence_ledger_path: str | Path,
    intake_profile_path: str | Path | None = None,
    citation_safety_report_path: str | Path | None = None,
    design_profile_path: str | Path | None = None,
    run_validation_path: str | Path | None = None,
    author_overrides_path: str | Path | None = None,
) -> ClaimLedgerBuildResult:
    result = ClaimLedgerBuildResult(claim_ledger={}, slot_map={"slots": {}})
    evidence_path = Path(evidence_ledger_path)
    evidence_ledger = _load_json(evidence_path, result, "evidence_ledger")
    _validate_adjacent_evidence_pack(evidence_path, result)
    intake_profile = _load_json(Path(intake_profile_path), result, "intake_profile") if intake_profile_path else {}
    citation_safety = _load_json(Path(citation_safety_report_path), result, "citation_safety_report") if citation_safety_report_path else {}
    design_profile = _load_json(Path(design_profile_path), result, "design_profile") if design_profile_path else {}
    run_validation = _load_json(Path(run_validation_path), result, "run_validation") if run_validation_path else {}
    author_overrides = _load_json(Path(author_overrides_path), result, "author_overrides") if author_overrides_path else {}

    claims: list[dict[str, Any]] = []
    if _run_validation_has_mock(run_validation):
        result.add_issue("mock_output_not_paper_draft", "hard_block", "Mock/smoke output cannot produce claim-ledger claims.", str(run_validation_path))
    if citation_safety.get("missing_citekeys"):
        result.add_issue(
            "missing_citekeys_in_citation_safety",
            "hard_block",
            "Citation safety report contains missing citekeys; claim ledger cannot be marked safe.",
            str(citation_safety_report_path),
        )

    evidence_items = _evidence_items_by_context(evidence_ledger)
    if not evidence_items:
        result.add_issue(
            "claimable_evidence_missing",
            "hard_block",
            "No coefficient evidence items were found in the evidence ledger.",
            str(evidence_ledger_path),
        )

    design_flags = _design_flags(design_profile)
    for idx, context in enumerate(evidence_items, start=1):
        claim = _main_result_claim(idx, context, evidence_ledger, intake_profile, design_flags, result.slot_map)
        claims.append(claim)

    claims.extend(_author_asserted_claims(intake_profile))
    _validate_claim_templates(claims, result)
    _apply_author_overrides(claims, author_overrides, result)

    result.claim_ledger = {
        "version": CLAIM_LEDGER_VERSION,
        "status": "failed" if result.has_hard_blocks else "passed",
        "claims": claims,
        "hard_blocks": [issue.to_dict() for issue in result.issues if issue.severity == "hard_block"],
        "author_overrides": author_overrides.get("overrides", []) if isinstance(author_overrides, dict) else [],
        "slot_map": result.slot_map,
    }
    result.status = result.claim_ledger["status"]
    return result


def write_claim_ledger(
    *,
    evidence_ledger_path: str | Path,
    out_dir: str | Path,
    intake_profile_path: str | Path | None = None,
    citation_safety_report_path: str | Path | None = None,
    design_profile_path: str | Path | None = None,
    run_validation_path: str | Path | None = None,
    author_overrides_path: str | Path | None = None,
) -> ClaimLedgerBuildResult:
    result = build_claim_ledger(
        evidence_ledger_path=evidence_ledger_path,
        intake_profile_path=intake_profile_path,
        citation_safety_report_path=citation_safety_report_path,
        design_profile_path=design_profile_path,
        run_validation_path=run_validation_path,
        author_overrides_path=author_overrides_path,
    )
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "claim_ledger.json").write_text(json.dumps(result.claim_ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "slots.json").write_text(json.dumps(result.slot_map, ensure_ascii=False, indent=2), encoding="utf-8")
    (internal / "claim_ledger_build.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _load_json(path: Path, result: ClaimLedgerBuildResult, label: str) -> dict[str, Any]:
    if not path.exists():
        severity = "hard_block" if label == "evidence_ledger" else "flag_and_confirm"
        result.add_issue(f"{label}_missing", severity, f"{label} file does not exist: {path}", str(path))
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        result.add_issue(f"{label}_invalid_json", "hard_block", f"Could not parse {label}: {exc}", str(path))
        return {}
    if not isinstance(payload, dict):
        result.add_issue(f"{label}_not_object", "hard_block", f"{label} must be a JSON object.", str(path))
        return {}
    return payload


def _validate_adjacent_evidence_pack(evidence_ledger_path: Path, result: ClaimLedgerBuildResult) -> None:
    pack_path = evidence_ledger_path.with_name("evidence_pack.json")
    if not pack_path.exists():
        return
    pack_result = load_evidence_pack(pack_path)
    if pack_result.has_hard_blocks:
        result.add_issue(
            "evidence_pack_invalid",
            "hard_block",
            "Adjacent EvidencePack v2 failed validation; claim ledger will not import untrusted evidence.",
            str(pack_path),
        )


def _run_validation_has_mock(run_validation: dict[str, Any]) -> bool:
    return bool(run_validation.get("mock_watermark_required") or run_validation.get("public_watermark"))


def _evidence_items_by_context(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = {item.get("artifact_id"): item for item in ledger.get("artifacts", []) if isinstance(item, dict)}
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in ledger.get("evidence_items", []):
        if not isinstance(item, dict):
            continue
        artifact = artifacts.get(item.get("artifact_id"), {})
        if artifact.get("artifact_type") != "model_table":
            continue
        display_type = item.get("display_type")
        if display_type not in {"coefficient", "standard_error", "p_value", "t_stat", "n"}:
            continue
        variable = str(item.get("variable") or item.get("row") or "term")
        model_id = str(item.get("model_id") or "model")
        artifact_id = str(item.get("artifact_id") or "")
        grouped.setdefault(
            (artifact_id, model_id, variable),
            {"artifact_id": artifact_id, "model_id": model_id, "variable": variable, "items": {}},
        )["items"][display_type] = item
    contexts = [value for value in grouped.values() if value["items"].get("coefficient")]
    return sorted(contexts, key=lambda item: (item["artifact_id"], item["model_id"], item["variable"]))


def _main_result_claim(
    idx: int,
    context: dict[str, Any],
    ledger: dict[str, Any],
    intake_profile: dict[str, Any],
    design_flags: list[str],
    slot_map: dict[str, Any],
) -> dict[str, Any]:
    claim_id = f"claim_main_{idx:03d}"
    items = context["items"]
    variable = context["variable"]
    coefficient = items["coefficient"]
    se = items.get("standard_error")
    p_value = items.get("p_value")
    t_stat = items.get("t_stat")
    n_item = items.get("n")
    magnitude_variable, variable_semantics = _magnitude_variable_for_claim(variable, ledger, intake_profile)
    magnitude_ready = _magnitude_ready(variable_semantics)

    slots = slot_map.setdefault("slots", {})
    slots[f"coef:{claim_id}"] = {"evidence_id": coefficient["evidence_id"]}
    if se:
        slots[f"se:{claim_id}"] = {"evidence_id": se["evidence_id"]}
    if p_value:
        slots[f"pvalue:{claim_id}"] = {"evidence_id": p_value["evidence_id"]}
    if n_item:
        slots[f"n:{claim_id}"] = {"evidence_id": n_item["evidence_id"]}
    if magnitude_ready:
        slots[f"magnitude:{claim_id}"] = {
            "coefficient_evidence_id": coefficient["evidence_id"],
            "variable": magnitude_variable,
            "kind": "sd_units",
        }

    template_parts = [f"The estimated coefficient for {_label_for_variable(variable, intake_profile)} is {{{{coef:{claim_id}}}}}"]
    if se:
        template_parts.append(f"(SE {{{{se:{claim_id}}}}}")
        if p_value:
            template_parts[-1] += f", p={{{{pvalue:{claim_id}}}}}"
        template_parts[-1] += ")"
    if magnitude_ready:
        template_parts.append(f"which equals {{{{magnitude:{claim_id}}}}}")
    else:
        template_parts.append(f"with {AUTHOR_INPUT_NEEDED}: magnitude context for {variable}")
    if n_item:
        template_parts.append(f"using N={{{{n:{claim_id}}}}}")
    prose_template = " ".join(template_parts) + "."

    flags: list[str] = []
    reviewer_questions: list[str] = []
    if not magnitude_ready:
        flags.append("magnitude_context_missing")
        reviewer_questions.append(f"What unit, mean, and standard deviation should be used to interpret `{magnitude_variable or variable}`?")
    if not se or not p_value:
        flags.append("inference_statistic_missing")
        reviewer_questions.append("Should this claim be reported without complete inference statistics?")
    if design_flags:
        flags.extend(design_flags)
        reviewer_questions.extend([f"Design gate requires confirmation: {flag}" for flag in design_flags])
    status = "flag_and_confirm" if flags else "safe"
    return {
        "claim_id": claim_id,
        "claim_type": "main_result",
        "status": status,
        "gate_tier": status,
        "prose_template": prose_template,
        "numeric_slots": sorted([key for key in slots if key.endswith(claim_id)]),
        "evidence_refs": [item["evidence_id"] for item in [coefficient, se, p_value, t_stat, n_item] if item],
        "citation_refs": [],
        "gate_reasons": flags,
        "suggested_rewrite": prose_template if status == "safe" else "Add missing diagnostics or author confirmation before using stronger result language.",
        "reviewer_questions": reviewer_questions,
        "author_override": None,
        "metadata": {
            "artifact_id": context["artifact_id"],
            "model_id": context["model_id"],
            "variable": variable,
            "magnitude_variable": magnitude_variable if magnitude_ready else None,
        },
    }


def _magnitude_variable_for_claim(variable: str, ledger: dict[str, Any], intake_profile: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    semantics_by_variable = ledger.get("variable_semantics") or {}
    if not isinstance(semantics_by_variable, dict):
        return variable, {}
    direct = semantics_by_variable.get(variable)
    if isinstance(direct, dict):
        return variable, direct
    if not _is_effect_term(variable):
        return variable, {}
    outcome_candidates = _outcome_variables_from_intake(intake_profile)
    ready_outcomes = [
        name
        for name in outcome_candidates
        if isinstance(semantics_by_variable.get(name), dict) and _magnitude_ready(semantics_by_variable[name])
    ]
    if len(ready_outcomes) == 1:
        selected = ready_outcomes[0]
        return selected, semantics_by_variable[selected]
    ready_semantics = [
        (str(name), semantics)
        for name, semantics in semantics_by_variable.items()
        if isinstance(semantics, dict) and _magnitude_ready(semantics)
    ]
    if len(ready_semantics) == 1:
        return ready_semantics[0]
    return variable, {}


def _outcome_variables_from_intake(intake_profile: dict[str, Any]) -> list[str]:
    variables: list[str] = []
    registry = intake_profile.get("variable_registry", []) if isinstance(intake_profile, dict) else []
    for entry in registry if isinstance(registry, list) else []:
        if not isinstance(entry, dict):
            continue
        role = str(entry.get("role") or "").lower()
        name = str(entry.get("name") or entry.get("variable") or "").strip()
        if name and "outcome" in role:
            variables.append(name)
    context = intake_profile.get("outcome_magnitude_context", []) if isinstance(intake_profile, dict) else []
    for entry in context if isinstance(context, list) else []:
        if isinstance(entry, dict):
            name = str(entry.get("variable") or "").strip()
            if name:
                variables.append(name)
    return sorted(set(variables))


def _is_effect_term(variable: str) -> bool:
    lowered = variable.lower()
    return bool(
        re.fullmatch(r"event_-?(?:m)?\d+", lowered)
        or re.fullmatch(r"att_\d+", lowered)
        or re.fullmatch(r"att_gt_g\d+_b\d+_t\d+", lowered)
    ) or lowered in {
        "_did_treat_post",
        "did_treat_post",
        "treat_post",
        "post_treat",
        "att",
        "robust",
        "bias-corrected",
        "bias_corrected",
        "conventional",
        "main_effect",
    }


def _magnitude_ready(semantics: dict[str, Any]) -> bool:
    return bool(semantics.get("unit")) and _number_present(semantics.get("mean")) and _number_present(semantics.get("sd"))


def _number_present(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        return float(value) != 0.0
    except Exception:
        return False


def _label_for_variable(variable: str, intake_profile: dict[str, Any]) -> str:
    for entry in intake_profile.get("outcome_magnitude_context", []) if isinstance(intake_profile, dict) else []:
        if isinstance(entry, dict) and entry.get("variable") == variable and entry.get("label"):
            return str(entry["label"])
    lowered = variable.lower()
    if re.fullmatch(r"att_\d+", lowered):
        return "the simple aggregated ATT"
    if re.fullmatch(r"att_gt_g\d+_b\d+_t\d+", lowered):
        return "a cohort-time ATT(g,t) estimate"
    if lowered in {"robust", "bias-corrected", "bias_corrected", "conventional"}:
        return "the rdrobust cutoff estimate"
    if re.fullmatch(r"event_-?(?:m)?\d+", lowered):
        if lowered.startswith("event_m") or lowered.startswith("event_-"):
            return "a pre-treatment event-study coefficient"
        if variable == "event_0":
            return "the treatment-period event-study coefficient"
        return "a post-treatment event-study coefficient"
    return re.sub(r"\s+", " ", variable.replace("_", " ")).strip()


def _design_flags(design_profile: dict[str, Any]) -> list[str]:
    if not design_profile:
        return []
    flags: list[str] = []
    for key in ["design_risks", "risk_flags", "diagnostics_missing", "contradicted_artifacts"]:
        value = design_profile.get(key)
        if isinstance(value, list):
            flags.extend(str(item.get("code") if isinstance(item, dict) else item) for item in value)
    status = str(design_profile.get("status") or "").lower()
    if status in {"failed", "unknown_design", "conflict"}:
        flags.append(status)
    return [flag for flag in flags if flag and flag != "None"]


def _author_asserted_claims(intake_profile: dict[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    raw_claims = intake_profile.get("author_asserted_claims", []) if isinstance(intake_profile, dict) else []
    for idx, item in enumerate(raw_claims if isinstance(raw_claims, list) else [], start=1):
        if not isinstance(item, dict):
            continue
        claim_text = str(item.get("claim") or "").strip()
        if not claim_text:
            continue
        assertion_type = str(item.get("assertion_type") or item.get("claim_type") or item.get("role") or "").strip()
        gate_reasons = ["author_asserted_from_intake"]
        if assertion_type:
            gate_reasons.append(f"author_asserted_{_slug(assertion_type)}")
        claims.append(
            {
                "claim_id": item.get("claim_id") or f"author_asserted_{idx:03d}",
                "claim_type": "author_asserted",
                "status": "author_asserted",
                "gate_tier": "author_asserted",
                "prose_template": claim_text,
                "numeric_slots": [],
                "evidence_refs": [],
                "citation_refs": [],
                "gate_reasons": gate_reasons,
                "suggested_rewrite": claim_text,
                "reviewer_questions": [],
                "author_override": {
                    "asserted": True,
                    "original_status": item.get("original_status") or "author_supplied_without_gate",
                    "reason": item.get("author_reason") or "",
                },
                "metadata": {
                    "source": "intake_profile",
                    "assertion_type": assertion_type or None,
                },
            }
        )
    return claims


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "claim"


def _validate_claim_templates(claims: list[dict[str, Any]], result: ClaimLedgerBuildResult) -> None:
    placeholder_re = re.compile(r"\{\{[^}]+\}\}")
    for claim in claims:
        if claim.get("claim_type") == "author_asserted":
            continue
        masked = placeholder_re.sub("", str(claim.get("prose_template") or ""))
        numeric_uses = extract_numeric_uses(masked)
        if numeric_uses:
            claim["status"] = "hard_block"
            claim["gate_tier"] = "hard_block"
            claim.setdefault("gate_reasons", []).append("raw_numeric_template")
            result.add_issue(
                "raw_numeric_claim_template",
                "hard_block",
                f"Claim `{claim.get('claim_id')}` contains raw numeric prose instead of placeholders.",
            )


def _apply_author_overrides(claims: list[dict[str, Any]], overrides_payload: dict[str, Any], result: ClaimLedgerBuildResult) -> None:
    overrides = overrides_payload.get("overrides", []) if isinstance(overrides_payload, dict) else []
    by_id = {str(item.get("claim_id")): item for item in overrides if isinstance(item, dict) and item.get("claim_id")}
    by_type = {str(item.get("claim_type")): item for item in overrides if isinstance(item, dict) and item.get("claim_type")}
    for claim in claims:
        override = by_id.get(str(claim.get("claim_id"))) or by_type.get(str(claim.get("claim_type")))
        if not override:
            continue
        reason = str(override.get("reason") or "").strip()
        if not reason:
            claim.setdefault("override_rejected", []).append("Author override reason is required.")
            continue
        if claim.get("status") == "hard_block":
            claim.setdefault("override_rejected", []).append("Hard-blocked claims are non-overridable.")
            continue
        if claim.get("status") == "safe":
            claim.setdefault("override_rejected", []).append("Safe claims do not need an author override.")
            continue
        original_status = str(claim.get("status"))
        claim["status"] = "author_asserted"
        claim["gate_tier"] = "author_asserted"
        claim["author_override"] = {
            "asserted": True,
            "original_status": original_status,
            "reason": reason,
        }


def _author_report_text(result: ClaimLedgerBuildResult) -> str:
    claims = result.claim_ledger.get("claims", [])
    hard_blocks = [issue for issue in result.issues if issue.severity == "hard_block"]
    flagged = [claim for claim in claims if claim.get("status") == "flag_and_confirm"]
    author_asserted = [claim for claim in claims if claim.get("status") == "author_asserted"]
    safe = [claim for claim in claims if claim.get("status") == "safe"]
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Claim Ledger Status",
        "",
        f"- Status: `{result.status}`",
        f"- Safe claims: `{len(safe)}`",
        f"- Flag-and-confirm claims: `{len(flagged)}`",
        f"- Author-asserted claims: `{len(author_asserted)}`",
        f"- Hard blocks: `{len(hard_blocks)}`",
        "",
        "## Safe Claims",
        "",
    ]
    lines.extend([f"- {_claim_report_line(claim)}" for claim in safe] if safe else ["- None."])
    lines.extend(["", "## Flagged And Downgraded Claims", ""])
    lines.extend([f"- `{claim['claim_id']}` reasons: {', '.join(claim.get('gate_reasons', []))}" for claim in flagged] if flagged else ["- None."])
    lines.extend(["", "## Author-Asserted Claims", ""])
    if author_asserted:
        for claim in author_asserted:
            override = claim.get("author_override") or {}
            lines.append(
                f"- `{claim['claim_id']}` original: `{override.get('original_status', claim.get('gate_tier'))}`; reason: {override.get('reason', '')}"
            )
    else:
        lines.append("- None.")
    lines.extend(["", "## Non-Overridable Hard Blocks", ""])
    lines.extend([f"- `{issue.code}`: {issue.message}" for issue in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Resolve hard blocks before section writing.")
    elif flagged:
        lines.append("- Add missing magnitude/design diagnostics or supply author overrides with reasons.")
    else:
        lines.append("- Continue to section writers.")
    return "\n".join(lines) + "\n"


def _claim_report_line(claim: dict[str, Any]) -> str:
    metadata = claim.get("metadata") if isinstance(claim.get("metadata"), dict) else {}
    variable = metadata.get("variable") or "unspecified variable"
    magnitude_variable = metadata.get("magnitude_variable")
    refs = claim.get("evidence_refs") if isinstance(claim.get("evidence_refs"), list) else []
    pieces = [
        f"`{claim.get('claim_id')}`",
        "ready for verified prose",
        f"variable: `{variable}`",
        f"evidence refs: `{len(refs)}`",
    ]
    if magnitude_variable:
        pieces.append(f"magnitude variable: `{magnitude_variable}`")
    return "; ".join(pieces) + "."
