#!/bin/bash
# Quick deployment verification script

set -e

echo "==================================="
echo "AI Receptionist - Deployment Check"
echo "==================================="
echo ""

# Check Docker
echo "✓ Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "✗ Docker not found. Please install Docker first."
    exit 1
fi
echo "  Docker version: $(docker --version)"

# Check Docker Compose
echo "✓ Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "✗ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi
echo "  Docker Compose version: $(docker-compose --version)"

# Check .env file
echo "✓ Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "  Creating .env from template..."
    cp backend/.env.example .env
    echo "  ⚠ Please edit .env with your configuration"
fi

# Validate docker-compose.yml
echo "✓ Validating docker-compose.yml..."
docker-compose config > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  Configuration is valid"
else
    echo "✗ Invalid docker-compose configuration"
    exit 1
fi

# Build images
echo "✓ Building Docker images..."
docker-compose build --quiet

echo ""
echo "==================================="
echo "Pre-deployment checks passed! ✓"
echo "==================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your configuration"
echo "  2. Run: docker-compose up -d"
echo "  3. Initialize DB: docker-compose exec backend python init_db.py"
echo "  4. Access frontend at http://localhost"
echo "  5. Access API at http://localhost:8000"
echo "  6. View API docs at http://localhost:8000/docs"
echo ""
