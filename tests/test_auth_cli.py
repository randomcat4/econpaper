from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.auth import auth_status, login_provider, verify_provider


def test_login_env_requires_present_variable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = login_provider("openai", api_key_env="OPENAI_API_KEY", auth_file=tmp_path / "auth.json")
    assert result.has_hard_blocks is True
    assert "env_key_missing" in {issue.code for issue in result.issues}


def test_login_env_records_redacted_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    auth_file = tmp_path / "auth.json"
    result = login_provider("openai", api_key_env="OPENAI_API_KEY", auth_file=auth_file)
    assert result.has_hard_blocks is False
    status = auth_status(auth_file=auth_file)
    assert status.providers["openai"]["configured"] is True
    assert status.providers["openai"]["source"] == "env"
    assert "sk-test-secret" not in json.dumps(status.to_dict())


def test_verify_openai_uses_models_endpoint_without_printing_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret")
    auth_file = tmp_path / "auth.json"
    login_provider("openai", api_key_env="OPENAI_API_KEY", auth_file=auth_file)
    captured: dict[str, object] = {}

    def fake_get(url: str, headers: dict[str, str], timeout: float) -> dict:
        captured.update({"url": url, "headers": headers, "timeout": timeout})
        return {"object": "list", "data": [{"id": "model-id-0", "object": "model"}]}

    result = verify_provider("openai", auth_file=auth_file, timeout=5.0, http_get_json=fake_get)
    assert result.has_hard_blocks is False
    assert captured["url"] == "https://api.openai.com/v1/models"
    assert captured["headers"] == {"Authorization": "Bearer sk-test-secret"}
    assert result.verification["model_count"] == 1
    assert "sk-test-secret" not in json.dumps(result.to_dict())


def test_verify_claude_uses_native_headers(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-secret")
    auth_file = tmp_path / "auth.json"
    login_provider("claude", api_key_env="ANTHROPIC_API_KEY", auth_file=auth_file)
    captured: dict[str, object] = {}

    def fake_get(url: str, headers: dict[str, str], timeout: float) -> dict:
        captured.update({"url": url, "headers": headers, "timeout": timeout})
        return {"type": "list", "data": [{"id": "claude-model"}]}

    result = verify_provider("anthropic", auth_file=auth_file, http_get_json=fake_get)
    assert result.has_hard_blocks is False
    assert captured["url"] == "https://api.anthropic.com/v1/models"
    assert captured["headers"] == {"x-api-key": "sk-ant-test-secret", "anthropic-version": "2023-06-01"}
    assert result.verification["model_count"] == 1
    assert "sk-ant-test-secret" not in json.dumps(result.to_dict())


def test_verify_missing_credential_hard_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    result = verify_provider("claude", auth_file=tmp_path / "auth.json")
    assert result.has_hard_blocks is True
    assert "credential_missing" in {issue.code for issue in result.issues}


def test_auth_cli_status_is_redacted(tmp_path: Path) -> None:
    auth_file = tmp_path / "auth.json"
    proc_login = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "auth",
            "login",
            "claude",
            "--api-key",
            "sk-ant-test-secret",
            "--auth-file",
            str(auth_file),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc_login.returncode == 0, proc_login.stdout + proc_login.stderr
    assert "sk-ant-test-secret" not in proc_login.stdout
    proc_status = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "auth",
            "status",
            "--auth-file",
            str(auth_file),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc_status.returncode == 0, proc_status.stdout + proc_status.stderr
    assert "sk-ant-test-secret" not in proc_status.stdout
    assert '"configured": true' in proc_status.stdout
