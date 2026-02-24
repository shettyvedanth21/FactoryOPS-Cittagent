from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.requests import TariffRequest
from src.schemas.responses import TariffResponse
from src.repositories.tariff_repository import TariffRepository

router = APIRouter(tags=["tariffs"])


@router.post("/", response_model=TariffResponse)
async def create_or_update_tariff(
    request: TariffRequest,
    db: AsyncSession = Depends(get_db)
):
    repo = TariffRepository(db)
    
    tariff = await repo.upsert_tariff(
        tenant_id=request.tenant_id,
        data=request.model_dump()
    )
    
    return TariffResponse(
        tenant_id=tariff.tenant_id,
        energy_rate_per_kwh=float(tariff.energy_rate_per_kwh),
        demand_charge_per_kw=float(tariff.demand_charge_per_kw),
        reactive_penalty_rate=float(tariff.reactive_penalty_rate),
        fixed_monthly_charge=float(tariff.fixed_monthly_charge),
        power_factor_threshold=float(tariff.power_factor_threshold),
        currency=str(tariff.currency)
    )


@router.get("/{tenant_id}", response_model=TariffResponse)
async def get_tariff(
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    repo = TariffRepository(db)
    tariff = await repo.get_tariff(tenant_id)
    
    if not tariff:
        raise HTTPException(status_code=404, detail="Tariff not found for tenant")
    
    return TariffResponse(
        tenant_id=tariff.tenant_id,
        energy_rate_per_kwh=float(tariff.energy_rate_per_kwh),
        demand_charge_per_kw=float(tariff.demand_charge_per_kw),
        reactive_penalty_rate=float(tariff.reactive_penalty_rate),
        fixed_monthly_charge=float(tariff.fixed_monthly_charge),
        power_factor_threshold=float(tariff.power_factor_threshold),
        currency=str(tariff.currency)
    )
