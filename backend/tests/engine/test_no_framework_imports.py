from pathlib import Path

FORBIDDEN_TERMS = (
    "fastapi",
    "pydantic",
    "sqlalchemy",
    "openai",
    "anthropic",
    "requests",
    "httpx",
    "codex_apps",
    "mcp__codex_apps",
    "react",
    "vite",
    "browser",
)


def test_engine_modules_have_no_framework_provider_ui_or_app_connector_imports() -> None:
    engine_root = Path(__file__).parents[2] / "src" / "graygo_arena" / "engine"
    offenders: list[str] = []
    for path in sorted(engine_root.glob("*.py")):
        source = path.read_text(encoding="utf-8").lower()
        for term in FORBIDDEN_TERMS:
            if f"import {term}" in source or f"from {term}" in source:
                offenders.append(f"{path.name}: {term}")

    assert offenders == []
