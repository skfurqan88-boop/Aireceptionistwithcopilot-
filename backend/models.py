"""
Database models for the AI Receptionist Appointment Booking System.

This module defines the core data models:
- BusinessSettings: Business configuration and hours
- Appointments: Confirmed appointments
- SlotLocks: Temporary locks during booking process
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
import enum

Base = declarative_base()


def get_utc_now():
    """Get current UTC time as timezone-aware datetime"""
    return datetime.now(timezone.utc)


class AppointmentStatus(enum.Enum):
    """Appointment status enumeration"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class LockState(enum.Enum):
    """Slot lock state enumeration"""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CONVERTED = "CONVERTED"


class BusinessSettings(Base):
    """
    Business configuration table.
    Defines working hours, slot durations, and booking constraints.
    """
    __tablename__ = "business_settings"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(String, unique=True, nullable=False, index=True)
    opening_time = Column(String, nullable=False)  # Format: "09:00"
    closing_time = Column(String, nullable=False)  # Format: "17:00"
    slot_duration_minutes = Column(Integer, nullable=False, default=30)
    buffer_minutes = Column(Integer, nullable=False, default=15)
    max_parallel_bookings = Column(Integer, nullable=False, default=1)
    timezone = Column(String, nullable=False, default="UTC")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)


class Appointment(Base):
    """
    Appointments table.
    Stores all confirmed and cancelled appointments.
    """
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(String, unique=True, nullable=False, index=True)
    business_id = Column(String, nullable=False, index=True)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False, index=True)
    service_type = Column(String, nullable=False)
    start_datetime = Column(DateTime, nullable=False, index=True)
    end_datetime = Column(DateTime, nullable=False, index=True)
    status = Column(SQLEnum(AppointmentStatus), nullable=False, default=AppointmentStatus.PENDING)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Composite index for efficient overlap queries
    __table_args__ = (
        Index('idx_business_time_status', 'business_id', 'start_datetime', 'end_datetime', 'status'),
    )


class SlotLock(Base):
    """
    Slot locks table.
    Temporary locks to prevent double booking during the conversation/booking process.
    """
    __tablename__ = "slot_locks"

    id = Column(Integer, primary_key=True, index=True)
    lock_id = Column(String, unique=True, nullable=False, index=True)
    business_id = Column(String, nullable=False, index=True)
    start_datetime = Column(DateTime, nullable=False, index=True)
    end_datetime = Column(DateTime, nullable=False, index=True)
    customer_phone = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    state = Column(SQLEnum(LockState), nullable=False, default=LockState.ACTIVE)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Composite index for efficient lock queries
    __table_args__ = (
        Index('idx_business_time_state', 'business_id', 'start_datetime', 'end_datetime', 'state'),
        Index('idx_expires_state', 'expires_at', 'state'),
    )
