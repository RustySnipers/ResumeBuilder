# ResumeBuilder - Quick Start Deployment Guide

Complete production deployment in **5 minutes** using Docker Compose.

## Version

**1.7.0-phase7** - Complete webhook system with local deployment support

## Prerequisites

- **Docker** 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose** 2.0+ (included with Docker Desktop)
- **Anthropic API Key** ([Get from console.anthropic.com](https://console.anthropic.com/))
- **4GB RAM** minimum, 8GB recommended
- **10GB disk space**

## Quick Start (5 Minutes)

### Step 1: Clone and Setup (1 minute)

```bash
# Navigate to project directory
cd /home/user/ResumeBuilder

# Copy environment template
cp .env.docker .env
```

### Step 2: Configure Environment (2 minutes)

Edit `.env` file and set **3 required variables**:

```bash
# Generate secret keys (run these commands)
openssl rand -hex 32  # Copy output to SECRET_KEY
openssl rand -hex 32  # Copy output to JWT_SECRET_KEY

# Edit .env file
nano .env
```

**Required changes in .env:**
```env
SECRET_KEY=<paste-output-from-first-command>
JWT_SECRET_KEY=<paste-output-from-second-command>
ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
```

### Step 3: Deploy (2 minutes)

```bash
# Run deployment script
./scripts/deploy.sh
```

This script will:
- ✅ Check prerequisites
- ✅ Build Docker images
- ✅ Start all services (API, Database, Redis, Webhook Worker)
- ✅ Wait for services to be healthy
- ✅ Run database migrations
- ✅ Verify deployment

### Step 4: Verify Deployment

```bash
# Check health
./scripts/health_check.sh

# Or manually
curl http://localhost:8000/health
```

**Expected output:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-04T...",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "llm": "healthy"
  }
}
```

## What's Deployed

### Services Running

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| **API Server** | `resumebuilder-api` | 8000 | FastAPI application |
| **PostgreSQL** | `resumebuilder-db` | 5432 | Database |
| **Redis** | `resumebuilder-redis` | 6379 | Cache & rate limiting |
| **Webhook Worker** | `resumebuilder-webhook-worker` | - | Background event processor |

### Endpoints Available

- **API Root:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (Interactive Swagger UI)
- **Health Check:** http://localhost:8000/health
- **OpenAPI Spec:** http://localhost:8000/openapi.json

## Test Your Deployment

### 1. Register a User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

Save the `access_token` from the response.

### 3. Create Resume

```bash
export TOKEN="your-access-token-here"

curl -X POST http://localhost:8000/api/v1/resumes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Software Engineer Resume",
    "raw_text": "John Doe\nSoftware Engineer\n\nExperience:\n- 5 years Python development\n- FastAPI and async programming\n- PostgreSQL and Redis"
  }'
```

### 4. Create Webhook

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.site/your-unique-url",
    "events": ["resume.created", "resume.updated", "export.completed"],
    "description": "Test webhook"
  }'
```

## Management Commands

```bash
# View logs
./scripts/manage.sh logs           # Recent logs
./scripts/manage.sh logs -f        # Follow logs

# Check status
./scripts/manage.sh status

# Restart services
./scripts/manage.sh restart

# Stop services
./scripts/manage.sh stop

# Start services
./scripts/manage.sh start

# Backup database
./scripts/manage.sh backup

# Open shell in API container
./scripts/manage.sh shell
```

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f webhook-worker
docker-compose logs -f db
docker-compose logs -f redis
```

### Check Container Status

```bash
docker-compose ps
```

### Check Resource Usage

```bash
docker stats
```

## Data Persistence

Data is persisted in Docker volumes:

- **postgres_data** - Database files
- **redis_data** - Redis persistence (AOF)

### Backup Database

```bash
# Automated backup
./scripts/manage.sh backup

# Manual backup
docker exec resumebuilder-db pg_dump -U postgres resumebuilder > backup.sql
```

### Restore Database

```bash
# Stop API to prevent connections
docker-compose stop api webhook-worker

# Restore
cat backup.sql | docker exec -i resumebuilder-db psql -U postgres -d resumebuilder

# Restart
docker-compose start api webhook-worker
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Check specific service
docker-compose logs api
docker-compose logs db
```

### Database Connection Issues

```bash
# Verify database is running
docker exec resumebuilder-db pg_isready -U postgres

# Check database logs
docker-compose logs db
```

### API Health Check Fails

```bash
# Check API logs
docker-compose logs api

# Verify environment variables
docker exec resumebuilder-api env | grep -E "DATABASE_URL|REDIS_URL|ANTHROPIC"

# Try health endpoint
curl -v http://localhost:8000/health
```

### Webhook Worker Not Processing

```bash
# Check worker logs
docker-compose logs webhook-worker

