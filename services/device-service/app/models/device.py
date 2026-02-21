"""SQLAlchemy models for Device Service."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DeviceStatus(str, Enum):
    """Device status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class Device(Base):
    """Device model representing IoT devices in the system.
    
    This model is designed to be multi-tenant ready. The tenant_id field
    is included for future multi-tenant support but is nullable for Phase-1.
    """
    
    __tablename__ = "devices"
    
    # Primary key - using business key for device_id
    device_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    
    # Multi-tenant support (nullable for Phase-1)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    # Device metadata
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    device_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Device status
    status: Mapped[DeviceStatus] = mapped_column(
        String(50),
        default=DeviceStatus.ACTIVE,
        nullable=False,
        index=True
    )
    
    # Extended metadata as JSON (for future extensibility)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Soft delete support (for future)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<Device(device_id={self.device_id}, name={self.device_name}, type={self.device_type})>"
    
    def is_active(self) -> bool:
        """Check if device is in active status."""
        return self.status == DeviceStatus.ACTIVE and self.deleted_at is None
