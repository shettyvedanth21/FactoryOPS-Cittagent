from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Enum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ScheduledReportType(PyEnum):
    consumption = "consumption"
    comparison = "comparison"


class ScheduledFrequency(PyEnum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class ScheduledReport(Base):
    __tablename__ = "scheduled_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(String(36), unique=True, nullable=False)
    tenant_id = Column(String(50), nullable=False, index=True)
    report_type = Column(Enum(ScheduledReportType), nullable=False)
    frequency = Column(Enum(ScheduledFrequency), nullable=False)
    params_template = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    last_status = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    last_result_url = Column(String(2000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
