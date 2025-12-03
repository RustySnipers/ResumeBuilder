# Webhook Background Worker Documentation

The webhook background worker automatically processes webhook events and handles delivery retries.

## Overview

The webhook worker is a continuously-running background service that:
- **Processes Pending Events**: Delivers newly created webhook events
- **Handles Retries**: Redelivers failed events with exponential backoff
- **Monitors Health**: Tracks processing statistics and health status
- **Graceful Shutdown**: Handles SIGTERM/SIGINT for clean shutdowns
- **Error Resilient**: Continues running even if individual deliveries fail

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Webhook Worker                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │   Process    │         │   Process    │                 │
│  │   Pending    │◄────────┤    Retry     │                 │
│  │   Events     │         │    Events    │                 │
│  └──────┬───────┘         └──────┬───────┘                 │
│         │                        │                          │
│         ├────────────────────────┘                          │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────┐                          │
│  │   WebhookService             │                          │
│  │   - deliver_event()          │                          │
│  │   - HMAC signature           │                          │
│  │   - HTTP POST delivery       │                          │
│  │   - Retry scheduling         │                          │
│  └──────────────────────────────┘                          │
│                                                              │
│  Sleep 10s → Repeat                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Installation

No additional dependencies required. The worker uses existing packages:
- `asyncio` - Async event loop
- `sqlalchemy` - Database access
- `httpx` - HTTP client (via WebhookService)

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | **Yes** | - | PostgreSQL connection URL |
| `WEBHOOK_PENDING_BATCH_SIZE` | No | 100 | Max pending events per cycle |
| `WEBHOOK_RETRY_BATCH_SIZE` | No | 100 | Max retry events per cycle |
| `WEBHOOK_SLEEP_SECONDS` | No | 10 | Sleep interval between cycles (seconds) |

### Example Configuration

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/resumebuilder"
export WEBHOOK_PENDING_BATCH_SIZE="100"
export WEBHOOK_RETRY_BATCH_SIZE="100"
export WEBHOOK_SLEEP_SECONDS="10"
```

## Running the Worker

### Method 1: Python Script (Recommended)

```bash
python scripts/run_webhook_worker.py
```

### Method 2: Python Module

```bash
python -m backend.webhooks.worker
```

### Method 3: Docker Container

```dockerfile
# In your Dockerfile
CMD ["python", "scripts/run_webhook_worker.py"]
```

```bash
docker run -e DATABASE_URL="..." your-image:tag
```

### Method 4: Systemd Service

```ini
# /etc/systemd/system/webhook-worker.service
[Unit]
Description=ResumeBuilder Webhook Worker
After=network.target postgresql.service

