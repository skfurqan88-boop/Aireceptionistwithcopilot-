# Deployment Guide - AI Receptionist Appointment Booking System

This guide covers different deployment options for the AI Receptionist Appointment Booking System.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Local Deployment with Docker](#local-deployment-with-docker)
- [Production Deployment](#production-deployment)
- [Environment Configuration](#environment-configuration)
- [Database Management](#database-management)
- [Monitoring & Health Checks](#monitoring--health-checks)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- Docker & Docker Compose (for containerized deployment)
- Python 3.12+ (for local development)
- Node.js 18+ (for frontend development)

### Required Configuration
- Azure OpenAI API credentials (optional, for AI conversation features)
- Domain name (for production deployment)
- SSL certificates (for HTTPS in production)

## Local Deployment with Docker

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-receptionist.git
   cd ai-receptionist
   ```

2. **Create environment file**
   ```bash
   cp backend/.env.example .env
   # Edit .env with your configuration
   ```

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Initialize the database**
   ```bash
   docker-compose exec backend python -c "
   from database import init_db
   from models import BusinessSettings
   from sqlalchemy.orm import sessionmaker
   from sqlalchemy import create_engine
   
   init_db()
   
   # Create default business settings
   engine = create_engine('sqlite:///./data/appointments.db')
   Session = sessionmaker(bind=engine)
   session = Session()
   
   from models import BusinessSettings
   business = BusinessSettings(
       business_id='default',
       opening_time='09:00',
       closing_time='17:00',
       slot_duration_minutes=30,
       buffer_minutes=15,
       timezone='America/New_York'
   )
   session.add(business)
   session.commit()
   print('Business initialized!')
   "
   ```

5. **Access the application**
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Stopping Services
```bash
docker-compose down
```

### Viewing Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Production Deployment

### Option 1: Cloud Platform (AWS/Azure/GCP)

#### AWS Deployment with ECS

1. **Build and push Docker images**
   ```bash
   # Backend
   docker build -t ai-receptionist-backend:latest ./backend
   docker tag ai-receptionist-backend:latest YOUR_ECR_REPO/backend:latest
   docker push YOUR_ECR_REPO/backend:latest
   
   # Frontend
   docker build -t ai-receptionist-frontend:latest ./frontend
   docker tag ai-receptionist-frontend:latest YOUR_ECR_REPO/frontend:latest
   docker push YOUR_ECR_REPO/frontend:latest
   ```

2. **Create ECS Task Definition**
   - Use the Docker images from ECR
   - Configure environment variables
   - Set up load balancer
   - Configure auto-scaling

3. **Set up RDS for PostgreSQL** (recommended for production)
   - Create PostgreSQL database
   - Update DATABASE_URL environment variable
   - Run database migrations

#### Azure Deployment with Container Instances

1. **Create Azure Container Registry**
   ```bash
   az acr create --resource-group myResourceGroup \
     --name myContainerRegistry --sku Basic
   ```

2. **Push images to ACR**
   ```bash
   az acr login --name myContainerRegistry
   docker build -t ai-receptionist-backend:latest ./backend
   docker tag ai-receptionist-backend:latest myContainerRegistry.azurecr.io/backend:latest
   docker push myContainerRegistry.azurecr.io/backend:latest
   ```

3. **Deploy with Azure Container Instances**
   ```bash
   az container create \
     --resource-group myResourceGroup \
     --name ai-receptionist-backend \
     --image myContainerRegistry.azurecr.io/backend:latest \
     --dns-name-label ai-receptionist-api \
     --ports 8000
   ```

### Option 2: VPS/Dedicated Server

1. **Install Docker and Docker Compose**
   ```bash
   # On Ubuntu/Debian
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   sudo apt-get install docker-compose-plugin
   ```

2. **Clone repository and configure**
   ```bash
   git clone https://github.com/yourusername/ai-receptionist.git
   cd ai-receptionist
   cp backend/.env.example .env
   nano .env  # Configure environment variables
   ```

3. **Set up reverse proxy (Nginx)**
   ```bash
   sudo apt-get install nginx certbot python3-certbot-nginx
   ```

   Create nginx configuration at `/etc/nginx/sites-available/ai-receptionist`:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:80;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
       
       location /api {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

4. **Enable SSL with Let's Encrypt**
   ```bash
   sudo ln -s /etc/nginx/sites-available/ai-receptionist /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   sudo certbot --nginx -d your-domain.com
   ```

5. **Start application**
   ```bash
   docker-compose up -d
   ```

### Option 3: Kubernetes Deployment

1. **Create Kubernetes manifests**
   See `k8s/` directory for example configurations

2. **Deploy to cluster**
   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/backend-deployment.yaml
   kubectl apply -f k8s/frontend-deployment.yaml
   kubectl apply -f k8s/services.yaml
   kubectl apply -f k8s/ingress.yaml
   ```

## Environment Configuration

### Backend Environment Variables

#### Required
- `DATABASE_URL` - Database connection string
  - Development: `sqlite:///./data/appointments.db`
  - Production: `postgresql://user:password@host:5432/dbname`

#### Optional (AI Features)
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_DEPLOYMENT` - Deployment name (default: gpt-4)

#### Production Settings
- `CORS_ORIGINS` - Comma-separated list of allowed origins
  - Example: `https://yourdomain.com,https://www.yourdomain.com`
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `MAX_CONNECTIONS` - Maximum database connections

### Frontend Environment Variables

- `REACT_APP_API_URL` - Backend API URL
  - Development: `http://localhost:8000`
  - Production: `https://api.yourdomain.com`

## Database Management

### Switching from SQLite to PostgreSQL (Recommended for Production)

1. **Install PostgreSQL**
   ```bash
   # Docker
   docker run --name postgres \
     -e POSTGRES_PASSWORD=yourpassword \
     -e POSTGRES_DB=appointments \
     -p 5432:5432 -d postgres:15
   ```

2. **Update DATABASE_URL**
   ```
   DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/appointments
   ```

3. **Run migrations**
   The application will automatically create tables on startup.

### Backup and Restore

#### SQLite
```bash
# Backup
docker-compose exec backend sqlite3 /app/data/appointments.db ".backup '/app/data/backup.db'"

# Restore
docker-compose exec backend sqlite3 /app/data/appointments.db ".restore '/app/data/backup.db'"
```

#### PostgreSQL
```bash
# Backup
docker-compose exec backend pg_dump $DATABASE_URL > backup.sql

# Restore
docker-compose exec backend psql $DATABASE_URL < backup.sql
```

## Monitoring & Health Checks

### Health Check Endpoints

- **Backend Health**: `GET /` - Returns `{"status": "healthy"}`
- **Readiness**: Services automatically check database connectivity

### Monitoring with Docker

```bash
# Check container health
docker-compose ps

# View resource usage
docker stats

# Check logs for errors
docker-compose logs --tail=100 backend | grep ERROR
```

### Production Monitoring

Recommended monitoring tools:
- **Prometheus + Grafana** - Metrics and dashboards
- **Sentry** - Error tracking
- **ELK Stack** - Log aggregation
- **Uptime Robot** - Uptime monitoring

## Security Best Practices

### Production Checklist

- [ ] Use HTTPS/SSL certificates
- [ ] Configure CORS properly (restrict origins)
- [ ] Use strong database passwords
- [ ] Enable rate limiting
- [ ] Set up firewall rules
- [ ] Regular security updates
- [ ] Database backups
- [ ] Monitor access logs
- [ ] Use secrets management (AWS Secrets Manager, Azure Key Vault)
- [ ] Enable application logging
- [ ] Set up intrusion detection

### CORS Configuration

Update `main.py` for production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Rate Limiting

Consider adding rate limiting middleware for production:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

## Troubleshooting

### Common Issues

#### Container won't start
```bash
# Check logs
docker-compose logs backend

# Verify environment variables
docker-compose config

# Rebuild images
docker-compose build --no-cache
```

#### Database connection errors
- Verify DATABASE_URL is correct
- Check database container is running
- Ensure network connectivity

#### Frontend can't connect to backend
- Check REACT_APP_API_URL is set correctly
- Verify CORS configuration
- Check firewall/security groups

#### Port conflicts
```bash
# Find process using port
sudo lsof -i :8000

# Change port in docker-compose.yml
```

### Getting Help

- Check logs: `docker-compose logs -f`
- Review API docs: http://localhost:8000/docs
- Test endpoints: Use curl or Postman
- Check GitHub issues

## Performance Optimization

### Production Optimizations

1. **Use PostgreSQL instead of SQLite**
2. **Enable Redis for caching** (optional)
3. **Use CDN for static assets**
4. **Enable Gzip compression** (already configured in nginx)
5. **Set up database connection pooling**
6. **Configure auto-scaling**
7. **Use load balancer for multiple instances**

### Database Indexing

The application includes optimized indexes for:
- Appointment time ranges
- Lock expiration queries
- Business ID lookups

### Caching Strategy

Consider adding Redis for:
- Session management
- Rate limiting
- Temporary data caching

## Scaling

### Horizontal Scaling

The application is stateless and can be scaled horizontally:

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3
```

### Load Balancing

Use nginx or cloud load balancer to distribute traffic:
- Round-robin
- Least connections
- IP hash (for sticky sessions)

## Maintenance

### Regular Tasks

- **Daily**: Monitor logs and error rates
- **Weekly**: Review performance metrics
- **Monthly**: Security updates and dependency patches
- **Quarterly**: Database optimization and cleanup

### Updates and Rollbacks

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Rollback if needed
git checkout <previous-commit>
docker-compose up -d --build
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/ai-receptionist/issues
- Documentation: See README.md and ARCHITECTURE.md
- Email: support@yourdomain.com
