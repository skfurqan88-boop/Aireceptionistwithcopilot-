"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class AvailabilityStatus(str, Enum):
    """Availability status enumeration"""
    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    TEMP_LOCKED = "TEMP_LOCKED"


class AppointmentStatusEnum(str, Enum):
    """Appointment status enumeration"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


# Request Schemas

class AvailabilityCheckRequest(BaseModel):
    """Request schema for availability check"""
    business_id: str = Field(..., description="Business ID")
    requested_datetime: datetime = Field(..., description="Requested appointment time (ISO format)")
    service_type: str = Field(..., description="Service type")
    customer_phone: Optional[str] = Field(None, description="Customer phone (for re-checking)")


class CreateLockRequest(BaseModel):
    """Request schema for creating a slot lock"""
    business_id: str = Field(..., description="Business ID")
    start_datetime: datetime = Field(..., description="Slot start time")
    service_type: str = Field(..., description="Service type")
    customer_phone: str = Field(..., description="Customer phone number")


class ConfirmAppointmentRequest(BaseModel):
    """Request schema for confirming an appointment"""
    business_id: str = Field(..., description="Business ID")
    lock_id: str = Field(..., description="Lock ID from slot lock")
    customer_name: str = Field(..., description="Customer name")
    customer_phone: str = Field(..., description="Customer phone number")
    service_type: str = Field(..., description="Service type")


class CancelAppointmentRequest(BaseModel):
    """Request schema for canceling an appointment"""
    appointment_id: str = Field(..., description="Appointment ID")
    customer_phone: str = Field(..., description="Customer phone number for verification")


# Response Schemas

class AvailabilityCheckResponse(BaseModel):
    """Response schema for availability check"""
    status: AvailabilityStatus = Field(..., description="Availability status")
    reason: Optional[str] = Field(None, description="Reason if not available")
    suggested_slots: List[datetime] = Field(default_factory=list, description="Alternative available slots")
    lock_id: Optional[str] = Field(None, description="Lock ID if slot was locked")
    expires_at: Optional[datetime] = Field(None, description="Lock expiration time")


class CreateLockResponse(BaseModel):
    """Response schema for lock creation"""
    success: bool = Field(..., description="Whether lock was created")
    lock_id: Optional[str] = Field(None, description="Lock ID")
    expires_at: Optional[datetime] = Field(None, description="Lock expiration time")
    reason: Optional[str] = Field(None, description="Reason if failed")


class ConfirmAppointmentResponse(BaseModel):
    """Response schema for appointment confirmation"""
    success: bool = Field(..., description="Whether appointment was confirmed")
    appointment_id: Optional[str] = Field(None, description="Appointment ID")
    start_datetime: Optional[datetime] = Field(None, description="Appointment start time")
    end_datetime: Optional[datetime] = Field(None, description="Appointment end time")
    reason: Optional[str] = Field(None, description="Reason if failed")


class CancelAppointmentResponse(BaseModel):
    """Response schema for appointment cancellation"""
    success: bool = Field(..., description="Whether appointment was cancelled")
    appointment_id: Optional[str] = Field(None, description="Appointment ID")
    reason: Optional[str] = Field(None, description="Reason if failed")


class AppointmentInfo(BaseModel):
    """Appointment information schema"""
    appointment_id: str
    business_id: str
    customer_name: str
    customer_phone: str
    service_type: str
    start_datetime: datetime
    end_datetime: datetime
    status: AppointmentStatusEnum
    created_at: datetime


class ListAppointmentsResponse(BaseModel):
    """Response schema for listing appointments"""
    appointments: List[AppointmentInfo]
    total: int


class SlotInfo(BaseModel):
    """Slot information for dashboard"""
    start_datetime: datetime
    end_datetime: datetime
    status: str  # "AVAILABLE", "LOCKED", "BOOKED"
    customer_phone: Optional[str] = None
    lock_expires_at: Optional[datetime] = None
    appointment_id: Optional[str] = None


class DashboardStatusResponse(BaseModel):
    """Response schema for dashboard status"""
    business_id: str
    active_locks_count: int
    confirmed_appointments_count: int
    today_appointments_count: int
    conversion_rate: float
    recent_slots: List[SlotInfo]