[Service]
Type=simple
User=resumebuilder
WorkingDirectory=/opt/resumebuilder
Environment="DATABASE_URL=postgresql://..."
Environment="WEBHOOK_SLEEP_SECONDS=10"
ExecStart=/usr/bin/python3 scripts/run_webhook_worker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable webhook-worker
sudo systemctl start webhook-worker
sudo systemctl status webhook-worker
```

## Operation

### Processing Cycle

Each cycle (default 10 seconds):

1. **Process Pending Events** (up to 100):
   - Query for events with status=`pending`
   - Order by creation time (FIFO)
   - Deliver via HTTP POST with HMAC signature
   - Update event status and delivery metadata

2. **Process Retry Events** (up to 100):
   - Query for events with status=`retrying` and `next_retry_at <= now`
   - Order by retry time (earliest first)
   - Redeliver via HTTP POST
   - Schedule next retry or mark as failed

3. **Sleep**: Wait configured interval before next cycle

### Retry Logic

Failed deliveries are automatically retried with exponential backoff:

| Attempt | Delay | Total Time |
|---------|-------|------------|
| 1 | Immediate | 0min |
| 2 | 2 minutes | 2min |
| 3 | 4 minutes | 6min |
| 4 | 8 minutes | 14min |

After max retries (default 3), events are marked as `failed`.

### Logging

The worker logs:
- **INFO**: Processing statistics, cycle completions, events processed
- **ERROR**: Delivery failures, database errors, fatal errors
- **Hourly**: Comprehensive statistics summary

Example output:
```
2025-12-03 10:30:00 - INFO - Webhook worker started
2025-12-03 10:30:00 - INFO - Pending batch size: 100
2025-12-03 10:30:00 - INFO - Retry batch size: 100
2025-12-03 10:30:00 - INFO - Sleep interval: 10s
2025-12-03 10:30:05 - INFO - Processed 5 pending webhook events
2025-12-03 10:30:05 - INFO - Cycle 1 complete: 5 pending, 0 retry (0.45s)
2025-12-03 10:30:15 - INFO - Processed 2 retry webhook events
2025-12-03 10:30:15 - INFO - Cycle 2 complete: 0 pending, 2 retry (0.23s)
```

## Health Monitoring

### Health Status

The worker tracks:
- **Uptime**: Total running time
- **Total Cycles**: Number of processing cycles completed
- **Events Processed**: Total pending + retry events processed
- **Last Cycle**: Timestamp of last successful cycle

### Health Check

The worker is considered **healthy** if:
- Status is `running`
- Last cycle completed within 2x sleep interval
- No fatal errors occurred

### Accessing Health Status

```python
# In your monitoring code
from backend.webhooks.worker import WebhookWorker

worker = WebhookWorker(database_url=...)
health = worker.get_health_status()

print(health)
# {
#     "status": "running",
#     "healthy": True,
#     "uptime_seconds": 3600.5,
#     "total_cycles": 360,
#     "total_events_processed": 1250,
#     "pending_processed": 800,
#     "retry_processed": 450,
#     "last_cycle": "2025-12-03T11:30:00"
# }
```

## Graceful Shutdown

The worker handles shutdown signals gracefully:

### SIGTERM / SIGINT (Ctrl+C)
1. Stop accepting new cycles
2. Complete current cycle if processing
3. Close database connections
4. Log final statistics
5. Exit cleanly

Example:
```bash
# Send SIGTERM
kill -TERM <pid>

# Or Ctrl+C
^C
```

Output:
```
2025-12-03 10:35:00 - INFO - Received signal 2, initiating graceful shutdown...
2025-12-03 10:35:00 - INFO - Shutting down webhook worker...
2025-12-03 10:35:00 - INFO - Database connections closed
============================================================
Webhook Worker Statistics
============================================================
Uptime: 0.08 hours
Total cycles: 30
Pending events processed: 15
Retry events processed: 5
Total events processed: 20
Average events per cycle: 0.67
Last cycle: 2025-12-03T10:34:55
============================================================
2025-12-03 10:35:00 - INFO - Webhook worker shutdown complete
```

## Production Deployment

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webhook-worker
spec:
  replicas: 1  # Single instance recommended
  selector:
    matchLabels:
      app: webhook-worker
  template:
    metadata:
      labels:
        app: webhook-worker
    spec:
      containers:
      - name: webhook-worker
        image: resumebuilder:1.7.0
        command: ["python", "scripts/run_webhook_worker.py"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: WEBHOOK_SLEEP_SECONDS
          value: "10"
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import sys; sys.exit(0)"
          initialDelaySeconds: 30
          periodSeconds: 60
```

### Docker Compose

