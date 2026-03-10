"""FastAPI application factory for Phase 1."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Response, status

from advay_platform.config import get_settings
from advay_platform.health import build_health_payload, build_readiness_payload


def create_app() -> FastAPI:
    app = FastAPI(title="Advay Platform API", version="0.1.0")
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        return build_health_payload(get_settings())

    @router.get("/ready")
    def ready(response: Response) -> dict[str, object]:
        payload, status_code = build_readiness_payload(get_settings())
        response.status_code = status_code
        return payload

    app.include_router(router)
    return app
