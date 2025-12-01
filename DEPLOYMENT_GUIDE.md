# ResumeBuilder Deployment Guide

## Quick Start

### Local Development with Docker

```bash
# 1. Clone repository
git clone <repository-url>
cd ResumeBuilder

# 2. Configure environment
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# 3. Start services
docker-compose up -d

# 4. Check health
curl http://localhost:8000/

# 5. View logs
docker-compose logs -f api
```

### Manual Setup (Without Docker)

```bash
# 1. Install Python 3.11+
python --version  # Should be 3.11 or higher

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download NLP models
python -m spacy download en_core_web_lg
python -c "import nltk; nltk.download('wordnet'); nltk.download('stopwords'); nltk.download('punkt')"

# 5. Setup PostgreSQL
createdb resumebuilder

# 6. Run migrations
alembic upgrade head

# 7. Start Redis
redis-server

# 8. Configure environment
export ANTHROPIC_API_KEY=your-key-here
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/resumebuilder
export REDIS_URL=redis://localhost:6379

# 9. Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Production Deployment

### AWS ECS/Fargate

```bash
# 1. Build and push image
docker build -t resumebuilder:latest .
docker tag resumebuilder:latest <aws-account-id>.dkr.ecr.<region>.amazonaws.com/resumebuilder:latest
docker push <aws-account-id>.dkr.ecr.<region>.amazonaws.com/resumebuilder:latest

# 2. Create task definition (see aws-ecs-task-definition.json)

# 3. Configure services
- RDS PostgreSQL 15
- ElastiCache Redis 7
- Application Load Balancer
- Auto Scaling Group

# 4. Set environment variables in ECS task
ANTHROPIC_API_KEY=<from-secrets-manager>
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
```

### Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resumebuilder
spec:
  replicas: 3
  selector:
    matchLabels:
      app: resumebuilder
  template:
    metadata:
      labels:
        app: resumebuilder
    spec:
      containers:
      - name: api
        image: resumebuilder:latest
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: resumebuilder-secrets
              key: anthropic-api-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: resumebuilder-secrets
              key: database-url
        - name: REDIS_URL
          value: redis://redis-service:6379
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
```

### Digital Ocean App Platform

```yaml
# app.yaml
name: resumebuilder
services:
- name: api
  github:
    repo: <your-username>/ResumeBuilder
    branch: main
    deploy_on_push: true
  dockerfile_path: Dockerfile
  http_port: 8000
  instance_count: 2
  instance_size_slug: professional-xs
  envs:
  - key: ANTHROPIC_API_KEY
    scope: RUN_TIME
    type: SECRET
  - key: DATABASE_URL
    scope: RUN_TIME
    type: SECRET
  - key: REDIS_URL
    scope: RUN_TIME
    value: ${redis.DATABASE_URL}
  health_check:
    http_path: /

databases:
- name: db
  engine: PG
  version: "15"

- name: redis
  engine: REDIS
  version: "7"
```

## Environment Variables

### Required
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

### Optional
- `ENV`: Environment (development/production)
- `LOG_LEVEL`: Logging level (INFO/DEBUG/WARNING/ERROR)
- `DEBUG`: Enable debug mode (True/False)
- `SECRET_KEY`: Application secret key
- `ALLOWED_ORIGINS`: CORS origins (comma-separated)
- `RATE_LIMIT_PER_MINUTE`: API rate limit (default: 50)
- `CACHE_TTL_SECONDS`: Cache TTL (default: 3600)
- `DEFAULT_MODEL`: Claude model (default: claude-sonnet-4-20250514)
- `MAX_TOKENS`: Max generation tokens (default: 4096)
- `TEMPERATURE`: LLM temperature (default: 1.0)

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Monitoring & Observability

### Health Checks

```bash
# Application health
curl http://localhost:8000/

# Cache stats
curl http://localhost:8000/api/v1/cache/stats

# LLM usage stats
curl http://localhost:8000/api/v1/stats
```

### Metrics to Monitor

**Application Metrics:**
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (%)
- Cache hit rate (%)

**Resource Metrics:**
- CPU utilization (%)
- Memory usage (MB)
- Database connections (active/idle)
- Redis memory usage (MB)

**Business Metrics:**
- Resumes analyzed (count)
- Resumes optimized (count)
- API cost ($)
- Cache savings ($)

### Logging

