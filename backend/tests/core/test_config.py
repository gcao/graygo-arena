import base64
import json
from pathlib import Path

import pytest

from graygo_arena.core.config import load_settings


def codex_jwt(account_id: str = "acc_test") -> str:
    def encode(value: object) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    payload = {"https://api.openai.com/auth": {"chatgpt_account_id": account_id}}
    return f"{encode({'alg': 'none'})}.{encode(payload)}.signature"


def test_load_settings_reads_root_env_file_and_codex_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "OPENAI_CODEX_API_KEY=sk-codex-test",
                "OPENAI_MODEL=gpt-5.1-codex-max",
                "OPENAI_REASONING_EFFORT=xhigh",
                "OPENAI_MAX_OUTPUT_TOKENS=4096",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GRAYGO_ENV_FILE", str(env_file))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_CODEX_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_CODEX_TOKEN", raising=False)
    monkeypatch.delenv("CODEX_TOKEN", raising=False)

    settings = load_settings()

    assert settings.openai_auth_token == "sk-codex-test"
    assert settings.openai_auth_source == "codex_api_key"
    assert settings.openai_auth_error is None
    assert settings.openai_model == "gpt-5.1-codex-max"
    assert settings.openai_reasoning_effort == "xhigh"
    assert settings.openai_max_output_tokens == 4096


def test_load_settings_accepts_codex_oauth_access_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"OPENAI_CODEX_TOKEN={codex_jwt()}\n", encoding="utf-8")
    monkeypatch.setenv("GRAYGO_ENV_FILE", str(env_file))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_CODEX_API_KEY", raising=False)

    settings = load_settings()

    assert settings.openai_auth_token == codex_jwt()
    assert settings.openai_auth_source == "codex_oauth"
    assert settings.openai_auth_error is None
    assert settings.openai_model == "gpt-5.5"
    assert settings.openai_codex_base_url == "https://chatgpt.com/backend-api"
    assert settings.openai_codex_originator == "pi"


def test_load_settings_prefers_openai_api_key_over_codex_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_CODEX_API_KEY=sk-codex-test\n", encoding="utf-8")
    monkeypatch.setenv("GRAYGO_ENV_FILE", str(env_file))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    settings = load_settings()

    assert settings.openai_auth_token == "sk-test"
    assert settings.openai_auth_source == "api_key"


def test_load_settings_rejects_unknown_reasoning_effort(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_REASONING_EFFORT=maximum\n", encoding="utf-8")
    monkeypatch.setenv("GRAYGO_ENV_FILE", str(env_file))

    with pytest.raises(ValueError, match="OPENAI_REASONING_EFFORT"):
        load_settings()
