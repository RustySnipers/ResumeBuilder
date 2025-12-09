"""
Email Service

Provides email sending functionality with support for multiple providers.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class EmailProvider(Enum):
    """Supported email providers."""
    SMTP = "smtp"
    SENDGRID = "sendgrid"
    AWS_SES = "aws_ses"
    CONSOLE = "console"  # For development - logs to console


@dataclass
class EmailConfig:
    """Email service configuration."""
    provider: EmailProvider = EmailProvider.SMTP
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    from_email: str = "noreply@resumebuilder.com"
    from_name: str = "ResumeBuilder"

    @classmethod
    def from_env(cls) -> "EmailConfig":
        """Create configuration from environment variables."""
        provider_str = os.getenv("EMAIL_PROVIDER", "console").lower()
        provider = EmailProvider.CONSOLE

        if provider_str == "smtp":
            provider = EmailProvider.SMTP
        elif provider_str == "sendgrid":
            provider = EmailProvider.SENDGRID
        elif provider_str == "aws_ses":
            provider = EmailProvider.AWS_SES

        return cls(
            provider=provider,
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            from_email=os.getenv("SMTP_FROM", "noreply@resumebuilder.com"),
            from_name=os.getenv("SMTP_FROM_NAME", "ResumeBuilder"),
        )


class EmailService:
    """
    Email service for sending emails via multiple providers.

    Usage:
        config = EmailConfig.from_env()
        service = EmailService(config)
        await service.send_email(
            to="user@example.com",
            subject="Welcome",
            html_body="<h1>Hello!</h1>"
        )
    """

    def __init__(self, config: Optional[EmailConfig] = None):
        """
        Initialize email service.

        Args:
            config: Email configuration. If None, loads from environment.
        """
        self.config = config or EmailConfig.from_env()
        logger.info(f"Email service initialized with provider: {self.config.provider.value}")

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (fallback)
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            if self.config.provider == EmailProvider.CONSOLE:
                return self._send_console(to, subject, html_body)
            elif self.config.provider == EmailProvider.SMTP:
                return self._send_smtp(to, subject, html_body, text_body, cc, bcc)
            elif self.config.provider == EmailProvider.SENDGRID:
                return self._send_sendgrid(to, subject, html_body, text_body)
            elif self.config.provider == EmailProvider.AWS_SES:
                return self._send_aws_ses(to, subject, html_body, text_body)
            else:
                logger.error(f"Unsupported email provider: {self.config.provider}")
                return False

        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False

    def _send_console(self, to: str, subject: str, html_body: str) -> bool:
        """Send email to console (development mode)."""
        logger.info(f"""
        ========================================
        EMAIL (Console Mode)
        ========================================
        To: {to}
        From: {self.config.from_email}
        Subject: {subject}
        ========================================
        {html_body}
        ========================================
        """)
        return True

    def _send_smtp(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """Send email via SMTP."""
        if not self.config.smtp_host:
            logger.error("SMTP_HOST not configured")
            return False

        # Create message
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
        msg["To"] = to
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = ", ".join(cc)
        if bcc:
            msg["Bcc"] = ", ".join(bcc)

        # Add plain text part
        if text_body:
            part1 = MIMEText(text_body, "plain")
            msg.attach(part1)

        # Add HTML part
        part2 = MIMEText(html_body, "html")
        msg.attach(part2)

        # Send email
        try:
            if self.config.smtp_use_tls:
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                    server.starttls()
                    if self.config.smtp_user and self.config.smtp_password:
                        server.login(self.config.smtp_user, self.config.smtp_password)

                    recipients = [to]
                    if cc:
                        recipients.extend(cc)
                    if bcc:
                        recipients.extend(bcc)

                    server.sendmail(self.config.from_email, recipients, msg.as_string())
            else:
                with smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port) as server:
                    if self.config.smtp_user and self.config.smtp_password:
                        server.login(self.config.smtp_user, self.config.smtp_password)

                    recipients = [to]
                    if cc:
                        recipients.extend(cc)
                    if bcc:
                        recipients.extend(bcc)

                    server.sendmail(self.config.from_email, recipients, msg.as_string())

            logger.info(f"Email sent successfully to {to}")
            return True

        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False

    def _send_sendgrid(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """Send email via SendGrid API."""
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content

            sg = sendgrid.SendGridAPIClient(api_key=self.config.smtp_password)

            from_email = Email(self.config.from_email, self.config.from_name)
            to_email = To(to)
            content = Content("text/html", html_body)

            mail = Mail(from_email, to_email, subject, content)

            if text_body:
                mail.add_content(Content("text/plain", text_body))

            response = sg.client.mail.send.post(request_body=mail.get())

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully via SendGrid to {to}")
                return True
            else:
                logger.error(f"SendGrid error: {response.status_code}")
                return False

        except ImportError:
            logger.error("SendGrid library not installed. Install with: pip install sendgrid")
            return False
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return False

    def _send_aws_ses(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
    ) -> bool:
        """Send email via AWS SES."""
        try:
            import boto3

            ses = boto3.client('ses', region_name=os.getenv('AWS_REGION', 'us-east-1'))

            email_data = {
                'Source': f"{self.config.from_name} <{self.config.from_email}>",
                'Destination': {'ToAddresses': [to]},
                'Message': {
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {}
                }
            }

            if text_body:
                email_data['Message']['Body']['Text'] = {
                    'Data': text_body,
                    'Charset': 'UTF-8'
                }

            email_data['Message']['Body']['Html'] = {
                'Data': html_body,
                'Charset': 'UTF-8'
            }

            response = ses.send_email(**email_data)

            logger.info(f"Email sent successfully via AWS SES to {to}: {response['MessageId']}")
            return True

        except ImportError:
            logger.error("Boto3 library not installed. Install with: pip install boto3")
            return False
        except Exception as e:
            logger.error(f"AWS SES error: {e}")
            return False

    async def send_verification_email(self, to: str, verification_token: str, base_url: str) -> bool:
        """
        Send email verification email.

        Args:
            to: User email address
            verification_token: Verification token
            base_url: Base URL of the application

        Returns:
            True if email was sent successfully
        """
        from .templates import EmailTemplates

        verification_link = f"{base_url}/auth/verify-email?token={verification_token}"

        html_body = EmailTemplates.verification_email(
            verification_link=verification_link
        )

        return await self.send_email(
            to=to,
            subject="Verify Your ResumeBuilder Account",
            html_body=html_body
        )

    async def send_password_reset_email(self, to: str, reset_token: str, base_url: str) -> bool:
        """
        Send password reset email.

        Args:
            to: User email address
            reset_token: Password reset token
            base_url: Base URL of the application

        Returns:
            True if email was sent successfully
        """
        from .templates import EmailTemplates

        reset_link = f"{base_url}/auth/reset-password?token={reset_token}"

        html_body = EmailTemplates.password_reset_email(
            reset_link=reset_link
        )

        return await self.send_email(
            to=to,
            subject="Reset Your ResumeBuilder Password",
            html_body=html_body
        )

    async def send_welcome_email(self, to: str, name: str) -> bool:
        """
        Send welcome email after successful registration.

        Args:
            to: User email address
            name: User name

        Returns:
            True if email was sent successfully
        """
        from .templates import EmailTemplates

        html_body = EmailTemplates.welcome_email(name=name)

        return await self.send_email(
            to=to,
            subject="Welcome to ResumeBuilder!",
            html_body=html_body
        )
