"""Schemas for deterministic KPI tool requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GetKPIRequest(BaseModel):
    metric_name: str
    period: str
    filters: dict[str, str] = Field(default_factory=dict)


class GetKPIResponse(BaseModel):
    metric_name: str
    value: float
    unit: str
    dataset_version: str
    computed_at: datetime
    freshness_status: str
