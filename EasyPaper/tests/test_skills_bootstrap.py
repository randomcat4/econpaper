import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.metadata_agent.figure_generation import derive_figure_style
from src.agents.metadata_agent.models import FigureSpec, PaperMetaData
from src.agents.metadata_agent.prompt_support import get_active_skills
from src.agents.metadata_agent.section_generation import generate_introduction_section
from src.config.schema import AgentConfig, AppConfig, ModelConfig, SkillsConfig
from src.skills.bootstrap import bootstrap_skill_registry, load_builtin_skills
from src.skills.loader import SkillLoader
from src.skills.models import WritingSkill
from src.skills.registry import SkillRegistry


def _minimal_config(skills: SkillsConfig) -> AppConfig:
    agents = [
        AgentConfig(name="metadata", model=ModelConfig(model_name="m", api_key="k", base_url="http://x")),
        AgentConfig(name="writer", model=ModelConfig(model_name="m", api_key="k", base_url="http://x")),
        AgentConfig(name="reviewer", model=ModelConfig(model_name="m", api_key="k", base_url="http://x")),
        AgentConfig(name="planner", model=ModelConfig(model_name="m", api_key="k", base_url="http://x")),
    ]
    return AppConfig(agents=agents, skills=skills)


def _skill_yaml(name: str, *, prompt: str = "CUSTOM", skill_type: str = "writing_constraint") -> str:
    return f"""
name: {name}
description: test skill
version: "1.0.0"
type: {skill_type}
target_sections:
  - "*"
priority: 1
system_prompt_append: |
  {prompt}
anti_patterns:
  - custom-pattern
""".lstrip()


def test_bootstrap_report_builtin_only(tmp_path: Path):
    registry, report = bootstrap_skill_registry(
        SkillsConfig(enabled=True, skills_dir=str(tmp_path / "missing"))
    )

    assert len(registry) > 0
    assert report.built_in_count > 0
    assert report.user_count == 0
    assert report.registry_size == len(report.final_skill_names)
    assert "anti-ai-style" in report.final_skill_names
    assert report.source_kind_by_skill["anti-ai-style"] == "builtin"
    assert not report.user_dir_exists


def test_bootstrap_report_user_override(tmp_path: Path):
    user_dir = tmp_path / "skills"
    (user_dir / "writing").mkdir(parents=True)
    (user_dir / "writing" / "anti_ai_style.yaml").write_text(
        _skill_yaml("anti-ai-style", prompt="USER OVERRIDE"),
        encoding="utf-8",
    )

    registry, report = bootstrap_skill_registry(SkillsConfig(enabled=True, skills_dir=str(user_dir)))

    assert "anti-ai-style" in report.overridden_names
    assert report.source_kind_by_skill["anti-ai-style"] == "user_dir"
    skill = registry.get_writing_skills("introduction", active_names=["anti-ai-style"])[0]
    assert "USER OVERRIDE" in skill.system_prompt_append


def test_builtin_packaged_tree_matches_canonical_skills_tree():
    root = Path(__file__).resolve().parents[1]
    canonical = root / "skills"
    packaged = root / "src" / "skills" / "builtin"

    canonical_files = sorted(path.relative_to(canonical) for path in canonical.rglob("*.yaml"))
    packaged_files = sorted(path.relative_to(packaged) for path in packaged.rglob("*.yaml"))

    assert packaged_files == canonical_files
    for relative in canonical_files:
        canonical_text = (canonical / relative).read_text(encoding="utf-8").strip()
        packaged_text = (packaged / relative).read_text(encoding="utf-8").strip()
        assert packaged_text == canonical_text


def test_active_skills_filters_writing_constraints_only():
    registry = SkillRegistry()
    registry.register(WritingSkill(name="alpha", type="writing_constraint", system_prompt_append="A"))
    registry.register(WritingSkill(name="beta", type="writing_constraint", system_prompt_append="B"))
    registry.register(WritingSkill(name="neurips", type="venue_profile", system_prompt_append="N"))

    skills = get_active_skills(
        registry,
        "introduction",
        "neurips",
        active_skill_names=["alpha"],
    )

    assert [skill.name for skill in skills] == ["alpha", "neurips"]


def test_venue_profile_included_independently_of_active_skills():
    registry = SkillRegistry()
    registry.register(WritingSkill(name="academic-polish", type="writing_constraint"))
    registry.register(WritingSkill(name="icml", type="venue_profile", system_prompt_append="ICML"))

    skills = registry.get_writing_skills(
        "method",
        venue="icml",
        active_names=["academic-polish"],
    )

    assert {skill.name for skill in skills} == {"academic-polish", "icml"}


def test_metadata_style_guide_overrides_config_venue_profile():
    from src.agents.metadata_agent.metadata_agent import MetaDataAgent

    agent = MetaDataAgent(ModelConfig(model_name="m", api_key="k", base_url="http://x"))
    agent._skills_config = SkillsConfig(enabled=True, venue_profile="neurips")
    metadata = PaperMetaData(
        title="T",
        idea_hypothesis="idea",
        method="method",
        data="data",
        experiments="experiments",
        style_guide="icml",
    )

    assert agent._effective_style_guide(metadata) == "icml"
    metadata.style_guide = None
    assert agent._effective_style_guide(metadata) == "neurips"


