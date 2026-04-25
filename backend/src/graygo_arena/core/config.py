"""Environment-driven backend settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

type OpenAIAuthSource = Literal["api_key", "codex_api_key", "none"]
type OpenAIReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]

OPENAI_REASONING_EFFORTS: frozenset[str] = frozenset(
    ("none", "minimal", "low", "medium", "high", "xhigh")
)


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(".runtime/graygo.db")
    openai_auth_token: str | None = None
    openai_auth_source: OpenAIAuthSource = "none"
    openai_auth_error: str | None = None
    openai_model: str = "gpt-5.1-codex-max"
    openai_reasoning_effort: OpenAIReasoningEffort = "medium"
    openai_max_output_tokens: int = 2048
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"


def load_settings() -> Settings:
    values = _environment_values()
    openai_token, openai_source, openai_error = _openai_auth(values)
    database_path = Path(values.get("GRAYGO_DATABASE_PATH", ".runtime/graygo.db"))
    return Settings(
        database_path=database_path,
        openai_auth_token=openai_token,
        openai_auth_source=openai_source,
        openai_auth_error=openai_error,
        openai_model=values.get("OPENAI_MODEL", "gpt-5.1-codex-max"),
        openai_reasoning_effort=_openai_reasoning_effort(
            values.get("OPENAI_REASONING_EFFORT", "medium")
        ),
        openai_max_output_tokens=_positive_int(values.get("OPENAI_MAX_OUTPUT_TOKENS"), 2048),
        anthropic_api_key=_non_empty(values.get("ANTHROPIC_API_KEY")),
        anthropic_model=values.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
    )


def _environment_values() -> dict[str, str]:
    dotenv_values = _read_first_env_file()
    return {**dotenv_values, **dict(os.environ)}


def _read_first_env_file() -> dict[str, str]:
    for path in _env_file_candidates():
        if path.is_file():
            return _parse_env_file(path)
    return {}


def _env_file_candidates() -> tuple[Path, ...]:
    override = os.environ.get("GRAYGO_ENV_FILE")
    if override:
        return (Path(override),)
    repo_root = Path(__file__).resolve().parents[4]
    cwd = Path.cwd()
    candidates = (cwd / ".env", cwd.parent / ".env", repo_root / ".env", repo_root / "backend/.env")
    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen:
            unique.append(candidate)
            seen.add(resolved)
    return tuple(unique)


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = _clean_env_value(value)
    return values


def _clean_env_value(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1]
    return cleaned


def _openai_auth(values: dict[str, str]) -> tuple[str | None, OpenAIAuthSource, str | None]:
    api_key = _non_empty(values.get("OPENAI_API_KEY"))
    if api_key is not None:
        return api_key, "api_key", None
    codex_api_key = _non_empty(values.get("OPENAI_CODEX_API_KEY"))
    if codex_api_key is not None:
        return codex_api_key, "codex_api_key", None
    legacy_codex_value = _non_empty(values.get("OPENAI_CODEX_TOKEN")) or _non_empty(
        values.get("CODEX_TOKEN")
    )
    if legacy_codex_value is None:
        return None, "none", None
    if legacy_codex_value.startswith("sk-"):
        return legacy_codex_value, "codex_api_key", None
    if legacy_codex_value.startswith("eyJ"):
        return (
            None,
            "none",
            (
                "OPENAI_CODEX_TOKEN/CODEX_TOKEN looks like a Codex or ChatGPT OAuth access "
                "token. The Responses API requires an API key with api.responses.write scope. "
                "Use OPENAI_API_KEY or OPENAI_CODEX_API_KEY with an sk-... key."
            ),
        )
    return (
        None,
        "none",
        (
            "OPENAI_CODEX_TOKEN/CODEX_TOKEN is not an API-key-shaped value. "
            "Use OPENAI_API_KEY or OPENAI_CODEX_API_KEY with an sk-... key."
        ),
    )


def _openai_reasoning_effort(value: str) -> OpenAIReasoningEffort:
    effort = value.strip().lower()
    if effort not in OPENAI_REASONING_EFFORTS:
        supported = ", ".join(sorted(OPENAI_REASONING_EFFORTS))
        msg = f"OPENAI_REASONING_EFFORT must be one of: {supported}"
        raise ValueError(msg)
    return cast(OpenAIReasoningEffort, effort)


def _positive_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    parsed = int(value)
    if parsed < 1:
        msg = "OPENAI_MAX_OUTPUT_TOKENS must be positive"
        raise ValueError(msg)
    return parsed


def _non_empty(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
