# Webhook Integration Documentation

This document describes the webhook event triggers integrated into the ResumeBuilder API endpoints.

## Overview

Webhook events are automatically triggered when specific actions occur in the system. Users can subscribe to these events by creating webhooks through the API (`POST /api/v1/webhooks`).

## Integrated Endpoints

### 1. Export Endpoints

#### PDF Export: `POST /api/v1/export/pdf`

**Success Event:** `export.completed`
- **Triggered:** After successful PDF generation and caching
- **Event ID:** Resume UUID
- **Payload:**
  ```json
  {
    "resume_id": "uuid",
    "user_id": "uuid",
    "format": "pdf",
    "template": "professional|modern|classic|minimal",
    "size_bytes": 123456,
    "title": "Resume Title"
  }
  ```

**Failure Event:** `export.failed`
- **Triggered:** When PDF generation fails
- **Event ID:** Resume UUID
- **Payload:**
  ```json
  {
    "resume_id": "uuid",
    "user_id": "uuid",
    "format": "pdf",
    "template": "professional|modern|classic|minimal",
    "error": "Error message",
    "title": "Resume Title"
  }
  ```

#### DOCX Export: `POST /api/v1/export/docx`

**Success Event:** `export.completed`
- **Triggered:** After successful DOCX generation and caching
- **Event ID:** Resume UUID
- **Payload:**
  ```json
  {
    "resume_id": "uuid",
    "user_id": "uuid",
    "format": "docx",
    "template": "professional|modern|classic|minimal",
    "size_bytes": 123456,
    "title": "Resume Title"
  }
  ```

**Failure Event:** `export.failed`
- **Triggered:** When DOCX generation fails
- **Event ID:** Resume UUID
- **Payload:**
  ```json
  {
    "resume_id": "uuid",
    "user_id": "uuid",
    "format": "docx",
    "template": "professional|modern|classic|minimal",
    "error": "Error message",
    "title": "Resume Title"
  }
  ```

### 2. Resume Endpoints

#### Resume Creation: `POST /api/v1/resumes`

**Event:** `resume.created`
- **Triggered:** When user creates a new resume
- **Event ID:** Resume UUID
- **Payload:**
  ```json
  {
    "resume_id": "uuid",
    "user_id": "uuid",
    "title": "Resume Title",
    "version": 1,
    "created_at": "2025-12-03T10:30:45.123456"
  }
  ```

#### Resume Update: `PUT /api/v1/resumes/{id}`

**Event:** `resume.updated`
- **Triggered:** When user updates an existing resume
- **Event ID:** Resume UUID
- **Payload:**
  ```json
  {
    "resume_id": "uuid",
    "user_id": "uuid",
    "title": "Updated Resume Title",
    "version": 1,
    "updated_at": "2025-12-03T11:45:30.123456"
  }
  ```

#### Resume Deletion: `DELETE /api/v1/resumes/{id}`

**Event:** `resume.deleted`
- **Triggered:** When user deletes a resume
- **Event ID:** Resume UUID
- **Payload:**
  ```json
  {
    "resume_id": "uuid",
    "user_id": "uuid",
    "title": "Deleted Resume Title",
    "version": 1,
    "deleted_at": "2025-12-03T12:00:00.123456"
  }
  ```

### 3. Authentication Endpoints

#### Email Verification: `POST /auth/verify-email`

**Event:** `user.email_verified`
- **Triggered:** When user successfully verifies their email address
- **Event ID:** User UUID
- **Payload:**
  ```json
  {
    "user_id": "uuid",
    "email": "user@example.com",
    "full_name": "User Name",
    "verified_at": "2025-12-03T10:30:45.123456"
  }
  ```

#### Password Change: `POST /auth/change-password`

**Event:** `user.password_changed`
- **Triggered:** When user successfully changes their password
- **Event ID:** User UUID
- **Payload:**
  ```json
  {
    "user_id": "uuid",
    "email": "user@example.com",
    "full_name": "User Name",
    "changed_at": "2025-12-03T10:30:45.123456"
  }
  ```

## Event Flow

1. **Action Occurs:** User performs an action (export, email verification, password change)
2. **Event Created:** If user has active webhooks subscribed to that event type, webhook events are created
3. **Background Delivery:** Events are queued for delivery (manual processing currently required)
4. **HTTP POST:** Webhook service delivers event to configured URL with HMAC signature
5. **Retry Logic:** Failed deliveries are automatically retried with exponential backoff

## Error Handling

Webhook triggers use graceful error handling:
- Webhook failures do **NOT** affect the main operation
- Errors are logged but the original action (export, verification, etc.) still succeeds
- This ensures webhook issues don't disrupt user experience

