from typing import Any
from pydantic import BaseModel


class ReportResponse(BaseModel):
    report_id: str
    status: str
    created_at: str


class ReportResultResponse(BaseModel):
    report_id: str
    status: str
    result: dict | None
    error_code: str | None
    error_message: str | None
    created_at: str
    completed_at: str | None


class TariffResponse(BaseModel):
    tenant_id: str
    energy_rate_per_kwh: float
    demand_charge_per_kw: float
    reactive_penalty_rate: float
    fixed_monthly_charge: float
    power_factor_threshold: float
    currency: str


class ErrorResponse(BaseModel):
    error: str
    message: str
