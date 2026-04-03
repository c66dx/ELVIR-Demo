"""Esquemas de respuesta para endpoints /health (OpenAPI y validación)."""

from typing import Literal

from pydantic import BaseModel, Field


def _default_live_checks() -> dict[str, Literal["ok"]]:
    return {"process": "ok"}


class HealthSummaryResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "elvir-api"
    version: str


class HealthLiveResponse(BaseModel):
    status: Literal["ok"] = "ok"
    checks: dict[str, Literal["ok"]] = Field(
        default_factory=_default_live_checks,
        description="Comprobaciones sin dependencias externas.",
    )


class HealthReadyOk(BaseModel):
    status: Literal["ok"] = "ok"
    checks: dict[str, Literal["ok"]]


class HealthReadyFailure(BaseModel):
    status: Literal["error"] = "error"
    checks: dict[str, Literal["down"]]


class HealthMetricsResponse(BaseModel):
    metrics: dict[str, int | float]
    thresholds: dict[str, float | int]
    alerts: dict[str, bool]


class RootMessage(BaseModel):
    message: str
    docs: str
