# EasyPaper Upstream and Integration Audit v3

Date: 2026-06-10  
Scope: static/source inspection only. I did not run `pip install easypaper`.

## Verdict

Can we fork and integrate EasyPaper? **Yes.**

- **Upstream track verdict:** **upstream track viable**, but pin the integration baseline to `v0.2.4` / `8797d4bf9cd8680f4da2d8b322533364d602b82d` in our fork. The GitHub repo exists, `master` and tag `v0.2.4` point to the same commit, and PyPI 0.2.4 was uploaded minutes after that commit. Risk is not source availability; risk is low bus factor and low external activity.
- **ccproxy verdict:** **ccproxy compatible for the primary OpenAI-compatible path via explicit `base_url` injection**, not via EvoScientist's env-only setup. EasyPaper passes `config.model.base_url` directly to `AsyncOpenAI`, and its schema defaults that field to `https://api.openai.com/v1`. Integration should create/pass an EasyPaper `AppConfig` or config YAML whose model `base_url` is `http://127.0.0.1:<ccproxy_port>/codex/v1` and `api_key` is `ccproxy-oauth`.
- **Anthropic caveat:** optional Claude VLM is not config-base-url compatible as written. `ClaudeVLM` ignores `base_url` kwargs and constructs `anthropic.AsyncAnthropic(api_key=api_key)`. Use EasyPaper's OpenAI VLM provider through ccproxy, disable Claude VLM, or patch this small provider. This is not a full integration redesign.
- **LangGraph verdict:** EasyPaper already uses LangGraph internally. Integration should treat EasyPaper as a graph-based orchestrator to wrap, not as a set of simple prompt files to merge into EvoScientist subagents one by one.

## Upstream Facts

Sources and commands used:

```powershell
git ls-remote --heads --tags https://github.com/PinkGranite/EasyPaper.git
Invoke-RestMethod -Headers @{ 'User-Agent'='codex-audit' } -Uri 'https://api.github.com/repos/PinkGranite/EasyPaper'
Invoke-RestMethod -Headers @{ 'User-Agent'='codex-audit' } -Uri 'https://api.github.com/repos/PinkGranite/EasyPaper/tags?per_page=100'
Invoke-RestMethod -Headers @{ 'User-Agent'='codex-audit' } -Uri 'https://api.github.com/repos/PinkGranite/EasyPaper/releases?per_page=100'
Invoke-RestMethod -Headers @{ 'User-Agent'='codex-audit' } -Uri 'https://api.github.com/search/issues?q=repo:PinkGranite/EasyPaper+type:issue&per_page=10'
Invoke-RestMethod -Headers @{ 'User-Agent'='codex-audit' } -Uri 'https://api.github.com/search/issues?q=repo:PinkGranite/EasyPaper+type:pr&per_page=10'
Invoke-RestMethod -Headers @{ 'User-Agent'='codex-audit' } -Uri 'https://api.github.com/repos/PinkGranite/EasyPaper/commits?per_page=20'
Invoke-RestMethod -Headers @{ 'User-Agent'='codex-audit' } -Uri 'https://api.github.com/repos/PinkGranite/EasyPaper/contributors?per_page=100'
Invoke-RestMethod -Headers @{ 'User-Agent'='codex-audit' } -Uri 'https://pypi.org/pypi/easypaper/0.2.4/json'
cmd /c "curl.exe -L -s https://files.pythonhosted.org/packages/39/0e/cf91b1678a68c4f2d84ee9ee22598834d2848fad4a694a675820b20c300f/easypaper-0.2.4.tar.gz | tar -xOzf - easypaper-0.2.4/PKG-INFO | findstr /n "Requires-Dist""
```

Confirmed URLs:

- Repo: https://github.com/PinkGranite/EasyPaper
- GitHub API repo record: https://api.github.com/repos/PinkGranite/EasyPaper
- Tags API: https://api.github.com/repos/PinkGranite/EasyPaper/tags?per_page=100
- PyPI release page: https://pypi.org/project/easypaper/0.2.4/
- PyPI JSON: https://pypi.org/pypi/easypaper/0.2.4/json
- PyPI sdist: https://files.pythonhosted.org/packages/39/0e/cf91b1678a68c4f2d84ee9ee22598834d2848fad4a694a675820b20c300f/easypaper-0.2.4.tar.gz

### Repository Existence

