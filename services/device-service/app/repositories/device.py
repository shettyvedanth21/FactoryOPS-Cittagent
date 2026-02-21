"""Device repository layer - data access abstraction."""

from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device


class DeviceRepository:
    """Repository for Device entity operations.
    
    Implements repository pattern for clean separation between
    data access and business logic layers.
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def create(self, device: Device) -> Device:
        """Create a new device in the database."""
        self._session.add(device)
        await self._session.flush()
        await self._session.refresh(device)
        return device
    
    async def get_by_id(
        self, 
        device_id: str, 
        tenant_id: Optional[str] = None
    ) -> Optional[Device]:
        """Get device by ID with optional tenant filtering."""
        query = select(Device).where(Device.device_id == device_id)
        
        # Apply tenant filter if provided (for future multi-tenancy)
        if tenant_id is not None:
            query = query.where(Device.tenant_id == tenant_id)
        
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
    
    async def list_devices(
        self,
        tenant_id: Optional[str] = None,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Device], int]:
        """List devices with filtering and pagination.
        
        Returns:
            Tuple of (devices list, total count)
        """
        # Build base query
        query = select(Device).where(Device.deleted_at.is_(None))
        count_query = select(func.count(Device.device_id)).where(Device.deleted_at.is_(None))
        
        # Apply filters
        if tenant_id is not None:
            query = query.where(Device.tenant_id == tenant_id)
            count_query = count_query.where(Device.tenant_id == tenant_id)
        
        if device_type:
            query = query.where(Device.device_type == device_type)
            count_query = count_query.where(Device.device_type == device_type)
        
        if status:
            query = query.where(Device.status == status)
            count_query = count_query.where(Device.status == status)
        
        # Get total count
        count_result = await self._session.execute(count_query)
        total = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = await self._session.execute(query)
        devices = result.scalars().all()
        
        return list(devices), total
    
    async def update(self, device: Device) -> Device:
        """Update an existing device."""
        await self._session.flush()
        await self._session.refresh(device)
        return device
    
    async def delete(self, device: Device, soft: bool = True) -> None:
        """Delete a device (soft or hard delete)."""
        if soft:
            from datetime import datetime
            device.deleted_at = datetime.utcnow()
            await self._session.flush()
        else:
            await self._session.delete(device)
            await self._session.flush()
    
    async def exists(self, device_id: str) -> bool:
        """Check if a device with given ID exists."""
        query = select(func.count(Device.device_id)).where(
            Device.device_id == device_id,
            Device.deleted_at.is_(None)
        )
        result = await self._session.execute(query)
        return result.scalar() > 0
