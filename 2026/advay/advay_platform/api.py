"""FastAPI application factory for the current platform phase."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException, Response

from advay_platform.config import get_settings
from advay_platform.db.postgres import PostgresConnector
from advay_platform.errors import (
    MetricComputationError,
    MetricNotFoundError,
    UnsupportedFilterError,
    UnsupportedMetricError,
)
from advay_platform.health import build_health_payload, build_readiness_payload
from advay_platform.schemas.kpi import GetKPIRequest, GetKPIResponse
from advay_platform.tools.get_kpi import get_kpi


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

    @router.post("/tools/get-kpi", response_model=GetKPIResponse)
    def get_kpi_route(request: GetKPIRequest) -> GetKPIResponse:
        settings = get_settings()
        connector = PostgresConnector(settings.postgres_dsn)
        try:
            payload = get_kpi(
                connector=connector,
                metric_name=request.metric_name,
                period=request.period,
                filters=request.filters,
            )
        except UnsupportedMetricError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except UnsupportedFilterError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except MetricComputationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except MetricNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return GetKPIResponse(**payload)

    app.include_router(router)
    return app
