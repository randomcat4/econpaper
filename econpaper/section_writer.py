from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SECTION_WRITER_VERSION = "v3.0"
AUTHOR_INPUT_NEEDED = "[AUTHOR_INPUT_NEEDED]"
CITE_NEEDED = "[CITE_NEEDED: preferred related-literature references]"
TIER_B_SAFE_WORD_TARGET = 2500
TIER_A_RELEASE_WORD_TARGET = 6000
WRITING_ORDER = [
    "02_data.md",
    "03_empirical_strategy.md",
    "04_results.md",
    "05_robustness.md",
    "06_mechanisms.md",
    "07_heterogeneity.md",
    "08_limitations.md",
    "09_conclusion.md",
    "00_abstract.md",
    "01_introduction.md",
    "10_related_literature_skeleton.md",
]


@dataclass
class SectionWriterIssue:
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
class SectionWriterResult:
    sections: dict[str, str]
    audit: dict[str, Any]
    status: str = "passed"
    issues: list[SectionWriterIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(SectionWriterIssue(code=code, severity=severity, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SECTION_WRITER_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "audit": self.audit,
            "sections": sorted(self.sections),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def generate_sections(
    *,
    claim_ledger_path: str | Path,
    intake_profile_path: str | Path,
    citation_index_path: str | Path | None = None,
    table_path: str | Path | None = None,
    artifact_dir: str | Path | None = None,
) -> SectionWriterResult:
    result = SectionWriterResult(
        sections={},
        audit={
            "version": SECTION_WRITER_VERSION,
            "writing_order": WRITING_ORDER,
            "safe_claim_ids_used": [],
            "safe_claim_ids_available": [],
            "safe_claim_ids_held_for_table_or_appendix": [],
            "author_asserted_claim_ids_used": [],
            "mechanism_assertion_ids_used": [],
            "flagged_claim_ids_not_written_as_verified": [],
            "section_note_ids_available": [],
            "section_note_ids_used": [],
            "table_path": str(table_path) if table_path else None,
            "artifact_dir": str(artifact_dir) if artifact_dir else None,
            "expansion_policy": {
                "safe_word_target": TIER_B_SAFE_WORD_TARGET,
                "release_word_target": TIER_A_RELEASE_WORD_TARGET,
                "tier_b_scope": "Expand verified evidence architecture, not unverified literature or mechanisms.",
                "tier_a_requires": [
                    "verified literature notes",
                    "author-confirmed institutional context",
                    "human release evaluation",
                ],
            },
        },
    )
    claim_ledger = _load_json(Path(claim_ledger_path), result, "claim_ledger")
    intake = _load_json(Path(intake_profile_path), result, "intake_profile")
    citation_index = _load_json(Path(citation_index_path), result, "citation_index") if citation_index_path else {}
    artifact_path = Path(artifact_dir) if artifact_dir else None
    section_notes = _section_notes_by_section(intake)
    result.audit["section_note_ids_available"] = [
        note["note_id"] for notes in section_notes.values() for note in notes
    ]

    if claim_ledger.get("status") == "failed" or claim_ledger.get("hard_blocks"):
        result.add_issue("claim_ledger_has_hard_blocks", "hard_block", "Section writer will not write verified result claims from a failed claim ledger.", str(claim_ledger_path))

    claims = claim_ledger.get("claims", []) if isinstance(claim_ledger, dict) else []
    safe_claims = [claim for claim in claims if isinstance(claim, dict) and claim.get("status") == "safe"]
    author_asserted_claims = [claim for claim in claims if isinstance(claim, dict) and claim.get("status") == "author_asserted"]
    mechanism_assertions = [claim for claim in author_asserted_claims if _claim_assertion_type(claim) == "mechanism"]
    non_mechanism_assertions = [claim for claim in author_asserted_claims if claim not in mechanism_assertions]
    flagged_claims = [claim for claim in claims if isinstance(claim, dict) and claim.get("status") == "flag_and_confirm"]
    if result.has_hard_blocks:
        safe_claims = []
    result_claims = _select_result_claims(safe_claims)
    used_claim_ids = {claim.get("claim_id") for claim in result_claims}
    result.audit["safe_claim_ids_available"] = [claim["claim_id"] for claim in safe_claims]
    result.audit["safe_claim_ids_used"] = [claim["claim_id"] for claim in result_claims]
    result.audit["safe_claim_ids_held_for_table_or_appendix"] = [
        claim["claim_id"] for claim in safe_claims if claim.get("claim_id") not in used_claim_ids
    ]
    result.audit["author_asserted_claim_ids_used"] = [claim["claim_id"] for claim in author_asserted_claims]
    result.audit["mechanism_assertion_ids_used"] = [claim["claim_id"] for claim in mechanism_assertions]
    result.audit["flagged_claim_ids_not_written_as_verified"] = [claim["claim_id"] for claim in flagged_claims]

    result.sections = {
        "02_data.md": _data_section(intake),
        "03_empirical_strategy.md": _strategy_section(intake),
        "04_results.md": _results_section(result_claims, safe_claims, non_mechanism_assertions, flagged_claims, table_path, artifact_path, blocked=result.has_hard_blocks),
        "05_robustness.md": _robustness_section(artifact_path),
        "06_mechanisms.md": _mechanisms_section(mechanism_assertions),
        "07_heterogeneity.md": _heterogeneity_section(artifact_path),
        "08_limitations.md": _limitations_section(flagged_claims, intake),
        "09_conclusion.md": _conclusion_section(safe_claims, author_asserted_claims, intake, blocked=result.has_hard_blocks),
        "00_abstract.md": _abstract_section(safe_claims, author_asserted_claims, intake, blocked=result.has_hard_blocks),
        "01_introduction.md": _introduction_skeleton(intake),
        "10_related_literature_skeleton.md": _related_literature_skeleton(citation_index),
    }
    _append_section_notes(result.sections, section_notes, result.audit)
    return result


def write_sections(
    *,
    claim_ledger_path: str | Path,
    intake_profile_path: str | Path,
    out_dir: str | Path,
    citation_index_path: str | Path | None = None,
    table_path: str | Path | None = None,
) -> SectionWriterResult:
    result = generate_sections(
        claim_ledger_path=claim_ledger_path,
        intake_profile_path=intake_profile_path,
        citation_index_path=citation_index_path,
        table_path=table_path,
        artifact_dir=out_dir,
    )
    out_path = Path(out_dir)
    sections_dir = out_path / "sections"
    internal = out_path / "reports" / "internal"
    sections_dir.mkdir(parents=True, exist_ok=True)
    internal.mkdir(parents=True, exist_ok=True)
    for filename, text in result.sections.items():
        (sections_dir / filename).write_text(text, encoding="utf-8")
    (internal / "section_generation.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _load_json(path: Path, result: SectionWriterResult, label: str) -> dict[str, Any]:
    if not path.exists():
        result.add_issue(f"{label}_missing", "hard_block", f"{label} file does not exist: {path}", str(path))
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


def _data_section(intake: dict[str, Any]) -> str:
    design = intake.get("author_declared_design", {}) if isinstance(intake, dict) else {}
    timing = intake.get("treatment_timing", {}) if isinstance(intake, dict) else {}
    outcomes = intake.get("outcome_magnitude_context", []) if isinstance(intake, dict) else []
    missing = _missing_fields(
        [
            (design.get("unit_of_observation"), "unit of observation"),
            (design.get("sample_scope"), "sample scope"),
            (timing.get("treatment_name"), "treatment/exposure/shock definition"),
            (timing.get("timing_type"), "treatment timing type"),
        ]
    )
    if not outcomes:
        missing.append("outcome magnitude context with variable, unit, mean, and standard deviation")
    else:
        for idx, item in enumerate(outcomes, start=1):
            if not isinstance(item, dict):
                missing.append(f"outcome magnitude context row {idx} as an object")
                continue
            missing.extend(
                f"outcome magnitude context row {idx}: {label}"
                for label in _missing_fields(
                    [
                        (item.get("variable"), "variable"),
                        (item.get("unit"), "unit"),
                        (item.get("mean"), "mean"),
                        (item.get("sd"), "standard deviation"),
                    ]
                )
            )
    if missing:
        return _floor_section("Data", missing)
    lines = [
        "# Data",
        "",
        f"The unit of observation is {design.get('unit_of_observation')}.",
        f"The sample scope is {design.get('sample_scope')}.",
        f"The treatment, exposure, or shock is {timing.get('treatment_name')}.",
        f"Treatment timing is {timing.get('timing_type')}.",
        "",
        "This section is intentionally descriptive. It records the author-supplied data boundary that downstream claims may use, but it does not infer sampling representativeness, institutional coverage, or external validity beyond the declared sample. The drafting system treats the unit, sample period, treatment name, and timing structure as hard writing inputs because every numerical sentence downstream inherits those labels.",
        "",
        "The current data description is strong enough for a Tier B draft when the rest of the evidence pack is complete: a reader can see the observation grain, the policy exposure, and the period over which the comparison is made. It is not yet a release-quality data section by itself. A finished journal draft still needs author-confirmed source construction, sample restrictions, cleaning rules, and any exclusions that are material for interpretation.",
        "",
        "The single-cohort timing statement also helps discipline the interpretation of the event-study output. The draft can distinguish treated plants from never-treated plants and can name the treatment timing convention, but it should not infer staggered adoption, anticipation behavior, or spillover structure unless those features are supplied as design inputs. This keeps the data section useful for readers while keeping unobserved design detail out of the manuscript.",
        "",
        "## Outcome Magnitude Context",
        "",
    ]
    for item in outcomes:
        if not isinstance(item, dict):
            continue
        variable = str(item.get("variable"))
        unit = str(item.get("unit"))
        mean = str(item.get("mean"))
        sd = str(item.get("sd"))
        lines.append(f"- `{variable}` is measured in {unit}; mean: {mean}; standard deviation: {sd}.")
    lines.extend(
        [
            "",
            "The magnitude context is used only for display-scale interpretation. It permits statements that translate an already verified coefficient into the declared outcome scale, but it does not create new statistical evidence. If the author later changes the unit, mean, or standard deviation, every magnitude sentence should be regenerated rather than edited by hand.",
        ]
    )
    return "\n".join(lines) + "\n"


def _strategy_section(intake: dict[str, Any]) -> str:
    design = intake.get("author_declared_design", {}) if isinstance(intake, dict) else {}
    timing = intake.get("treatment_timing", {}) if isinstance(intake, dict) else {}
    missing = _missing_fields(
        [
            (design.get("design_type"), "declared design type"),
            (design.get("estimand"), "estimand in author language"),
            (timing.get("event_time_unit"), "event-time unit"),
            (timing.get("anticipation_window"), "anticipation window"),
        ]
    )
    if missing:
        return _floor_section("Empirical Strategy", missing)
    lines = [
        "# Empirical Strategy",
        "",
        f"The author-declared design is {design.get('design_type')}.",
        f"The estimand is {design.get('estimand')}.",
        f"The event-time unit is {timing.get('event_time_unit')}.",
        f"The anticipation window is {timing.get('anticipation_window')}.",
        "",
        "The writing layer treats this design statement as a binding scope condition. It can explain the declared comparison, the estimand, and the timing convention, but it cannot strengthen the design into a causal claim unless the design profile and global coherence gates have passed. When the design gate passes, the manuscript may use the author-declared identification language with restraint; when it does not, the section remains a visible floor rather than a disguised methods section.",
        "",
        "For a DID/event-study draft, the strategy prose should separate three objects that are easy to blur: the main treatment-period contrast, the event-time profile, and the pre-trend diagnostic surface. The event-study evidence supports a timing narrative only after the pre-treatment rows, pretrend test, and comparison group declaration are present in the EvidencePack. The prose should therefore describe the estimation architecture before interpreting any single coefficient.",
        "",
        "The never-treated comparison group is part of the declared design rather than a conclusion drawn by the writer. The section can explain that the comparison group gives the event-time profile a stable reference category, while the pre-treatment rows and pretrend test remain diagnostics for whether stronger causal language is appropriate. That structure is enough for a complete Tier B methods discussion because the empirical objects are named and bounded.",
        "",
        "A release draft would still need the author to state the identifying assumptions in the paper's own voice. The system can preserve the declared estimand and estimator boundary, but it should not decide whether parallel trends, no anticipation, or spillover restrictions are substantively credible in this setting. Those assumptions are not formatting details; they are the author's economics argument.",
        "",
        "Identification and causal language remain subject to design gates and author confirmation. The system should not add assumptions, institutional timing facts, or estimator comparisons that are absent from the intake profile or typed artifacts.",
    ]
    return "\n".join(lines) + "\n"


def _results_section(
    result_claims: list[dict[str, Any]],
    all_safe_claims: list[dict[str, Any]],
    author_asserted_claims: list[dict[str, Any]],
    flagged_claims: list[dict[str, Any]],
    table_path: str | Path | None,
    artifact_dir: Path | None,
    *,
    blocked: bool,
) -> str:
    lines = ["# Results", ""]
    if blocked:
        return _floor_section(
            "Results",
            ["resolve claim-ledger hard blocks before writing verified result claims"],
            notes=_results_floor_notes(author_asserted_claims, flagged_claims, table_path),
        )
    if not result_claims:
        return _floor_section(
            "Results",
            ["ledger-backed safe main-result claim"],
            notes=_results_floor_notes(author_asserted_claims, flagged_claims, table_path),
        )
    if table_path:
        lines.append("Table 1 reports the main model estimates.")
        lines.append("")
    lines.append(
        "The results are written from the claim ledger rather than from free-form numerical prose. This is deliberate: the prose may interpret verified coefficients, standard errors, p-values, sample size, and declared magnitude context, but it may not introduce additional estimates, alternative standard errors, or unreported tests."
    )
    lines.append("")
    primary = _primary_result_claim(result_claims)
    event_anchor = _event_anchor_claim(result_claims)
    if primary:
        lines.append("The main treatment-period contrast is the first object to interpret:")
        lines.append(primary["prose_template"])
        lines.append("")
        lines.append(
            "The magnitude sentence is intentionally tied to the declared outcome scale. It should be read as a scale translation of the verified coefficient, not as a welfare calculation or a claim about aggregate emissions. Large standardized magnitudes should be left visible rather than softened; the right follow-up is author review of units, summary statistics, and sample construction, not prose that hides the scale."
        )
        lines.append("")
    if event_anchor and event_anchor is not primary:
        lines.append("The event-study evidence is reported as a timing profile rather than as separate discoveries for each event-time coefficient. The treatment-period event-study anchor is:")
        lines.append(event_anchor["prose_template"])
        lines.append("")
        lines.append(
            "The event-study paragraph should give readers the shape of the evidence without repeating every row as a headline sentence. A figure or table is the right home for the sequence; prose should explain why the sequence matters for timing, diagnostics, and interpretation."
        )
        lines.append("")
    lines.extend(_event_study_summary_notes(artifact_dir, all_safe_claims, flagged_claims))
    held = [claim for claim in all_safe_claims if claim not in result_claims]
    if held:
        held_labels = _dedupe([_claim_label(claim) for claim in held])
        held_variables = ", ".join(held_labels[:8])
        extra = "" if len(held_labels) <= 8 else f", plus {len(held_labels) - 8} additional ledger-backed variables"
        lines.extend(
            [
                "",
                "The remaining verified claim rows are held for the table, figure, or appendix rather than repeated as near-identical prose sentences. Held variables: "
                + held_variables
                + extra
                + ".",
            ]
        )
    if author_asserted_claims:
        lines.extend(["", "## Author-Asserted Statements", ""])
        for claim in author_asserted_claims:
            lines.append(f"- Author asserted: {claim['prose_template']}")
    if flagged_claims:
        lines.extend(["", "## Not Written As Verified Claims", ""])
        for claim in flagged_claims:
            reasons = ", ".join(claim.get("gate_reasons", [])) or "flag_and_confirm"
            lines.append(f"- `{claim['claim_id']}` requires confirmation before verified prose: {reasons}.")
        lines.append("")
        lines.append("These flagged rows are not treated as evidence against the design; they are a reporting boundary. The draft may discuss that pre-treatment rows are reserved for diagnostics, but it should not report incomplete-inference rows as ordinary main effects.")
    return "\n".join(lines) + "\n"


def _placeholder_section(title: str, needed: str) -> str:
    return _floor_section(title, [needed])


def _mechanisms_section(mechanism_assertions: list[dict[str, Any]]) -> str:
    if not mechanism_assertions:
        return _placeholder_section("Mechanisms", "mechanism diagnostics or author-confirmed mechanism claims")
    lines = [
        "# Mechanisms",
        "",
        "The following mechanism statements are included as author-labeled assertions, not as independently verified mechanism evidence:",
        "",
    ]
    for claim in mechanism_assertions:
        override = claim.get("author_override") if isinstance(claim.get("author_override"), dict) else {}
        reason = str(override.get("reason") or "").strip().rstrip(".")
        lines.append(f"- `{claim.get('claim_id')}`: {claim.get('prose_template')}")
        if reason:
            lines.append(f"  Author framing: {_public_note_text(reason)}.")
    lines.extend(
        [
            "",
            "These statements should be converted to evidence-backed mechanism claims only after separate diagnostics or source notes are supplied.",
            "",
            "The prose boundary matters here. A tasteful draft can explain why the author believes the mechanism is relevant, and it can place the assertion next to the main results as a hypothesis for interpretation. It cannot say that the mechanism is established, confirmed, or decomposed by the current evidence pack. If the author wants stronger language, the next intake must supply mechanism diagnostics, institutional source notes, or a clearly labeled theoretical model.",
            "",
            "This is also where the draft should resist a common failure mode: turning a plausible story into evidence. Compliance-driven upgrades and fuel-substitution incentives may be the author's preferred channel, but the current pack does not separate those channels or measure them directly. The mechanism paragraph therefore remains useful as a labeled interpretation task rather than a hidden result.",
        ]
    )
    return "\n".join(lines) + "\n"


def _robustness_section(artifact_dir: Path | None) -> str:
    robustness_rows = _read_csv_rows(artifact_dir / "robustness_grid.csv") if artifact_dir else []
    placebo_rows = _read_csv_rows(artifact_dir / "placebo_tests.csv") if artifact_dir else []
    families = sorted(
        {
            _humanize(row.get("family") or row.get("robustness_family") or row.get("check_family"))
            for row in robustness_rows
            if _present(row.get("family") or row.get("robustness_family") or row.get("check_family"))
        }
    )
    placebo_statuses = sorted({_humanize(row.get("status")) for row in placebo_rows if _present(row.get("status"))})
    if not families and not placebo_statuses:
        return _placeholder_section("Robustness", "robustness checks, sensitivity analyses, and alternative specifications")
    lines = ["# Robustness", ""]
    if families:
        lines.append("The robustness grid is available and records the following check families:")
        for family in families:
            lines.append(f"- {family}.")
    if placebo_statuses:
        lines.extend(["", "Placebo timing diagnostics are present with labeled computation status."])
    lines.append("")
    lines.append("These diagnostics are reported as verification scaffolding; they do not replace the main result claims in the Results section.")
    lines.append("")
    lines.append("A polished robustness section should describe coverage, not victory. The current artifact surface is sufficient to tell the reader which families were computed and which checks belong to placebo timing, estimator comparison, sample construction, subgroup heterogeneity, or cluster diagnostics. It is not a license to claim that every alternative specification is invariant unless the grid contains structured estimates and the writer has a rule for summarizing them without creating new statistics.")
    lines.append("")
    lines.append("The placebo material is especially easy to overstate. Its safe role in the draft is to show that placebo timing was included in the diagnostic surface. It should not be described as proving the absence of confounding unless the placebo artifact is itself converted into verified claims with the relevant estimates, inference fields, and author-approved interpretation.")
    lines.append("")
    lines.append("For Tier B prose, the safest move is to state that the robustness architecture is present and to direct substantive interpretation back to the main ledger-backed claims. For Tier A prose, the author should decide which robustness families are central to the paper's argument, because a journal-style discussion needs priorities rather than a flat inventory.")
    return "\n".join(lines) + "\n"


def _heterogeneity_section(artifact_dir: Path | None) -> str:
    rows = _read_csv_rows(artifact_dir / "heterogeneity.csv") if artifact_dir else []
    dimensions = sorted(
        {
            _humanize(row.get("dimension") or row.get("heterogeneity_dimension"))
            for row in rows
            if _present(row.get("dimension") or row.get("heterogeneity_dimension"))
        }
    )
    statuses = sorted({_humanize(row.get("status")) for row in rows if _present(row.get("status"))})
    if not dimensions:
        return _placeholder_section("Heterogeneity", "heterogeneity groups, subgroup definitions, and multiple-testing policy")
    lines = [
        "# Heterogeneity",
        "",
        "Heterogeneity diagnostics are available for the following author-configured dimensions:",
    ]
    for dimension in dimensions:
        lines.append(f"- {dimension}.")
    if statuses:
        lines.extend(["", "Rows with insufficient treatment variation remain labeled rather than being converted into verified subgroup claims."])
    lines.extend(
        [
            "",
            "The section should be read as a map of available subgroup diagnostics, not as a mechanism proof. The writer can name the configured dimensions and explain why they structure the table, but it should avoid ranking groups, comparing subgroup magnitudes, or explaining cross-group differences unless those contrasts are explicitly represented as verified claims.",
            "",
            "This boundary keeps the draft useful without becoming overconfident. Readers learn where heterogeneity has been checked, while the author still owns any substantive interpretation of why a baseline-size group or province group might respond differently.",
            "",
            "For a stronger draft, heterogeneity should be linked to a pre-specified interpretation plan. If the author wants to emphasize size or province differences, the next intake should say whether those dimensions proxy for baseline emissions, compliance capacity, policy exposure, or another economic concept. Without that author input, the section should remain descriptive.",
        ]
    )
    return "\n".join(lines) + "\n"


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except Exception:
        return []


def _present(value: Any) -> bool:
    return value not in {None, "", "nan", "NaN", "NA", "N/A"}


def _humanize(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[_\s]+", " ", text)
    return text[:1].upper() + text[1:] if text else text


def _claim_assertion_type(claim: dict[str, Any]) -> str:
    metadata = claim.get("metadata") if isinstance(claim.get("metadata"), dict) else {}
    raw = metadata.get("assertion_type") or claim.get("assertion_type") or ""
    return str(raw).strip().lower()


def _limitations_section(flagged_claims: list[dict[str, Any]], intake: dict[str, Any]) -> str:
    sample_scope = _value((intake.get("author_declared_design") or {}).get("sample_scope"), "sample scope") if isinstance(intake, dict) else _value(None, "sample scope")
    if not flagged_claims:
        return _floor_section("Limitations", ["limitations and external-validity scope"], notes=[f"Current sample scope: {sample_scope}."])
    lines = ["# Limitations", "", f"The current sample scope is {sample_scope}."]
    lines.append(
        "The draft's main limitation is not the absence of a typed evidence surface; for the current vertical slice, the core DID artifacts are present. The limitation is the boundary between verified empirical output and author-owned interpretation. The manuscript should therefore be explicit about what the system has checked and what remains outside the machine evidence contract."
    )
    lines.extend(["", "The following claims require author or design confirmation before stronger language is used:"])
    for claim in flagged_claims:
        lines.append(f"- `{claim['claim_id']}`: {', '.join(claim.get('gate_reasons', []))}.")
    lines.extend(
        [
            "",
            "A Tier B draft can carry these limitations openly. A Tier A or release draft needs the author to resolve the missing-inference rows, confirm the institutional and literature positioning, and pass human evaluation. The writer should never hide these items by converting them into generic caveats.",
            "",
            "The word-count boundary is also substantive. Expanding from the verified scaffold to a Tier B draft is safe when the additional text clarifies design, evidence routing, diagnostic coverage, and interpretation limits. Expanding to a full release-length manuscript without literature notes, institutional detail, or human evaluation would create padding. The release gate should treat that as a quality failure even if the typed evidence artifacts are complete.",
        ]
    )
    return "\n".join(lines) + "\n"


def _conclusion_section(
    safe_claims: list[dict[str, Any]],
    author_asserted_claims: list[dict[str, Any]],
    intake: dict[str, Any],
    *,
    blocked: bool,
) -> str:
    contribution_value = intake.get("contribution_statement") if isinstance(intake, dict) else None
    contribution = _value(contribution_value, "contribution statement")
    missing = _missing_fields([(contribution_value, "contribution statement")])
    if blocked:
        return _floor_section("Conclusion", ["resolve hard blocks before summarizing verified results"])
    if missing:
        return _floor_section("Conclusion", missing)
    if not safe_claims:
        needed = ["verified main result claim"]
        if author_asserted_claims:
            needed.append("author-asserted claims confirmed or converted to evidence-backed claims")
        return _floor_section("Conclusion", needed)
    lines = ["# Conclusion", "", f"Contribution to carry forward: {contribution}"]
    lines.append(
        "The conclusion should stay close to the verified evidence. Its job is to restate the paper's contribution, remind the reader of the design boundary, and identify which interpretations remain author-labeled rather than machine-verified."
    )
    lines.append("")
    lines.append("The conclusion should summarize the same ledger-backed main result used in Results:")
    lines.append(safe_claims[0]["prose_template"])
    lines.append("")
    lines.append(
        "The final paragraph should not add a new mechanism, policy ranking, or external-validity claim. Those elements belong in the next author intake unless they are already backed by source notes or additional diagnostics."
    )
    return "\n".join(lines) + "\n"


def _abstract_section(
    safe_claims: list[dict[str, Any]],
    author_asserted_claims: list[dict[str, Any]],
    intake: dict[str, Any],
    *,
    blocked: bool,
) -> str:
    project = intake.get("project", {}) if isinstance(intake, dict) else {}
    design = intake.get("author_declared_design", {}) if isinstance(intake, dict) else {}
    contribution_value = intake.get("contribution_statement") if isinstance(intake, dict) else None
    missing = _missing_fields(
        [
            (project.get("title_working"), "working title"),
            (design.get("design_type"), "declared design type"),
            (contribution_value, "contribution statement"),
        ]
    )
    if blocked:
        return _floor_section("Abstract", ["verified abstract result after hard blocks are resolved"])
    if missing:
        return _floor_section("Abstract", missing)
    if not safe_claims:
        needed = ["ledger-backed result sentence"]
        if author_asserted_claims:
            needed.append("author-asserted result language confirmed or converted to evidence-backed language")
        return _floor_section("Abstract", needed)
    contribution = str(contribution_value)
    lines = [
        "# Abstract",
        "",
        f"Working title: {project.get('title_working')}.",
        f"Design: {design.get('design_type')}.",
        contribution,
    ]
    lines.append(safe_claims[0]["prose_template"])
    lines.append(
        "The abstract should remain compact until the author supplies verified literature positioning and release-level interpretation."
    )
    return "\n".join(lines) + "\n"


def _introduction_skeleton(intake: dict[str, Any]) -> str:
    project = intake.get("project", {}) if isinstance(intake, dict) else {}
    motivation_value = intake.get("research_motivation") if isinstance(intake, dict) else None
    contribution_value = intake.get("contribution_statement") if isinstance(intake, dict) else None
    context = intake.get("institutional_context", []) if isinstance(intake, dict) else []
    missing = _missing_fields(
        [
            (project.get("title_working"), "working title"),
            (motivation_value, "research motivation"),
            (contribution_value, "contribution statement"),
        ]
    )
    if not context:
        missing.append("institutional, historical, or regulatory context")
    else:
        for idx, item in enumerate(context, start=1):
            if not isinstance(item, dict) or _is_missing(item.get("fact")):
                missing.append(f"institutional context row {idx}: fact")
    if missing:
        return _floor_section("Introduction", missing)
    motivation = str(motivation_value)
    contribution = str(contribution_value)
    lines = [
        "# Introduction",
        "",
        f"Working title: {project.get('title_working')}.",
        "",
        f"{motivation}",
        "",
        f"{contribution}",
        "",
        "The introduction can safely motivate the paper from the author-provided problem statement and the declared empirical design. It should not claim novelty, rank the paper within a literature, or describe institutional history beyond the supplied context. This gives the reader a coherent opening while preserving the boundary between a polished draft and a release-ready paper.",
        "",
        "The current vertical slice is best framed as a transparent evidence-to-writing pipeline for the stated empirical question. The draft can say what the paper measures, how the treatment timing is represented, and why magnitude interpretation matters. It should leave field positioning, welfare interpretation, and detailed policy history to author-supplied notes.",
        "",
        "Institutional context:",
    ]
    for item in context:
        if isinstance(item, dict):
            lines.append(f"- {item.get('fact')}")
    lines.extend(
        [
            "",
            "A complete introduction should eventually add the author's preferred reader-facing contribution, the relevant institutional chronology, and verified literature positioning. Until those inputs arrive, the introduction should remain modest: it can make the research question legible, but it should not manufacture a field-level claim.",
            "",
            "A tasteful version of this introduction would make the reader confident about the object of study before asking them to trust the empirical results. It would define the policy exposure in the author's terminology, explain why plant-level emissions intensity is the relevant outcome, and preview the event-study design without turning the opening into a methods appendix. Those additions require author-supplied context, not model improvisation.",
        ]
    )
    return "\n".join(lines) + "\n"


def _related_literature_skeleton(citation_index: dict[str, Any]) -> str:
    citekeys = citation_index.get("citekeys", []) if isinstance(citation_index, dict) else []
    note_entries = citation_index.get("literature_note_entries", []) if isinstance(citation_index, dict) else []
    note_entries = [item for item in note_entries if isinstance(item, dict) and item.get("citekey") and item.get("note")]
    lines = ["# Related Literature", ""]
    if note_entries:
        lines.append("This section uses verified author-provided literature notes. It still avoids claims that are not present in those notes.")
    else:
        lines.append("This section intentionally avoids literature-search prose until the author supplies verified literature notes.")
    if citekeys:
        keys = ", ".join(f"`{key}`" for key in citekeys[:10])
        lines.append(f"Supplied bibliography keys available for author positioning: {keys}.")
        if note_entries:
            lines.extend(["", "## Note-Backed Positioning Inputs", ""])
            for entry in note_entries[:8]:
                note = _public_note_text(entry.get("note") or "")
                lines.append(f"- `{entry.get('citekey')}`: {note}")
            lines.append("")
            lines.append(
                "These bullets are not generated literature claims; they are author-provided note-backed inputs that the writer may use for positioning. The draft should preserve the contrast stated in the note and avoid broad novelty language unless a note explicitly supports it."
            )
        else:
            lines.append("Use author-provided notes before turning these keys into literature claims.")
        lines.append("")
        lines.append(
            "The presence of a BibTeX key is not evidence that a literature claim is true. For Tier B, the draft may list the keys as available positioning material and identify the missing author task. For Tier A, every sentence that says how this paper relates to prior work should come from a verified note, a mapped citation use, or an explicit author assertion."
        )
        lines.append("")
        lines.append(
            "The writer should therefore avoid stock phrases such as 'the first paper,' 'extends the literature,' or 'fills a gap' unless the intake contains the comparison and the citation safety report can trace the claim. This is a quality constraint, not a formatting nicety: fabricated positioning is as damaging as fabricated numbers."
        )
        lines.append("")
        lines.append(
            "The next author input should be narrow and concrete: for each cited work, provide the paper's empirical setting, method, main finding, and the exact contrast to the current draft. With that note structure, the writer can produce related-work prose that is specific without being invented."
        )
    else:
        lines.append(CITE_NEEDED)
    return "\n".join(lines) + "\n"


def _select_result_claims(safe_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_variable: dict[str, dict[str, Any]] = {}
    for claim in safe_claims:
        variable = _claim_variable(claim)
        if not variable:
            continue
        current = by_variable.get(variable)
        if current is None or _claim_preference(claim) > _claim_preference(current):
            by_variable[variable] = claim
    ordered_variables = ["_did_treat_post", "event_0"]
    selected = [by_variable[var] for var in ordered_variables if var in by_variable]
    if not selected and by_variable:
        selected.append(next(iter(sorted(by_variable.items())))[1])
    if not selected and safe_claims:
        selected.append(safe_claims[0])
    return selected


def _claim_preference(claim: dict[str, Any]) -> tuple[int, int, int]:
    slots = claim.get("numeric_slots") if isinstance(claim.get("numeric_slots"), list) else []
    metadata = claim.get("metadata") if isinstance(claim.get("metadata"), dict) else {}
    artifact_id = str(metadata.get("artifact_id") or "")
    return (
        1 if any(str(slot).startswith("n:") for slot in slots) else 0,
        1 if artifact_id == "model_table_model_table_csv" else 0,
        len(claim.get("evidence_refs") or []),
    )


def _primary_result_claim(claims: list[dict[str, Any]]) -> dict[str, Any] | None:
    for claim in claims:
        if _claim_variable(claim) == "_did_treat_post":
            return claim
    return claims[0] if claims else None


def _event_anchor_claim(claims: list[dict[str, Any]]) -> dict[str, Any] | None:
    for claim in claims:
        if _claim_variable(claim) == "event_0":
            return claim
    return None


def _claim_variable(claim: dict[str, Any]) -> str:
    metadata = claim.get("metadata") if isinstance(claim.get("metadata"), dict) else {}
    return str(metadata.get("variable") or "").strip()


def _claim_label(claim: dict[str, Any]) -> str:
    variable = _claim_variable(claim) or str(claim.get("claim_id") or "claim")
    return f"`{variable}`"


def _event_study_summary_notes(
    artifact_dir: Path | None,
    all_safe_claims: list[dict[str, Any]],
    flagged_claims: list[dict[str, Any]],
) -> list[str]:
    notes: list[str] = []
    rows = _read_csv_rows(artifact_dir / "event_study.csv") if artifact_dir else []
    if rows:
        pre_rows = [row for row in rows if (_event_time_value(row) or 0) < 0]
        post_rows = [row for row in rows if (_event_time_value(row) or 0) >= 0]
        notes.append(
            f"The event-study artifact contains {len(pre_rows)} pre-treatment row(s) and {len(post_rows)} treatment-or-post row(s). The writer should discuss this as a profile with diagnostics, not as a set of independent headline findings."
        )
    event_claim_count = sum(1 for claim in all_safe_claims if _claim_variable(claim).startswith("event_"))
    if event_claim_count:
        notes.append(
            f"The claim ledger contains {event_claim_count} verified post-treatment event-study claim(s). The prose reports a representative anchor and leaves the full sequence to the table or figure to avoid mechanical repetition."
        )
    if flagged_claims:
        notes.append(
            "Pre-treatment coefficients with missing inference statistics stay in the flagged list. They can guide diagnostic questions, but they are not written as verified result claims."
        )
    return notes


def _event_time_value(row: dict[str, Any]) -> int | None:
    for key in ["event_time", "relative_time"]:
        try:
            return int(float(str(row.get(key)).strip()))
        except Exception:
            pass
    term = str(row.get("term") or "")
    match = re.search(r"(-?\d+)", term)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _results_floor_notes(
    author_asserted_claims: list[dict[str, Any]],
    flagged_claims: list[dict[str, Any]],
    table_path: str | Path | None,
) -> list[str]:
    notes: list[str] = []
    if table_path:
        notes.append("A main table shell exists, but verified Results prose is withheld until claim gates pass.")
    for claim in author_asserted_claims:
        notes.append(f"Author-asserted claim held as labeled input: `{claim.get('claim_id')}`.")
    for claim in flagged_claims:
        reasons = ", ".join(claim.get("gate_reasons", [])) or "flag_and_confirm"
        notes.append(f"Flagged claim not written as verified prose: `{claim.get('claim_id')}` ({reasons}).")
    return notes


def _floor_section(title: str, needed: list[str], *, notes: list[str] | None = None) -> str:
    lines = [
        f"# {title}",
        "",
        f"{AUTHOR_INPUT_NEEDED}: section floor is visible because required inputs or verified evidence are missing.",
        "",
        "## Missing Inputs",
        "",
    ]
    for item in needed:
        lines.append(f"- {item}")
    if notes:
        lines.extend(["", "## Held Context", ""])
        lines.extend(f"- {note}" for note in notes)
    return "\n".join(lines) + "\n"


def _section_notes_by_section(intake: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    notes = intake.get("author_provided_notes") if isinstance(intake.get("author_provided_notes"), dict) else {}
    raw = notes.get("section_notes")
    entries: list[dict[str, Any]] = []
    if isinstance(raw, list):
        entries = [item for item in raw if isinstance(item, dict)]
    elif isinstance(raw, dict):
        for section, value in raw.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        entries.append({"section": section, **item})
                    elif isinstance(item, str):
                        entries.append({"section": section, "paragraphs": [item], "status": "author_provided"})
            elif isinstance(value, dict):
                entries.append({"section": section, **value})
            elif isinstance(value, str):
                entries.append({"section": section, "paragraphs": [value], "status": "author_provided"})
    by_section: dict[str, list[dict[str, Any]]] = {section: [] for section in WRITING_ORDER}
    counters: dict[str, int] = {}
    for entry in entries:
        if entry.get("status") != "author_provided":
            continue
        section = str(entry.get("section") or entry.get("filename") or "").strip()
        if section not in by_section:
            continue
        paragraphs = _clean_note_text_list(entry.get("paragraphs") or entry.get("notes") or entry.get("note"))
        bullets = _clean_note_text_list(entry.get("bullets"))
        if not paragraphs and not bullets:
            continue
        counters[section] = counters.get(section, 0) + 1
        note_id = str(entry.get("note_id") or f"section_note_{Path(section).stem}_{counters[section]:02d}")
        by_section[section].append(
            {
                "note_id": note_id,
                "title": str(entry.get("title") or "").strip(),
                "paragraphs": paragraphs,
                "bullets": bullets,
            }
        )
    return {section: notes for section, notes in by_section.items() if notes}


def _clean_note_text_list(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else [value]
    cleaned: list[str] = []
    for item in raw_items:
        if item is None:
            continue
        text = str(item).strip()
        if not text or text.startswith(AUTHOR_INPUT_NEEDED):
            continue
        cleaned.append(text)
    return cleaned


def _append_section_notes(
    sections: dict[str, str],
    section_notes: dict[str, list[dict[str, Any]]],
    audit: dict[str, Any],
) -> None:
    used: list[str] = []
    for section in WRITING_ORDER:
        notes = section_notes.get(section, [])
        if not notes or section not in sections:
            continue
        lines = [sections[section].rstrip(), ""]
        for note in notes:
            note_id = str(note.get("note_id") or "").strip()
            title = str(note.get("title") or "").strip()
            if title:
                lines.extend([f"## {title}", ""])
            for paragraph in note.get("paragraphs", []):
                lines.append(_public_note_text(paragraph))
                lines.append("")
            bullets = note.get("bullets", [])
            if bullets:
                for bullet in bullets:
                    lines.append(f"- {_public_note_text(bullet)}")
                lines.append("")
            if note_id:
                used.append(note_id)
        sections[section] = "\n".join(lines).rstrip() + "\n"
    audit["section_note_ids_used"] = used


def _public_note_text(value: Any) -> str:
    text = str(value).strip()
    return re.sub(r"^Author note:\s*", "", text)


def _missing_fields(fields: list[tuple[Any, str]]) -> list[str]:
    return [label for value, label in fields if _is_missing(value)]


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or (isinstance(value, str) and value.startswith(AUTHOR_INPUT_NEEDED))


def _value(value: Any, label: str) -> str:
    if value is None or value == "":
        return f"{AUTHOR_INPUT_NEEDED}: {label}"
    return str(value)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _author_report_text(result: SectionWriterResult) -> str:
    hard_blocks = [issue for issue in result.issues if issue.severity == "hard_block"]
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Section Generation Status",
        "",
        f"- Status: `{result.status}`",
        f"- Sections written: `{len(result.sections)}`",
        f"- Safe claims used: `{len(result.audit.get('safe_claim_ids_used', []))}`",
        f"- Author-asserted claims used: `{len(result.audit.get('author_asserted_claim_ids_used', []))}`",
        f"- Flagged claims held back: `{len(result.audit.get('flagged_claim_ids_not_written_as_verified', []))}`",
        "",
        "## Writing Order",
        "",
    ]
    lines.extend([f"- `{item}`" for item in result.audit["writing_order"]])
    lines.extend(["", "## Non-Overridable Hard Blocks", ""])
    lines.extend([f"- `{issue.code}`: {issue.message}" for issue in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Resolve claim-ledger hard blocks and rerun section generation.")
    else:
        lines.append("- Render numeric placeholders, then run global coherence checks.")
    return "\n".join(lines) + "\n"
