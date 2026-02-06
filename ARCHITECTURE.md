# System Architecture

## Overview

The AI Receptionist Appointment Booking System is a deterministic, production-grade system that ensures double booking is mathematically impossible. It follows a strict layered architecture where AI is the interface and the system is the authority.

## Architecture Layers

### 1. Conversation Layer (AI)
**Location:** `backend/ai_layer.py`

**Responsibilities:**
- Collects user intent through natural conversation
- Interfaces with Azure OpenAI for conversation management
- **NEVER decides availability**
- **NEVER confirms bookings independently**

**Key Rules:**
- Always calls `availability/check` before offering any time
- Never assumes availability
- If slot is locked, offers nearest available slots
- Never says "booked" until confirm API succeeds

### 2. Scheduling Engine (Pure Logic)
**Location:** `backend/scheduling_engine.py`

**Responsibilities:**
- Time normalization to business timezone
- Business hours validation
- Overlap detection with appointments
- Overlap detection with locks
- Available slot generation

**Key Features:**
- Stateless, deterministic functions
- No AI logic allowed
- Pure computational logic only
- Mathematical correctness guaranteed

**Core Algorithm:**
```python
1. Normalize requested time to business timezone
2. Reject if outside working hours
3. Generate time window including buffer
4. Check confirmed appointments for overlap
5. Check active slot locks for overlap
6. Return AVAILABLE only if all checks pass
```

**Overlap Detection:**
Uses the mathematical formula: `start1 < end2 AND end1 > start2`

### 3. Locking & Conflict Control Layer
**Location:** `backend/locking.py`

**Responsibilities:**
- Creates slot locks with 180-second TTL
- Manages lock expiration
- Handles concurrent access
- Prevents race conditions

**Key Features:**
- Atomic lock creation
- Automatic expiration
- Thread-safe operations
- Lock state transitions (ACTIVE → EXPIRED | CONVERTED)

### 4. Persistence Layer
**Location:** `backend/models.py`, `backend/database.py`

**Responsibilities:**
- Source of truth for all bookings
- Stores business settings, appointments, locks
- Ensures data consistency
- Provides transaction support

## Data Models

### BusinessSettings
```python
- business_id: Unique identifier
- opening_time: "HH:MM"
- closing_time: "HH:MM"
- slot_duration_minutes: Duration per appointment
- buffer_minutes: Time between appointments
- max_parallel_bookings: Concurrent booking limit
- timezone: Business timezone (e.g., "America/New_York")
```

### Appointment
```python
- appointment_id: Unique identifier
- business_id: Business reference
- customer_name: Customer full name
- customer_phone: Contact number
- service_type: Service requested
- start_datetime: Appointment start (UTC)
- end_datetime: Appointment end with buffer (UTC)
- status: PENDING | CONFIRMED | CANCELLED
```

### SlotLock
```python
- lock_id: Unique identifier
- business_id: Business reference
- start_datetime: Slot start (UTC)
- end_datetime: Slot end with buffer (UTC)
- customer_phone: Customer phone
- expires_at: Expiration time (UTC)
- state: ACTIVE | EXPIRED | CONVERTED
```

## API Contracts

### POST /availability/check
**Purpose:** Check if a slot is available and create a temporary lock

**Request:**
```json
{
  "business_id": "string",
  "requested_datetime": "ISO 8601 datetime",
  "service_type": "string",
  "customer_phone": "string (optional)"
}
```

**Response:**
```json
{
  "status": "AVAILABLE | NOT_AVAILABLE | TEMP_LOCKED",
  "reason": "string (if not available)",
  "suggested_slots": ["ISO 8601 datetime"],
  "lock_id": "string (if available)",
  "expires_at": "ISO 8601 datetime (if available)"
}
```

### POST /appointments/confirm
**Purpose:** Convert a slot lock into a confirmed appointment

**Request:**
```json
{
  "business_id": "string",
  "lock_id": "string",
  "customer_name": "string",
  "customer_phone": "string",
  "service_type": "string"
}
```

**Response:**
```json
{
  "success": true/false,
  "appointment_id": "string",
  "start_datetime": "ISO 8601 datetime",
  "end_datetime": "ISO 8601 datetime",
  "reason": "string (if failed)"
}
```

### POST /appointments/cancel
**Purpose:** Cancel a confirmed appointment

**Request:**
```json
{
  "appointment_id": "string",
  "customer_phone": "string"
}
```

**Response:**
```json
{
  "success": true/false,
  "appointment_id": "string",
  "reason": "string (if failed)"
}
```

## Edge Cases Handled

1. **Parallel Booking Attempts**
   - Two customers request same slot simultaneously
   - Lock mechanism ensures only one gets the slot
   - Second customer receives alternative suggestions

2. **Expired Locks**
   - Locks automatically expire after 180 seconds
   - Expired locks are cleaned up
   - Slots become available again after expiration

3. **Buffer Time Collisions**
   - Buffer time is included in overlap calculation
   - Prevents appointments from being too close
   - Ensures adequate time between services

4. **Business Hours**
   - All times normalized to business timezone
   - Appointments outside hours rejected
   - Appointments extending beyond closing rejected

5. **Cancellations**
   - Cancelled appointments release slots
   - Slots immediately available for rebooking
   - Phone verification required for cancellation

6. **Multiple Lock Requests**
   - Same customer can have only one active lock
   - Previous locks auto-expired on new request
   - Prevents slot hoarding

## Dashboard Features

### Real-Time Visualization
- Live slot states (Available/Locked/Booked)
- Auto-refresh every 5 seconds
- Visual countdown timers for locks

### Key Metrics
- Active locks count
- Today's appointments
- Total confirmed appointments
- Conversion rate (locks → bookings)

### Manual Controls
- Cancel appointments
- View appointment details
- Monitor system health

## Security Considerations

1. **Phone Verification**
   - Required for cancellations
   - Prevents unauthorized modifications

2. **Lock Ownership**
   - Locks tied to customer phone
   - Only owner can convert to booking

3. **Atomic Operations**
   - Database transactions ensure consistency
   - No partial state changes

4. **Input Validation**
   - All inputs validated via Pydantic schemas
   - Type safety enforced

## Scalability Notes

1. **Database Indexes**
   - Composite indexes on time ranges
   - Efficient overlap queries
   - Fast lock expiration checks

2. **Stateless Design**
   - API endpoints are stateless
   - Horizontal scaling possible
   - Load balancing supported

3. **Background Tasks**
   - Lock cleanup can run periodically
   - Minimal impact on user requests

## Testing Strategy

Comprehensive test suite validates:
1. Parallel booking prevention
2. Lock expiration and reclaiming
3. Booking after cancellation
4. Buffer time enforcement
5. Business hours validation

All tests must pass before deployment.
