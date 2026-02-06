"""
Core Scheduling Engine - Pure Logic Layer

This module implements the deterministic scheduling algorithm:
1. Time normalization to business timezone
2. Business hours validation
3. Overlap detection with confirmed appointments
4. Overlap detection with active locks
5. Available slot generation

NO AI LOGIC ALLOWED IN THIS MODULE.
All functions are stateless and deterministic.
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import pytz
from models import BusinessSettings, Appointment, SlotLock, AppointmentStatus, LockState


def normalize_datetime_to_timezone(dt: datetime, timezone: str) -> datetime:
    """
    Normalize a datetime to the business timezone.
    
    Args:
        dt: DateTime to normalize (assumes UTC if naive)
        timezone: Target timezone (e.g., "America/New_York")
    
    Returns:
        DateTime in the target timezone
    """
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = pytz.utc.localize(dt)
    
    target_tz = pytz.timezone(timezone)
    return dt.astimezone(target_tz)


def is_within_business_hours(
    dt: datetime,
    opening_time: str,
    closing_time: str,
    timezone: str
) -> bool:
    """
    Check if a datetime falls within business hours.
    
    Args:
        dt: DateTime to check
        opening_time: Opening time (format: "HH:MM")
        closing_time: Closing time (format: "HH:MM")
        timezone: Business timezone
    
    Returns:
        True if within business hours, False otherwise
    """
    # Normalize to business timezone
    local_dt = normalize_datetime_to_timezone(dt, timezone)
    
    # Parse opening and closing times
    open_hour, open_minute = map(int, opening_time.split(':'))
    close_hour, close_minute = map(int, closing_time.split(':'))
    
    # Create datetime objects for opening and closing on the same day
    opening_dt = local_dt.replace(hour=open_hour, minute=open_minute, second=0, microsecond=0)
    closing_dt = local_dt.replace(hour=close_hour, minute=close_minute, second=0, microsecond=0)
    
    return opening_dt <= local_dt < closing_dt


def check_overlap(
    start1: datetime,
    end1: datetime,
    start2: datetime,
    end2: datetime
) -> bool:
    """
    Check if two time ranges overlap.
    
    Overlap logic: start1 < end2 AND end1 > start2
    
    Args:
        start1: Start of first range
        end1: End of first range
        start2: Start of second range
        end2: End of second range
    
    Returns:
        True if ranges overlap, False otherwise
    """
    return start1 < end2 and end1 > start2


def calculate_time_window(
    start_datetime: datetime,
    slot_duration_minutes: int,
    buffer_minutes: int
) -> Tuple[datetime, datetime]:
    """
    Calculate the full time window including buffer time.
    
    Args:
        start_datetime: Requested start time
        slot_duration_minutes: Duration of the appointment
        buffer_minutes: Buffer time before next appointment
    
    Returns:
        Tuple of (start_datetime, end_datetime_with_buffer)
    """
    slot_end = start_datetime + timedelta(minutes=slot_duration_minutes)
    window_end = slot_end + timedelta(minutes=buffer_minutes)
    return start_datetime, window_end


def check_confirmed_appointments_overlap(
    business_id: str,
    start_datetime: datetime,
    end_datetime: datetime,
    appointments: List[Appointment]
) -> bool:
    """
    Check if the requested time overlaps with any confirmed appointments.
    
    Args:
        business_id: Business ID
        start_datetime: Start of requested slot
        end_datetime: End of requested slot (including buffer)
        appointments: List of appointments to check
    
    Returns:
        True if there's an overlap, False otherwise
    """
    for appointment in appointments:
        # Only check confirmed appointments
        if appointment.status != AppointmentStatus.CONFIRMED:
            continue
        
        # Check for overlap
        if check_overlap(start_datetime, end_datetime, 
                        appointment.start_datetime, appointment.end_datetime):
            return True
    
    return False


def check_active_locks_overlap(
    business_id: str,
    start_datetime: datetime,
    end_datetime: datetime,
    locks: List[SlotLock],
    exclude_customer_phone: Optional[str] = None
) -> bool:
    """
    Check if the requested time overlaps with any active locks.
    
    Args:
        business_id: Business ID
        start_datetime: Start of requested slot
        end_datetime: End of requested slot (including buffer)
        locks: List of slot locks to check
        exclude_customer_phone: Phone number to exclude (for same customer re-checking)
    
    Returns:
        True if there's an overlap with another customer's lock, False otherwise
    """
    now = datetime.utcnow()
    
    for lock in locks:
        # Skip if expired
        if lock.expires_at < now:
            continue
        
        # Skip if not active
        if lock.state != LockState.ACTIVE:
            continue
        
        # Skip if same customer
        if exclude_customer_phone and lock.customer_phone == exclude_customer_phone:
            continue
        
        # Check for overlap
        if check_overlap(start_datetime, end_datetime,
                        lock.start_datetime, lock.end_datetime):
            return True
    
    return False


def generate_available_slots(
    business_settings: BusinessSettings,
    date: datetime,
    appointments: List[Appointment],
    locks: List[SlotLock],
    num_slots: int = 5
) -> List[datetime]:
    """
    Generate a list of available time slots for a given date.
    
    Args:
        business_settings: Business configuration
        date: Date to generate slots for
        appointments: List of all appointments
        locks: List of all locks
        num_slots: Number of slots to return
    
    Returns:
        List of available start times
    """
    available_slots = []
    
    # Normalize date to business timezone
    local_date = normalize_datetime_to_timezone(date, business_settings.timezone)
    
    # Parse opening and closing times
    open_hour, open_minute = map(int, business_settings.opening_time.split(':'))
    close_hour, close_minute = map(int, business_settings.closing_time.split(':'))
    
    # Start from opening time
    current_time = local_date.replace(hour=open_hour, minute=open_minute, second=0, microsecond=0)
    closing_time = local_date.replace(hour=close_hour, minute=close_minute, second=0, microsecond=0)
    
    # Calculate slot increment (no overlap in slot generation)
    slot_increment = timedelta(minutes=business_settings.slot_duration_minutes)
    
    while current_time < closing_time and len(available_slots) < num_slots:
        # Calculate time window with buffer
        start_dt, end_dt = calculate_time_window(
            current_time,
            business_settings.slot_duration_minutes,
            business_settings.buffer_minutes
        )
        
        # Check if slot end is within business hours
        if end_dt > closing_time:
            break
        
        # Check for conflicts
        has_appointment_conflict = check_confirmed_appointments_overlap(
            business_settings.business_id,
            start_dt,
            end_dt,
            appointments
        )
        
        has_lock_conflict = check_active_locks_overlap(
            business_settings.business_id,
            start_dt,
            end_dt,
            locks
        )
        
        # If no conflicts, add to available slots
        if not has_appointment_conflict and not has_lock_conflict:
            # Convert to UTC for storage
            utc_time = current_time.astimezone(pytz.utc)
            available_slots.append(utc_time)
        
        # Move to next slot
        current_time += slot_increment
    
    return available_slots


def is_slot_available(
    business_settings: BusinessSettings,
    requested_datetime: datetime,
    appointments: List[Appointment],
    locks: List[SlotLock],
    customer_phone: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Check if a specific slot is available.
    
    This is the core availability check function implementing the strict algorithm:
    1. Normalize requested time to business timezone
    2. Reject if outside working hours
    3. Generate time window including buffer
    4. Check confirmed appointments for overlap
    5. Check active slot locks for overlap
    
    Args:
        business_settings: Business configuration
        requested_datetime: Requested appointment time
        appointments: List of all appointments
        locks: List of all locks
        customer_phone: Customer phone (to allow re-checking same customer's lock)
    
    Returns:
        Tuple of (is_available: bool, reason: str)
    """
    # Step 1: Normalize to business timezone
    local_dt = normalize_datetime_to_timezone(requested_datetime, business_settings.timezone)
    
    # Step 2: Check business hours
    if not is_within_business_hours(
        local_dt,
        business_settings.opening_time,
        business_settings.closing_time,
        business_settings.timezone
    ):
        return False, "OUTSIDE_BUSINESS_HOURS"
    
    # Step 3: Calculate time window with buffer
    start_dt, end_dt = calculate_time_window(
        requested_datetime,
        business_settings.slot_duration_minutes,
        business_settings.buffer_minutes
    )
    
    # Check if appointment end is within business hours
    if not is_within_business_hours(
        end_dt,
        business_settings.opening_time,
        business_settings.closing_time,
        business_settings.timezone
    ):
        return False, "EXTENDS_BEYOND_BUSINESS_HOURS"
    
    # Step 4: Check confirmed appointments
    if check_confirmed_appointments_overlap(
        business_settings.business_id,
        start_dt,
        end_dt,
        appointments
    ):
        return False, "CONFLICTS_WITH_APPOINTMENT"
    
    # Step 5: Check active locks
    if check_active_locks_overlap(
        business_settings.business_id,
        start_dt,
        end_dt,
        locks,
        exclude_customer_phone=customer_phone
    ):
        return False, "TEMPORARILY_LOCKED"
    
    return True, "AVAILABLE"
