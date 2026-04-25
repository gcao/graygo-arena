"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from graygo_arena.api.routes import AppServices, build_router, create_services


def create_app(services: AppServices | None = None) -> FastAPI:
    app = FastAPI(title="Gray Go Arena", version="0.1.0")
    app.state.services = services or create_services()
    app.include_router(build_router(app.state.services))
    return app


app = create_app()
