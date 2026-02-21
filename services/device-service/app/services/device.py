"""Device service layer - business logic."""

from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device, DeviceStatus
from app.repositories.device import DeviceRepository
from app.schemas.device import DeviceCreate, DeviceUpdate
import logging

logger = logging.getLogger(__name__)


class DeviceService:
    """Service layer for device management business logic.
    
    This service encapsulates all business rules and operations
    related to device management, providing a clean API for
    the HTTP handlers.
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repository = DeviceRepository(session)
    
    async def create_device(self, device_data: DeviceCreate) -> Device:
        """Create a new device.
        
        Args:
            device_data: Device creation data
            
        Returns:
            Created Device instance
            
        Raises:
            ValueError: If device with same ID already exists
        """
        # Check for duplicate device ID
        if await self._repository.exists(device_data.device_id):
            logger.warning(
                "Attempted to create device with existing ID",
                extra={"device_id": device_data.device_id}
            )
            raise ValueError(f"Device with ID '{device_data.device_id}' already exists")
        
        # Create device entity
        device = Device(
            device_id=device_data.device_id,
            tenant_id=device_data.tenant_id,
            device_name=device_data.device_name,
            device_type=device_data.device_type,
            manufacturer=device_data.manufacturer,
            model=device_data.model,
            location=device_data.location,
            status=DeviceStatus(device_data.status),
            metadata_json=device_data.metadata_json,
        )
        
        # Persist to database
        created_device = await self._repository.create(device)
        await self._session.commit()
        
        logger.info(
            "Device created successfully",
            extra={
                "device_id": created_device.device_id,
                "device_type": created_device.device_type,
            }
        )
        
        return created_device
    
    async def get_device(
        self, 
        device_id: str, 
        tenant_id: Optional[str] = None
    ) -> Optional[Device]:
        """Get device by ID.
        
        Args:
            device_id: Device identifier
            tenant_id: Optional tenant ID for multi-tenancy
            
        Returns:
            Device instance or None if not found
        """
        return await self._repository.get_by_id(device_id, tenant_id)
    
    async def list_devices(
        self,
        tenant_id: Optional[str] = None,
        device_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Device], int]:
        """List devices with filtering and pagination.
        
        Args:
            tenant_id: Optional tenant filter
            device_type: Optional device type filter
            status: Optional status filter
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            Tuple of (devices list, total count)
        """
        return await self._repository.list_devices(
            tenant_id=tenant_id,
            device_type=device_type,
            status=status,
            page=page,
            page_size=page_size,
        )
    
    async def update_device(
        self,
        device_id: str,
        device_data: DeviceUpdate,
        tenant_id: Optional[str] = None,
    ) -> Optional[Device]:
        """Update an existing device.
        
        Args:
            device_id: Device identifier
            device_data: Update data
            tenant_id: Optional tenant ID for multi-tenancy
            
        Returns:
            Updated Device instance or None if not found
        """
        # Fetch existing device
        device = await self._repository.get_by_id(device_id, tenant_id)
        if not device:
            logger.warning(
                "Attempted to update non-existent device",
                extra={"device_id": device_id}
            )
            return None
        
        # Update only provided fields
        update_data = device_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "status" and value:
                value = DeviceStatus(value)
            setattr(device, field, value)
        
        # Persist changes
        updated_device = await self._repository.update(device)
        await self._session.commit()
        
        logger.info(
            "Device updated successfully",
            extra={"device_id": updated_device.device_id}
        )
        
        return updated_device
    
    async def delete_device(
        self,
        device_id: str,
        tenant_id: Optional[str] = None,
        soft: bool = True,
    ) -> bool:
        """Delete a device.
        
        Args:
            device_id: Device identifier
            tenant_id: Optional tenant ID for multi-tenancy
            soft: If True, performs soft delete; otherwise hard delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        device = await self._repository.get_by_id(device_id, tenant_id)
        if not device:
            return False
        
        await self._repository.delete(device, soft=soft)
        await self._session.commit()
        
        logger.info(
            "Device deleted successfully",
            extra={
                "device_id": device_id,
                "soft_delete": soft,
            }
        )
        
        return True