`PinkGranite/EasyPaper` exists and is public. GitHub API reported:

- `full_name`: `PinkGranite/EasyPaper`
- `default_branch`: `master`
- `created_at`: `2026-02-08T14:22:41Z`
- `updated_at`: `2026-05-24T04:47:20Z`
- `pushed_at`: `2026-05-24T04:49:16Z`
- `stargazers_count`: 4
- `forks_count`: 4
- `open_issues_count`: 0
- `archived`: false
- `disabled`: false

Rendered GitHub page also showed 146 commits, 11 tags, 4 stars, 4 forks, 0 open issues, and 0 open PRs on 2026-06-10.

### Tags, Releases, and PyPI 0.2.4 Alignment

`git ls-remote` reported:

```text
8797d4bf9cd8680f4da2d8b322533364d602b82d refs/heads/master
a794eedb871fef941449f3a1930b1b08a9a2dca3 refs/heads/commercial
8797d4bf9cd8680f4da2d8b322533364d602b82d refs/tags/v0.2.4
```

So `v0.2.4` and `master` are the same commit as of this audit.

The GitHub releases API returned `[]`; upstream uses tags, not GitHub Releases. Tags API returned `v0.1.2` through `v0.2.4`, with `v0.2.4` at `8797d4bf9cd8680f4da2d8b322533364d602b82d`.

PyPI 0.2.4 JSON reported:

- wheel upload: `2026-05-24T04:50:09.658679Z`
- sdist upload: `2026-05-24T04:50:11.062964Z`
- wheel sha256: `b24607894d051e7f42f80e44d16e2c0e0a6a9182719b75e6f1429f51a6a453d5`
- sdist sha256: `17d2d79e5366dec32bb1ac8a1698b48353c56d5652d32f957a6183c8923b624e`

The PyPI sdist `PKG-INFO` has:

```text
Name: easypaper
Version: 0.2.4
Requires-Dist: openai>=2.7.2
Requires-Dist: langgraph>=0.0.26
Requires-Dist: anthropic>=0.18.0; extra == "vlm"
```

The local source at `competitor_repos/easypaper-source` has no `.git`, includes `PKG-INFO` and `easypaper.egg-info`, and has file timestamps around `2026-05-24 12:50` local time, matching the PyPI upload time in UTC+8. It looks like an extracted source distribution, not a clone.

Snapshot conclusion: **the package source is aligned with the public `v0.2.4` tag**, but the sdist is not a full repo archive. The sdist contains packaged source (`easypaper/`, `src/`, `tests/`, metadata) while the GitHub tag archive also contains repo-only assets such as `.github/`, `configs/`, `examples/`, `plugins/`, `scripts/`, `skills/`, `templates/`, and `uv.lock`.

### Issue and PR Activity

GitHub issue search returned `issues_total = 0`.

GitHub PR search returned `prs_total = 6`, all closed. Recent PRs:

- PR #6, `v0.2.4`, by `PinkGranite`, created `2026-05-24T04:47:07Z`, closed `2026-05-24T04:47:16Z`
- PR #5, `Prevent public setup drift from breaking richer SDK installs`, by `PinkGranite`, created `2026-05-23T17:14:48Z`, closed `2026-05-23T17:14:56Z`
- PRs #1-#4 are also closed and by `PinkGranite`

This is low external collaboration. There are no open upstream issue threads to rely on for support or coordination.

### Recent Commit Authorship

GitHub contributors API returned a single contributor:

```text
PinkGranite, contributions=30, https://github.com/PinkGranite
```

The latest 20 commits API results all have commit author `Yuwei Yan`; GitHub login was either `PinkGranite` for merge commits or `null` for direct commits. Examples:

- `8797d4bf9cd8680f4da2d8b322533364d602b82d`, `2026-05-24T04:47:15Z`, `Merge pull request #6 from PinkGranite/commercial`
- `a794eedb871fef941449f3a1930b1b08a9a2dca3`, `2026-05-24T04:39:18Z`, `v0.2.4 fix canonical skill sync`
- `a9d96ae6b961ce466b1def85722232eba3ecfca6`, `2026-05-24T04:35:52Z`, `v0.2.4 support pip-installed skill defaults`
- `de3d5c09e239186d33a7cd0719504eede3280483`, `2026-05-24T03:38:16Z`, `Prevent generated papers from over-structuring synthesis and introductions`

