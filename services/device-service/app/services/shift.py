"""Shift service layer - business logic for shift management and uptime calculation."""

from typing import Optional, List
from datetime import datetime, time as time_type

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError

from app.models.device import DeviceShift, Device
from app.schemas.device import ShiftCreate, ShiftUpdate
import logging

logger = logging.getLogger(__name__)


class ShiftService:
    """Service layer for shift management and uptime calculation."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def create_shift(self, shift_data: ShiftCreate) -> DeviceShift:
        """Create a new shift configuration for a device.
        
        Args:
            shift_data: Shift creation data
            
        Returns:
            Created DeviceShift instance
        """
        # Verify device exists
        result = await self._session.execute(
            select(Device).where(Device.device_id == shift_data.device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise ValueError(f"Device '{shift_data.device_id}' not found")
        
        # Validate shift times
        if shift_data.shift_start == shift_data.shift_end:
            raise ValueError("Shift start and end times cannot be the same")
        
        # Create shift
        shift = DeviceShift(
            device_id=shift_data.device_id,
            tenant_id=shift_data.tenant_id,
            shift_name=shift_data.shift_name,
            shift_start=shift_data.shift_start,
            shift_end=shift_data.shift_end,
            maintenance_break_minutes=shift_data.maintenance_break_minutes,
            day_of_week=shift_data.day_of_week,
            is_active=shift_data.is_active,
        )
        
        self._session.add(shift)
        
        try:
            await self._session.commit()
            await self._session.refresh(shift)
            logger.info(
                "Shift created successfully",
                extra={
                    "shift_id": shift.id,
                    "device_id": shift.device_id,
                    "shift_name": shift.shift_name,
                }
            )
        except IntegrityError as e:
            await self._session.rollback()
            logger.error("Failed to create shift", extra={"error": str(e)})
            raise
        
        return shift
    
    async def get_shifts_by_device(
        self, 
        device_id: str, 
        tenant_id: Optional[str] = None
    ) -> List[DeviceShift]:
        """Get all shifts for a device.
        
        Args:
            device_id: Device ID
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            List of DeviceShift instances
        """
        query = select(DeviceShift).where(DeviceShift.device_id == device_id)
        
        if tenant_id:
            query = query.where(DeviceShift.tenant_id == tenant_id)
        
        query = query.order_by(DeviceShift.shift_start)
        
        result = await self._session.execute(query)
        return list(result.scalars().all())
    
    async def get_shift(
        self, 
        shift_id: int, 
        device_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[DeviceShift]:
        """Get a specific shift by ID.
        
        Args:
            shift_id: Shift ID
            device_id: Device ID
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            DeviceShift instance or None
        """
        query = select(DeviceShift).where(
            DeviceShift.id == shift_id,
            DeviceShift.device_id == device_id
        )
        
        if tenant_id:
            query = query.where(DeviceShift.tenant_id == tenant_id)
        
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
    
    async def update_shift(
        self,
        shift_id: int,
        device_id: str,
        tenant_id: Optional[str],
        shift_data: ShiftUpdate
    ) -> Optional[DeviceShift]:
        """Update an existing shift.
        
        Args:
            shift_id: Shift ID
            device_id: Device ID
            tenant_id: Optional tenant ID for filtering
            shift_data: Update data
            
        Returns:
            Updated DeviceShift instance or None
        """
        shift = await self.get_shift(shift_id, device_id, tenant_id)
        
        if not shift:
            return None
        
        # Update fields
        update_data = shift_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(shift, field, value)
        
        # Validate shift times if updated
        if shift.shift_start == shift.shift_end:
            raise ValueError("Shift start and end times cannot be the same")
        
        try:
            await self._session.commit()
            await self._session.refresh(shift)
            logger.info(
                "Shift updated successfully",
                extra={"shift_id": shift.id}
            )
        except IntegrityError as e:
            await self._session.rollback()
            logger.error("Failed to update shift", extra={"error": str(e)})
            raise
        
        return shift
    
    async def delete_shift(
        self,
        shift_id: int,
        device_id: str,
        tenant_id: Optional[str]
    ) -> bool:
        """Delete a shift.
        
        Args:
            shift_id: Shift ID
            device_id: Device ID
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            True if deleted, False if not found
        """
        shift = await self.get_shift(shift_id, device_id, tenant_id)
        
        if not shift:
            return False
        
        await self._session.delete(shift)
        await self._session.commit()
        
        logger.info(
            "Shift deleted successfully",
            extra={"shift_id": shift_id}
        )
        
        return True
    
    async def calculate_uptime(
        self,
        device_id: str,
        tenant_id: Optional[str] = None
    ) -> dict:
        """Calculate uptime based on configured shifts.
        
        Formula:
        Uptime % = ((Actual Run Duration - Maintenance Break) / (Shift Duration - Maintenance Break)) × 100
        
        For now, calculates potential uptime based on configured shifts.
        Actual runtime would require telemetry data with device on/off status.
        
        Args:
            device_id: Device ID
            tenant_id: Optional tenant ID for filtering
            
        Returns:
            Dictionary with uptime calculation results
        """
        shifts = await self.get_shifts_by_device(device_id, tenant_id)
        
        if not shifts:
            return {
                "device_id": device_id,
                "uptime_percentage": None,
                "total_planned_minutes": 0,
                "total_effective_minutes": 0,
                "shifts_configured": 0,
                "message": "No shifts configured. Please configure shifts to calculate uptime.",
            }
        
        active_shifts = [s for s in shifts if s.is_active]
        
        if not active_shifts:
            return {
                "device_id": device_id,
                "uptime_percentage": None,
                "total_planned_minutes": 0,
                "total_effective_minutes": 0,
                "shifts_configured": len(shifts),
                "message": "No active shifts configured. Please activate at least one shift.",
            }
        
        total_planned = 0
        total_effective = 0
        
        for shift in active_shifts:
            total_planned += shift.planned_duration_minutes
            total_effective += shift.effective_runtime_minutes
        
        # Calculate uptime percentage
        if total_planned > 0:
            uptime_percentage = (total_effective / total_planned) * 100
        else:
            uptime_percentage = 0.0
        
        return {
            "device_id": device_id,
            "uptime_percentage": round(uptime_percentage, 2),
            "total_planned_minutes": total_planned,
            "total_effective_minutes": total_effective,
            "shifts_configured": len(active_shifts),
            "message": f"Uptime calculated based on {len(active_shifts)} active shift(s)",
        }
