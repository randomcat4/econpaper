# easypaper-setup-environment

Use this setup skill when preparing a local EasyPaper econ/finance run.

## Config Template

The synchronized template lives at `config.example.yaml` inside this skill and
must match the project-level `configs/example.yaml` file exactly. Copy it to a
local `easypaper_config.yaml` before editing machine-specific model, base URL,
or key values.

Recommended local flow:

```powershell
Copy-Item plugins/easypaper/skills/easypaper-setup-environment/config.example.yaml easypaper_config.yaml
```

Keep secrets outside git. API keys should come from environment variables or a
local untracked config file. The committed example uses the ccproxy-compatible
placeholder `ccproxy-oauth` and a localhost OpenAI-compatible base URL.

## Econ/Finance Safety

- Empirical tables and figures must come from file-backed artifacts.
- Failed, missing-dependency, parser-only, or interface-only artifacts must not
  become paper claims.
- Do not enable autonomous generated result figures for economics or finance
  manuscripts.
