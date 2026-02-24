from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum, Index
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ReportType(PyEnum):
    consumption = "consumption"
    comparison = "comparison"


class ReportStatus(PyEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ComputationMode(PyEnum):
    direct_power = "direct_power"
    derived_single = "derived_single"
    derived_three = "derived_three"


class EnergyReport(Base):
    __tablename__ = "energy_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(36), unique=True, nullable=False)
    tenant_id = Column(String(50), nullable=False, index=True)
    report_type = Column(Enum(ReportType), nullable=False)
    status = Column(Enum(ReportStatus), default=ReportStatus.pending, nullable=False)
    params = Column(JSON, nullable=False)
    computation_mode = Column(Enum(ComputationMode), nullable=True)
    phase_type_used = Column(String(20), nullable=True)
    result_json = Column(JSON, nullable=True)
    s3_key = Column(String(500), nullable=True)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    progress = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_energy_reports_tenant_status", "tenant_id", "status"),
        Index("ix_energy_reports_tenant_type_created", "tenant_id", "report_type", "created_at"),
    )
