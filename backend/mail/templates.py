"""
Email Templates

Pre-built HTML email templates for various email types.
"""


class EmailTemplates:
    """Collection of email templates."""

    @staticmethod
    def _base_template(title: str, content: str) -> str:
        """Base email template with consistent styling."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 32px;
            font-weight: bold;
            color: #4F46E5;
            margin-bottom: 10px;
        }}
        .content {{
            margin-bottom: 30px;
        }}
        .button {{
            display: inline-block;
            padding: 14px 32px;
            background-color: #4F46E5;
            color: #ffffff;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }}
        .button:hover {{
            background-color: #4338CA;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            font-size: 14px;
            color: #6b7280;
            text-align: center;
        }}
        .code {{
            background-color: #f3f4f6;
            padding: 12px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 18px;
            letter-spacing: 2px;
            text-align: center;
            margin: 20px 0;
        }}
        .warning {{
            background-color: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 12px;
            margin: 20px 0;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">ResumeBuilder</div>
            <p style="color: #6b7280; margin: 0;">AI-Powered Resume Optimization</p>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p>This email was sent by ResumeBuilder</p>
            <p>If you didn't request this email, please ignore it.</p>
            <p style="margin-top: 20px;">
                <a href="https://resumebuilder.com" style="color: #4F46E5; text-decoration: none;">ResumeBuilder</a> |
                <a href="https://resumebuilder.com/privacy" style="color: #4F46E5; text-decoration: none;">Privacy Policy</a> |
                <a href="https://resumebuilder.com/support" style="color: #4F46E5; text-decoration: none;">Support</a>
            </p>
        </div>
    </div>
</body>
</html>
"""

    @staticmethod
    def verification_email(verification_link: str) -> str:
        """
        Email verification template.

        Args:
            verification_link: URL to verify email

        Returns:
            HTML email content
        """
        content = f"""
            <h2 style="color: #111827; margin-bottom: 20px;">Verify Your Email Address</h2>
            <p>Thank you for registering with ResumeBuilder!</p>
            <p>To complete your registration and start building ATS-optimized resumes, please verify your email address by clicking the button below:</p>
            <div style="text-align: center;">
                <a href="{verification_link}" class="button">Verify Email Address</a>
            </div>
            <p>Or copy and paste this link into your browser:</p>
            <div class="code">{verification_link}</div>
            <div class="warning">
                <strong>⚠️ Security Note:</strong> This verification link will expire in 24 hours. If you didn't create an account with ResumeBuilder, please ignore this email.
            </div>
        """
        return EmailTemplates._base_template("Verify Your Email", content)

    @staticmethod
    def password_reset_email(reset_link: str) -> str:
        """
        Password reset template.

        Args:
            reset_link: URL to reset password

        Returns:
            HTML email content
        """
        content = f"""
            <h2 style="color: #111827; margin-bottom: 20px;">Reset Your Password</h2>
            <p>We received a request to reset your ResumeBuilder account password.</p>
            <p>To reset your password, click the button below:</p>
            <div style="text-align: center;">
                <a href="{reset_link}" class="button">Reset Password</a>
            </div>
            <p>Or copy and paste this link into your browser:</p>
            <div class="code">{reset_link}</div>
            <div class="warning">
                <strong>⚠️ Security Note:</strong> This password reset link will expire in 1 hour. If you didn't request a password reset, please ignore this email and your password will remain unchanged.
            </div>
            <p>For security reasons, we recommend choosing a strong password that you don't use for other accounts.</p>
        """
        return EmailTemplates._base_template("Reset Your Password", content)

    @staticmethod
    def welcome_email(name: str) -> str:
        """
        Welcome email template.

        Args:
            name: User's name

        Returns:
            HTML email content
        """
        content = f"""
            <h2 style="color: #111827; margin-bottom: 20px;">Welcome to ResumeBuilder! 🎉</h2>
            <p>Hi {name},</p>
            <p>Welcome to ResumeBuilder - your AI-powered resume optimization platform!</p>
            <p>You now have access to:</p>
            <ul style="line-height: 2;">
                <li><strong>AI-Powered Optimization:</strong> Claude AI analyzes and enhances your resume</li>
                <li><strong>ATS Compatibility:</strong> Ensure your resume passes Applicant Tracking Systems</li>
                <li><strong>Semantic Analysis:</strong> Advanced NLP for keyword matching</li>
                <li><strong>Professional Templates:</strong> 4 ATS-friendly resume templates</li>
                <li><strong>Export Options:</strong> Download as PDF or DOCX</li>
            </ul>
            <div style="text-align: center;">
                <a href="https://resumebuilder.com/dashboard" class="button">Get Started</a>
            </div>
            <h3 style="color: #111827; margin-top: 40px;">Quick Start Guide</h3>
            <ol style="line-height: 2;">
                <li>Upload your current resume</li>
                <li>Paste the job description you're targeting</li>
                <li>Let our AI analyze and optimize your resume</li>
                <li>Download your ATS-friendly resume</li>
            </ol>
            <p>Need help? Check out our <a href="https://resumebuilder.com/docs" style="color: #4F46E5;">documentation</a> or contact our <a href="https://resumebuilder.com/support" style="color: #4F46E5;">support team</a>.</p>
        """
        return EmailTemplates._base_template("Welcome to ResumeBuilder", content)

    @staticmethod
    def password_changed_email(name: str) -> str:
        """
        Password changed confirmation template.

        Args:
            name: User's name

        Returns:
            HTML email content
        """
        content = f"""
            <h2 style="color: #111827; margin-bottom: 20px;">Password Changed Successfully</h2>
            <p>Hi {name},</p>
            <p>This email confirms that your ResumeBuilder account password was successfully changed.</p>
            <p><strong>When:</strong> Just now</p>
            <p><strong>IP Address:</strong> [Logged]</p>
            <div class="warning">
                <strong>⚠️ Didn't make this change?</strong> If you didn't change your password, please contact our support team immediately at <a href="mailto:support@resumebuilder.com" style="color: #f59e0b;">support@resumebuilder.com</a>
            </div>
            <p>For your security, we recommend:</p>
            <ul>
                <li>Using a unique password for your ResumeBuilder account</li>
                <li>Enabling two-factor authentication (coming soon)</li>
                <li>Not sharing your password with anyone</li>
            </ul>
        """
        return EmailTemplates._base_template("Password Changed", content)

    @staticmethod
    def account_locked_email(name: str, unlock_time: str) -> str:
        """
        Account locked notification template.

        Args:
            name: User's name
            unlock_time: When account will be unlocked

        Returns:
            HTML email content
        """
        content = f"""
            <h2 style="color: #dc2626; margin-bottom: 20px;">🔒 Account Temporarily Locked</h2>
            <p>Hi {name},</p>
            <p>Your ResumeBuilder account has been temporarily locked due to multiple failed login attempts.</p>
            <p><strong>Unlock Time:</strong> {unlock_time}</p>
            <div class="warning">
                <strong>⚠️ Security Alert:</strong> If these login attempts weren't made by you, your account may be at risk. Please reset your password immediately after your account is unlocked.
            </div>
            <p>To regain access to your account:</p>
            <ol>
                <li>Wait until {unlock_time}</li>
                <li>Try logging in again with the correct password</li>
                <li>If you've forgotten your password, use the "Forgot Password" option</li>
            </ol>
            <p>Need help? Contact us at <a href="mailto:support@resumebuilder.com" style="color: #4F46E5;">support@resumebuilder.com</a></p>
        """
        return EmailTemplates._base_template("Account Locked", content)