# Check if events exist
docker exec resumebuilder-api python -c "
from backend.database import AsyncSessionLocal
from backend.repositories.webhook_event_repository import WebhookEventRepository
import asyncio

async def check():
    async with AsyncSessionLocal() as session:
        repo = WebhookEventRepository(session)
        pending = await repo.get_pending_events(limit=10)
        print(f'Pending events: {len(pending)}')

asyncio.run(check())
"
```

### Port Already in Use

```bash
# Stop conflicting service on port 8000
lsof -ti:8000 | xargs kill -9

# Or change port in docker-compose.yml
# Change "8000:8000" to "8080:8000"
```

### Out of Disk Space

```bash
# Clean Docker system
docker system prune -a --volumes

# Remove old images
docker images | grep resumebuilder | awk '{print $3}' | xargs docker rmi
```

## Updating the Application

### Pull Latest Changes

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker-compose build --no-cache

# Apply migrations
docker-compose up -d
docker-compose exec api alembic upgrade head

# Restart services
docker-compose restart
```

## Production Checklist

Before going to production, ensure:

- [ ] **Security Keys** - Unique SECRET_KEY and JWT_SECRET_KEY generated
- [ ] **API Key** - Valid Anthropic API key with sufficient credits
- [ ] **Email** - Email provider configured (SMTP/SendGrid/AWS SES)
- [ ] **HTTPS** - SSL/TLS certificates configured (use Nginx reverse proxy)
- [ ] **Domain** - APP_BASE_URL set to your domain
- [ ] **CORS** - ALLOWED_ORIGINS set to your frontend domains (not *)
- [ ] **Backups** - Automated database backups configured
- [ ] **Monitoring** - Health checks and alerting configured
- [ ] **Firewall** - Only necessary ports exposed (80, 443)
- [ ] **Resources** - Adequate RAM (8GB+) and disk space (20GB+)
- [ ] **Redis Persistence** - AOF enabled (already configured)
- [ ] **Database Backups** - Regular pg_dump schedule
- [ ] **Log Rotation** - Docker log rotation configured

## Next Steps

### 1. Add HTTPS with Nginx

See [LOCAL_DEPLOYMENT.md](LOCAL_DEPLOYMENT.md#nginx-reverse-proxy) for complete Nginx configuration with SSL/TLS.

### 2. Configure Email

Update `.env` with your email provider:

```env
# For SendGrid
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM=noreply@yourdomain.com
```

### 3. Set Up Monitoring

- Configure Sentry for error tracking
- Set up Prometheus + Grafana for metrics
- Configure health check alerts

### 4. Scale for Production

- Run multiple API containers behind load balancer
- Use managed PostgreSQL (AWS RDS, Google Cloud SQL)
- Use managed Redis (AWS ElastiCache, Redis Cloud)
- Deploy webhook worker as separate service

## Advanced Configuration

### Custom Port

Edit `docker-compose.yml`:

```yaml
services:
  api:
    ports:
      - "8080:8000"  # Change from 8000:8000
```

### Custom Database Credentials

Edit `docker-compose.yml`:

```yaml
services:
  db:
    environment:
      - POSTGRES_USER=customuser
      - POSTGRES_PASSWORD=strongpassword
      - POSTGRES_DB=resumedb
```

Update DATABASE_URL in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://customuser:strongpassword@db:5432/resumedb
```

### Enable Debug Mode

Edit `.env`:

```env
DEBUG=True
LOG_LEVEL=DEBUG
```

⚠️ **Never use DEBUG=True in production!**

## Getting Help

- **Documentation:** [LOCAL_DEPLOYMENT.md](LOCAL_DEPLOYMENT.md)
- **Webhook Guide:** [WEBHOOK_INTEGRATION.md](WEBHOOK_INTEGRATION.md)
- **Worker Guide:** [WEBHOOK_WORKER.md](WEBHOOK_WORKER.md)
- **Project Status:** [PROJECT_STATUS.md](PROJECT_STATUS.md)
- **API Docs:** http://localhost:8000/docs (after deployment)

## Summary

You now have a fully functional ResumeBuilder instance running with:

✅ **AI-Powered Resume Optimization** - Claude Sonnet 4.5
✅ **Authentication & Authorization** - JWT with refresh tokens
✅ **Resume CRUD** - Full management API
✅ **Export System** - PDF & DOCX with 4 ATS templates
✅ **Email Service** - Verification and password reset
✅ **Analytics Dashboard** - User activity tracking
✅ **Webhook System** - Third-party integrations
✅ **Background Worker** - Automatic event processing
✅ **Caching** - Redis for LLM and export caching
✅ **Rate Limiting** - Per-user limits
✅ **Health Checks** - Kubernetes-ready probes

**Time to deploy:** 5 minutes
**Services running:** 4 containers
**API endpoints:** 50+
**Features:** Production-ready

Enjoy your deployment! 🚀
