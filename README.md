# AI Receptionist Appointment Booking System

A deterministic, production-grade appointment booking system with AI-powered conversation interface.

## System Architecture

This system follows a strict layered architecture:

1. **Conversation Layer (AI)** - Collects user intent via natural conversation
2. **Scheduling Engine** - Pure logic for availability calculation
3. **Locking & Conflict Control** - Prevents race conditions and double booking
4. **Persistence Layer** - Source of truth for all bookings

## Core Philosophy

- AI = interface only (conversation)
- System = authority (logic & decisions)
- No booking can be confirmed without system validation
- Double booking is mathematically impossible

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

### Environment Variables

Create a `.env` file in the backend directory:

```
DATABASE_URL=sqlite:///./appointments.db
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_DEPLOYMENT=your_deployment
```

## API Endpoints

- `POST /availability/check` - Check slot availability
- `POST /locks/create` - Create temporary slot lock
- `POST /appointments/confirm` - Confirm appointment booking
- `POST /appointments/cancel` - Cancel appointment
- `GET /appointments/list` - List all appointments
- `GET /dashboard/status` - Get dashboard status

## Testing

Run validation tests:

```bash
cd backend
pytest tests/
```

## Architecture Details

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design documentation.
