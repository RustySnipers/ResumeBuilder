"""
Email Service Module

Provides email sending capabilities for:
- Email verification
- Password reset
- Notifications

Supports multiple providers:
- SMTP (generic)
- SendGrid
- AWS SES
"""

from .service import EmailService, EmailConfig
from .templates import EmailTemplates

__all__ = ["EmailService", "EmailConfig", "EmailTemplates"]
