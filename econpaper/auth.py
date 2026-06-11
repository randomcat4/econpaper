from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


AUTH_VERSION = "v3.0"
ANTHROPIC_VERSION = "2023-06-01"


class AuthError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    display_name: str
    env_vars: tuple[str, ...]
    verify_url: str
    docs_url: str


@dataclass(frozen=True)
class SubscriptionProviderSpec:
    name: str
    display_name: str
    cli_name: str
    status_command: tuple[str, ...]
    login_command: str
    docs_url: str


PROVIDERS: dict[str, ProviderSpec] = {
    "openai": ProviderSpec(
        name="openai",
        display_name="OpenAI",
        env_vars=("OPENAI_API_KEY",),
        verify_url="https://api.openai.com/v1/models",
        docs_url="https://platform.openai.com/docs/api-reference/authentication",
    ),
    "claude": ProviderSpec(
        name="claude",
        display_name="Claude",
        env_vars=("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
        verify_url="https://api.anthropic.com/v1/models",
        docs_url="https://docs.anthropic.com/en/api/models-list",
    ),
}

ALIASES = {
    "anthropic": "claude",
}

SUBSCRIPTION_PROVIDERS: dict[str, SubscriptionProviderSpec] = {
    "codex": SubscriptionProviderSpec(
        name="codex",
        display_name="OpenAI Codex / ChatGPT subscription",
        cli_name="codex",
        # Override service_tier because older local configs may still contain
        # service_tier="default". Use fast because it also works for real
        # subscription-backed Codex model calls.
        status_command=("codex", "-c", 'service_tier="fast"', "login", "status"),
        login_command="codex login --device-auth",
        docs_url="https://github.com/openai/codex",
    ),
    "claude-code": SubscriptionProviderSpec(
        name="claude-code",
        display_name="Claude Code subscription",
        cli_name="claude",
        status_command=("claude", "auth", "status"),
        login_command="claude auth login",
        docs_url="https://github.com/anthropics/claude-code",
    ),
}

SUBSCRIPTION_ALIASES = {
    "chatgpt": "codex",
    "openai-codex": "codex",
    "codex-cli": "codex",
    "claude_code": "claude-code",
    "claude-code-cli": "claude-code",
    "claude-subscription": "claude-code",
}


@dataclass
class AuthIssue:
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


@dataclass
class AuthResult:
    status: str
    provider: str | None = None
    action: str | None = None
    auth_file: str | None = None
    providers: dict[str, Any] = field(default_factory=dict)
    subscriptions: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    issues: list[AuthIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(AuthIssue(code=code, severity=severity, message=message))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": AUTH_VERSION,
            "status": self.status,
            "provider": self.provider,
            "action": self.action,
            "auth_file": self.auth_file,
            "providers": self.providers,
            "subscriptions": self.subscriptions,
            "verification": self.verification,
            "issues": [issue.to_dict() for issue in self.issues],
        }


HttpGetJson = Callable[[str, dict[str, str], float], dict[str, Any]]
CommandRunner = Callable[[tuple[str, ...], float], subprocess.CompletedProcess[str]]


def canonical_provider(provider: str) -> str:
    key = provider.strip().lower()
    key = ALIASES.get(key, key)
    if key not in PROVIDERS:
        allowed = ", ".join(sorted(PROVIDERS))
        raise AuthError(f"Unknown auth provider `{provider}`. Supported providers: {allowed}.")
    return key


def canonical_subscription_provider(provider: str) -> str:
    key = provider.strip().lower()
    key = SUBSCRIPTION_ALIASES.get(key, key)
    if key not in SUBSCRIPTION_PROVIDERS:
        allowed = ", ".join(sorted(SUBSCRIPTION_PROVIDERS))
        raise AuthError(f"Unknown subscription provider `{provider}`. Supported providers: {allowed}.")
    return key


def default_auth_file() -> Path:
    explicit = os.environ.get("ECONPAPER_AUTH_FILE")
    if explicit:
        return Path(explicit).expanduser()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "econpaper" / "auth.json"
    return Path.home() / ".econpaper" / "auth.json"


def login_provider(
    provider: str,
    *,
    api_key: str | None = None,
    api_key_env: str | None = None,
    auth_file: str | Path | None = None,
) -> AuthResult:
    path = Path(auth_file) if auth_file else default_auth_file()
    result = AuthResult(status="passed", provider=canonical_provider(provider), action="login", auth_file=str(path))
    spec = PROVIDERS[result.provider]
    config = _load_config(path, result)

    if api_key and api_key_env:
        result.add_issue("ambiguous_auth_source", "hard_block", "Use either --api-key or --api-key-env, not both.")
        return result
    if api_key_env:
        env_var = api_key_env.strip()
        if not env_var:
            result.add_issue("empty_env_var", "hard_block", "--api-key-env must name a non-empty environment variable.")
            return result
        if not os.environ.get(env_var):
            result.add_issue("env_key_missing", "hard_block", f"Environment variable `{env_var}` is not set, so login would not be usable.")
            return result
        record = {"source": "env", "env_var": env_var}
    elif api_key:
        if not api_key.strip():
            result.add_issue("empty_api_key", "hard_block", "--api-key cannot be empty.")
            return result
        record = {"source": "stored_key", "api_key": api_key.strip()}
    else:
        env_var = _first_present_env(spec.env_vars)
        if not env_var:
            names = ", ".join(spec.env_vars)
            result.add_issue(
                "credential_missing",
                "hard_block",
                f"No usable {spec.display_name} key was found. Set one of {names} or pass --api-key.",
            )
            return result
        record = {"source": "env", "env_var": env_var}

    record.update(
        {
            "provider": spec.name,
            "display_name": spec.display_name,
            "created_at": int(time.time()),
            "verify_url": spec.verify_url,
            "docs_url": spec.docs_url,
        }
    )
    config.setdefault("providers", {})[spec.name] = record
    _write_config(path, config)
    result.providers[spec.name] = _status_for_provider(spec, config)
    return result


def auth_status(*, auth_file: str | Path | None = None) -> AuthResult:
    path = Path(auth_file) if auth_file else default_auth_file()
    result = AuthResult(status="passed", action="status", auth_file=str(path))
    config = _load_config(path, result)
    result.providers = {name: _status_for_provider(spec, config) for name, spec in PROVIDERS.items()}
    return result


def subscription_status(
    *,
    timeout: float = 15.0,
    command_runner: CommandRunner | None = None,
) -> AuthResult:
    result = AuthResult(status="passed", action="subscription-status")
    for name, spec in SUBSCRIPTION_PROVIDERS.items():
        result.subscriptions[name] = _subscription_status_for_provider(
            spec,
            timeout=timeout,
            command_runner=command_runner,
        )
    if any(item.get("configured") for item in result.subscriptions.values()):
        return result
    result.add_issue(
        "subscription_auth_missing",
        "hard_block",
        "No usable Codex/ChatGPT or Claude Code subscription login was detected.",
    )
    return result


def verify_subscription(
    provider: str,
    *,
    timeout: float = 15.0,
    command_runner: CommandRunner | None = None,
) -> AuthResult:
    provider_name = canonical_subscription_provider(provider)
    spec = SUBSCRIPTION_PROVIDERS[provider_name]
    result = AuthResult(status="passed", provider=provider_name, action="verify-subscription")
    status = _subscription_status_for_provider(spec, timeout=timeout, command_runner=command_runner)
    result.subscriptions[provider_name] = status
    result.verification = {
        "provider": provider_name,
        "subscription_status_attempted": True,
        "live_model_request_attempted": False,
        "docs_url": spec.docs_url,
        "login_command": spec.login_command,
    }
    if not status.get("configured"):
        result.add_issue(
            "subscription_auth_missing",
            "hard_block",
            f"No usable {spec.display_name} login was detected. Run `{spec.login_command}` and retry.",
        )
    return result


def verify_provider(
    provider: str,
    *,
    auth_file: str | Path | None = None,
    timeout: float = 30.0,
    http_get_json: HttpGetJson | None = None,
) -> AuthResult:
    provider_name = canonical_provider(provider)
    spec = PROVIDERS[provider_name]
    path = Path(auth_file) if auth_file else default_auth_file()
    result = AuthResult(status="passed", provider=provider_name, action="verify", auth_file=str(path))
    config = _load_config(path, result)
    credential = _resolve_key(spec, config)
    result.providers[provider_name] = _status_for_provider(spec, config)
    result.verification = {
        "provider": provider_name,
        "endpoint": spec.verify_url,
        "docs_url": spec.docs_url,
        "live_request_attempted": False,
    }
    if not credential:
        names = ", ".join(spec.env_vars)
        result.add_issue(
            "credential_missing",
            "hard_block",
            f"No usable {spec.display_name} credential is configured. Set {names} or run auth login with --api-key.",
        )
        return result

    headers = _verify_headers(spec, credential)
    getter = http_get_json or _http_get_json
    result.verification["live_request_attempted"] = True
    try:
        payload = getter(spec.verify_url, headers, timeout)
    except Exception as exc:
        result.add_issue("provider_verification_failed", "hard_block", f"{spec.display_name} verification failed: {exc}")
        return result
    data = payload.get("data")
    result.verification.update(
        {
            "reachable": True,
            "model_count": len(data) if isinstance(data, list) else None,
            "response_object": payload.get("object") or payload.get("type"),
        }
    )
    return result


def _load_config(path: Path, result: AuthResult) -> dict[str, Any]:
    if not path.exists():
        return {"version": AUTH_VERSION, "providers": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        result.add_issue("auth_file_invalid_json", "hard_block", f"Could not parse auth file `{path}`: {exc}")
        return {"version": AUTH_VERSION, "providers": {}}
    if not isinstance(payload, dict):
        result.add_issue("auth_file_not_object", "hard_block", f"Auth file `{path}` must contain a JSON object.")
        return {"version": AUTH_VERSION, "providers": {}}
    payload.setdefault("version", AUTH_VERSION)
    payload.setdefault("providers", {})
    return payload


def _write_config(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_redaction_safe_config(config, keep_secret=True), ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def _redaction_safe_config(config: dict[str, Any], *, keep_secret: bool) -> dict[str, Any]:
    copied = json.loads(json.dumps(config))
    if keep_secret:
        return copied
    for record in copied.get("providers", {}).values():
        if isinstance(record, dict) and "api_key" in record:
            record["api_key"] = "<redacted>"
    return copied


def _status_for_provider(spec: ProviderSpec, config: dict[str, Any]) -> dict[str, Any]:
    record = (config.get("providers") or {}).get(spec.name, {})
    env_var = _first_present_env(spec.env_vars)
    source = record.get("source") if isinstance(record, dict) else None
    configured = False
    detail: dict[str, Any] = {
        "display_name": spec.display_name,
        "configured": False,
        "source": None,
        "env_var": None,
        "stored_key_present": False,
        "docs_url": spec.docs_url,
    }
    if isinstance(record, dict) and source == "stored_key" and record.get("api_key"):
        configured = True
        detail.update({"source": "stored_key", "stored_key_present": True})
    elif isinstance(record, dict) and source == "env" and record.get("env_var"):
        configured = bool(os.environ.get(str(record["env_var"])))
        detail.update({"source": "env", "env_var": str(record["env_var"])})
    elif env_var:
        configured = True
        detail.update({"source": "env", "env_var": env_var})
    detail["configured"] = configured
    return detail


def _resolve_key(spec: ProviderSpec, config: dict[str, Any]) -> str | None:
    record = (config.get("providers") or {}).get(spec.name, {})
    if isinstance(record, dict) and record.get("source") == "stored_key" and record.get("api_key"):
        return str(record["api_key"])
    if isinstance(record, dict) and record.get("source") == "env" and record.get("env_var"):
        key = os.environ.get(str(record["env_var"]))
        if key:
            return key
    for env_var in spec.env_vars:
        key = os.environ.get(env_var)
        if key:
            return key
    return None


def _first_present_env(names: tuple[str, ...]) -> str | None:
    for name in names:
        if os.environ.get(name):
            return name
    return None


def _verify_headers(spec: ProviderSpec, api_key: str) -> dict[str, str]:
    if spec.name == "openai":
        return {"Authorization": f"Bearer {api_key}"}
    if spec.name == "claude":
        return {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }
    raise AuthError(f"Unsupported provider `{spec.name}`.")


def _subscription_status_for_provider(
    spec: SubscriptionProviderSpec,
    *,
    timeout: float,
    command_runner: CommandRunner | None,
) -> dict[str, Any]:
    command_candidates = (
        [(shutil.which(spec.cli_name) or spec.cli_name, spec.status_command)]
        if command_runner
        else _subscription_command_candidates(spec)
    )
    cli_path = command_candidates[0][0] if command_candidates else None
    detail: dict[str, Any] = {
        "display_name": spec.display_name,
        "configured": False,
        "source": "subscription_cli",
        "cli": spec.cli_name,
        "cli_path": cli_path,
        "docs_url": spec.docs_url,
        "login_command": spec.login_command,
    }
    if not cli_path:
        detail.update({"status": "missing_cli", "message": f"`{spec.cli_name}` was not found on PATH."})
        return detail
    runner = command_runner or _run_command
    last_detail: dict[str, Any] | None = None
    attempted = 0
    for candidate_path, command in command_candidates:
        attempted += 1
        attempt = dict(detail)
        attempt["cli_path"] = candidate_path
        try:
            proc = runner(command, timeout)
        except subprocess.TimeoutExpired:
            attempt.update({"status": "status_timeout", "message": f"`{spec.cli_name}` status command timed out."})
            last_detail = attempt
            continue
        except Exception as exc:
            attempt.update({"status": "status_error", "message": str(exc)})
            last_detail = attempt
            continue
        parsed = _subscription_detail_from_status_process(spec, attempt, proc)
        last_detail = parsed
        if parsed.get("configured"):
            if len(command_candidates) > 1:
                parsed["attempted_cli_count"] = attempted
            return parsed
    if last_detail is None:
        detail.update({"status": "missing_cli", "message": f"`{spec.cli_name}` was not found on PATH."})
        return detail
    if len(command_candidates) > 1:
        last_detail["attempted_cli_count"] = len(command_candidates)
    return last_detail


def _subscription_detail_from_status_process(
    spec: SubscriptionProviderSpec,
    detail: dict[str, Any],
    proc: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    try:
        return _parse_subscription_status_process(spec, detail, proc)
    except Exception as exc:
        detail.update({"status": "status_error", "message": str(exc)})
        return detail


def _parse_subscription_status_process(
    spec: SubscriptionProviderSpec,
    detail: dict[str, Any],
    proc: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    combined = "\n".join(part for part in [stdout, stderr] if part).strip()
    detail["returncode"] = proc.returncode
    if spec.name == "codex":
        configured = proc.returncode == 0 and "logged in using chatgpt" in combined.lower()
        detail.update(
            {
                "configured": configured,
                "auth_method": "chatgpt" if configured else None,
                "plan_type": "unknown",
                "status": "passed" if configured else "failed",
                "message": _safe_status_message(combined),
            }
        )
        return detail
    if spec.name == "claude-code":
        parsed = _parse_json_object(stdout)
        configured = (
            proc.returncode == 0
            and bool(parsed.get("loggedIn"))
            and str(parsed.get("authMethod") or "").lower() == "claude.ai"
            and str(parsed.get("apiProvider") or "").lower() == "firstparty"
        )
        detail.update(
            {
                "configured": configured,
                "auth_method": parsed.get("authMethod") if parsed else None,
                "api_provider": parsed.get("apiProvider") if parsed else None,
                "subscription_type": parsed.get("subscriptionType") if parsed else None,
                "email_present": bool(parsed.get("email")) if parsed else False,
                "org_present": bool(parsed.get("orgId") or parsed.get("orgName")) if parsed else False,
                "status": "passed" if configured else "failed",
                "message": "logged in with Claude Code subscription" if configured else _safe_status_message(stderr or stdout),
            }
        )
        return detail
    detail.update({"status": "unsupported", "message": "Unsupported subscription provider."})
    return detail


def _subscription_command_candidates(spec: SubscriptionProviderSpec) -> list[tuple[str | None, tuple[str, ...]]]:
    paths = _subscription_cli_candidates(spec)
    return [(path, (path, *spec.status_command[1:])) for path in paths]


def _subscription_cli_candidates(spec: SubscriptionProviderSpec) -> list[str]:
    candidates: list[str] = []
    path_cli = shutil.which(spec.cli_name)
    if path_cli:
        candidates.append(path_cli)

    if os.name == "nt" and spec.name == "codex":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            bin_root = Path(local_appdata) / "OpenAI" / "Codex" / "bin"
            if bin_root.exists():
                codex_bins = sorted(
                    bin_root.glob("*/codex.exe"),
                    key=lambda path: path.stat().st_mtime,
                    reverse=True,
                )
                candidates.extend(str(path) for path in codex_bins)
        appdata = os.environ.get("APPDATA")
        if appdata:
            npm_root = Path(appdata) / "npm"
            candidates.extend(
                str(path)
                for path in [
                    npm_root / "codex.cmd",
                    npm_root / "codex.ps1",
                    npm_root
                    / "node_modules"
                    / "@openai"
                    / "codex"
                    / "node_modules"
                    / "@openai"
                    / "codex-win32-x64"
                    / "vendor"
                    / "x86_64-pc-windows-msvc"
                    / "bin"
                    / "codex.exe",
                ]
                if path.exists()
            )

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(os.path.abspath(candidate))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _run_command(args: tuple[str, ...], timeout: float) -> subprocess.CompletedProcess[str]:
    if os.name == "nt":
        return subprocess.run(
            subprocess.list2cmdline(list(args)),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
            shell=True,
        )
    return subprocess.run(
        list(args),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_status_message(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("\r", " ").replace("\n", " ")
    # Keep diagnostics useful without leaking long terminal output.
    return cleaned[:500]


def _http_get_json(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={**headers, "accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise AuthError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AuthError(str(exc.reason)) from exc
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AuthError(f"Provider returned non-JSON response: {exc}") from exc
    if not isinstance(payload, dict):
        raise AuthError("Provider returned a JSON value that is not an object.")
    return payload
