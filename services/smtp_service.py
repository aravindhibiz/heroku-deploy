"""
SMTP Email Service for sending emails via SMTP (Outlook/Office365)
Replaces SendGrid service with SMTP-based email delivery
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class SMTPService:
    """Service for sending emails via SMTP (Outlook/Office365)"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_pass: str,
        from_email: str,
        smtp_secure: bool = False
    ):
        """
        Initialize SMTP service

        Args:
            smtp_host: SMTP server hostname (e.g., smtp.office365.com)
            smtp_port: SMTP server port (e.g., 587 for TLS)
            smtp_user: SMTP username/email
            smtp_pass: SMTP password
            from_email: Default sender email address
            smtp_secure: Use SMTP_SSL if True, otherwise use STARTTLS
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.from_email = from_email
        self.smtp_secure = smtp_secure

        logger.info(f"SMTP Service initialized with host: {smtp_host}:{smtp_port}")

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and return authenticated SMTP connection"""
        try:
            print(f"🔌 Connecting to SMTP server: {self.smtp_host}:{self.smtp_port}")

            if self.smtp_secure:
                # Use SMTP_SSL for secure connection
                print("  Using SMTP_SSL (direct SSL connection)")
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            else:
                # Use SMTP with STARTTLS
                print("  Using SMTP with STARTTLS")
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                print("  Sending EHLO...")
                server.ehlo()
                print("  Starting TLS...")
                server.starttls()
                print("  Sending EHLO again after TLS...")
                server.ehlo()

            # Login to SMTP server
            print(f"  Authenticating as: {self.smtp_user}")
            server.login(self.smtp_user, self.smtp_pass)
            print("✅ Successfully connected and authenticated to SMTP server")
            logger.info("Successfully connected and authenticated to SMTP server")
            return server

        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP Authentication failed for user {self.smtp_user}: {e}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            raise Exception(f"Email authentication failed. Please check your username and password. Error: {e}")
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {e}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            raise Exception(f"Email server error: {e}")
        except Exception as e:
            error_msg = f"Failed to connect to SMTP server {self.smtp_host}:{self.smtp_port}: {e}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            raise Exception(f"Failed to connect to email server: {e}")

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send HTML email via SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            from_email: Sender email (defaults to configured from_email)
            from_name: Sender name
            reply_to: Reply-to email address
            cc: List of CC recipients
            bcc: List of BCC recipients

        Returns:
            Dict with success status and message
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['To'] = to_email

            # Set from address
            sender_email = from_email or self.from_email
            if from_name:
                msg['From'] = f"{from_name} <{sender_email}>"
            else:
                msg['From'] = sender_email

            # Set reply-to if provided
            if reply_to:
                msg['Reply-To'] = reply_to

            # Set CC if provided
            if cc:
                msg['Cc'] = ', '.join(cc)

            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Prepare recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Send email
            server = self._create_smtp_connection()
            server.sendmail(sender_email, recipients, msg.as_string())
            server.quit()

            logger.info(f"Email sent successfully to {to_email}")
            return {
                'success': True,
                'message': f'Email sent to {to_email}',
                'status_code': 200
            }

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return {
                'success': False,
                'message': str(e),
                'status_code': 500
            }

    def send_plain_text_email(
        self,
        to_email: str,
        subject: str,
        text_content: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send plain text email via SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            text_content: Plain text content
            from_email: Sender email
            from_name: Sender name

        Returns:
            Dict with success status and message
        """
        # Convert plain text to simple HTML
        html_content = f"<html><body><pre>{text_content}</pre></body></html>"
        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            from_email=from_email,
            from_name=from_name
        )

    def send_email_with_attachment(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        attachments: List[Dict[str, Any]],
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email with file attachments via SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            attachments: List of dicts with 'filename', 'content' (bytes), and optional 'content_type'
            from_email: Sender email
            from_name: Sender name
            reply_to: Reply-to email address

        Returns:
            Dict with success status and message
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['To'] = to_email

            # Set from address
            sender_email = from_email or self.from_email
            if from_name:
                msg['From'] = f"{from_name} <{sender_email}>"
            else:
                msg['From'] = sender_email

            # Set reply-to if provided
            if reply_to:
                msg['Reply-To'] = reply_to

            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Attach files
            for attachment in attachments:
                filename = attachment.get('filename', 'attachment')
                content = attachment.get('content')
                content_type = attachment.get('content_type', 'application/octet-stream')

                if content:
                    # Create attachment part
                    part = MIMEBase('application', 'octet-stream')

                    # Handle both bytes and file paths
                    if isinstance(content, bytes):
                        part.set_payload(content)
                    elif isinstance(content, str) and os.path.isfile(content):
                        with open(content, 'rb') as f:
                            part.set_payload(f.read())
                    else:
                        logger.warning(f"Invalid attachment content for {filename}")
                        continue

                    # Encode attachment
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    msg.attach(part)

            # Send email
            server = self._create_smtp_connection()
            server.sendmail(sender_email, [to_email], msg.as_string())
            server.quit()

            logger.info(f"Email with attachments sent successfully to {to_email}")
            return {
                'success': True,
                'message': f'Email with attachments sent to {to_email}',
                'status_code': 200
            }

        except Exception as e:
            logger.error(f"Failed to send email with attachments to {to_email}: {e}")
            return {
                'success': False,
                'message': str(e),
                'status_code': 500
            }

    def verify_connection(self) -> bool:
        """
        Verify SMTP connection and credentials

        Returns:
            True if connection successful, False otherwise
        """
        try:
            server = self._create_smtp_connection()
            server.quit()
            logger.info("SMTP connection verified successfully")
            return True
        except Exception as e:
            logger.error(f"SMTP connection verification failed: {e}")
            return False

    def send_bulk_emails(
        self,
        recipients: List[Dict[str, str]],
        subject: str,
        html_content: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        rate_limit_delay: float = 0.1
    ) -> Dict[str, Any]:
        """
        Send bulk emails to multiple recipients

        Args:
            recipients: List of dicts with 'email' and optional 'name'
            subject: Email subject
            html_content: HTML content (can include {{name}} placeholder)
            from_email: Sender email
            from_name: Sender name
            rate_limit_delay: Delay between emails in seconds

        Returns:
            Dict with success/failure counts and failed recipients
        """
        import time

        results = {
            'total': len(recipients),
            'sent': 0,
            'failed': 0,
            'failed_recipients': []
        }

        try:
            # Create one connection for all emails
            server = self._create_smtp_connection()

            for recipient in recipients:
                try:
                    email = recipient.get('email')
                    name = recipient.get('name', '')

                    if not email:
                        continue

                    # Personalize content if name is provided
                    personalized_content = html_content.replace('{{name}}', name) if name else html_content

                    # Create message
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = subject
                    msg['To'] = email

                    sender_email = from_email or self.from_email
                    if from_name:
                        msg['From'] = f"{from_name} <{sender_email}>"
                    else:
                        msg['From'] = sender_email

                    html_part = MIMEText(personalized_content, 'html')
                    msg.attach(html_part)

                    # Send email
                    server.sendmail(sender_email, [email], msg.as_string())
                    results['sent'] += 1

                    # Rate limiting
                    if rate_limit_delay > 0:
                        time.sleep(rate_limit_delay)

                except Exception as e:
                    logger.error(f"Failed to send email to {email}: {e}")
                    results['failed'] += 1
                    results['failed_recipients'].append({
                        'email': email,
                        'error': str(e)
                    })

            server.quit()
            logger.info(f"Bulk email sending complete: {results['sent']} sent, {results['failed']} failed")

        except Exception as e:
            logger.error(f"Bulk email sending failed: {e}")
            results['error'] = str(e)

        return results