Application logs are output to stdout in JSON format:

```json
{
  "timestamp": "2025-11-30T10:00:00Z",
  "level": "INFO",
  "message": "Cache HIT for key: a3f2b9e4...",
  "request_id": "uuid-here",
  "user_id": "user-uuid"
}
```

**Log Aggregation:**
- CloudWatch Logs (AWS)
- Datadog
- Elasticsearch + Kibana
- Grafana Loki

## Scaling

### Horizontal Scaling

```bash
# Docker Compose
docker-compose up --scale api=3

# Kubernetes
kubectl scale deployment resumebuilder --replicas=5

# AWS ECS
aws ecs update-service --service resumebuilder --desired-count 5
```

### Vertical Scaling

Increase container resources:
- Memory: 512Mi → 2Gi
- CPU: 500m → 2000m

### Database Scaling

- Read replicas for read-heavy workloads
- Connection pooling (already configured: 20 connections)
- Partitioning for large tables

### Cache Scaling

- Redis Cluster for distributed caching
- ElastiCache with replication
- Increase memory limit

## Security

### Secrets Management

**AWS Secrets Manager:**
```bash
aws secretsmanager create-secret \
  --name resumebuilder/anthropic-api-key \
  --secret-string "sk-ant-..."
```

**Kubernetes Secrets:**
```bash
kubectl create secret generic resumebuilder-secrets \
  --from-literal=anthropic-api-key=sk-ant-... \
  --from-literal=database-url=postgresql://...
```

### SSL/TLS

Use reverse proxy (Nginx, Traefik) or load balancer for HTTPS:

```nginx
server {
    listen 443 ssl;
    server_name api.resumebuilder.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Network Security

- Use VPC/private subnets for databases
- Security groups/firewall rules
- WAF for DDoS protection
- Rate limiting at load balancer

## Troubleshooting

### Common Issues

**Database Connection Errors:**
```bash
# Check database is running
docker-compose ps db

# Test connection
psql $DATABASE_URL

# View logs
docker-compose logs db
```

**Redis Connection Errors:**
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
redis-cli ping

# View logs
docker-compose logs redis
```

**High Memory Usage:**
```bash
# Check container stats
docker stats

# Reduce cache TTL
export CACHE_TTL_SECONDS=1800

# Reduce worker count
uvicorn main:app --workers 2
```

**Slow Response Times:**
```bash
# Check cache hit rate
curl http://localhost:8000/api/v1/cache/stats

# Clear cache if needed
curl -X DELETE http://localhost:8000/api/v1/cache

# Monitor database queries
# Enable SQLAlchemy logging
```

## Backup & Recovery

### Database Backups

```bash
# Backup
pg_dump $DATABASE_URL > backup.sql

# Restore
psql $DATABASE_URL < backup.sql

# Automated backups (AWS RDS)
- Enable automated backups (7-35 days retention)
- Create manual snapshots before major changes
```

### Redis Backups

```bash
# Enable AOF persistence
redis-server --appendonly yes

# Create snapshot
redis-cli BGSAVE

# Backup RDB file
cp /var/lib/redis/dump.rdb /backup/
```

## Performance Tuning

### Application

```python
# Adjust worker count
uvicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker

# Increase connection pool
# In backend/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=50,        # Increase from 20
    max_overflow=20,     # Increase from 10
)
```

### Database

```sql
-- Add indexes
CREATE INDEX CONCURRENTLY idx_resumes_user_created
ON resumes(user_id, created_at DESC);

-- Analyze tables
ANALYZE resumes;
ANALYZE analyses;

-- Vacuum
VACUUM ANALYZE;
```

### Redis

```bash
# Increase max memory
redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru
```

## Cost Optimization

**LLM Costs:**
- Enable caching (90% savings)
- Use Sonnet-4 instead of Opus-4 (5x cheaper)
- Monitor usage with `/api/v1/stats`
- Set budget alerts

**Infrastructure Costs:**
- Right-size containers (start small, scale up)
- Use spot/preemptible instances
- Enable auto-scaling (scale down during low traffic)
- Use reserved instances for production

**Database Costs:**
- Use appropriate instance size
- Enable storage auto-scaling
- Delete old data (retention policies)
- Use read replicas only if needed

---

**Last Updated:** 2025-11-30
**Version:** 1.3.0-phase3.2
