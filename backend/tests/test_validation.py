"""
Validation tests for the AI Receptionist Appointment Booking System.

These tests validate the core requirements:
1. Parallel booking attempts for same slot (double booking prevention)
2. Expired lock reclaiming slot
3. Booking after cancellation
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import threading
import time

from main import app, get_db
from models import Base, BusinessSettings, Appointment, SlotLock
from database import get_db as get_db_original


def get_utc_now():
    """Get current UTC time as timezone-aware datetime"""
    return datetime.now(timezone.utc)


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_appointments.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """Setup test database before each test"""
    Base.metadata.create_all(bind=engine)
    
    # Create test business
    db = TestingSessionLocal()
    business = BusinessSettings(
        business_id="test_business",
        opening_time="09:00",
        closing_time="17:00",
        slot_duration_minutes=30,
        buffer_minutes=15,
        timezone="UTC"
    )
    db.add(business)
    db.commit()
    db.close()
    
    yield
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


def test_parallel_booking_same_slot(setup_database):
    """
    TEST 1: Two callers requesting same slot simultaneously.
    
    EXPECTED: Only one booking succeeds, the other gets rejected or offered alternatives.
    This validates that double booking is mathematically impossible.
    """
    # Get a future time slot
    request_time = get_utc_now() + timedelta(hours=2)
    request_time = request_time.replace(minute=0, second=0, microsecond=0)
    
    results = []
    
    def book_slot(customer_id: str):
        """Attempt to book a slot"""
        # Step 1: Check availability
        response1 = client.post("/availability/check", json={
            "business_id": "test_business",
            "requested_datetime": request_time.isoformat(),
            "service_type": "Haircut",
            "customer_phone": f"+1234567890{customer_id}"
        })
        
        result = {
            "customer_id": customer_id,
            "availability_check": response1.json(),
            "confirmation": None
        }
        
        if response1.status_code == 200 and response1.json().get("status") == "AVAILABLE":
            lock_id = response1.json().get("lock_id")
            
            # Small delay to simulate real-world scenario
            time.sleep(0.1)
            
            # Step 2: Confirm booking
            response2 = client.post("/appointments/confirm", json={
                "business_id": "test_business",
                "lock_id": lock_id,
                "customer_name": f"Customer {customer_id}",
                "customer_phone": f"+1234567890{customer_id}",
                "service_type": "Haircut"
            })
            
            result["confirmation"] = response2.json()
        
        results.append(result)
    
    # Create two threads to simulate parallel requests
    thread1 = threading.Thread(target=book_slot, args=("1",))
    thread2 = threading.Thread(target=book_slot, args=("2",))
    
    # Start both threads simultaneously
    thread1.start()
    thread2.start()
    
    # Wait for both to complete
    thread1.join()
    thread2.join()
    
    # Validate results
    assert len(results) == 2
    
    successful_bookings = [
        r for r in results 
        if r["confirmation"] and r["confirmation"].get("success") == True
    ]
    
    # CRITICAL: Only ONE booking should succeed
    assert len(successful_bookings) == 1, f"Expected 1 successful booking, got {len(successful_bookings)}"
    
    print("✓ TEST 1 PASSED: Parallel booking prevention works correctly")
    print(f"  Customer {successful_bookings[0]['customer_id']} got the slot")
    print(f"  Customer {[r['customer_id'] for r in results if r not in successful_bookings][0]} was correctly rejected")


def test_expired_lock_reclaiming(setup_database):
    """
    TEST 2: Expired lock reclaiming slot.
    
    EXPECTED: After a lock expires, the slot becomes available again.
    """
    # Get a future time slot
    request_time = get_utc_now() + timedelta(hours=3)
    request_time = request_time.replace(minute=0, second=0, microsecond=0)
    
    # Customer 1 checks availability (creates lock)
    response1 = client.post("/availability/check", json={
        "business_id": "test_business",
        "requested_datetime": request_time.isoformat(),
        "service_type": "Haircut",
        "customer_phone": "+1111111111"
    })
    
    assert response1.status_code == 200
    assert response1.json()["status"] == "AVAILABLE"
    lock_id = response1.json()["lock_id"]
    
    # Customer 2 tries immediately (should be locked)
    response2 = client.post("/availability/check", json={
        "business_id": "test_business",
        "requested_datetime": request_time.isoformat(),
        "service_type": "Haircut",
        "customer_phone": "+2222222222"
    })
    
    assert response2.status_code == 200
    # Should either be temp_locked or not_available
    assert response2.json()["status"] in ["TEMP_LOCKED", "NOT_AVAILABLE"]
    
    # Manually expire the lock (simulate time passing)
    db = TestingSessionLocal()
    lock = db.query(SlotLock).filter(SlotLock.lock_id == lock_id).first()
    lock.expires_at = get_utc_now() - timedelta(seconds=1)
    db.commit()
    db.close()
    
    # Customer 2 tries again (should be available now)
    response3 = client.post("/availability/check", json={
        "business_id": "test_business",
        "requested_datetime": request_time.isoformat(),
        "service_type": "Haircut",
        "customer_phone": "+2222222222"
    })
    
    assert response3.status_code == 200
    assert response3.json()["status"] == "AVAILABLE"
    
    print("✓ TEST 2 PASSED: Expired lock reclaiming works correctly")
    print("  Lock expired and slot became available again")


def test_booking_after_cancellation(setup_database):
    """
    TEST 3: Booking after cancellation.
    
    EXPECTED: After cancellation, the slot becomes available for rebooking.
    """
    # Get a future time slot
    request_time = get_utc_now() + timedelta(hours=4)
    request_time = request_time.replace(minute=0, second=0, microsecond=0)
    
    # Customer 1 books a slot
    response1 = client.post("/availability/check", json={
        "business_id": "test_business",
        "requested_datetime": request_time.isoformat(),
        "service_type": "Haircut",
        "customer_phone": "+3333333333"
    })
    
    assert response1.status_code == 200
    assert response1.json()["status"] == "AVAILABLE"
    lock_id = response1.json()["lock_id"]
    
    response2 = client.post("/appointments/confirm", json={
        "business_id": "test_business",
        "lock_id": lock_id,
        "customer_name": "Customer 1",
        "customer_phone": "+3333333333",
        "service_type": "Haircut"
    })
    
    assert response2.status_code == 200
    assert response2.json()["success"] == True
    appointment_id = response2.json()["appointment_id"]
    
    # Customer 2 tries to book same slot (should fail)
    response3 = client.post("/availability/check", json={
        "business_id": "test_business",
        "requested_datetime": request_time.isoformat(),
        "service_type": "Haircut",
        "customer_phone": "+4444444444"
    })
    
    assert response3.status_code == 200
    assert response3.json()["status"] == "NOT_AVAILABLE"
    
    # Customer 1 cancels
    response4 = client.post("/appointments/cancel", json={
        "appointment_id": appointment_id,
        "customer_phone": "+3333333333"
    })
    
    assert response4.status_code == 200
    assert response4.json()["success"] == True
    
    # Customer 2 tries again (should be available now)
    response5 = client.post("/availability/check", json={
        "business_id": "test_business",
        "requested_datetime": request_time.isoformat(),
        "service_type": "Haircut",
        "customer_phone": "+4444444444"
    })
    
    assert response5.status_code == 200
    assert response5.json()["status"] == "AVAILABLE"
    
    print("✓ TEST 3 PASSED: Booking after cancellation works correctly")
    print("  Slot became available after cancellation")


def test_buffer_time_collision(setup_database):
    """
    TEST 4: Buffer time collisions.
    
    EXPECTED: Appointments respect buffer time between slots.
    """
    base_time = get_utc_now() + timedelta(hours=5)
    base_time = base_time.replace(minute=0, second=0, microsecond=0)
    
    # Book first slot
    response1 = client.post("/availability/check", json={
        "business_id": "test_business",
        "requested_datetime": base_time.isoformat(),
        "service_type": "Haircut",
        "customer_phone": "+5555555555"
    })
    
    assert response1.json()["status"] == "AVAILABLE"
    
    response2 = client.post("/appointments/confirm", json={
        "business_id": "test_business",
        "lock_id": response1.json()["lock_id"],
        "customer_name": "Customer 1",
        "customer_phone": "+5555555555",
        "service_type": "Haircut"
    })
    
    assert response2.json()["success"] == True
    
    # Try to book 30 minutes later (should fail due to buffer)
    # First appointment: 30 min slot + 15 min buffer = 45 minutes total
    next_time = base_time + timedelta(minutes=30)
    
    response3 = client.post("/availability/check", json={
        "business_id": "test_business",
        "requested_datetime": next_time.isoformat(),
        "service_type": "Haircut",
        "customer_phone": "+6666666666"
    })
    
    # Should not be available due to buffer
    assert response3.json()["status"] == "NOT_AVAILABLE"
    
    # Try 45 minutes later (should be available)
    next_time_2 = base_time + timedelta(minutes=45)
    
    response4 = client.post("/availability/check", json={
        "business_id": "test_business",
        "requested_datetime": next_time_2.isoformat(),
        "service_type": "Haircut",
        "customer_phone": "+6666666666"
    })
    
    assert response4.json()["status"] == "AVAILABLE"
    
    print("✓ TEST 4 PASSED: Buffer time collision prevention works correctly")
    print("  Buffer time is properly enforced between appointments")


def test_business_hours_validation(setup_database):
    """
    TEST 5: Business hours validation.
    
    EXPECTED: Appointments outside business hours are rejected.
    """
    # Try to book before opening (8 AM when business opens at 9 AM)
    before_opening = get_utc_now().replace(hour=8, minute=0, second=0, microsecond=0)
    if before_opening < get_utc_now():
        before_opening += timedelta(days=1)
    
    response1 = client.post("/availability/check", json={
        "business_id": "test_business",
        "requested_datetime": before_opening.isoformat(),
        "service_type": "Haircut",
        "customer_phone": "+7777777777"
    })
    
    assert response1.json()["status"] == "NOT_AVAILABLE"
    assert "BUSINESS_HOURS" in response1.json()["reason"]
    
    # Try to book after closing (5 PM when business closes at 5 PM)
    after_closing = get_utc_now().replace(hour=17, minute=0, second=0, microsecond=0)
    if after_closing < get_utc_now():
        after_closing += timedelta(days=1)
    
    response2 = client.post("/availability/check", json={
        "business_id": "test_business",
        "requested_datetime": after_closing.isoformat(),
        "service_type": "Haircut",
        "customer_phone": "+7777777777"
    })
    
    assert response2.json()["status"] == "NOT_AVAILABLE"
    
    print("✓ TEST 5 PASSED: Business hours validation works correctly")
    print("  Appointments outside business hours are rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
