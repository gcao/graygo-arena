"""Environment-driven backend settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(".runtime/graygo.db")


def load_settings() -> Settings:
    database_path = Path(os.environ.get("GRAYGO_DATABASE_PATH", ".runtime/graygo.db"))
    return Settings(database_path=database_path)
