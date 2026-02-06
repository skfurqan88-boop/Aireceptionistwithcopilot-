"""
Main FastAPI application for AI Receptionist Appointment Booking System.

This module implements the API layer with strict separation of concerns:
- API endpoints handle HTTP concerns only
- Business logic is delegated to scheduling_engine and locking modules
- All responses are deterministic and based on database state
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
import uuid

from database import get_db, init_db
from models import BusinessSettings, Appointment, SlotLock, AppointmentStatus, LockState
from schemas import (
    AvailabilityCheckRequest, AvailabilityCheckResponse, AvailabilityStatus,
    CreateLockRequest, CreateLockResponse,
    ConfirmAppointmentRequest, ConfirmAppointmentResponse,
    CancelAppointmentRequest, CancelAppointmentResponse,
    ListAppointmentsResponse, AppointmentInfo, AppointmentStatusEnum,
    DashboardStatusResponse, SlotInfo
)
from scheduling_engine import (
    is_slot_available, generate_available_slots, calculate_time_window
)
from locking import (
    create_slot_lock, get_active_locks, cleanup_expired_locks,
    validate_lock_for_booking, convert_lock, get_customer_active_lock,
    release_customer_locks
)

# Initialize FastAPI app
app = FastAPI(
    title="AI Receptionist Appointment Booking System",
    description="Deterministic, production-grade appointment booking with AI conversation interface",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("Database initialized")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Receptionist Appointment Booking System",
        "version": "1.0.0"
    }


@app.post("/availability/check", response_model=AvailabilityCheckResponse)
async def check_availability(
    request: AvailabilityCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Check slot availability and suggest alternatives.
    
    This endpoint implements the strict availability algorithm:
    1. Validate business hours
    2. Check for appointment conflicts
    3. Check for active lock conflicts
    4. If available, create a temporary lock
    5. Return suggested slots if not available
    """
    # Cleanup expired locks first
    cleanup_expired_locks(db, request.business_id)
    
    # Get business settings
    business = db.query(BusinessSettings).filter(
        BusinessSettings.business_id == request.business_id
    ).first()
    
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # Get all appointments and locks
    appointments = db.query(Appointment).filter(
        Appointment.business_id == request.business_id,
        Appointment.status == AppointmentStatus.CONFIRMED
    ).all()
    
    locks = get_active_locks(db, request.business_id)
    
    # Check if slot is available
    is_available, reason = is_slot_available(
        business,
        request.requested_datetime,
        appointments,
        locks,
        customer_phone=request.customer_phone
    )
    
    if is_available:
        # Create slot lock
        start_dt, end_dt = calculate_time_window(
            request.requested_datetime,
            business.slot_duration_minutes,
            business.buffer_minutes
        )
        
        # Release any existing locks for this customer first
        if request.customer_phone:
            release_customer_locks(db, request.business_id, request.customer_phone)
        
        # Create new lock
        lock = create_slot_lock(
            db,
            request.business_id,
            start_dt,
            end_dt,
            request.customer_phone or "UNKNOWN"
        )
        
        return AvailabilityCheckResponse(
            status=AvailabilityStatus.AVAILABLE,
            reason=None,
            suggested_slots=[],
            lock_id=lock.lock_id,
            expires_at=lock.expires_at
        )
    else:
        # Generate suggested slots
        suggested = generate_available_slots(
            business,
            request.requested_datetime,
            appointments,
            locks,
            num_slots=5
        )
        
        # Determine status
        availability_status = (
            AvailabilityStatus.TEMP_LOCKED if reason == "TEMPORARILY_LOCKED"
            else AvailabilityStatus.NOT_AVAILABLE
        )
        
        return AvailabilityCheckResponse(
            status=availability_status,
            reason=reason,
            suggested_slots=suggested,
            lock_id=None,
            expires_at=None
        )


@app.post("/locks/create", response_model=CreateLockResponse)
async def create_lock(
    request: CreateLockRequest,
    db: Session = Depends(get_db)
):
    """
    Create a temporary slot lock.
    
    This is typically called by the AI layer after confirming user intent.
    """
    # Get business settings
    business = db.query(BusinessSettings).filter(
        BusinessSettings.business_id == request.business_id
    ).first()
    
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # Calculate time window
    start_dt, end_dt = calculate_time_window(
        request.start_datetime,
        business.slot_duration_minutes,
        business.buffer_minutes
    )
    
    # Check availability
    appointments = db.query(Appointment).filter(
        Appointment.business_id == request.business_id,
        Appointment.status == AppointmentStatus.CONFIRMED
    ).all()
    
    locks = get_active_locks(db, request.business_id)
    
    is_available, reason = is_slot_available(
        business,
        request.start_datetime,
        appointments,
        locks,
        customer_phone=request.customer_phone
    )
    
    if not is_available:
        return CreateLockResponse(
            success=False,
            lock_id=None,
            expires_at=None,
            reason=reason
        )
    
    # Release any existing locks for this customer
    release_customer_locks(db, request.business_id, request.customer_phone)
    
    # Create lock
    lock = create_slot_lock(
        db,
        request.business_id,
        start_dt,
        end_dt,
        request.customer_phone
    )
    
    return CreateLockResponse(
        success=True,
        lock_id=lock.lock_id,
        expires_at=lock.expires_at,
        reason=None
    )