def test_effective_venue_used_for_default_template_resolution():
    from src.agents.metadata_agent.metadata_agent import MetaDataAgent

    agent = MetaDataAgent(ModelConfig(model_name="m", api_key="k", base_url="http://x"))
    agent._skills_config = SkillsConfig(enabled=True, venue_profile="nature")
    metadata = PaperMetaData(
        title="T",
        idea_hypothesis="idea",
        method="method",
        data="data",
        experiments="experiments",
    )

    assert agent._effective_style_guide(metadata) == "nature"


@pytest.mark.asyncio
async def test_effective_venue_used_for_section_prompt_and_skill_lookup(monkeypatch):
    captured = {}

    def fake_compile_introduction_prompt(**kwargs):
        captured["style_guide"] = kwargs["style_guide"]
        captured["active_skills"] = kwargs["active_skills"]
        return "prompt"

    async def fake_generate_section_decomposed_fn(**kwargs):
        return "generated"

    monkeypatch.setattr(
        "src.agents.metadata_agent.section_generation.compile_introduction_prompt",
        fake_compile_introduction_prompt,
    )

    metadata = PaperMetaData(
        title="T",
        idea_hypothesis="idea",
        method="method",
        data="data",
        experiments="experiments",
    )
    ref_pool = MagicMock()
    ref_pool.citable_refs.return_value = []
    ref_pool.citable_keys.return_value = []

    result = await generate_introduction_section(
        metadata=metadata,
        ref_pool=ref_pool,
        section_plan=None,
        figures=[],
        tables=[],
        code_context=None,
        research_context=None,
        prompt_traces=[],
        memory=None,
        evidence_dag=None,
        template_guide=None,
        exemplar_guidance=None,
        emitter=MagicMock(),
        tools_config=None,
        retrieve_runtime_code_evidence_fn=lambda **_: [],
        format_research_context_for_prompt_fn=lambda **_: "",
        get_active_skills_fn=lambda section, style: [f"{section}:{style}"],
        generate_section_decomposed_fn=fake_generate_section_decomposed_fn,
        effective_style_guide="neurips",
    )

    assert result.status == "ok"
    assert captured["style_guide"] == "neurips"
    assert captured["active_skills"] == ["introduction:neurips"]


def test_effective_venue_used_for_reviewer_and_vlm_payloads():
    source = Path("src/agents/metadata_agent/orchestrator.py").read_text(encoding="utf-8")

    assert "style_guide=self.host._effective_style_guide(metadata)" in source
    assert "template_type=self.host._effective_style_guide(metadata) or \"ICML\"" in source


def test_effective_venue_used_for_figure_style_derivation():
    metadata = PaperMetaData(
        title="T",
        idea_hypothesis="idea",
        method="method",
        data="data",
        experiments="experiments",
    )
    fig = FigureSpec(id="fig:one", caption="Figure", auto_generate=True)

    assert "ICML-style" in derive_figure_style(fig, metadata, style_guide="icml")


def test_style_checker_uses_builtin_and_user_override_rules(tmp_path: Path):
    from src.agents.reviewer_agent.checkers.style_check import StyleChecker

    registry, _ = bootstrap_skill_registry(SkillsConfig(enabled=True, skills_dir=str(tmp_path / "missing")))
    checker = StyleChecker(skill_registry=registry)
    assert "delve" in checker._load_anti_patterns()

    user_dir = tmp_path / "skills"
    (user_dir / "reviewing").mkdir(parents=True)
    (user_dir / "reviewing" / "style_check.yaml").write_text(
        _skill_yaml("style-check", prompt="", skill_type="reviewer_checker"),
        encoding="utf-8",
    )
    registry, report = bootstrap_skill_registry(SkillsConfig(enabled=True, skills_dir=str(user_dir)))
    checker = StyleChecker(skill_registry=registry)
    assert "style-check" in report.overridden_names
    assert "custom-pattern" in checker._load_anti_patterns()


def test_logic_checker_uses_builtin_and_user_override_prompt(tmp_path: Path):
    from src.agents.reviewer_agent.checkers.logic_check import LogicChecker

    registry, _ = bootstrap_skill_registry(SkillsConfig(enabled=True, skills_dir=str(tmp_path / "missing")))
    checker = LogicChecker(llm_client=MagicMock(), model_name="m", skill_registry=registry)
    assert "meticulous academic paper reviewer" in checker._get_system_prompt()

    user_dir = tmp_path / "skills"
    (user_dir / "reviewing").mkdir(parents=True)
    (user_dir / "reviewing" / "logic_check.yaml").write_text(
        _skill_yaml("logic-check", prompt="USER LOGIC PROMPT", skill_type="reviewer_checker"),
        encoding="utf-8",
    )
    registry, report = bootstrap_skill_registry(SkillsConfig(enabled=True, skills_dir=str(user_dir)))
    checker = LogicChecker(llm_client=MagicMock(), model_name="m", skill_registry=registry)
    assert "logic-check" in report.overridden_names
    assert checker._get_system_prompt().strip() == "USER LOGIC PROMPT"