Conclusion: recent commits are effectively one-author pushes/merges.

## EvoScientist Integration Surface

### ccproxy

Relevant files:

- `EvoScientist/ccproxy_manager.py`
- `EvoScientist/config/settings.py`

Integration facts:

- `maybe_start_ccproxy()` checks `config.anthropic_auth_mode` and `config.openai_auth_mode` for `oauth` (`ccproxy_manager.py:292`, `ccproxy_manager.py:309`, `ccproxy_manager.py:310`).
- One ccproxy process serves both providers (`ccproxy_manager.py:299`, `ccproxy_manager.py:342`).
- Anthropic env routing is force-set to:
  - `ANTHROPIC_BASE_URL=http://127.0.0.1:{port}/claude`
  - `ANTHROPIC_API_KEY=ccproxy-oauth`
  - Evidence: `ccproxy_manager.py:260`, `ccproxy_manager.py:269`, `ccproxy_manager.py:270`
- OpenAI/Codex env routing is force-set to:
  - `OPENAI_BASE_URL=http://127.0.0.1:{port}/codex/v1`
  - `OPENAI_API_KEY=ccproxy-oauth`
  - Evidence: `ccproxy_manager.py:273`, `ccproxy_manager.py:283`, `ccproxy_manager.py:284`
- Default ccproxy port is `8000` (`settings.py:278`).
- EvoScientist's settings layer can also propagate configured API keys/base URLs into process env, but only if those env vars are not already set (`settings.py:523` through `settings.py:528`).

For EasyPaper, env setup alone is not enough for OpenAI-compatible calls because EasyPaper passes an explicit `base_url` from its config. The integration wrapper should call `maybe_start_ccproxy()` first, then pass the same resolved ccproxy URL into EasyPaper's `AppConfig`.

### LangGraph Dev Manager

Relevant files:

- `EvoScientist/langgraph_dev/manager.py`
- `EvoScientist/langgraph_dev/langgraph.json`
- `EvoScientist/langgraph_dev/graphs.py`

Integration facts:

- EvoScientist runs `langgraph dev` as a subprocess for async subagents (`manager.py:1`, `manager.py:329`).
- Default dev server base URL is `http://127.0.0.1:6174` (`manager.py:48`, `manager.py:51`).
- The packaged manifest is `EvoScientist/langgraph_dev/langgraph.json` (`manager.py:312`, `manager.py:321`).
- Startup passes workspace and safety env:
  - `EVOSCIENTIST_WORKSPACE_DIR` (`manager.py:445`)
  - `PYTHONUTF8=1` (`manager.py:446`)
  - optional `LANGGRAPH_DISABLE_FILE_PERSISTENCE=true` (`manager.py:454`)
  - `EVOSCIENTIST_DEPLOYED_NO_MCP=true` to avoid duplicated MCP servers (`manager.py:466`)
- It starts with `langgraph dev --config <langgraph.json> --port <port> --jobs-per-worker <n>` and `cwd` set to workspace (`manager.py:469` through `manager.py:481`).
- Current manifest registers only:
  - `EvoScientist`
  - `writing-agent`
  - `data-analysis-agent`
  - Evidence: `langgraph.json:3` through `langgraph.json:6`
- `graphs.py` builds deployed async graphs from YAML via `build_async_subagent_graph()` (`graphs.py:25`, `graphs.py:27`, `graphs.py:28`).

If EasyPaper is exposed as an EvoScientist async subagent, adding YAML is not enough: a graph binding and `langgraph.json` entry are also required.

### Channels

The three channel files inspected were `EvoScientist/channels/standalone.py`, `EvoScientist/channels/telegram/channel.py`, and `EvoScientist/channels/telegram/serve.py`.

Integration facts:

- `standalone.py` is the channel-agnostic runner that consumes inbound messages, streams agent events, and dispatches outbound replies (`standalone.py:1` through `standalone.py:5`).
- When run with `use_agent=True`, it loads config, starts ccproxy if needed, then creates the CLI agent (`standalone.py:108`, `standalone.py:112`, `standalone.py:115`, `standalone.py:120`, `standalone.py:122`).
- This means EasyPaper-as-tool integration should be inside `create_cli_agent()` / tool surface, not duplicated per channel.
- Telegram channel uses `python-telegram-bot` long polling (`telegram/channel.py:32`, `telegram/channel.py:127`) and accepts text plus media (`telegram/channel.py:104`, `telegram/channel.py:276` through `telegram/channel.py:292`).
- Telegram has a local passcode gate before messages reach the agent (`telegram/channel.py:238` through `telegram/channel.py:251`).
- Telegram server CLI supports `--agent` and `--thinking`, then calls `run_standalone()` (`telegram/serve.py:58`, `telegram/serve.py:65`, `telegram/serve.py:84`).

