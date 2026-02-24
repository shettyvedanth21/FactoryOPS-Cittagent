"""SQLAlchemy models for Device Service."""

from datetime import datetime, time, timezone, timedelta
from enum import Enum
from typing import Optional

from sqlalchemy import String, DateTime, Text, Integer, ForeignKey, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Configurable timeout threshold for telemetry (in seconds)
TELEMETRY_TIMEOUT_SECONDS = 60  # Device considered STOPPED if no telemetry for 60 seconds


class DeviceStatus(str, Enum):
    """Device status enumeration (LEGACY - for backward compatibility only)."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class RuntimeStatus(str, Enum):
    """Runtime status derived from telemetry activity."""
    RUNNING = "running"
    STOPPED = "stopped"


class PhaseType(str, Enum):
    """Electrical phase type for devices.
    
    Used for energy reporting to distinguish between:
    - single: Single-phase equipment
    - three: Three-phase equipment
    """
    SINGLE = "single"
    THREE = "three"


class Device(Base):
    """Device model representing IoT devices in the system.
    
    This model is designed to be multi-tenant ready. The tenant_id field
    is included for future multi-tenancy support but is nullable for Phase-1.
    
    Runtime status is computed dynamically based on last_seen_timestamp:
    - RUNNING: telemetry received within TELEMETRY_TIMEOUT_SECONDS
    - STOPPED: no telemetry received within TELEMETRY_TIMEOUT_SECONDS or never received
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
    
    # Phase type - electrical configuration for energy reporting
    # This is static metadata, not telemetry-derived
    phase_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True
    )
    
    # Legacy status field - DEPRECATED
    # This field is kept for backward compatibility only.
    # Do NOT use for runtime display - use get_runtime_status() instead.
    legacy_status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        index=True
    )
    
    # Last seen timestamp - tracks when telemetry was last received
    # This is the source of truth for runtime status
    last_seen_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    
    # Relationships
    shifts: Mapped[list["DeviceShift"]] = relationship(
        "DeviceShift", 
        back_populates="device", 
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    health_configs: Mapped[list["ParameterHealthConfig"]] = relationship(
        "ParameterHealthConfig",
        back_populates="device",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Device(device_id={self.device_id}, name={self.device_name}, type={self.device_type})>"
    
    @property
    def status(self) -> str:
        """Legacy status property for backward compatibility.
        
        DEPRECATED: Use get_runtime_status() instead.
        """
        return self.legacy_status
    
    @property
    def runtime_status(self) -> str:
        """Computed runtime status property for API responses.
        
        This is a computed property that returns the runtime status
        based on last_seen_timestamp. It is used by the ORM when
        serializing to JSON.
        """
        return self.get_runtime_status()
    
    def get_runtime_status(self) -> str:
        """Compute runtime status based on telemetry activity.
        
        Returns:
            'running' - if telemetry received within TELEMETRY_TIMEOUT_SECONDS
            'stopped' - if no telemetry received within TELEMETRY_TIMEOUT_SECONDS or never received
        """
        if self.last_seen_timestamp is None:
            return RuntimeStatus.STOPPED.value
        
        now = datetime.now(timezone.utc)
        
        # Handle naive datetime from database
        last_seen = self.last_seen_timestamp
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        
        time_diff = (now - last_seen).total_seconds()
        
        if time_diff <= TELEMETRY_TIMEOUT_SECONDS:
            return RuntimeStatus.RUNNING.value
        else:
            return RuntimeStatus.STOPPED.value
    
    def is_running(self) -> bool:
        """Check if device is currently running (receiving telemetry)."""
        return self.get_runtime_status() == RuntimeStatus.RUNNING.value
    
    def is_stopped(self) -> bool:
        """Check if device is currently stopped (not receiving telemetry)."""
        return self.get_runtime_status() == RuntimeStatus.STOPPED.value
    
    def update_last_seen(self) -> None:
        """Update last_seen_timestamp to current time.
        
        Called when telemetry is received for this device.
        """
        self.last_seen_timestamp = datetime.now(timezone.utc)


class DeviceShift(Base):
    """Shift configuration for device uptime calculation.
    
    Supports multiple shifts per day per device.
    Each shift has planned start/end times and optional maintenance break.
    """
    
    __tablename__ = "device_shifts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to device
    device_id: Mapped[str] = mapped_column(
        String(50), 
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Tenant for multi-tenancy
    tenant_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    # Shift identification
    shift_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Planned times (stored as time for date-agnostic scheduling)
    shift_start: Mapped[time] = mapped_column(Time, nullable=False)
    shift_end: Mapped[time] = mapped_column(Time, nullable=False)
    
    # Maintenance break duration in minutes
    maintenance_break_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Day of week (0=Monday, 6=Sunday). Null means all days.
    day_of_week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Active flag
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
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
    
    # Relationship
    device: Mapped["Device"] = relationship("Device", back_populates="shifts")
    
    def __repr__(self) -> str:
        return f"<DeviceShift(id={self.id}, device_id={self.device_id}, shift_name={self.shift_name})>"
    
    @property
    def planned_duration_minutes(self) -> int:
        """Calculate total planned shift duration in minutes."""
        start_minutes = self.shift_start.hour * 60 + self.shift_start.minute
        end_minutes = self.shift_end.hour * 60 + self.shift_end.minute
        
        if end_minutes <= start_minutes:
            # Shift crosses midnight
            end_minutes += 24 * 60
            
        return end_minutes - start_minutes
    
    @property
    def effective_runtime_minutes(self) -> int:
        """Calculate effective runtime after maintenance break."""
        return self.planned_duration_minutes - self.maintenance_break_minutes


class ParameterHealthConfig(Base):
    """Parameter health configuration for device health scoring.
    
    Each parameter can have configurable ranges and weights for health calculation.
    """
    
    __tablename__ = "parameter_health_config"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    device_id: Mapped[str] = mapped_column(
        String(50), 
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    tenant_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    parameter_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    normal_min: Mapped[Optional[float]] = mapped_column(nullable=True)
    normal_max: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    max_min: Mapped[Optional[float]] = mapped_column(nullable=True)
    max_max: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    weight: Mapped[float] = mapped_column(default=0.0, nullable=False)
    
    ignore_zero_value: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
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
    
    device: Mapped["Device"] = relationship("Device", back_populates="health_configs")
    
    def __repr__(self) -> str:
        return f"<ParameterHealthConfig(id={self.id}, device_id={self.device_id}, parameter={self.parameter_name})>"


class DeviceProperty(Base):
    """Dynamic device properties discovered from telemetry.
    
    This table stores the properties (fields) discovered from each device's
    telemetry data. Used for dynamic rule property selection.
    """
    
    __tablename__ = "device_properties"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    device_id: Mapped[str] = mapped_column(
        String(50), 
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    property_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    data_type: Mapped[str] = mapped_column(String(20), default="float", nullable=False)
    
    is_numeric: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    __table_args__ = (
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )
    
    def __repr__(self) -> str:
        return f"<DeviceProperty(device_id={self.device_id}, property={self.property_name})>"
