"""Local trust guardrail checks."""

from __future__ import annotations

import json
from dataclasses import dataclass

from graygo_arena.application.export import SECRET_PATTERN, build_export_bundle
from graygo_arena.application.models import GameRepository
from graygo_arena.providers.registry import ProviderCatalog


@dataclass(frozen=True)
class GuardrailCheck:
    name: str
    ok: bool
    detail: str


def run_guardrails(
    repository: GameRepository,
    providers: ProviderCatalog,
    game_id: str,
) -> tuple[GuardrailCheck, ...]:
    bundle = build_export_bundle(repository, game_id)
    serialized = json.dumps(bundle)
    provider_metadata = json.dumps([provider.__dict__ for provider in providers.list_providers()])
    transcripts = repository.list_transcripts(game_id, "debug")
    seats = repository.get_seats(game_id)
    views = {entry.view for entry in transcripts}
    return (
        GuardrailCheck(
            name="secret_values_absent",
            ok=SECRET_PATTERN.search(serialized) is None,
            detail=(
                "No raw OpenAI/Anthropic-looking keys or token values found in exportable records."
            ),
        ),
        GuardrailCheck(
            name="credential_refs_only",
            ok=all(SECRET_PATTERN.search(seat.credential_ref) is None for seat in seats),
            detail="Seat sessions store credential references rather than key values.",
        ),
        GuardrailCheck(
            name="transcript_views_separated",
            ok=views.issuperset({"public", "black_private", "white_private"}) if views else True,
            detail="Transcript records retain distinct public and seat-private views.",
        ),
        GuardrailCheck(
            name="provider_settings_safe",
            ok=SECRET_PATTERN.search(provider_metadata) is None,
            detail=(
                "Provider settings expose aliases, auth type, configured status, and models only."
            ),
        ),
    )