```yaml
version: '3.8'

services:
  webhook-worker:
    build: .
    command: python scripts/run_webhook_worker.py
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/resumebuilder
      - WEBHOOK_SLEEP_SECONDS=10
    depends_on:
      - db
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Scaling Considerations

**Single Instance Recommended**:
- Webhook processing is idempotent but concurrent processing may cause duplicate deliveries
- Single worker ensures events are delivered in order
- For high-volume scenarios, increase batch sizes instead of replicas

**High Volume Tuning**:
```bash
export WEBHOOK_PENDING_BATCH_SIZE="500"
export WEBHOOK_RETRY_BATCH_SIZE="500"
export WEBHOOK_SLEEP_SECONDS="5"
```

## Monitoring

### Metrics to Track

1. **Events Processed** - Total and per-cycle average
2. **Delivery Success Rate** - Success vs. failed deliveries
3. **Retry Rate** - Percentage of events requiring retries
4. **Cycle Duration** - Time to process one cycle
5. **Queue Depth** - Number of pending events waiting
6. **Worker Uptime** - Continuous operation time

### Prometheus Metrics (Future Enhancement)

```python
# Example metrics to expose
webhook_events_processed_total{type="pending|retry"}
webhook_delivery_success_rate
webhook_cycle_duration_seconds
webhook_queue_depth{status="pending|retrying"}
webhook_worker_uptime_seconds
```

## Troubleshooting

### Worker Not Processing Events

1. **Check database connection**:
   ```bash
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM webhook_events WHERE status='pending';"
   ```

2. **Check worker logs**:
   ```bash
   tail -f webhook-worker.log
   ```

3. **Verify webhooks are active**:
   ```bash
   psql $DATABASE_URL -c "SELECT id, url, is_active FROM webhooks;"
   ```

### High Retry Rate

**Possible causes**:
- Webhook endpoints are down or slow
- Network connectivity issues
- Invalid HMAC signatures (check webhook secrets)

**Solutions**:
- Check webhook endpoint health
- Increase timeout: Update `webhook.timeout_seconds`
- Verify network connectivity
- Check delivery logs for specific errors

### Database Connection Errors

**Error**: `could not connect to server`

**Solutions**:
- Verify DATABASE_URL is correct
- Check database is running
- Verify network connectivity
- Check connection pool settings

### Memory Issues

**Error**: `MemoryError` or high memory usage

**Solutions**:
- Reduce batch sizes:
  ```bash
  export WEBHOOK_PENDING_BATCH_SIZE="50"
  export WEBHOOK_RETRY_BATCH_SIZE="50"
  ```
- Increase sleep interval:
  ```bash
  export WEBHOOK_SLEEP_SECONDS="30"
  ```
- Monitor with `docker stats` or `htop`

## Best Practices

1. **Single Worker**: Run only one worker instance to avoid duplicate deliveries
2. **Monitor Logs**: Set up log aggregation (ELK, Splunk, CloudWatch)
3. **Alert on Failures**: Alert if worker stops or error rate increases
4. **Database Connection Pool**: Configure appropriate pool size for load
5. **Resource Limits**: Set CPU/memory limits in container orchestration
6. **Graceful Deploys**: Use rolling deployments with SIGTERM handling
7. **Regular Cleanup**: Implement periodic cleanup of old webhook events

## Testing

### Local Testing

1. **Start database**:
   ```bash
   docker-compose up -d db
   ```

2. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Start worker**:
   ```bash
   export DATABASE_URL="postgresql://localhost/resumebuilder"
   python scripts/run_webhook_worker.py
   ```

4. **Create test webhook**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/webhooks \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"url":"https://webhook.site/test","events":["export.completed"]}'
   ```

5. **Trigger event**:
   ```bash
   # Export a resume to trigger export.completed event
   curl -X POST http://localhost:8000/api/v1/export/pdf \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"resume_id":"..."}'
   ```

6. **Watch logs**: Worker should process and deliver the event within 10 seconds

## Version

- **Worker Version**: 1.7.0-phase7
- **Date**: 2025-12-03
- **Status**: Production Ready

## See Also

- [WEBHOOK_INTEGRATION.md](./WEBHOOK_INTEGRATION.md) - Webhook integration guide
- [PROJECT_STATUS.md](./PROJECT_STATUS.md) - Project status and documentation
- [backend/webhooks/service.py](./backend/webhooks/service.py) - Webhook service implementation
