from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.models import ScheduledReport, ScheduledReportType, ScheduledFrequency

FREQUENCY_OFFSETS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}


class ScheduledRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_schedule(self, data: dict) -> ScheduledReport:
        freq = data["frequency"]
        offset = FREQUENCY_OFFSETS.get(freq, timedelta(days=1))
        
        schedule = ScheduledReport(
            schedule_id=str(uuid4()),
            tenant_id=data["tenant_id"],
            report_type=ScheduledReportType(data["report_type"]),
            frequency=ScheduledFrequency(data["frequency"]),
            params_template=data["params_template"],
            is_active=True,
            next_run_at=datetime.utcnow() + offset,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule
    
    async def get_schedule(self, schedule_id: str) -> Optional[ScheduledReport]:
        result = await self.db.execute(
            select(ScheduledReport).where(ScheduledReport.schedule_id == schedule_id)
        )
        return result.scalar_one_or_none()
    
    async def list_schedules(self, tenant_id: str) -> list[ScheduledReport]:
        result = await self.db.execute(
            select(ScheduledReport)
            .where(ScheduledReport.tenant_id == tenant_id)
            .order_by(ScheduledReport.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_due_schedules(self) -> list[ScheduledReport]:
        now = datetime.utcnow()
        result = await self.db.execute(
            select(ScheduledReport)
            .where(
                ScheduledReport.is_active == True,
                ScheduledReport.next_run_at <= now
            )
        )
        return list(result.scalars().all())
    
    async def update_schedule(
        self,
        schedule_id: str,
        **kwargs
    ) -> None:
        update_values = {k: v for k, v in kwargs.items() if v is not None}
        if "is_active" in update_values:
            update_values["updated_at"] = datetime.utcnow()
        await self.db.execute(
            update(ScheduledReport)
            .where(ScheduledReport.schedule_id == schedule_id)
            .values(**update_values)
        )
        await self.db.commit()
