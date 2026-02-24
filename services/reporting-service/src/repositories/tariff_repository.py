from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models import TenantTariff


class TariffRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_tariff(self, tenant_id: str) -> Optional[TenantTariff]:
        result = await self.db.execute(
            select(TenantTariff).where(TenantTariff.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    async def upsert_tariff(
        self,
        tenant_id: str,
        data: dict
    ) -> TenantTariff:
        existing = await self.get_tariff(tenant_id)
        
        if existing:
            existing.energy_rate_per_kwh = float(data.get("energy_rate_per_kwh", 0))
            existing.demand_charge_per_kw = float(data.get("demand_charge_per_kw", 0))
            existing.reactive_penalty_rate = float(data.get("reactive_penalty_rate", 0))
            existing.fixed_monthly_charge = float(data.get("fixed_monthly_charge", 0))
            existing.power_factor_threshold = float(data.get("power_factor_threshold", 0.90))
            existing.currency = data.get("currency", "INR")
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        else:
            tariff = TenantTariff(
                tenant_id=tenant_id,
                energy_rate_per_kwh=float(data.get("energy_rate_per_kwh", 0)),
                demand_charge_per_kw=float(data.get("demand_charge_per_kw", 0)),
                reactive_penalty_rate=float(data.get("reactive_penalty_rate", 0)),
                fixed_monthly_charge=float(data.get("fixed_monthly_charge", 0)),
                power_factor_threshold=float(data.get("power_factor_threshold", 0.90)),
                currency=data.get("currency", "INR"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.db.add(tariff)
            await self.db.commit()
            await self.db.refresh(tariff)
            return tariff
