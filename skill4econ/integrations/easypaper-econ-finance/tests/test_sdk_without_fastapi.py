import subprocess
import sys
import textwrap


def test_sdk_import_and_init_do_not_require_fastapi():
    code = r"""
import importlib.abc
import sys


class BlockFastAPI(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "fastapi" or fullname.startswith("fastapi."):
            raise ModuleNotFoundError("No module named 'fastapi' (blocked)")
        return None


sys.meta_path.insert(0, BlockFastAPI())

from easypaper import EasyPaper, PaperMetaData
from src.config.schema import AgentConfig, AppConfig, ModelConfig, SkillsConfig

agents = [
    AgentConfig(name="metadata", model=ModelConfig(model_name="m", api_key="k", base_url="http://x")),
    AgentConfig(name="writer", model=ModelConfig(model_name="m", api_key="k", base_url="http://x")),
    AgentConfig(name="reviewer", model=ModelConfig(model_name="m", api_key="k", base_url="http://x")),
    AgentConfig(name="planner", model=ModelConfig(model_name="m", api_key="k", base_url="http://x")),
]
config = AppConfig(agents=agents, skills=SkillsConfig(enabled=True, skills_dir="/tmp/no-skills"))
ep = EasyPaper(config=config)
metadata = PaperMetaData(
    title="t",
    idea_hypothesis="i",
    method="m",
    data="d",
    experiments="e",
)
assert metadata.title == "t"
assert sorted(ep._agents) == ["metadata", "planner", "reviewer", "writer"]
"""
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