@app.post("/appointments/confirm", response_model=ConfirmAppointmentResponse)
async def confirm_appointment(
    request: ConfirmAppointmentRequest,
    db: Session = Depends(get_db)
):
    """
    Confirm an appointment booking.
    
    This endpoint converts a slot lock into a confirmed appointment.
    It's the only way to create a confirmed booking.
    """
    # Validate lock
    is_valid, lock, reason = validate_lock_for_booking(
        db,
        request.lock_id,
        request.customer_phone
    )
    
    if not is_valid:
        return ConfirmAppointmentResponse(
            success=False,
            appointment_id=None,
            start_datetime=None,
            end_datetime=None,
            reason=reason
        )
    
    # Double-check availability (defensive programming)
    business = db.query(BusinessSettings).filter(
        BusinessSettings.business_id == request.business_id
    ).first()
    
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    appointments = db.query(Appointment).filter(
        Appointment.business_id == request.business_id,
        Appointment.status == AppointmentStatus.CONFIRMED
    ).all()
    
    other_locks = [l for l in get_active_locks(db, request.business_id) 
                   if l.lock_id != request.lock_id]
    
    is_available, avail_reason = is_slot_available(
        business,
        lock.start_datetime,
        appointments,
        other_locks,
        customer_phone=request.customer_phone
    )
    
    if not is_available:
        return ConfirmAppointmentResponse(
            success=False,
            appointment_id=None,
            start_datetime=None,
            end_datetime=None,
            reason=f"SLOT_NO_LONGER_AVAILABLE: {avail_reason}"
        )
    
    # Create appointment
    appointment_id = str(uuid.uuid4())
    
    appointment = Appointment(
        appointment_id=appointment_id,
        business_id=request.business_id,
        customer_name=request.customer_name,
        customer_phone=request.customer_phone,
        service_type=request.service_type,
        start_datetime=lock.start_datetime,
        end_datetime=lock.end_datetime,
        status=AppointmentStatus.CONFIRMED
    )
    
    db.add(appointment)
    
    # Convert lock
    convert_lock(db, lock)
    
    db.commit()
    db.refresh(appointment)
    
    return ConfirmAppointmentResponse(
        success=True,
        appointment_id=appointment.appointment_id,
        start_datetime=appointment.start_datetime,
        end_datetime=appointment.end_datetime,
        reason=None
    )


@app.post("/appointments/cancel", response_model=CancelAppointmentResponse)
async def cancel_appointment(
    request: CancelAppointmentRequest,
    db: Session = Depends(get_db)
):
    """
    Cancel an appointment.
    
    This releases the slot for rebooking.
    """
    appointment = db.query(Appointment).filter(
        Appointment.appointment_id == request.appointment_id
    ).first()
    
    if not appointment:
        return CancelAppointmentResponse(
            success=False,
            appointment_id=None,
            reason="APPOINTMENT_NOT_FOUND"
        )
    
    # Verify customer phone
    if appointment.customer_phone != request.customer_phone:
        return CancelAppointmentResponse(
            success=False,
            appointment_id=None,
            reason="PHONE_MISMATCH"
        )
    
    # Check if already cancelled
    if appointment.status == AppointmentStatus.CANCELLED:
        return CancelAppointmentResponse(
            success=False,
            appointment_id=appointment.appointment_id,
            reason="ALREADY_CANCELLED"
        )
    
    # Cancel appointment
    appointment.status = AppointmentStatus.CANCELLED
    appointment.updated_at = datetime.utcnow()
    
    db.commit()
    
    return CancelAppointmentResponse(
        success=True,
        appointment_id=appointment.appointment_id,
        reason=None
    )