EasyPaper progress events should be converted to EvoScientist thinking/outbound updates at the agent/tool layer so Telegram and future channels receive the same behavior.

### Subagent YAML Shape

Relevant files:

- `EvoScientist/subagents/*.yaml`
- `EvoScientist/utils.py`
- `EvoScientist/subagents/_factory.py`
- `EvoScientist/EvoScientist.py`

Current YAML shape:

```yaml
<agent-name>:
  description: "..."
  tools: [...]
  skills: [...]
  async: true     # optional, boolean only
  system_prompt: |
    ...
```

Observed top-level YAML keys:

- `code-agent`
- `data-analysis-agent`
- `debug-agent`
- `latex-formatter-agent`
- `planner-agent`
- `research-agent`
- `reviewer-agent`
- `writing-agent`

Nested fields in current files are `description`, `tools`, `skills`, `system_prompt`, `system_prompt_ref`, and optional `async`. Only `data-analysis-agent` and `writing-agent` had `async: true` in the scan (`data_analysis.yaml:8`, `writing.yaml:8`).

Loader facts:

- `load_subagents()` loads all `*.yaml` files from a directory (`utils.py:112`, `utils.py:124`, `utils.py:157`).
- It supports `system_prompt_ref` (`utils.py:198` through `utils.py:202`), `skills` (`utils.py:211`), and tool name resolution (`utils.py:214` through `utils.py:223`).
- It carries the YAML `async` flag as internal `_async` and enforces that it is a boolean (`utils.py:225` through `utils.py:238`).
- `_maybe_swap_async_subagents()` replaces `_async` subagents with remote `AsyncSubAgent` specs only when `enable_async_subagents` and `langgraph dev` are available (`EvoScientist.py:244` through `EvoScientist.py:323`).
- The async factory builds deployable graphs with `deepagents.create_deep_agent()` and loads the same tools/skills/MCP exposure for that agent (`_factory.py:22`, `_factory.py:63`, `_factory.py:81`, `_factory.py:105` through `_factory.py:112`).

## EasyPaper Static Scan

### Package and Dependency Facts

Local source facts:

- `competitor_repos/easypaper-source/.git` is absent.
- `competitor_repos/easypaper-source/PKG-INFO` and `easypaper.egg-info/` are present.
- Local package metadata:
  - `pyproject.toml:3`: `version = "0.2.4"`
  - `pyproject.toml:9`: `openai>=2.7.2`
  - `pyproject.toml:10`: `langgraph>=0.0.26`
  - `pyproject.toml:36`: `anthropic>=0.18.0` under the `vlm` extra
  - `PKG-INFO:9`: `Requires-Dist: openai>=2.7.2`
  - `PKG-INFO:10`: `Requires-Dist: langgraph>=0.0.26`
  - `PKG-INFO:31`: `Requires-Dist: anthropic>=0.18.0; extra == "vlm"`

EvoScientist already has newer LangGraph/DeepAgents dependencies:

- `pyproject.toml:19`: `deepagents>=0.5.7`
- `pyproject.toml:20`: `langchain>=1.2`
- `pyproject.toml:34`: `langgraph-cli[inmem]>=0.4`
- `uv.lock` currently resolves `langgraph==1.1.10`

EasyPaper's `langgraph>=0.0.26` has no upper bound, so dependency resolution is probably compatible, but it must be smoke-tested against EvoScientist's resolved LangGraph 1.x API.

### OpenAI Usage and ccproxy

EasyPaper centralizes text model calls through `LLMClient`:

- `src/agents/shared/llm_client.py:22`: `from openai import AsyncOpenAI`
- `src/agents/shared/llm_client.py:318`: `class LLMClient`
- `src/agents/shared/llm_client.py:339`: `def __init__(self, **kwargs)`
- `src/agents/shared/llm_client.py:340`: `self._client = AsyncOpenAI(**kwargs)`

Agents pass `api_key` and `base_url` from config:

