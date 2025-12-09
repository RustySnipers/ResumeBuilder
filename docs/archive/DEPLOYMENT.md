# ResumeBuilder Deployment Guide

**Version:** 1.5.0-phase5
**Status:** Production-Ready
**Last Updated:** 2025-12-02

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Health Checks](#health-checks)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Docker**: 20.10+ and Docker Compose 2.0+
- **Python**: 3.11+ (for local development)
- **PostgreSQL**: 15+ (if not using Docker)
- **Redis**: 7+ (if not using Docker)

### Required Accounts & Keys

- **Anthropic API Key**: Get from [console.anthropic.com](https://console.anthropic.com)
- **Database**: PostgreSQL instance (or use Docker)
- **Redis**: Redis instance (or use Docker)

---

## Local Development

### 1. Clone Repository

```bash
git clone https://github.com/RustySnipers/ResumeBuilder.git
cd ResumeBuilder
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 3. Install Dependencies

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download NLP models
python -m spacy download en_core_web_lg
python -c "import nltk; nltk.download('wordnet'); nltk.download('stopwords'); nltk.download('punkt')"
```

### 4. Run Database Migrations

```bash
# Initialize Alembic (if not done)
alembic upgrade head
```

### 5. Start Development Server

```bash
# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the convenience script
python main.py
```

### 6. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check API documentation
open http://localhost:8000/docs
```

---

## Docker Deployment

### Quick Start (Recommended)

```bash
# 1. Set environment variables
cp .env.example .env
nano .env  # Add your ANTHROPIC_API_KEY

# 2. Build and start all services
docker-compose up -d

# 3. Check service status
docker-compose ps
docker-compose logs -f api

# 4. Verify deployment
curl http://localhost:8000/health
```

### Services Included

The `docker-compose.yml` starts three services:

1. **api** - FastAPI backend (port 8000)
2. **db** - PostgreSQL database (port 5432)
3. **redis** - Redis cache (port 6379)

### Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f db
docker-compose logs -f redis

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Reset everything (including data)
docker-compose down -v
docker-compose up -d --build
```

### Running Migrations with Docker

```bash
# Run migrations in running container
docker-compose exec api alembic upgrade head

# Or run migrations during build
docker-compose run --rm api alembic upgrade head
```

---

## Production Deployment

### Option 1: Docker Compose (Single Server)

**Best for:** Small to medium deployments, staging environments

```bash
# 1. Set production environment
cp .env.example .env.production
nano .env.production  # Configure production values

# 2. Use production compose file
docker-compose -f docker-compose.yml --env-file .env.production up -d

# 3. Set up reverse proxy (Nginx/Caddy)
# See nginx.conf.example below
```

**Production Nginx Configuration:**

```nginx
server {
    listen 80;
    server_name api.resumebuilder.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for streaming
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
```

### Option 2: Kubernetes

**Best for:** Large-scale deployments, high availability

```bash
# 1. Build and push image
docker build -t resumebuilder:1.5.0 .
docker tag resumebuilder:1.5.0 your-registry/resumebuilder:1.5.0
docker push your-registry/resumebuilder:1.5.0

# 2. Apply Kubernetes manifests (see k8s/ directory)
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 3. Verify deployment
kubectl get pods -n resumebuilder
kubectl logs -f deployment/resumebuilder-api -n resumebuilder
```

**Kubernetes Health Checks:**

```yaml
# Liveness probe
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

# Readiness probe
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

### Option 3: Cloud Platforms

#### AWS (ECS Fargate)

```bash
# 1. Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t resumebuilder .
docker tag resumebuilder:latest <account>.dkr.ecr.us-east-1.amazonaws.com/resumebuilder:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/resumebuilder:latest

# 2. Create ECS task definition with environment variables
# 3. Create ECS service with ALB
# 4. Configure RDS PostgreSQL and ElastiCache Redis
```

#### Google Cloud (Cloud Run)

```bash
# 1. Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/resumebuilder

# 2. Deploy to Cloud Run
gcloud run deploy resumebuilder \
  --image gcr.io/PROJECT_ID/resumebuilder \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ANTHROPIC_API_KEY=your-key \
  --set-env-vars DATABASE_URL=your-db-url \
  --set-env-vars REDIS_URL=your-redis-url

# 3. Use Cloud SQL and Memorystore
```

---

## Environment Configuration

### Required Environment Variables

```bash
# Anthropic Claude API (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# Database Configuration (REQUIRED)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/resumebuilder

# Redis Configuration (REQUIRED)
REDIS_URL=redis://host:6379
```

### Optional Environment Variables

```bash
# Application Configuration
ENV=production                    # development | staging | production
LOG_LEVEL=INFO                    # DEBUG | INFO | WARNING | ERROR
DEBUG=False                       # True | False

# Security (REQUIRED in production)
SECRET_KEY=your-secret-key-here   # Generate with: openssl rand -hex 32
JWT_SECRET_KEY=your-jwt-secret    # Generate with: openssl rand -hex 32

# CORS Configuration
ALLOWED_ORIGINS=https://app.resumebuilder.com,https://www.resumebuilder.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=50

# LLM Configuration
DEFAULT_MODEL=claude-sonnet-4-20250514
MAX_TOKENS=4096
TEMPERATURE=1.0
CACHE_TTL_SECONDS=3600

# Export Configuration
EXPORT_CACHE_TTL=900              # 15 minutes
MAX_EXPORT_SIZE_MB=10
EXPORTS_PER_MINUTE=10
EXPORTS_PER_DAY=50
```

### Production Environment Template

Create `.env.production`:

```bash
# Production Configuration
ENV=production
DEBUG=False
LOG_LEVEL=INFO

# Security Keys (MUST generate unique keys)
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-your-production-key

# Database (RDS, Cloud SQL, or managed PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db.example.com:5432/resumebuilder

# Redis (ElastiCache, Memorystore, or managed Redis)
REDIS_URL=redis://prod-redis.example.com:6379

# CORS (production domains only)
ALLOWED_ORIGINS=https://app.resumebuilder.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
EXPORTS_PER_MINUTE=10
EXPORTS_PER_DAY=50
```

---

## Health Checks

### Available Endpoints

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `GET /` | Basic status | Quick check |
| `GET /health` | Comprehensive health | Monitoring dashboards |
| `GET /health/ready` | Readiness probe | Kubernetes readiness |
| `GET /health/live` | Liveness probe | Kubernetes liveness |

### Health Check Examples

```bash
# Basic status
curl http://localhost:8000/

# Comprehensive health check
curl http://localhost:8000/health | jq

# Readiness check (for load balancers)
curl http://localhost:8000/health/ready

# Liveness check (for container orchestrators)
curl http://localhost:8000/health/live
```

### Health Response Format

```json
{
  "status": "healthy",
  "timestamp": 1701475200,
  "version": "1.5.0-phase5",
  "services": {
    "database": {
      "status": "healthy",
      "type": "postgresql"
    },
    "redis": {
      "status": "healthy",
      "keys": 42
    },
    "llm": {
      "status": "healthy",
      "model": "claude-sonnet-4-20250514"
    },
    "nlp": {
      "status": "healthy",
      "components": ["pii_detector", "semantic_analyzer", "keyword_extractor", "section_parser"]
    }
  }
}
```

---

## Monitoring

### Recommended Monitoring Stack

1. **Application Monitoring**: Datadog, New Relic, or Prometheus
2. **Log Aggregation**: ELK Stack, CloudWatch, or Stackdriver
3. **Error Tracking**: Sentry
4. **Uptime Monitoring**: UptimeRobot, Pingdom

### Key Metrics to Monitor

**Application Metrics:**
- Request rate (requests/sec)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- LLM API latency
- Cache hit rate

**Infrastructure Metrics:**
- CPU usage
- Memory usage
- Disk I/O
- Network throughput

**Database Metrics:**
- Connection pool size
- Query latency
- Active connections

**Redis Metrics:**
- Memory usage
- Cache hit/miss rate
- Commands/sec

### Health Check Monitoring

```bash
# Add to monitoring system
curl http://localhost:8000/health

# Alert if status != "healthy"
# Alert if any service.status != "healthy"
```

### Log Levels

```bash
# Production: INFO or WARNING
LOG_LEVEL=INFO

# Development: DEBUG
LOG_LEVEL=DEBUG

# Critical systems: ERROR
LOG_LEVEL=ERROR
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

**Error:** `asyncpg.exceptions.InvalidPasswordError`

**Solution:**
```bash
# Check DATABASE_URL format
# postgresql+asyncpg://user:password@host:port/database

# Verify PostgreSQL is running
docker-compose ps db
docker-compose logs db

# Test connection
docker-compose exec db psql -U postgres -c "SELECT 1"
```

#### 2. Redis Connection Failed

**Error:** `redis.exceptions.ConnectionError`

**Solution:**
```bash
# Check REDIS_URL format
# redis://host:port

# Verify Redis is running
docker-compose ps redis
docker-compose logs redis

# Test connection
docker-compose exec redis redis-cli ping
```

#### 3. LLM API Unavailable

**Error:** `LLM service unavailable. ANTHROPIC_API_KEY not configured.`

**Solution:**
```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Check .env file
cat .env | grep ANTHROPIC_API_KEY

# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

#### 4. Docker Build Fails

**Error:** `ERROR: failed to solve: process "/bin/sh -c pip install -r requirements.txt" did not complete successfully`

**Solution:**
```bash
# Clear Docker cache
docker-compose down
docker system prune -a

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up -d
```

#### 5. Migration Failed

**Error:** `alembic.util.exc.CommandError: Can't locate revision identified by`

**Solution:**
```bash
# Reset database and rerun migrations
docker-compose down -v  # WARNING: Deletes all data
docker-compose up -d db
docker-compose exec api alembic upgrade head
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG=True

# Run with verbose output
uvicorn main:app --log-level debug
```

### Container Logs

```bash
# Follow API logs
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api

# All services
docker-compose logs -f
```

---

## Performance Tuning

### Uvicorn Workers

For production, use multiple workers:

```bash
# Dockerfile CMD
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Or via environment
WORKERS=4
```

**Recommended:** `workers = (2 x CPU cores) + 1`

### Database Connection Pool

```python
# backend/database/connection.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # Default: 5
    max_overflow=10,     # Default: 10
    pool_pre_ping=True,  # Check connections
)
```

### Redis Memory

```bash
# docker-compose.yml
redis:
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

---

## Security Checklist

- [ ] Strong `SECRET_KEY` and `JWT_SECRET_KEY` (32+ random bytes)
- [ ] `DEBUG=False` in production
- [ ] HTTPS enforced (use reverse proxy)
- [ ] CORS configured with specific origins (not `*`)
- [ ] Database credentials rotated regularly
- [ ] API keys stored in secrets manager (not .env files)
- [ ] Rate limiting enabled
- [ ] Container runs as non-root user (✅ implemented)
- [ ] Network isolation (firewall rules)
- [ ] Regular security updates

---

## Backup & Recovery

### Database Backups

```bash
# Manual backup
docker-compose exec db pg_dump -U postgres resumebuilder > backup.sql

# Restore
docker-compose exec -T db psql -U postgres resumebuilder < backup.sql

# Automated backups (cron)
0 2 * * * docker-compose -f /path/to/docker-compose.yml exec -T db pg_dump -U postgres resumebuilder | gzip > /backups/resumebuilder-$(date +\%Y\%m\%d).sql.gz
```

### Redis Persistence

Redis is configured with AOF (Append-Only File):

```bash
# docker-compose.yml already includes:
command: redis-server --appendonly yes
```

---

## Scaling

### Horizontal Scaling

1. **Load Balancer:** Nginx, HAProxy, or cloud LB (ALB, Cloud Load Balancing)
2. **Multiple API Instances:** Scale `docker-compose` or Kubernetes replicas
3. **Database:** PostgreSQL read replicas or managed service
4. **Redis:** Redis Cluster or managed service (ElastiCache, Memorystore)

### Vertical Scaling

```yaml
# docker-compose.yml
api:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
      reservations:
        cpus: '1.0'
        memory: 2G
```

---

## Support

For issues and questions:

- **Issues:** https://github.com/RustySnipers/ResumeBuilder/issues
- **Discussions:** https://github.com/RustySnipers/ResumeBuilder/discussions
- **Documentation:** https://github.com/RustySnipers/ResumeBuilder/wiki

---

**Last Updated:** 2025-12-02
**Version:** 1.5.0-phase5