def test_sdk_uses_shared_bootstrap_and_exposes_visibility(tmp_path: Path, caplog):
    from easypaper import EasyPaper

    caplog.set_level(logging.INFO)
    config = _minimal_config(SkillsConfig(enabled=True, skills_dir=str(tmp_path / "missing")))
    with patch("easypaper.client.initialize_agents") as mock_init:
        mock_init.return_value = {"metadata": MagicMock()}
        EasyPaper(config=config)

    _, kwargs = mock_init.call_args
    assert kwargs["skill_registry"] is not None
    assert kwargs["skills_config"] == config.skills
    assert "Loaded built-in skills" in caplog.text
    assert "anti-ai-style" in caplog.text


@pytest.mark.asyncio
async def test_sdk_and_fastapi_normalize_missing_skills_config_the_same_way(capsys):
    from easypaper import EasyPaper
    from src import main as main_module

    config = _minimal_config(SkillsConfig(enabled=True))
    config.skills = None
    with patch("easypaper.client.initialize_agents") as sdk_init:
        sdk_init.return_value = {"metadata": MagicMock()}
        EasyPaper(config=config)

    _, sdk_kwargs = sdk_init.call_args
    assert sdk_kwargs["skill_registry"] is not None
    assert sdk_kwargs["skills_config"] is not None
    assert len(sdk_kwargs["skill_registry"]) > 0

    fake_app = SimpleNamespace(
        state=SimpleNamespace(),
        include_router=MagicMock(),
    )
    with (
        patch.object(main_module, "load_config", return_value=config),
        patch.object(main_module, "_validate_llm_and_vlm_connections", new=AsyncMock()),
        patch.object(main_module, "initialize_agents", return_value={}) as fastapi_init,
        patch.object(main_module, "register_agent_routers"),
    ):
        async with main_module.lifespan(fake_app):
            pass

    _, fastapi_kwargs = fastapi_init.call_args
    assert fastapi_kwargs["skill_registry"] is not None
    assert fastapi_kwargs["skills_config"] is not None
    assert len(fastapi_kwargs["skill_registry"]) > 0
    assert "Loaded built-in skills" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_sdk_and_fastapi_share_bootstrap_failure_policy(capsys):
    from easypaper import EasyPaper
    from src import main as main_module

    config = _minimal_config(SkillsConfig(enabled=True))

    def fail_bootstrap(_skills_config):
        raise RuntimeError("boom")

    with (
        patch("src.skills.bootstrap.bootstrap_skill_registry", side_effect=fail_bootstrap),
        patch("easypaper.client.initialize_agents") as sdk_init,
    ):
        sdk_init.return_value = {"metadata": MagicMock()}
        EasyPaper(config=config)

    _, sdk_kwargs = sdk_init.call_args
    assert sdk_kwargs["skill_registry"] is None
    assert sdk_kwargs["skills_config"] is None

    fake_app = SimpleNamespace(
        state=SimpleNamespace(),
        include_router=MagicMock(),
    )
    with (
        patch("src.skills.bootstrap.bootstrap_skill_registry", side_effect=fail_bootstrap),
        patch.object(main_module, "load_config", return_value=config),
        patch.object(main_module, "_validate_llm_and_vlm_connections", new=AsyncMock()),
        patch.object(main_module, "initialize_agents", return_value={}) as fastapi_init,
        patch.object(main_module, "register_agent_routers"),
    ):
        async with main_module.lifespan(fake_app):
            pass

    _, fastapi_kwargs = fastapi_init.call_args
    assert len(fastapi_kwargs["skill_registry"]) == 0
    assert fastapi_kwargs["skills_config"] is None
    assert "Skills system disabled" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_fastapi_lifespan_uses_shared_bootstrap_and_exposes_visibility(tmp_path: Path, capsys):
    from src import main as main_module

    config = _minimal_config(SkillsConfig(enabled=True, skills_dir=str(tmp_path / "missing")))
    fake_app = SimpleNamespace(
        state=SimpleNamespace(),
        include_router=MagicMock(),
    )

    with (
        patch.object(main_module, "load_config", return_value=config),
        patch.object(main_module, "_validate_llm_and_vlm_connections", new=AsyncMock()),
        patch.object(main_module, "initialize_agents", return_value={}),
        patch.object(main_module, "register_agent_routers"),
    ):
        async with main_module.lifespan(fake_app):
            pass

    output = capsys.readouterr().out
    assert "Loaded built-in skills" in output
    assert "anti-ai-style" in output


def test_builtin_resource_files_are_discoverable():
    skills = load_builtin_skills(SkillLoader())
    names = {skill.name for skill in skills}

    assert {"anti-ai-style", "academic-polish", "style-check", "logic-check"}.issubset(names)