- `src/agents/react_base.py:36` through `src/agents/react_base.py:38`
- `src/agents/commander_agent/commander_agent.py:166` through `src/agents/commander_agent/commander_agent.py:168`
- `src/agents/planner_agent/planner_agent.py:175` through `src/agents/planner_agent/planner_agent.py:177`
- `src/agents/parse_agent/parse_agent.py:57` through `src/agents/parse_agent/parse_agent.py:59`
- `src/agents/template_agent/template_agent.py:94` through `src/agents/template_agent/template_agent.py:96`
- `src/agents/typesetter_agent/typesetter_agent.py:144` through `src/agents/typesetter_agent/typesetter_agent.py:146`
- `src/agents/reviewer_agent/reviewer_agent.py:100` through `src/agents/reviewer_agent/reviewer_agent.py:102`

Config facts:

- `src/config/schema.py:6` through `src/config/schema.py:9` define `ModelConfig(model_name, api_key, base_url="https://api.openai.com/v1")`.
- `src/config/loader.py:30` reads only `AGENT_CONFIG_PATH`, then parses YAML and returns `AppConfig` (`loader.py:39`, `loader.py:41`).
- `easypaper/client.py:48` through `easypaper/client.py:65` allow `EasyPaper(config_path=...)`, but also allow a pre-built `AppConfig`.

ccproxy implication:

- `OPENAI_BASE_URL` env by itself is not reliable for EasyPaper because `base_url` is explicit in `ModelConfig` and passed to `AsyncOpenAI`.
- Use one of:
  - `EasyPaper(config=AppConfig(...))` with every agent `model.base_url` set to `http://127.0.0.1:<ccproxy_port>/codex/v1`; preferred for no temp config file.
  - A generated EasyPaper YAML at `AGENT_CONFIG_PATH` with those same model fields.
- Use `api_key: ccproxy-oauth` for the OpenAI-compatible ccproxy path.

### Anthropic Usage and ccproxy

Anthropic is only in the optional VLM provider path:

- `pyproject.toml:36`: `anthropic>=0.18.0` under `[project.optional-dependencies].vlm`
- `src/agents/vlm_review_agent/providers/claude_vlm.py:52`: lazy `import anthropic`
- `src/agents/vlm_review_agent/providers/claude_vlm.py:53`: `self.client = anthropic.AsyncAnthropic(api_key=api_key)`
- `src/agents/vlm_review_agent/providers/claude_vlm.py:109`: `self.client.messages.create(...)`

`ClaudeVLM.__init__` accepts `**kwargs` but does not forward `base_url` to `AsyncAnthropic` (`claude_vlm.py:27`, `claude_vlm.py:33`, `claude_vlm.py:45`, `claude_vlm.py:53`). By contrast, OpenAI VLM handles `base_url`:

- `src/agents/vlm_review_agent/providers/openai_vlm.py:33`: `base_url: Optional[str] = None`
- `src/agents/vlm_review_agent/providers/openai_vlm.py:56` through `src/agents/vlm_review_agent/providers/openai_vlm.py:57`: sets `client_kwargs["base_url"]`
- `src/agents/vlm_review_agent/providers/openai_vlm.py:59`: `self.client = LLMClient(**client_kwargs)`

ccproxy implication:

- OpenAI VLM provider is compatible via config `base_url`.
- Claude VLM needs either env support from the Anthropic SDK or a small EasyPaper patch to pass `base_url` into `anthropic.AsyncAnthropic`. Static EasyPaper source contains no direct `ANTHROPIC_BASE_URL` handling.

### base_url, api_base, and httpx Scan

Static grep results:

- `api_base`: no matches in `competitor_repos/easypaper-source` or `EvoScientist`.
- `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL`: no EasyPaper source matches. These exist in EvoScientist ccproxy/config code only.
- `base_url`: used extensively in EasyPaper config and OpenAI-compatible clients.
- `httpx.AsyncClient`: present for non-model HTTP calls:
  - `src/agents/commander_agent/commander_agent.py:221` for backend graph data
  - `src/agents/typesetter_agent/typesetter_agent.py:361` for backend figure/files API
  - `src/agents/metadata_agent/compile_support.py:414`
  - `src/agents/shared/docling_analyzer.py:91`
  - `src/agents/shared/tools/paper_search.py:90` and `paper_search.py:284`
  - `src/agents/writer_agent/router.py:999` and `writer_agent/router.py:1051`
