"""Environment-driven backend settings."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from graygo_arena.core.codex_auth import read_access_token

type OpenAIAuthSource = Literal["api_key", "codex_api_key", "codex_oauth", "none"]
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
    openai_codex_base_url: str = "https://chatgpt.com/backend-api"
    openai_codex_originator: str = "pi"
    openai_codex_auth_file: Path | None = None
    openai_codex_binary: str = "codex"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    graygo_model_repo: Path = Path("../graygo")
    graygo_model_path: Path = Path("../graygo/checkpoints/champion_traced.pt")
    graygo_model_python: Path = Path(sys.executable)
    graygo_model_device: str = "cpu"
    graygo_model_board_size: int = 9
    graygo_nfsp_model_path: Path | None = None
    graygo_old_model_repo: Path | None = None
    graygo_old_model_path: Path | None = None
    graygo_loop_manifest: Path | None = None


def load_settings() -> Settings:
    values = _environment_values()
    openai_token, openai_source, openai_error = _openai_auth(values)
    database_path = Path(values.get("GRAYGO_DATABASE_PATH", ".runtime/graygo.db"))
    graygo_model_repo = Path(
        values.get("GRAYGO_MODEL_REPO", str(_default_graygo_model_repo()))
    ).expanduser()
    graygo_model_path = _graygo_model_path(values.get("GRAYGO_MODEL_PATH"), graygo_model_repo)
    return Settings(
        database_path=database_path,
        openai_auth_token=openai_token,
        openai_auth_source=openai_source,
        openai_auth_error=openai_error,
        openai_model=values.get("OPENAI_MODEL", _default_openai_model(openai_source)),
        openai_reasoning_effort=_openai_reasoning_effort(
            values.get("OPENAI_REASONING_EFFORT", "medium")
        ),
        openai_max_output_tokens=_positive_int(
            values.get("OPENAI_MAX_OUTPUT_TOKENS"), 2048, "OPENAI_MAX_OUTPUT_TOKENS"
        ),
        openai_codex_base_url=values.get(
            "OPENAI_CODEX_BASE_URL", "https://chatgpt.com/backend-api"
        ),
        openai_codex_originator=values.get("OPENAI_CODEX_ORIGINATOR", "pi"),
        openai_codex_auth_file=_optional_path(values.get("OPENAI_CODEX_AUTH_FILE")),
        openai_codex_binary=values.get("OPENAI_CODEX_BINARY", "codex"),
        anthropic_api_key=_non_empty(values.get("ANTHROPIC_API_KEY")),
        anthropic_model=values.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        graygo_model_repo=graygo_model_repo,
        graygo_model_path=graygo_model_path,
        graygo_model_python=Path(
            values.get("GRAYGO_MODEL_PYTHON", str(_default_graygo_model_python(graygo_model_repo)))
        ).expanduser(),
        graygo_model_device=values.get("GRAYGO_MODEL_DEVICE", "cpu"),
        graygo_old_model_repo=_optional_path(values.get("GRAYGO_OLD_MODEL_REPO")),
        graygo_old_model_path=_optional_path(values.get("GRAYGO_OLD_MODEL_PATH")),
        graygo_loop_manifest=_optional_path(values.get("GRAYGO_LOOP_MANIFEST")),
        graygo_nfsp_model_path=(
            Path(values["GRAYGO_NFSP_MODEL_PATH"]).expanduser()
            if _non_empty(values.get("GRAYGO_NFSP_MODEL_PATH"))
            else None
        ),
        graygo_model_board_size=_positive_int(
            values.get("GRAYGO_MODEL_BOARD_SIZE"), 9, "GRAYGO_MODEL_BOARD_SIZE"
        ),
    )


def _optional_path(value: str | None) -> Path | None:
    return Path(value).expanduser() if value and value.strip() else None


def _environment_values() -> dict[str, str]:
    dotenv_values = _read_first_env_file()
    return {**dotenv_values, **dict(os.environ)}


def _read_first_env_file() -> dict[str, str]:
    for path in _env_file_candidates():
        if path.is_file():
            return _parse_env_file(path)
    return {}


def _default_graygo_model_repo() -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root.parent / "graygo"


def _default_graygo_model_python(repo: Path) -> Path:
    venv_python = repo / ".venv" / "bin" / "python"
    return venv_python if venv_python.is_file() else Path(sys.executable)


def _graygo_model_path(value: str | None, repo: Path) -> Path:
    if value and value.strip().lower() not in {"auto", "latest"}:
        return Path(value).expanduser()
    return _latest_graygo_model_path(repo)


def _latest_graygo_model_path(repo: Path) -> Path:
    checkpoints = repo / "checkpoints"
    traced = checkpoints / "champion_traced.pt"
    latest_champion = _latest_numbered_checkpoint(checkpoints, "champion_iter_*.pt")
    if latest_champion is None:
        return traced
    if traced.is_file() and traced.stat().st_mtime >= latest_champion.stat().st_mtime:
        return traced
    return latest_champion


def _latest_numbered_checkpoint(directory: Path, pattern: str) -> Path | None:
    best: tuple[int, Path] | None = None
    for path in directory.glob(pattern):
        match = re.search(r"_(\d+)\.pt$", path.name)
        if not match:
            continue
        candidate = (int(match.group(1)), path)
        if best is None or candidate[0] > best[0]:
            best = candidate
    return best[1] if best else None


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
    auth_file = _optional_path(values.get("OPENAI_CODEX_AUTH_FILE"))
    if auth_file is not None:
        try:
            return read_access_token(auth_file), "codex_oauth", None
        except ValueError:
            return None, "none", "Cannot read configured Codex ChatGPT login; run codex login"
    legacy_codex_value = _non_empty(values.get("OPENAI_CODEX_TOKEN")) or _non_empty(
        values.get("CODEX_TOKEN")
    )
    if legacy_codex_value is None:
        return None, "none", None
    if legacy_codex_value.startswith("sk-"):
        return legacy_codex_value, "codex_api_key", None
    if legacy_codex_value.startswith("eyJ"):
        return legacy_codex_value, "codex_oauth", None
    return (
        None,
        "none",
        (
            "OPENAI_CODEX_TOKEN/CODEX_TOKEN is not an API-key-shaped value. "
            "Use OPENAI_API_KEY/OPENAI_CODEX_API_KEY with an sk-... key, or "
            "OPENAI_CODEX_TOKEN with a Codex OAuth access token."
        ),
    )


def _default_openai_model(source: OpenAIAuthSource) -> str:
    if source == "codex_oauth":
        return "gpt-6.1-terra"
    return "gpt-5.1-codex-max"


def _openai_reasoning_effort(value: str) -> OpenAIReasoningEffort:
    effort = value.strip().lower()
    if effort not in OPENAI_REASONING_EFFORTS:
        supported = ", ".join(sorted(OPENAI_REASONING_EFFORTS))
        msg = f"OPENAI_REASONING_EFFORT must be one of: {supported}"
        raise ValueError(msg)
    return cast(OpenAIReasoningEffort, effort)


def _positive_int(value: str | None, default: int, name: str) -> int:
    if value is None or not value.strip():
        return default
    parsed = int(value)
    if parsed < 1:
        msg = f"{name} must be positive"
        raise ValueError(msg)
    return parsed


def _non_empty(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