## Currently Not Integrated

The following endpoints do **NOT** currently trigger webhooks because they lack necessary context (authentication, entity IDs, or database persistence):

### Analysis & Generation Operations
- `POST /api/v1/analyze` - Analysis endpoint (no auth, no persistence)
- `POST /api/v1/generate` - Generation endpoint (no auth, no persistence)
- `POST /api/v1/generate/stream` - Streaming generation (no auth, no persistence)

**Potential Events (not yet integrated):**
- `analysis.completed` - Would trigger after successful analysis
- `analysis.failed` - Would trigger when analysis fails
- `generation.completed` - Would trigger after successful generation
- `generation.failed` - Would trigger when generation fails

## Future Enhancements

### Recommended Next Steps

1. **Enhance Analysis/Generation Endpoints:**
   - Add authentication requirement
   - Add database persistence for analysis results
   - Integrate webhook triggers

3. **Background Worker:**
   - Implement automatic webhook event processing
   - Continuous retry handling
   - Health monitoring

4. **Manual Webhook Processing:**
   Currently, webhook events need manual processing:
   ```python
   from backend.webhooks.service import WebhookService
   from backend.database import AsyncSessionLocal

   async with AsyncSessionLocal() as session:
       webhook_service = WebhookService(session)
       # Process pending events
       await webhook_service.process_pending_events(limit=100)
       # Process retry events
       await webhook_service.process_retry_events(limit=100)
   ```

## Testing Webhooks

### Create a Test Webhook

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.site/your-unique-url",
    "events": [
      "resume.created",
      "resume.updated",
      "resume.deleted",
      "export.completed",
      "user.email_verified",
      "user.password_changed"
    ],
    "description": "Test webhook",
    "timeout_seconds": 30,
    "max_retries": 3
  }'
```

### Trigger Events

1. **Resume Events:** Create, update, or delete a resume
   ```bash
   # Create resume
   curl -X POST http://localhost:8000/api/v1/resumes \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title":"Test Resume","raw_text":"Resume content..."}'

   # Update resume
   curl -X PUT http://localhost:8000/api/v1/resumes/{id} \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title":"Updated Resume"}'

   # Delete resume
   curl -X DELETE http://localhost:8000/api/v1/resumes/{id} \
     -H "Authorization: Bearer $TOKEN"
   ```

2. **Export Event:** Export a resume as PDF or DOCX
3. **Email Verification Event:** Verify an email address
4. **Password Change Event:** Change your password

### Verify Delivery

Check webhook delivery logs:
```bash
curl -X GET http://localhost:8000/api/v1/webhooks/{webhook_id}/events \
  -H "Authorization: Bearer $TOKEN"
```

## Webhook Payload Verification

Receivers should verify HMAC signatures to ensure authenticity:

```python
import hmac
import hashlib

def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify webhook HMAC signature."""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, f"sha256={expected_signature}")

# In your webhook receiver:
signature = request.headers.get('X-Webhook-Signature')
payload = request.body.decode('utf-8')

if verify_webhook_signature(payload, signature, webhook_secret):
    # Process webhook
    pass
else:
    # Invalid signature
    return 401
```

## Implementation Details

### Files Modified/Created
- `backend/export/router.py` - Added webhook triggers to PDF and DOCX export endpoints
- `backend/auth/router.py` - Added webhook triggers to email verification and password change endpoints
- `backend/resumes/router.py` - Created resume CRUD endpoints with webhook triggers (NEW)
- `backend/resumes/schemas.py` - Created resume API schemas (NEW)
- `main.py` - Integrated resume router

### Dependencies Added
- `WebhookService` from `backend.webhooks.service`
- `WebhookEventType` from `backend.models.webhook`

### Error Handling Pattern
All webhook triggers follow this pattern:
```python
try:
    webhook_service = WebhookService(session)
    await webhook_service.trigger_event(
        event_type=WebhookEventType.EVENT_NAME,
        event_id=entity_id,
        payload={...},
        user_id=user_id,
    )
    await session.commit()
except Exception as webhook_error:
    logger.error(f"Failed to trigger webhook: {webhook_error}")
    # Continue with main flow
```

## Version

- **Integration Version:** 1.7.0-phase7
- **Date:** 2025-12-03
- **Integrated Events:** 7 event types across 7 endpoints
  - `export.completed` (PDF and DOCX)
  - `export.failed` (PDF and DOCX)
  - `user.email_verified`
  - `user.password_changed`
  - `resume.created` (NEW)
  - `resume.updated` (NEW)
  - `resume.deleted` (NEW)
