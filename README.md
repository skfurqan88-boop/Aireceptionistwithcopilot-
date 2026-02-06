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

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/skfurqan88-boop/Aireceptionistwithcopilot-.git
cd Aireceptionistwithcopilot-

# Configure environment
cp backend/.env.example .env
# Edit .env with your configuration

# Start with Docker Compose
docker-compose up -d

# Initialize database
docker-compose exec backend python init_db.py

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

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

## Deployment

For production deployment, see **[DEPLOYMENT.md](DEPLOYMENT.md)** for comprehensive guides on:

- Docker deployment
- Cloud platform deployment (AWS, Azure, GCP)
- VPS/Dedicated server setup
- Kubernetes deployment
- Security best practices
- Monitoring and scaling

### Quick Production Deploy

```bash
# Using Docker Compose
docker-compose up -d
docker-compose exec backend python init_db.py --business-id=default --timezone=America/New_York
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

All 5 core validation tests verify:
1. ✅ Parallel booking prevention (no double booking)
2. ✅ Expired lock reclaiming
3. ✅ Booking after cancellation
4. ✅ Buffer time enforcement
5. ✅ Business hours validation

## Production Ready

This system is production-ready with:
- ✅ All tests passing
- ✅ Docker containerization
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ Security best practices
- ✅ Comprehensive documentation
- ✅ Health checks and monitoring
- ✅ Database migration support
- ✅ Scalable architecture

## Architecture Details

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design documentation.
