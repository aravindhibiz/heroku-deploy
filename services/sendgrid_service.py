"""
SendGrid Email Service

This module provides email sending functionality using SendGrid API.
Handles actual email delivery for the CRM system.

Features:
- Send emails with HTML content
- CC and BCC support
- Error handling and logging
- Email status tracking

Author: CRM System
Date: 2024
"""

import os
import base64
from typing import Optional, List, Any
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Cc, Bcc, Content, Attachment, FileContent, FileName, FileType, Disposition
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SendGridService:
    """
    Service for sending emails via SendGrid API.

    This class handles the integration with SendGrid to send emails
    from the CRM system.
    """

    def __init__(self):
        """Initialize SendGrid service with API key."""
        self.api_key = os.getenv('SENDGRID_API_KEY')
        if not self.api_key:
            raise ValueError(
                "SENDGRID_API_KEY environment variable is not set")

        self.client = SendGridAPIClient(self.api_key)

    def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        html_content: str,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        from_name: Optional[str] = None
    ) -> dict:
        """
        Send an email using SendGrid.

        Args:
            from_email (str): Sender email address
            to_email (str): Recipient email address
            subject (str): Email subject
            html_content (str): Email body in HTML format
            cc_emails (Optional[List[str]]): CC recipients
            bcc_emails (Optional[List[str]]): BCC recipients
            from_name (Optional[str]): Sender name (optional)

        Returns:
            dict: Response with status and message

        Raises:
            Exception: If email sending fails
        """
        try:
            # Create the email message
            from_email_obj = Email(from_email, from_name)
            to_email_obj = To(to_email)

            # Convert plain text to HTML if needed
            content = Content("text/html", html_content)

            # Create mail object
            mail = Mail(
                from_email=from_email_obj,
                to_emails=to_email_obj,
                subject=subject,
                html_content=content
            )

            # Add CC recipients
            if cc_emails:
                cc_list = [Cc(email.strip())
                           for email in cc_emails if email.strip()]
                if cc_list:
                    mail.add_cc(cc_list)

            # Add BCC recipients
            if bcc_emails:
                bcc_list = [Bcc(email.strip())
                            for email in bcc_emails if email.strip()]
                if bcc_list:
                    mail.add_bcc(bcc_list)

            # Send email
            response = self.client.send(mail)

            # Detailed logging
            print(f"\n{'='*60}")
            print(f"📧 SendGrid Response:")
            print(f"Status Code: {response.status_code}")
            print(
                f"Message ID: {response.headers.get('X-Message-Id', 'None')}")
            print(f"Response Body: {response.body}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"{'='*60}\n")

            return {
                'success': True,
                'status_code': response.status_code,
                'message': 'Email sent successfully',
                'message_id': response.headers.get('X-Message-Id', None)
            }

        except Exception as e:
            error_message = str(e)
            print(f"SendGrid Error: {error_message}")

            return {
                'success': False,
                'status_code': 500,
                'message': f'Failed to send email: {error_message}',
                'error': error_message
            }

    def send_plain_text_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        text_content: str,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        from_name: Optional[str] = None
    ) -> dict:
        """
        Send a plain text email using SendGrid.

        Args:
            from_email (str): Sender email address
            to_email (str): Recipient email address
            subject (str): Email subject
            text_content (str): Email body in plain text
            cc_emails (Optional[List[str]]): CC recipients
            bcc_emails (Optional[List[str]]): BCC recipients
            from_name (Optional[str]): Sender name (optional)

        Returns:
            dict: Response with status and message
        """
        # Convert plain text to basic HTML
        html_content = text_content.replace('\n', '<br>')

        return self.send_email(
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails,
            from_name=from_name
        )

    async def send_email_with_attachments(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        html_content: str,
        attachments: Optional[List[Any]] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        from_name: Optional[str] = None
    ) -> dict:
        """
        Send an email with file attachments using SendGrid.

        Args:
            from_email (str): Sender email address
            to_email (str): Recipient email address
            subject (str): Email subject
            html_content (str): Email body in HTML format
            attachments (Optional[List[UploadFile]]): List of file attachments
            cc_emails (Optional[List[str]]): CC recipients
            bcc_emails (Optional[List[str]]): BCC recipients
            from_name (Optional[str]): Sender name (optional)

        Returns:
            dict: Response with status and message

        Raises:
            Exception: If email sending fails
        """
        try:
            # Create the email message
            from_email_obj = Email(from_email, from_name)
            to_email_obj = To(to_email)

            # Convert plain text to HTML if needed
            content = Content("text/html", html_content)

            # Create mail object
            mail = Mail(
                from_email=from_email_obj,
                to_emails=to_email_obj,
                subject=subject,
                html_content=content
            )

            # Add CC recipients
            if cc_emails:
                cc_list = [Cc(email.strip())
                           for email in cc_emails if email.strip()]
                if cc_list:
                    mail.add_cc(cc_list)

            # Add BCC recipients
            if bcc_emails:
                bcc_list = [Bcc(email.strip())
                            for email in bcc_emails if email.strip()]
                if bcc_list:
                    mail.add_bcc(bcc_list)

            # Add attachments
            if attachments:
                for file in attachments:
                    # Read file content
                    file_content = await file.read()

                    # Encode to base64
                    encoded_file = base64.b64encode(file_content).decode()

                    # Create attachment
                    attachment = Attachment()
                    attachment.file_content = FileContent(encoded_file)
                    attachment.file_name = FileName(file.filename)
                    attachment.file_type = FileType(
                        file.content_type or 'application/octet-stream')
                    attachment.disposition = Disposition('attachment')

                    # Add to mail
                    mail.add_attachment(attachment)

                    print(
                        f"Added attachment: {file.filename} ({file.content_type})")

            # Send email
            response = self.client.send(mail)

            # Detailed logging
            print(f"\n{'='*60}")
            print(f"📧 SendGrid Response (with attachments):")
            print(f"Status Code: {response.status_code}")
            print(
                f"Message ID: {response.headers.get('X-Message-Id', 'None')}")
            if attachments:
                print(f"Attachments: {len(attachments)} file(s)")
            print(f"{'='*60}\n")

            return {
                'success': True,
                'status_code': response.status_code,
                'message': 'Email sent successfully with attachments',
                'message_id': response.headers.get('X-Message-Id', None)
            }

        except Exception as e:
            error_message = str(e)
            print(f"SendGrid Error (with attachments): {error_message}")

            return {
                'success': False,
                'status_code': 500,
                'message': f'Failed to send email with attachments: {error_message}',
                'error': error_message
            }

    def verify_api_key(self) -> bool:
        """
        Verify that the SendGrid API key is valid.

        Returns:
            bool: True if API key is valid, False otherwise
        """
        try:
            # Try to get API key info (this will fail if key is invalid)
            response = self.client.client.api_keys.get()
            return response.status_code == 200
        except Exception as e:
            print(f"API Key verification failed: {e}")
            return False


# Singleton instance
_sendgrid_service = None


def get_sendgrid_service() -> SendGridService:
    """
    Get or create SendGrid service instance.

    Returns:
        SendGridService: Singleton instance of SendGrid service
    """
    global _sendgrid_service
    if _sendgrid_service is None:
        _sendgrid_service = SendGridService()
    return _sendgrid_service
