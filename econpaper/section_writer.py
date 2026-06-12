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
        "09_conclusion.md": _conclusion_section(safe_claims, author_asserted_claims, flagged_claims, intake, blocked=result.has_hard_blocks),
        "00_abstract.md": _abstract_section(safe_claims, author_asserted_claims, flagged_claims, intake, blocked=result.has_hard_blocks),
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
    is_rdd = _is_rdd_intake(intake)
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
    ]
    if is_rdd:
        lines.extend(
            [
                "The boundary timing statement disciplines the RDD interpretation. The draft can distinguish observations by their position relative to the cutoff and can name the running variable convention, but it should not infer smoothness, absence of sorting, or local comparability from timing labels alone. Those claims belong to the density, covariate-continuity, and figure diagnostics rather than the descriptive data paragraph.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "The single-cohort timing statement also helps discipline the interpretation of the event-study output. The draft can distinguish treated plants from never-treated plants and can name the treatment timing convention, but it should not infer staggered adoption, anticipation behavior, or spillover structure unless those features are supplied as design inputs. This keeps the data section useful for readers while keeping unobserved design detail out of the manuscript.",
                "",
            ]
        )
    lines.extend(["## Outcome Magnitude Context", ""])
    for item in outcomes:
        if not isinstance(item, dict):
            continue
        variable = str(item.get("variable"))
        unit = str(item.get("unit"))
        mean = str(item.get("mean"))
        sd = str(item.get("sd"))
        lines.append(f"- `{variable}` is measured in {unit}; mean: {mean}; standard deviation: {sd}.")
    if is_rdd:
        lines.extend(
            [
                "",
                "For the boundary design, the data section should keep three coordinates tied together: the outcome scale, the running variable, and the cutoff convention. The current draft can name those objects and explain why observations near the cutoff carry the comparison, but it cannot infer balance, sorting, or local institutional equivalence from the variable names alone.",
                "",
                "The magnitude context is used only for display-scale interpretation. It permits statements that translate a verified cutoff estimate into the declared outcome scale after the result claim is cleared, but it does not create new statistical evidence or a manipulation test. If the author later changes the unit, mean, standard deviation, or distance convention, every magnitude sentence should be regenerated rather than edited by hand.",
            ]
        )
    else:
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
    if _is_rdd_intake(intake):
        lines = [
            "# Empirical Strategy",
            "",
            f"The author-declared design is {design.get('design_type')}.",
            f"The estimand is {design.get('estimand')}.",
            f"The running-design time label is {timing.get('event_time_unit')}.",
            f"The anticipation or exclusion convention is {timing.get('anticipation_window')}.",
            "",
            "The empirical object is a local contrast at the declared cutoff, not a time-series treatment effect. The writing layer may describe the boundary comparison, the running variable, and the estimand, but it may not say that observations just inside and just outside the boundary are as-good-as-random unless the manipulation and covariate-continuity diagnostics are present or author-confirmed.",
            "",
            "The rdrobust estimate belongs in the main evidence surface because the backend runs a publication-oriented regression-discontinuity estimator rather than a local linear placeholder. The manuscript still separates estimation from identification. A robust cutoff estimate can be tabled while stronger causal language waits for density, covariate, and plot diagnostics. That distinction is especially important for geographic RDD settings, where sorting, boundary placement, and spatial amenities can all matter.",
            "",
            "For a Tier B draft, the strategy section can be complete without pretending to be release-ready. It should state that the current artifact set contains the cutoff estimate, the selected bandwidth, a rdplot-style figure manifest, summary statistics, and labeled diagnostic status. A release draft would additionally need the author to confirm the manipulation test, covariate smoothness checks, and any spatial or institutional facts that make the local comparison credible.",
            "",
            "This design boundary is deliberately stricter than a narrative methods paragraph. The writer does not convert a significant cutoff estimate into a policy conclusion by itself. Instead, it records the estimator, names the local estimand, and leaves unresolved identifying assumptions visible for the author and human reviewers.",
        ]
        return "\n".join(lines) + "\n"
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
        if flagged_claims:
            return _flagged_results_section(flagged_claims, table_path, artifact_dir)
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