- `httpx.Client`: no sync client matches in the main source scan.

These `httpx.AsyncClient` usages are not the main LLM provider path. They may still matter for network policy, but not for ccproxy OpenAI routing.

### LangGraph Usage

EasyPaper does use LangGraph:

- `pyproject.toml:10`: `langgraph>=0.0.26`
- `PKG-INFO:10`: `Requires-Dist: langgraph>=0.0.26`
- `src/agents/commander_agent/commander_agent.py:12`: `from langgraph.graph import StateGraph, START, END`
- `src/agents/parse_agent/parse_agent.py:4`: `from langgraph.graph import StateGraph, START, END`
- `src/agents/template_agent/template_agent.py:10`: `from langgraph.graph import StateGraph, START, END`
- `src/agents/typesetter_agent/typesetter_agent.py:10`: `from langgraph.graph import StateGraph, START, END`
- `src/agents/vlm_review_agent/vlm_review_agent.py:14`: `from langgraph.graph import StateGraph, END`

Compiled graph examples:

- Commander builds and compiles a `StateGraph` (`commander_agent.py:183`, `commander_agent.py:197`) and invokes it (`commander_agent.py:833`).
- Parse agent builds and compiles a `StateGraph` (`parse_agent.py:68`, `parse_agent.py:74`) and invokes it (`parse_agent.py:134`).
- Template agent builds and compiles a `StateGraph` (`template_agent.py:110`, `template_agent.py:116`) and invokes it (`template_agent.py:286`).
- Typesetter builds and compiles a `StateGraph` (`typesetter_agent.py:180`, `typesetter_agent.py:194`) and invokes it (`typesetter_agent.py:1185`).
- VLM review builds and compiles a graph (`vlm_review_agent.py:242`, `vlm_review_agent.py:269`) and invokes it (`vlm_review_agent.py:913`).

Integration implication:

- If EasyPaper did not use LangGraph, the simple path would be a thin EvoScientist tool that calls a plain SDK method.
- Because EasyPaper already uses LangGraph, the integration should wrap EasyPaper's SDK orchestration boundary (`EasyPaper.generate()` / `generate_stream()`) rather than trying to translate every EasyPaper agent into EvoScientist YAML subagents.
- For EvoScientist async execution, the clean path is an `easypaper-agent` wrapper graph/subagent that calls `EasyPaper.generate_stream()` and forwards events. Deeply merging EasyPaper's internal StateGraphs into EvoScientist's `langgraph_dev` manifest would couple two orchestration systems and increase maintenance cost.

## Recommended Integration Plan

1. Fork upstream `PinkGranite/EasyPaper` at `v0.2.4` / `8797d4bf9cd8680f4da2d8b322533364d602b82d`.
2. Vendor or submodule the fork initially with a version lock; keep an upstream remote for periodic manual merges.
3. Add an EvoScientist wrapper tool/subagent that:
   - ensures ccproxy is running through existing `maybe_start_ccproxy()`;
   - builds an EasyPaper `AppConfig` in memory;
   - sets every EasyPaper OpenAI-compatible model `api_key` to `ccproxy-oauth`;
   - sets every EasyPaper OpenAI-compatible model `base_url` to `http://127.0.0.1:<ccproxy_port>/codex/v1`;
   - calls `EasyPaper(config=app_config).generate_stream(...)`;
   - converts EasyPaper progress events into EvoScientist channel/thinking events.
4. Use EasyPaper's OpenAI VLM provider or disable VLM review for the first integration. Patch Claude VLM only if Anthropic VLM through ccproxy is required.
5. If the wrapper is async-subagent backed, add:
   - `EvoScientist/subagents/easypaper.yaml`
   - one `graphs.py` binding
   - one `langgraph.json` entry
   - a smoke test that runs the wrapper with mocked `LLMClient` and verifies no network calls escape the configured `base_url`.

## Final Decision

Proceed with a fork-and-integrate path. Do not downgrade to PyPI-only vendoring. The repo and PyPI artifact are sufficiently aligned for a hard fork baseline, but the upstream is one-author/low-activity, so integration should be pinned and tested rather than tracking floating `master`.

ccproxy does not require an integration redesign for the main EasyPaper path. It requires explicit EasyPaper config injection. The only redesign-like edge is optional Claude VLM, which can be deferred or patched narrowly.
