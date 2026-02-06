"""
Locking & Conflict Control Layer

This module handles:
- Slot lock creation with TTL
- Lock expiration and cleanup
- Concurrent access protection
- Lock state transitions

This layer prevents race conditions and ensures atomic operations.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid
from models import SlotLock, LockState, Appointment, AppointmentStatus
from scheduling_engine import calculate_time_window


LOCK_TTL_SECONDS = 180  # 3 minutes


def create_slot_lock(
    db: Session,
    business_id: str,
    start_datetime: datetime,
    end_datetime: datetime,
    customer_phone: str
) -> SlotLock:
    """
    Create a new slot lock with TTL.
    
    This function is atomic and thread-safe when used with proper database isolation.
    
    Args:
        db: Database session
        business_id: Business ID
        start_datetime: Start of the slot
        end_datetime: End of the slot (including buffer)
        customer_phone: Customer phone number
    
    Returns:
        Created SlotLock instance
    """
    lock_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(seconds=LOCK_TTL_SECONDS)
    
    lock = SlotLock(
        lock_id=lock_id,
        business_id=business_id,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        customer_phone=customer_phone,
        expires_at=expires_at,
        state=LockState.ACTIVE
    )
    
    db.add(lock)
    db.commit()
    db.refresh(lock)
    
    return lock


def get_active_locks(
    db: Session,
    business_id: str,
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None
) -> list[SlotLock]:
    """
    Get all active (non-expired) locks for a business.
    
    Args:
        db: Database session
        business_id: Business ID
        start_datetime: Optional start time filter
        end_datetime: Optional end time filter
    
    Returns:
        List of active SlotLock instances
    """
    now = datetime.utcnow()
    
    query = db.query(SlotLock).filter(
        and_(
            SlotLock.business_id == business_id,
            SlotLock.state == LockState.ACTIVE,
            SlotLock.expires_at > now
        )
    )
    
    # Add time range filter if provided
    if start_datetime and end_datetime:
        query = query.filter(
            or_(
                and_(
                    SlotLock.start_datetime < end_datetime,
                    SlotLock.end_datetime > start_datetime
                )
            )
        )
    
    return query.all()


def get_customer_active_lock(
    db: Session,
    business_id: str,
    customer_phone: str
) -> Optional[SlotLock]:
    """
    Get the active lock for a specific customer.
    
    Args:
        db: Database session
        business_id: Business ID
        customer_phone: Customer phone number
    
    Returns:
        Active SlotLock if exists, None otherwise
    """
    now = datetime.utcnow()
    
    return db.query(SlotLock).filter(
        and_(
            SlotLock.business_id == business_id,
            SlotLock.customer_phone == customer_phone,
            SlotLock.state == LockState.ACTIVE,
            SlotLock.expires_at > now
        )
    ).first()


def expire_lock(db: Session, lock: SlotLock) -> None:
    """
    Mark a lock as expired.
    
    Args:
        db: Database session
        lock: SlotLock to expire
    """
    lock.state = LockState.EXPIRED
    lock.updated_at = datetime.utcnow()
    db.commit()


def convert_lock(db: Session, lock: SlotLock) -> None:
    """
    Mark a lock as converted (booking confirmed).
    
    Args:
        db: Database session
        lock: SlotLock to convert
    """
    lock.state = LockState.CONVERTED
    lock.updated_at = datetime.utcnow()
    db.commit()


def cleanup_expired_locks(db: Session, business_id: Optional[str] = None) -> int:
    """
    Clean up expired locks by marking them as EXPIRED.
    
    This function should be run periodically (e.g., via background task).
    
    Args:
        db: Database session
        business_id: Optional business ID filter
    
    Returns:
        Number of locks cleaned up
    """
    now = datetime.utcnow()
    
    query = db.query(SlotLock).filter(
        and_(
            SlotLock.state == LockState.ACTIVE,
            SlotLock.expires_at <= now
        )
    )
    
    if business_id:
        query = query.filter(SlotLock.business_id == business_id)
    
    expired_locks = query.all()
    count = len(expired_locks)
    
    for lock in expired_locks:
        lock.state = LockState.EXPIRED
        lock.updated_at = datetime.utcnow()
    
    db.commit()
    
    return count


def refresh_lock(db: Session, lock: SlotLock) -> SlotLock:
    """
    Refresh a lock's expiration time.
    
    Args:
        db: Database session
        lock: SlotLock to refresh
    
    Returns:
        Updated SlotLock instance
    """
    lock.expires_at = datetime.utcnow() + timedelta(seconds=LOCK_TTL_SECONDS)
    lock.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lock)
    
    return lock


def release_customer_locks(db: Session, business_id: str, customer_phone: str) -> int:
    """
    Release all locks for a specific customer (mark as expired).
    
    Args:
        db: Database session
        business_id: Business ID
        customer_phone: Customer phone number
    
    Returns:
        Number of locks released
    """
    locks = db.query(SlotLock).filter(
        and_(
            SlotLock.business_id == business_id,
            SlotLock.customer_phone == customer_phone,
            SlotLock.state == LockState.ACTIVE
        )
    ).all()
    
    count = len(locks)
    
    for lock in locks:
        lock.state = LockState.EXPIRED
        lock.updated_at = datetime.utcnow()
    
    db.commit()
    
    return count


def validate_lock_for_booking(
    db: Session,
    lock_id: str,
    customer_phone: str
) -> Tuple[bool, Optional[SlotLock], str]:
    """
    Validate that a lock is valid for booking confirmation.
    
    Checks:
    1. Lock exists
    2. Lock belongs to the customer
    3. Lock is active
    4. Lock has not expired
    
    Args:
        db: Database session
        lock_id: Lock ID
        customer_phone: Customer phone number
    
    Returns:
        Tuple of (is_valid: bool, lock: Optional[SlotLock], reason: str)
    """
    lock = db.query(SlotLock).filter(SlotLock.lock_id == lock_id).first()
    
    if not lock:
        return False, None, "LOCK_NOT_FOUND"
    
    if lock.customer_phone != customer_phone:
        return False, None, "LOCK_BELONGS_TO_DIFFERENT_CUSTOMER"
    
    if lock.state != LockState.ACTIVE:
        return False, None, f"LOCK_STATE_IS_{lock.state.value}"
    
    now = datetime.utcnow()
    if lock.expires_at <= now:
        return False, None, "LOCK_EXPIRED"
    
    return True, lock, "VALID"
