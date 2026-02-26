from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, model_validator


class DateRangeValidator(BaseModel):
    start_date: date
    end_date: date


class ConsumptionReportRequest(DateRangeValidator):
    device_ids: list[str]
    group_by: Literal["daily", "weekly"] = "daily"
    tenant_id: str


class ComparisonReportRequest(BaseModel):
    comparison_type: Literal["machine_vs_machine", "period_vs_period"]
    tenant_id: str
    machine_a_id: str | None = None
    machine_b_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    device_id: str | None = None
    period_a_start: date | None = None
    period_a_end: date | None = None
    period_b_start: date | None = None
    period_b_end: date | None = None

    @model_validator(mode="after")
    def validate_comparison(self):
        if self.comparison_type == "machine_vs_machine":
            if not self.machine_a_id or not self.machine_b_id:
                raise ValueError("machine_a_id and machine_b_id required")
            if self.machine_a_id == self.machine_b_id:
                raise ValueError("machine_a_id and machine_b_id must be different")
            if not self.start_date or not self.end_date:
                raise ValueError("start_date and end_date required for machine comparison")
        elif self.comparison_type == "period_vs_period":
            if not self.device_id:
                raise ValueError("device_id required for period comparison")
            if not all([self.period_a_start, self.period_a_end, self.period_b_start, self.period_b_end]):
                raise ValueError("period_a_start, period_a_end, period_b_start, period_b_end required")
            if self.period_a_start and self.period_a_end and self.period_b_start and self.period_b_end:
                a_len = (self.period_a_end - self.period_a_start).days
                b_len = (self.period_b_end - self.period_b_start).days
                if a_len != b_len:
                    raise ValueError(f"Periods must be equal length. A={a_len} days, B={b_len} days.")
        return self


class TariffRequest(BaseModel):
    tenant_id: str
    energy_rate_per_kwh: Decimal
    demand_charge_per_kw: Decimal = Decimal("0")
    reactive_penalty_rate: Decimal = Decimal("0")
    fixed_monthly_charge: Decimal = Decimal("0")
    power_factor_threshold: Decimal = Decimal("0.90")
    currency: str = "INR"