@app.get("/appointments/list", response_model=ListAppointmentsResponse)
async def list_appointments(
    business_id: str,
    status: str = None,
    from_date: datetime = None,
    to_date: datetime = None,
    db: Session = Depends(get_db)
):
    """
    List appointments for a business.
    """
    query = db.query(Appointment).filter(
        Appointment.business_id == business_id
    )
    
    if status:
        query = query.filter(Appointment.status == AppointmentStatus[status])
    
    if from_date:
        query = query.filter(Appointment.start_datetime >= from_date)
    
    if to_date:
        query = query.filter(Appointment.start_datetime <= to_date)
    
    appointments = query.order_by(Appointment.start_datetime).all()
    
    appointment_infos = [
        AppointmentInfo(
            appointment_id=apt.appointment_id,
            business_id=apt.business_id,
            customer_name=apt.customer_name,
            customer_phone=apt.customer_phone,
            service_type=apt.service_type,
            start_datetime=apt.start_datetime,
            end_datetime=apt.end_datetime,
            status=AppointmentStatusEnum[apt.status.value],
            created_at=apt.created_at
        )
        for apt in appointments
    ]
    
    return ListAppointmentsResponse(
        appointments=appointment_infos,
        total=len(appointment_infos)
    )


@app.get("/dashboard/status", response_model=DashboardStatusResponse)
async def get_dashboard_status(
    business_id: str,
    db: Session = Depends(get_db)
):
    """
    Get dashboard status including real-time slot states.
    """
    # Cleanup expired locks
    cleanup_expired_locks(db, business_id)
    
    # Get active locks
    active_locks = get_active_locks(db, business_id)
    
    # Get confirmed appointments
    confirmed_appointments = db.query(Appointment).filter(
        Appointment.business_id == business_id,
        Appointment.status == AppointmentStatus.CONFIRMED
    ).all()
    
    # Get today's appointments
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    today_appointments = db.query(Appointment).filter(
        Appointment.business_id == business_id,
        Appointment.status == AppointmentStatus.CONFIRMED,
        Appointment.start_datetime >= today_start,
        Appointment.start_datetime < today_end
    ).count()
    
    # Calculate conversion rate
    total_locks = db.query(SlotLock).filter(
        SlotLock.business_id == business_id
    ).count()
    
    converted_locks = db.query(SlotLock).filter(
        SlotLock.business_id == business_id,
        SlotLock.state == LockState.CONVERTED
    ).count()
    
    conversion_rate = (converted_locks / total_locks * 100) if total_locks > 0 else 0.0
    
    # Build recent slots info
    recent_slots: List[SlotInfo] = []
    
    # Add active locks
    for lock in active_locks[:5]:
        recent_slots.append(SlotInfo(
            start_datetime=lock.start_datetime,
            end_datetime=lock.end_datetime,
            status="LOCKED",
            customer_phone=lock.customer_phone,
            lock_expires_at=lock.expires_at,
            appointment_id=None
        ))
    
    # Add today's appointments
    for apt in confirmed_appointments[:5]:
        if apt.start_datetime >= today_start and apt.start_datetime < today_end:
            recent_slots.append(SlotInfo(
                start_datetime=apt.start_datetime,
                end_datetime=apt.end_datetime,
                status="BOOKED",
                customer_phone=apt.customer_phone,
                lock_expires_at=None,
                appointment_id=apt.appointment_id
            ))
    
    # Sort by start time
    recent_slots.sort(key=lambda x: x.start_datetime)
    
    return DashboardStatusResponse(
        business_id=business_id,
        active_locks_count=len(active_locks),
        confirmed_appointments_count=len(confirmed_appointments),
        today_appointments_count=today_appointments,
        conversion_rate=conversion_rate,
        recent_slots=recent_slots[:10]
    )


@app.post("/admin/business/setup")
async def setup_business(
    business_id: str,
    opening_time: str = "09:00",
    closing_time: str = "17:00",
    slot_duration_minutes: int = 30,
    buffer_minutes: int = 15,
    timezone: str = "UTC",
    db: Session = Depends(get_db)
):
    """
    Setup or update business settings.
    
    This is an admin endpoint for initializing business configuration.
    """
    existing = db.query(BusinessSettings).filter(
        BusinessSettings.business_id == business_id
    ).first()
    
    if existing:
        existing.opening_time = opening_time
        existing.closing_time = closing_time
        existing.slot_duration_minutes = slot_duration_minutes
        existing.buffer_minutes = buffer_minutes
        existing.timezone = timezone
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        business = existing
    else:
        business = BusinessSettings(
            business_id=business_id,
            opening_time=opening_time,
            closing_time=closing_time,
            slot_duration_minutes=slot_duration_minutes,
            buffer_minutes=buffer_minutes,
            timezone=timezone
        )
        db.add(business)
        db.commit()
        db.refresh(business)
    
    return {
        "success": True,
        "business_id": business.business_id,
        "settings": {
            "opening_time": business.opening_time,
            "closing_time": business.closing_time,
            "slot_duration_minutes": business.slot_duration_minutes,
            "buffer_minutes": business.buffer_minutes,
            "timezone": business.timezone
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