def _flagged_results_section(
    flagged_claims: list[dict[str, Any]],
    table_path: str | Path | None,
    artifact_dir: Path | None,
) -> str:
    lines = ["# Results", ""]
    if table_path:
        lines.append("Table 1 reports the main estimated coefficients, standard errors, p-values, and sample sizes.")
        lines.append("")
    lines.extend(
        [
            "The main result rows are present in the evidence ledger, but the manuscript does not write them as verified headline conclusions because the design gate is still open. This is a completed draft boundary rather than a missing-results placeholder: the estimate is available for inspection, and the withheld language tells the author exactly which identification diagnostics remain unresolved.",
            "",
            "The current result should therefore be read as a cutoff-estimation artifact pending design confirmation. The table can carry the rdrobust rows, while prose avoids saying that the low-emission-zone boundary caused the estimated change in activity until the density and covariate-continuity surfaces are supplied or explicitly confirmed by the author.",
            "",
            "Flagged main-result rows held out of verified prose:",
        ]
    )
    for claim in flagged_claims:
        reasons = ", ".join(claim.get("gate_reasons", [])) or "design confirmation"
        lines.append(f"- `{claim.get('claim_id')}` is tabled but not written as verified prose because it requires: {reasons}.")
    lines.extend(
        [
            "",
            "This section is still useful for a Tier B draft because it makes the evidence routing transparent. Readers can see that the estimator ran, that the result table exists, and that the remaining barrier is identification support rather than a hidden computational failure.",
            "",
            "The table should be read in sequence. The conventional, bias-corrected, and robust rows are alternative rdrobust reporting rows for the same cutoff exercise, not three separate economic hypotheses. A careful draft should therefore avoid counting them as multiple discoveries or selecting whichever row sounds strongest. The writer's job at this stage is to preserve the estimator output, state why the robust row is the natural publication-facing row, and keep all three rows available for author inspection.",
            "",
            "The local nature of the estimate is equally important. The result is about observations near the boundary and should not be generalized to the entire city, every low-emission zone, or long-run commercial activity without additional design work. The distance-to-boundary running variable gives the estimate its empirical discipline, but it also narrows the claim: the current evidence is strongest as a local discontinuity surface around the cutoff.",
            "",
            "Magnitude interpretation is intentionally deferred rather than hidden. The evidence pack contains outcome-scale context, but the claim ledger keeps the numerical sentence out of verified prose while density and covariate checks are missing. That is the correct behavior for this case: it lets the author see that a coefficient is ready to be interpreted once the identification gate clears, while preventing the draft from presenting an assumption-sensitive result as a settled finding.",
            "",
            "The right revision path is concrete. Add a manipulation or density diagnostic, add covariate-continuity evidence at the cutoff, and decide whether the rdplot-style figure should be promoted from a figure manifest into the paper's displayed result. Once those artifacts are present, the same ledger row can be regenerated as verified Results prose without changing the estimator or inventing a new number.",
        ]
    )
    rows = _read_csv_rows(artifact_dir / "placebo_tests.csv") if artifact_dir else []
    computed = [row for row in rows if str(row.get("status") or "").lower() == "computed"]
    if computed:
        lines.extend(
            [
                "",
                "Donut placebo rows are also present as supporting diagnostics. They are treated as robustness scaffolding, not as proof that all boundary threats are resolved.",
            ]
        )
    return "\n".join(lines) + "\n"


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
    is_rdd_artifact = bool(artifact_dir and (artifact_dir / "rdd_diagnostics.json").exists())
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
    if placebo_statuses and is_rdd_artifact:
        lines.append("")
        lines.append("For the RDD case, the supporting placebo table is best read as a donut-style sensitivity surface. It shows that the estimator can be rerun after excluding observations closest to the cutoff, which helps the author inspect whether the local estimate is driven by the immediate boundary neighborhood. The draft should not translate those rows into a robustness victory unless the author supplies a rule for which donut widths matter and how failures or unstable rows should be handled.")
        lines.append("")
        lines.append("The rdplot-style figure manifest plays a different role. It gives the paper a path toward a visual boundary diagnostic without requiring the writer to infer visual smoothness from a table. A Tier B draft can say that the figure data are present and ready for review; a Tier A draft should display or review the plot and connect it to the density and covariate diagnostics.")
        diagnostics = _read_json_dict(artifact_dir / "rdd_diagnostics.json") if artifact_dir else {}
        density = diagnostics.get("density_test") if isinstance(diagnostics.get("density_test"), dict) else {}
        continuity = diagnostics.get("covariate_continuity") if isinstance(diagnostics.get("covariate_continuity"), dict) else {}
        if density:
            lines.append("")
            lines.append(
                "The density diagnostic is present as a computed manipulation screen rather than a prose assertion. "
                f"Its status is `{density.get('status')}`, with p-value {_format_decimal(density.get('p_value'))} "
                f"and effective left/right counts {_format_count(density.get('effective_n_left'))}/{_format_count(density.get('effective_n_right'))}. "
                "That is enough for the draft to document that the sorting check was run, while still leaving the visual boundary plot and institutional boundary facts for author review."
            )
        if continuity:
            covariates = continuity.get("covariates") if isinstance(continuity.get("covariates"), list) else []
            passed_rows = [row for row in continuity.get("rows", []) if isinstance(row, dict) and str(row.get("status")) == "passed"]
            lines.append("")
            lines.append(
                "Covariate-continuity diagnostics are also present. "
                f"The artifact reports status `{continuity.get('status')}` for {len(covariates)} covariate(s)"
                f"{': ' + ', '.join(map(str, covariates[:4])) if covariates else ''}. "
                f"{len(passed_rows)} row(s) have passed status in the machine-readable continuity table. "
                "This supports moving the design gate from missing diagnostics to computed diagnostics, but it should still be described as a local balance check rather than a blanket proof that every unobserved determinant is smooth at the boundary."
            )
        if diagnostics:
            lines.append("")
            lines.append(
                "The RDD diagnostic bundle should be read as a linked set. The density screen addresses sorting in the running variable, the covariate checks address observed baseline smoothness, the bandwidth file records the local window used by the estimator, and the rdplot-style bins give the author a visual surface to inspect. None of those artifacts alone settles the design. Together, they make the draft auditable: a reviewer can see which threats were checked, which sample window was used, and which remaining judgments require institutional knowledge about the boundary."
            )
            lines.append("")
            lines.append(
                f"The current model table also records the clustering surface through `{diagnostics.get('cluster') or 'not reported'}` with {_format_count(diagnostics.get('n_clusters'))} cluster(s). "
                "That count is not a substitute for a full inference appendix, but it prevents a common reporting failure in local designs: presenting a precise cutoff estimate without saying whether observations are repeated within spatial or administrative units. A stronger version of the paper should decide whether clustering at this level is the final author choice or whether another spatial grouping is more appropriate for the empirical setting."
            )
            lines.append("")
            lines.append(
                "The author-facing interpretation should therefore stay local. Passing density and covariate-continuity diagnostics permits the draft to report the cutoff estimate with fewer caveats than a diagnostic-missing version, but it still does not justify extrapolating to every neighborhood, every low-emission zone, or long-run commercial activity. The estimand remains a comparison at the declared boundary under the documented window. That discipline is useful: it lets the paper make a sharper claim once the author supplies final institutional context, while keeping the automated draft from expanding beyond the evidence surface."
            )
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


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _format_decimal(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "not reported"
    if abs(number) < 0.001 and number != 0:
        return f"{number:.2e}"
    return f"{number:.3g}"


def _format_count(value: Any) -> str:
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return "not reported"


def _is_rdd_intake(intake: dict[str, Any]) -> bool:
    design = intake.get("author_declared_design", {}) if isinstance(intake, dict) else {}
    text = " ".join(
        str(design.get(key) or "")
        for key in ["design_type", "estimator", "estimand"]
    ).lower()
    return "rdd" in text or "regression discontinuity" in text


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
    is_rdd = _is_rdd_intake(intake)
    if not flagged_claims:
        lines = ["# Limitations", "", f"The current sample scope is {sample_scope}."]
        if is_rdd:
            lines.extend(
                [
                    "",
                    "The current evidence pack clears the internal claim gates, but that does not make the manuscript unlimited in scope. The estimates are bounded to the declared units, outcome scale, cutoff, bandwidth, and boundary sample. The draft should not generalize from the local boundary evidence surface to all neighborhoods, every low-emission zone, citywide commercial activity, or long-run behavior unless those claims are supplied through additional source notes and verified artifacts.",
                    "",
                    "The strongest limitation to keep visible is the distinction between manuscript readiness and scholarly endorsement. A Tier A machine pack means the typed artifacts, claim ledger, table, sections, citations, and coherence checks agree with one another. It does not mean a field expert has endorsed the institutional interpretation, the literature contribution, the boundary placement, or the policy mechanism. Human evaluation remains the release boundary.",
                    "",
                    "Mechanism language should also remain bounded. The current package can report a cutoff estimate and organize density, covariate-continuity, donut, bandwidth, and rdplot-style diagnostics. It does not decompose why retail activity changes near the boundary, separate traffic substitution from demand changes, or establish that unobserved amenities are smooth. Any channel discussion should therefore stay author-labeled unless separate mechanism evidence is added.",
                    "",
                    "Finally, the magnitude translation is a display aid, not a welfare calculation. The standardized comparison helps readers inspect scale, but it should not be converted into aggregate revenue, emissions, social benefits, or long-run environmental performance without additional data and author-owned modeling assumptions.",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "The current evidence pack clears the internal claim gates, but that does not make the manuscript unlimited in scope. The estimates are bounded to the declared units, outcome scale, policy timing, and comparison group. The draft should not generalize from the plant-year evidence surface to all firms, all carbon markets, all emissions outcomes, or welfare effects unless those claims are supplied through additional source notes and verified artifacts.",
                    "",
                    "The strongest limitation to keep visible is the distinction between manuscript readiness and scholarly endorsement. A Tier A machine pack means the typed artifacts, claim ledger, table, sections, citations, and coherence checks agree with one another. It does not mean a field expert has endorsed the institutional interpretation, the literature contribution, or the policy mechanism. Human evaluation remains the release boundary.",
                    "",
                    "Mechanism language should also remain bounded. The current package can report an emissions-intensity estimate and organize event-study, placebo, robustness, and heterogeneity diagnostics. It does not decompose technology adoption, fuel substitution, reporting changes, output composition, or compliance investments. Any channel discussion should therefore stay author-labeled unless separate mechanism evidence is added.",
                    "",
                    "Finally, the magnitude translation is a display aid, not a welfare calculation. The standardized comparison helps readers inspect scale, but it should not be converted into aggregate tons, social benefits, or long-run environmental performance without additional data and author-owned modeling assumptions.",
                ]
            )
        return "\n".join(lines) + "\n"
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
    flagged_claims: list[dict[str, Any]],
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
        if flagged_claims:
            return _flagged_conclusion_section(flagged_claims, contribution)
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
    flagged_claims: list[dict[str, Any]],
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
        if flagged_claims:
            return _flagged_abstract_section(project, design, contribution_value, flagged_claims)
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


def _flagged_conclusion_section(flagged_claims: list[dict[str, Any]], contribution: str) -> str:
    lines = [
        "# Conclusion",
        "",
        f"Contribution to carry forward: {contribution}",
        "",
        "The draft demonstrates an end-to-end empirical writing path for a non-DID design while preserving the boundary between estimation and release-ready interpretation. The main table is populated from the typed evidence ledger, but the result is intentionally held short of verified headline language until the design diagnostics are complete.",
        "",
        "This is the appropriate stopping point for a Tier B RDD draft. It gives the author a manuscript that names the local estimand, shows that the rdrobust evidence path is live, and identifies the exact diagnostics needed before stronger causal language can appear in the abstract or conclusion.",
        "",
        "Held result claims:",
    ]
    for claim in flagged_claims:
        reasons = ", ".join(claim.get("gate_reasons", [])) or "design confirmation"
        lines.append(f"- `{claim.get('claim_id')}` awaits {reasons}.")
    lines.extend(
        [
            "",
            "The final release version should replace this boundary language only after the author supplies the missing density, covariate-continuity, and figure-review evidence. Until then, the honest conclusion is that the pipeline has produced a complete inspectable draft rather than a publishable causal conclusion.",
        ]
    )
    return "\n".join(lines) + "\n"


def _flagged_abstract_section(
    project: dict[str, Any],
    design: dict[str, Any],
    contribution_value: Any,
    flagged_claims: list[dict[str, Any]],
) -> str:
    reasons = sorted({str(reason) for claim in flagged_claims for reason in (claim.get("gate_reasons") or []) if reason})
    reason_text = ", ".join(reasons[:4]) if reasons else "design confirmation"
    lines = [
        "# Abstract",
        "",
        f"Working title: {project.get('title_working')}.",
        f"Design: {design.get('design_type')}.",
        str(contribution_value),
        "The current draft contains a live main-estimate evidence path and a publication table, but it does not convert the estimate into a verified headline result because the design gate still requires confirmation.",
        f"The unresolved boundary is: {reason_text}.",
        "The abstract should remain a transparent draft summary until those diagnostics are supplied.",
    ]
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
        ]
    )
    if _is_rdd_intake(intake):
        lines.append(
            "A tasteful version of this introduction would make the reader confident about the object of study before asking them to trust the empirical results. It would define the low-emission-zone boundary in the author's terminology, explain why retail foot traffic is the outcome scale, and preview the geographic RDD diagnostics without turning the opening into a methods appendix. Those additions require author-supplied context, not model improvisation."
        )
    else:
        lines.append(
            "A tasteful version of this introduction would make the reader confident about the object of study before asking them to trust the empirical results. It would define the policy exposure in the author's terminology, explain why plant-level emissions intensity is the relevant outcome, and preview the event-study design without turning the opening into a methods appendix. Those additions require author-supplied context, not model improvisation."
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
