# Local Deployment Guide

Complete guide for deploying ResumeBuilder on your local machine or local server.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Development)](#quick-start-development)
3. [Local Production Setup (Docker Compose)](#local-production-setup-docker-compose)
4. [Local Server Deployment](#local-server-deployment)
5. [Database Setup](#database-setup)
6. [Environment Configuration](#environment-configuration)
7. [Running the Application](#running-the-application)
8. [Testing the System](#testing-the-system)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

```bash
# Python 3.10 or higher
python3 --version

# PostgreSQL 14 or higher
psql --version

# Redis 6 or higher
redis-server --version

# Git
git --version
```

### Optional (for Docker deployment)

```bash
# Docker
docker --version

# Docker Compose
docker-compose --version
```

---

## Quick Start (Development)

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd ResumeBuilder

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download NLP models
python -m spacy download en_core_web_sm
```

### 2. Setup Local PostgreSQL

```bash
# Create database
sudo -u postgres psql -c "CREATE DATABASE resumebuilder;"
sudo -u postgres psql -c "CREATE USER resumeuser WITH PASSWORD 'resumepass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE resumebuilder TO resumeuser;"
```

### 3. Setup Local Redis

```bash
# Start Redis (if not running)
sudo systemctl start redis
# Or on macOS with Homebrew:
brew services start redis
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Minimal `.env` for local development:**

```bash
# Database
DATABASE_URL=postgresql://resumeuser:resumepass@localhost:5432/resumebuilder

# Redis
REDIS_URL=redis://localhost:6379

# API Keys
ANTHROPIC_API_KEY=your_api_key_here

# Email (Console for development)
EMAIL_PROVIDER=console

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here
```

### 5. Run Migrations

```bash
# Apply database migrations
alembic upgrade head
```

### 6. Start the Application

**Terminal 1 - API Server:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Webhook Worker:**
```bash
python scripts/run_webhook_worker.py
```

### 7. Access the API

- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **API Base:** http://localhost:8000/api/v1

---

## Local Production Setup (Docker Compose)

Production-like deployment using Docker Compose on your local machine.

### 1. Create Docker Compose File

Create `docker-compose.local.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:14-alpine
    container_name: resumebuilder-db
    environment:
      POSTGRES_DB: resumebuilder
      POSTGRES_USER: resumeuser
      POSTGRES_PASSWORD: resumepass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U resumeuser"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: resumebuilder-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # API Server
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: resumebuilder-api
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://resumeuser:resumepass@db:5432/resumebuilder
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
      - EMAIL_PROVIDER=console
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./:/app
    restart: unless-stopped

  # Webhook Worker
  webhook-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: resumebuilder-webhook-worker
    command: python scripts/run_webhook_worker.py
    environment:
      - DATABASE_URL=postgresql://resumeuser:resumepass@db:5432/resumebuilder
      - WEBHOOK_SLEEP_SECONDS=10
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./:/app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 2. Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download NLP models
RUN python -m spacy download en_core_web_sm

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Default command (can be overridden)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Create .env File

```bash
# Create .env for docker-compose
cat > .env << EOF
ANTHROPIC_API_KEY=your_api_key_here
SECRET_KEY=$(openssl rand -hex 32)
EOF
```

### 4. Start Services

```bash
# Build and start all services
docker-compose -f docker-compose.local.yml up -d

# View logs
docker-compose -f docker-compose.local.yml logs -f

# Run migrations (first time only)
docker-compose -f docker-compose.local.yml exec api alembic upgrade head
```

### 5. Stop Services

```bash
# Stop services
docker-compose -f docker-compose.local.yml down

# Stop and remove volumes (WARNING: deletes data)
docker-compose -f docker-compose.local.yml down -v
```

---

## Local Server Deployment

Deploy on a dedicated local server (e.g., Ubuntu 22.04 LTS).

### 1. Server Prerequisites

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3.10 \
    python3-pip \
    python3-venv \
    postgresql-14 \
    redis-server \
    nginx \
    git

# Install build dependencies
sudo apt install -y \
    build-essential \
    libpq-dev \
    python3-dev
```

### 2. Setup Application User

```bash
# Create application user
sudo useradd -m -s /bin/bash resumebuilder
sudo su - resumebuilder

# Clone repository
git clone <repository-url> /home/resumebuilder/app
cd /home/resumebuilder/app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Configure PostgreSQL

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE resumebuilder;
CREATE USER resumeuser WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE resumebuilder TO resumeuser;
\q
```

### 4. Configure Environment

```bash
# Create environment file
sudo nano /home/resumebuilder/app/.env
```

```bash
# Production .env
DATABASE_URL=postgresql://resumeuser:your_secure_password@localhost:5432/resumebuilder
REDIS_URL=redis://localhost:6379
ANTHROPIC_API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here
EMAIL_PROVIDER=smtp
SMTP_HOST=localhost
SMTP_PORT=25
```

### 5. Run Database Migrations

```bash
cd /home/resumebuilder/app
source venv/bin/activate
alembic upgrade head
```

### 6. Create Systemd Services

**API Service** - `/etc/systemd/system/resumebuilder-api.service`:

```ini
[Unit]
Description=ResumeBuilder API Server
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=resumebuilder
WorkingDirectory=/home/resumebuilder/app
Environment="PATH=/home/resumebuilder/app/venv/bin"
EnvironmentFile=/home/resumebuilder/app/.env
ExecStart=/home/resumebuilder/app/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Webhook Worker Service** - `/etc/systemd/system/resumebuilder-webhook-worker.service`:

```ini
[Unit]
Description=ResumeBuilder Webhook Worker
After=network.target postgresql.service

[Service]
Type=simple
User=resumebuilder
WorkingDirectory=/home/resumebuilder/app
Environment="PATH=/home/resumebuilder/app/venv/bin"
EnvironmentFile=/home/resumebuilder/app/.env
ExecStart=/home/resumebuilder/app/venv/bin/python scripts/run_webhook_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 7. Configure Nginx

Create `/etc/nginx/sites-available/resumebuilder`:

```nginx
server {
    listen 80;
    server_name localhost;  # Or your server's IP/domain

    # API endpoints
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (for streaming)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # API documentation
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
    }

    # Health checks
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/resumebuilder /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable resumebuilder-api
sudo systemctl enable resumebuilder-webhook-worker

# Start services
sudo systemctl start resumebuilder-api
sudo systemctl start resumebuilder-webhook-worker

# Check status
sudo systemctl status resumebuilder-api
sudo systemctl status resumebuilder-webhook-worker
```

### 9. View Logs

```bash
# API logs
sudo journalctl -u resumebuilder-api -f

# Webhook worker logs
sudo journalctl -u resumebuilder-webhook-worker -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## Database Setup

### Manual PostgreSQL Setup

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres createdb resumebuilder

# Create user with password
sudo -u postgres psql -c "CREATE USER resumeuser WITH PASSWORD 'your_password';"

# Grant privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE resumebuilder TO resumeuser;"

# Test connection
psql -U resumeuser -d resumebuilder -h localhost
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

---

## Environment Configuration

### Complete .env Template

```bash
# ============================================================================
# Database Configuration
# ============================================================================
DATABASE_URL=postgresql://resumeuser:password@localhost:5432/resumebuilder

# ============================================================================
# Redis Configuration
# ============================================================================
REDIS_URL=redis://localhost:6379

# ============================================================================
# API Keys
# ============================================================================
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# ============================================================================
# Security
# ============================================================================
# Generate with: openssl rand -hex 32
SECRET_KEY=your_secret_key_here

# JWT Settings
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ============================================================================
# Email Configuration
# ============================================================================
# Options: smtp, sendgrid, ses, console
EMAIL_PROVIDER=console

# SMTP Settings (if using smtp)
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=true
EMAIL_FROM=noreply@resumebuilder.local

# SendGrid Settings (if using sendgrid)
SENDGRID_API_KEY=

# AWS SES Settings (if using ses)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1

# ============================================================================
# Webhook Worker Configuration
# ============================================================================
WEBHOOK_PENDING_BATCH_SIZE=100
WEBHOOK_RETRY_BATCH_SIZE=100
WEBHOOK_SLEEP_SECONDS=10

# ============================================================================
# Application Settings
# ============================================================================
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

### Generating Secure Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate API key for testing
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Running the Application

### Development Mode

```bash
# Terminal 1 - API with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Webhook worker
python scripts/run_webhook_worker.py

# Terminal 3 - Watch logs
tail -f app.log
```

### Production Mode (Manual)

```bash
# API Server (with multiple workers)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Webhook Worker (in background)
nohup python scripts/run_webhook_worker.py > webhook_worker.log 2>&1 &
```

### Using Process Manager (PM2)

```bash
# Install PM2
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [
    {
      name: 'resumebuilder-api',
      script: 'venv/bin/uvicorn',
      args: 'main:app --host 0.0.0.0 --port 8000 --workers 4',
      cwd: '/home/resumebuilder/app',
      env: {
        NODE_ENV: 'production'
      }
    },
    {
      name: 'webhook-worker',
      script: 'venv/bin/python',
      args: 'scripts/run_webhook_worker.py',
      cwd: '/home/resumebuilder/app'
    }
  ]
};
EOF

# Start applications
pm2 start ecosystem.config.js

# View status
pm2 status

# View logs
pm2 logs

# Stop applications
pm2 stop all
```

---

## Testing the System

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "llm": "available"
}
```

### 2. Register User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
  }'
```

### 3. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=TestPassword123!"
```

Save the `access_token` from the response.

### 4. Create Resume

```bash
TOKEN="your_access_token_here"

curl -X POST http://localhost:8000/api/v1/resumes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior Python Developer",
    "raw_text": "John Doe\nSenior Python Developer\n\nExperience:\n- Led team..."
  }'
```

### 5. Create Webhook

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://localhost:9000/webhook",
    "events": ["resume.created", "export.completed"],
    "description": "Test webhook"
  }'
```

### 6. Export Resume

```bash
curl -X POST http://localhost:8000/api/v1/export/pdf \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_id": "your_resume_id",
    "template": "professional"
  }' \
  --output resume.pdf
```

### 7. Check Webhook Events

```bash
curl -X GET http://localhost:8000/api/v1/webhooks/{webhook_id}/events \
  -H "Authorization: Bearer $TOKEN"
```

---

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U resumeuser -d resumebuilder -h localhost

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Redis Connection Issues

```bash
# Check if Redis is running
sudo systemctl status redis

# Test connection
redis-cli ping

# Check Redis logs
sudo journalctl -u redis -f
```

### Port Already in Use

```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
```

### Migration Issues

```bash
# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head

# Or recreate database
sudo -u postgres dropdb resumebuilder
sudo -u postgres createdb resumebuilder
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE resumebuilder TO resumeuser;"
alembic upgrade head
```

### Webhook Worker Not Processing

```bash
# Check worker logs
tail -f webhook_worker.log

# Or if using systemd
sudo journalctl -u resumebuilder-webhook-worker -f

# Check pending events in database
psql -U resumeuser -d resumebuilder -c "SELECT COUNT(*) FROM webhook_events WHERE status='pending';"
```

### API Errors

```bash
# Check API logs
tail -f app.log

# Or if using systemd
sudo journalctl -u resumebuilder-api -f

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Permission Issues

```bash
# Fix file ownership
sudo chown -R resumebuilder:resumebuilder /home/resumebuilder/app

# Fix file permissions
sudo chmod -R 755 /home/resumebuilder/app
```

---

## Performance Tuning

### PostgreSQL Optimization

Edit `/etc/postgresql/14/main/postgresql.conf`:

```conf
# For systems with 4GB RAM
shared_buffers = 1GB
effective_cache_size = 3GB
maintenance_work_mem = 256MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
min_wal_size = 1GB
max_wal_size = 4GB
```

```bash
# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Nginx Optimization

Edit `/etc/nginx/nginx.conf`:

```nginx
worker_processes auto;
worker_connections 1024;

http {
    # Enable gzip
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript;

    # Client body size
    client_max_body_size 20M;

    # Timeouts
    keepalive_timeout 65;
    send_timeout 60;
}
```

---

## Backup and Restore

### Database Backup

```bash
# Create backup
pg_dump -U resumeuser resumebuilder > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
psql -U resumeuser resumebuilder < backup_20231203_120000.sql
```

### Automated Backups

Create `/home/resumebuilder/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/resumebuilder/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U resumeuser resumebuilder > $BACKUP_DIR/db_$DATE.sql

# Compress
gzip $BACKUP_DIR/db_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/db_$DATE.sql.gz"
```

Add to crontab:

```bash
# Run daily at 2 AM
0 2 * * * /home/resumebuilder/backup.sh
```

---

## Monitoring

### System Monitoring

```bash
# CPU and Memory
htop

# Disk usage
df -h

# Service status
systemctl status resumebuilder-api resumebuilder-webhook-worker

# Database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
```

### Application Metrics

Access built-in endpoints:

- **Health:** http://localhost:8000/health
- **API Stats:** http://localhost:8000/api/v1/stats
- **Cache Stats:** http://localhost:8000/api/v1/cache/stats
- **Analytics:** http://localhost:8000/api/v1/analytics/dashboard

---

## Security Checklist

- [ ] Use strong database passwords
- [ ] Keep SECRET_KEY secure and random
- [ ] Enable firewall (ufw)
- [ ] Configure fail2ban
- [ ] Regular security updates
- [ ] Backup database regularly
- [ ] Use HTTPS in production (Let's Encrypt)
- [ ] Restrict database access to localhost
- [ ] Monitor application logs
- [ ] Keep dependencies updated

---

## Next Steps

Once deployed locally:

1. **Test all endpoints** using API documentation at http://localhost:8000/docs
2. **Create test data** (users, resumes, webhooks)
3. **Monitor logs** to ensure everything works correctly
4. **Set up backups** for production data
5. **Configure monitoring** for system health

For production deployment to the internet, consider adding:
- HTTPS with Let's Encrypt/SSL certificates
- Domain name configuration
- Firewall rules (ufw/iptables)
- fail2ban for security
- Log rotation
- Automated backups

---

**Version:** 1.7.0-phase7
**Last Updated:** 2025-12-04
**Status:** Production Ready for Local Deployment
