"""
Database initialization script for production deployment.

This script creates the database tables and initializes default business settings.
"""
import sys
from database import init_db, get_db
from models import BusinessSettings

def initialize_database(
    business_id: str = "default",
    opening_time: str = "09:00",
    closing_time: str = "17:00",
    slot_duration_minutes: int = 30,
    buffer_minutes: int = 15,
    timezone: str = "UTC"
):
    """
    Initialize the database with default settings.
    
    Args:
        business_id: Unique business identifier
        opening_time: Business opening time (HH:MM format)
        closing_time: Business closing time (HH:MM format)
        slot_duration_minutes: Duration of each appointment slot
        buffer_minutes: Buffer time between appointments
        timezone: Business timezone (e.g., "America/New_York")
    """
    print("Initializing database...")
    
    # Create tables
    init_db()
    print("✓ Database tables created")
    
    # Check if business already exists
    db = next(get_db())
    existing = db.query(BusinessSettings).filter(
        BusinessSettings.business_id == business_id
    ).first()
    
    if existing:
        print(f"✓ Business '{business_id}' already exists")
        print(f"  Opening: {existing.opening_time}")
        print(f"  Closing: {existing.closing_time}")
        print(f"  Timezone: {existing.timezone}")
        return
    
    # Create default business
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
    
    print(f"✓ Business '{business_id}' created successfully")
    print(f"  Opening: {opening_time}")
    print(f"  Closing: {closing_time}")
    print(f"  Slot duration: {slot_duration_minutes} minutes")
    print(f"  Buffer time: {buffer_minutes} minutes")
    print(f"  Timezone: {timezone}")
    
    db.close()
    print("\n✓ Database initialization complete!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize the appointment booking database")
    parser.add_argument("--business-id", default="default", help="Business ID (default: default)")
    parser.add_argument("--opening-time", default="09:00", help="Opening time in HH:MM format (default: 09:00)")
    parser.add_argument("--closing-time", default="17:00", help="Closing time in HH:MM format (default: 17:00)")
    parser.add_argument("--slot-duration", type=int, default=30, help="Slot duration in minutes (default: 30)")
    parser.add_argument("--buffer-minutes", type=int, default=15, help="Buffer time in minutes (default: 15)")
    parser.add_argument("--timezone", default="UTC", help="Business timezone (default: UTC)")
    
    args = parser.parse_args()
    
    try:
        initialize_database(
            business_id=args.business_id,
            opening_time=args.opening_time,
            closing_time=args.closing_time,
            slot_duration_minutes=args.slot_duration,
            buffer_minutes=args.buffer_minutes,
            timezone=args.timezone
        )
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
