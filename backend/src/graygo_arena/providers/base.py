"""Provider metadata contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    provider: str
    auth_type: str
    configured: bool
    models: tuple[str, ...]


@dataclass(frozen=True)
class ProviderTestResult:
    provider: str
    model: str
    ok: bool
    message: str
