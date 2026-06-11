from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
DOMAIN = SKILLS / "domain"
REPORTING = SKILLS / "reporting"
SHARED = SKILLS / "_shared"


REQUIRED_DOMAIN_FIELDS = [
    "literature_anchors",
    "canonical_papers_or_authors",
    "canonical_data_sources",
    "measurement_regimes",
    "identification_debate",
    "referee_entry_points",
]

EXPECTED_DOMAIN_FILENAMES = [
    "01_environmental_policy_eval_skill.md",
    "02_climate_exposure_design_skill.md",
    "03_pollution_exposure_health_skill.md",
    "04_spatial_exposure_design_skill.md",
    "05_conley_spatial_inference_skill.md",
    "06_carbon_market_ets_eval_skill.md",
    "07_carbon_accounting_mrv_skill.md",
    "08_esg_text_greenwashing_skill.md",
    "09_climate_finance_risk_skill.md",
    "10_environmental_justice_distribution_skill.md",
    "11_green_innovation_patent_text_skill.md",
    "12_input_output_carbon_network_skill.md",
    "13_remote_sensing_mrv_skill.md",
    "14_cbam_trade_policy_skill.md",
    "15_lca_hybrid_econometrics_skill.md",
    "16_dea_environmental_efficiency_skill.md",
    "17_ppmlhdfe_environmental_flows_skill.md",
    "18_sdid_gsc_for_pilot_policies_skill.md",
    "19_panel_threshold_environment_skill.md",
    "20_sar_sem_sdm_structural_spatial_skill.md",
]

GENERIC_REASONING_PHRASES = [
    "Clarify the empirical object",
    "Map measurement and identification risks",
    "Select the econometric workflow",
    "Run claim gates",
    "Return reproducible outputs",
    "Clarify unit, time, outcome, treatment/exposure, and estimand",
    "Map the domain risks to required diagnostics",
    "Rank candidate methods while respecting repo capability and forbidden fallbacks",
    "Define robustness and metadata requirements",
    "Draft only safe claim language allowed before artifacts",
]

REVIEWER_REPORT_HEADINGS = [
    "# Referee report",
    "## Recommendation",
    "## Summary",
    "## Major comments",
    "## Minor comments",
    "## Required evidence before revision",
    "## Claims that must be removed or downgraded",
]

GLOBAL_FORBIDDEN_CLAIMS = [
    "Failure to reject pre-treatment differences",
    "parallel trends holds",
    "A short-run pass-through coefficient",
    "long-run welfare",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _indented_field_block(text: str, field: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != f"{field}:":
            continue
        indent = len(line) - len(line.lstrip(" "))
        block = []
        for next_line in lines[index + 1 :]:
            stripped = next_line.strip()
            next_indent = len(next_line) - len(next_line.lstrip(" "))
            if stripped.startswith("```") or next_line.startswith("## "):
                break
            if (
                stripped
                and next_indent <= indent
                and re.match(r"[A-Za-z_][A-Za-z0-9_]*:", stripped)
            ):
                break
            block.append(next_line)
        return "\n".join(block).strip()
    raise AssertionError(f"missing field: {field}")


def _markdown_section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    next_match = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.end() : end].strip()


def test_shared_domain_literature_anchor_contract_exists() -> None:
    contract = SHARED / "08_domain_literature_anchor_rules.md"
    text = _read(contract)
    for field in REQUIRED_DOMAIN_FIELDS:
        assert field in text
    assert "Do not invent citations" in text


def test_domain_skill_filenames_match_goal_contract() -> None:
    assert [path.name for path in sorted(DOMAIN.glob("*.md"))] == EXPECTED_DOMAIN_FILENAMES


def test_every_domain_skill_exposes_literature_anchor_contract_fields() -> None:
    for path in sorted(DOMAIN.glob("*.md")):
        text = _read(path)
        missing = [field for field in REQUIRED_DOMAIN_FIELDS if field not in text]
        assert not missing, f"{path.name} missing {missing}"
        for field in ("canonical_papers_or_authors", "canonical_data_sources"):
            block = _indented_field_block(text, field)
            assert re.search(r"^\s*-\s+\S", block, re.MULTILINE), (
                f"{path.name} has empty {field}"
            )
        for heading in (
            "Literature anchors",
            "Measurement regimes",
            "Identification debate",
            "Referee entry points",
        ):
            assert _markdown_section(text, heading), f"{path.name} has empty {heading}"
        forbidden = _markdown_section(text, "Forbidden claims")
        assert "Do not" in forbidden, f"{path.name} has no explicit forbidden claim"


def test_global_claim_guards_contract_exists() -> None:
    text = _read(SHARED / "09_global_claim_guards.md")
    assert "Pretrend non-rejection claim guard" in text
    assert "Pass-through welfare claim guard" in text


def test_domain_skills_01_to_05_do_not_share_identical_reasoning_steps() -> None:
    blocks = {}
    for path in sorted(DOMAIN.glob("0[1-5]_*.md")):
        blocks[path.name] = _markdown_section(_read(path), "Domain reasoning steps")
    normalized = {name: re.sub(r"\s+", " ", block).strip() for name, block in blocks.items()}
    duplicates = {
        block
        for block in normalized.values()
        if list(normalized.values()).count(block) > 1
    }
    assert not duplicates, "domain skills 01-05 still share identical reasoning steps"


def test_domain_reasoning_steps_are_not_generic_template_blocks() -> None:
    for path in sorted(DOMAIN.glob("*.md")):
        block = _markdown_section(_read(path), "Domain reasoning steps")
        hits = [phrase for phrase in GENERIC_REASONING_PHRASES if phrase in block]
        assert len(hits) < 4, f"{path.name} has generic reasoning block: {hits}"


def test_reporting_skills_reference_shared_contract() -> None:
    assert (REPORTING / "_reporting_shared_contract.md").exists()
    for path in sorted(p for p in REPORTING.glob("*.md") if not p.name.startswith("_")):
        assert "_reporting_shared_contract.md" in _read(path), path.name


def test_reviewer_summary_template_is_referee_report_template() -> None:
    text = _read(REPORTING / "reviewer_summary_template.md")
    for heading in REVIEWER_REPORT_HEADINGS:
        assert heading in text
    assert "exactly these ten sections" not in text


def test_global_forbidden_claims_are_present_in_shared_and_reporting_contracts() -> None:
    paths = [
        SHARED / "01_claim_language_rules.md",
        SHARED / "05_forbidden_fallbacks.md",
        SHARED / "06_reviewer_mode_rules.md",
        SHARED / "07_scholarly_depth_rules.md",
        SHARED / "09_global_claim_guards.md",
        REPORTING / "_reporting_shared_contract.md",
    ]
    for path in paths:
        text = re.sub(r"\s+", " ", _read(path))
        for claim in GLOBAL_FORBIDDEN_CLAIMS:
            assert claim in text, f"{path.name} missing {claim}"
