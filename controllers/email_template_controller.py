"""
Email Template Controller Layer

This module provides HTTP request handling for Email Template operations.
Implements the Controller pattern for email template management.

Key Features:
- HTTP request/response handling
- Error translation to HTTP exceptions
- Input validation
- Response formatting
- Merge field validation

Author: CRM System
Date: 2024
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from schemas.email_template import (
    EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateResponse,
    EmailTemplateListResponse, SendEmailRequest, SendEmailResponse,
    EmailLogResponse, MergeFieldsResponse, MergeField,
    TemplatePreviewRequest, TemplatePreviewResponse,
    TemplateCategory, TemplateStatus
)
from models.user import UserProfile
from services.email_template_service_new import EmailTemplateService


class EmailTemplateController:
    """
    Controller class for Email Template HTTP operations.

    This class handles HTTP requests, translates service exceptions
    to appropriate HTTP responses, and formats data for the API.

    Responsibilities:
    - Handle HTTP request/response cycle
    - Translate service errors to HTTP exceptions
    - Validate input data
    - Format responses
    - Enforce business rules
    """

    def __init__(self, db: Session):
        """
        Initialize the EmailTemplateController.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        self.service = EmailTemplateService(db)

    def get_merge_fields(self) -> MergeFieldsResponse:
        """
        Get available merge fields.

        Returns:
            MergeFieldsResponse: List of available merge fields
        """
        try:
            fields = self.service.get_available_merge_fields()
            return MergeFieldsResponse(
                fields=[MergeField(**field) for field in fields]
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve merge fields: {str(e)}"
            )

    def list_templates(
        self,
        search: Optional[str] = None,
        category: Optional[TemplateCategory] = None,
        status_filter: Optional[TemplateStatus] = None,
        limit: int = 50,
        offset: int = 0,
        current_user: UserProfile = None
    ) -> EmailTemplateListResponse:
        """
        Get all templates with filtering.

        Args:
            search (Optional[str]): Search term
            category (Optional[TemplateCategory]): Filter by category
            status_filter (Optional[TemplateStatus]): Filter by status
            limit (int): Maximum results
            offset (int): Pagination offset
            current_user (UserProfile): Authenticated user

        Returns:
            EmailTemplateListResponse: List of templates with total count

        Raises:
            HTTPException: 500 for internal errors
        """
        try:
            templates, total = self.service.get_all_templates(
                search=search,
                category=category,
                status=status_filter,
                limit=limit,
                offset=offset
            )

            return EmailTemplateListResponse(
                templates=[
                    EmailTemplateResponse.model_validate(template)
                    for template in templates
                ],
                total=total
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve templates: {str(e)}"
            )

    def get_template(
        self,
        template_id: UUID,
        current_user: UserProfile
    ) -> EmailTemplateResponse:
        """
        Get a specific template by ID.

        Args:
            template_id (UUID): The template ID
            current_user (UserProfile): Authenticated user

        Returns:
            EmailTemplateResponse: Template data

        Raises:
            HTTPException: 404 if not found, 500 for internal errors
        """
        try:
            template = self.service.get_template_by_id(template_id)

            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found"
                )

            return EmailTemplateResponse.model_validate(template)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve template: {str(e)}"
            )

    def create_template(
        self,
        template_data: EmailTemplateCreate,
        current_user: UserProfile
    ) -> EmailTemplateResponse:
        """
        Create a new email template.

        Args:
            template_data (EmailTemplateCreate): Template creation data
            current_user (UserProfile): Authenticated user

        Returns:
            EmailTemplateResponse: Created template

        Raises:
            HTTPException: 400 for validation errors, 500 for internal errors
        """
        try:
            template = self.service.create_template(
                template_data=template_data,
                user_id=current_user.id
            )

            return EmailTemplateResponse.model_validate(template)

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create template: {str(e)}"
            )

    def update_template(
        self,
        template_id: UUID,
        template_data: EmailTemplateUpdate,
        current_user: UserProfile
    ) -> EmailTemplateResponse:
        """
        Update an existing template.

        Args:
            template_id (UUID): The template ID
            template_data (EmailTemplateUpdate): Update data
            current_user (UserProfile): Authenticated user

        Returns:
            EmailTemplateResponse: Updated template

        Raises:
            HTTPException: 404 if not found, 400 for validation, 500 for internal errors
        """
        try:
            template = self.service.update_template(
                template_id=template_id,
                template_data=template_data,
                user_id=current_user.id
            )

            return EmailTemplateResponse.model_validate(template)

        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_msg
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update template: {str(e)}"
            )

    def delete_template(
        self,
        template_id: UUID,
        current_user: UserProfile
    ) -> Dict[str, str]:
        """
        Delete a template.

        Args:
            template_id (UUID): The template ID
            current_user (UserProfile): Authenticated user

        Returns:
            Dict[str, str]: Success message

        Raises:
            HTTPException: 404 if not found, 500 for internal errors
        """
        try:
            result = self.service.delete_template(template_id)
            return result

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete template: {str(e)}"
            )

    def preview_template(
        self,
        preview_data: TemplatePreviewRequest,
        current_user: UserProfile
    ) -> TemplatePreviewResponse:
        """
        Preview a template with merge data.

        Args:
            preview_data (TemplatePreviewRequest): Preview request data
            current_user (UserProfile): Authenticated user

        Returns:
            TemplatePreviewResponse: Processed template

        Raises:
            HTTPException: 404 if template not found, 500 for internal errors
        """
        try:
            processed = self.service.preview_template(
                preview_data=preview_data,
                user=current_user
            )

            return TemplatePreviewResponse(
                subject=processed["subject"],
                content=processed["content"]
            )

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to preview template: {str(e)}"
            )

    def send_email(
        self,
        email_data: SendEmailRequest,
        current_user: UserProfile
    ) -> SendEmailResponse:
        """
        Send an email using a template or custom content.

        Args:
            email_data (SendEmailRequest): Email data
            current_user (UserProfile): Authenticated user

        Returns:
            SendEmailResponse: Send result with log ID and sender email

        Raises:
            HTTPException: 404 if template not found, 400 for validation, 500 for errors
        """
        try:
            email_log = self.service.send_email(
                email_data=email_data,
                sender=current_user
            )

            return SendEmailResponse(
                success=True,
                message="Email sent successfully",
                email_log_id=email_log.id,
                sender_email=email_log.sender_email  # Include the actual sender email used
            )

        except ValueError as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_msg
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
        except Exception as e:
            # Log failed email attempt
            try:
                self.service.log_email_sent(
                    template_id=email_data.template_id,
                    sender_email=current_user.email,
                    recipient_email=email_data.to,
                    subject=email_data.subject or "Failed email",
                    content=email_data.content or "Failed email",
                    status="failed",
                    cc=email_data.cc,
                    bcc=email_data.bcc
                )
            except Exception:
                pass  # Don't fail if logging fails

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {str(e)}"
            )

    async def send_email_with_attachments(
        self,
        email_data: SendEmailRequest,
        current_user: UserProfile,
        attachments: Optional[List[Any]] = None
    ) -> SendEmailResponse:
        """
        Send an email with file attachments.

        Args:
            email_data (SendEmailRequest): Email data (content already merged)
            current_user (UserProfile): Authenticated user
            attachments (Optional[List[UploadFile]]): List of file attachments

        Returns:
            SendEmailResponse: Send result with log ID and sender email

        Raises:
            HTTPException: 400 for validation, 413 for file too large, 500 for errors
        """
        try:
            # Validate file sizes (10MB limit per file)
            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

            if attachments:
                for file in attachments:
                    # Read file to check size
                    file_content = await file.read()
                    if len(file_content) > MAX_FILE_SIZE:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File {file.filename} exceeds maximum size of 10MB"
                        )
                    # Reset file pointer for later use
                    await file.seek(0)

            # Send email with attachments
            email_log = await self.service.send_email_with_attachments(
                email_data=email_data,
                sender=current_user,
                attachments=attachments
            )

            return SendEmailResponse(
                success=True,
                message="Email sent successfully with attachments",
                email_log_id=email_log.id,
                sender_email=email_log.sender_email
            )

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            # Log failed email attempt
            try:
                self.service.log_email_sent(
                    template_id=None,
                    sender_email=current_user.email,
                    recipient_email=email_data.to,
                    subject=email_data.subject or "Failed email",
                    content=email_data.content or "Failed email",
                    status="failed",
                    cc=email_data.cc,
                    bcc=email_data.bcc
                )
            except Exception:
                pass  # Don't fail if logging fails

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email with attachments: {str(e)}"
            )

    def get_email_logs(
        self,
        template_id: Optional[UUID] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        current_user: UserProfile = None
    ) -> List[EmailLogResponse]:
        """
        Get email logs for the current user.

        Args:
            template_id (Optional[UUID]): Filter by template
            status_filter (Optional[str]): Filter by status
            limit (int): Maximum results
            offset (int): Pagination offset
            current_user (UserProfile): Authenticated user

        Returns:
            List[EmailLogResponse]: Email logs

        Raises:
            HTTPException: 500 for internal errors
        """
        try:
            logs = self.service.get_email_logs(
                sender_email=current_user.email,
                template_id=template_id,
                status=status_filter,
                limit=limit,
                offset=offset
            )

            return [EmailLogResponse.model_validate(log) for log in logs]

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve email logs: {str(e)}"
            )

    def get_template_statistics(
        self,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Get template usage statistics.

        Args:
            current_user (UserProfile): Authenticated user

        Returns:
            Dict[str, Any]: Statistics data

        Raises:
            HTTPException: 500 for internal errors
        """
        try:
            return self.service.get_template_statistics()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve statistics: {str(e)}"
            )

    def get_email_statistics(
        self,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Get email sending statistics.

        Args:
            current_user (UserProfile): Authenticated user

        Returns:
            Dict[str, Any]: Email statistics

        Raises:
            HTTPException: 500 for internal errors
        """
        try:
            return self.service.get_email_statistics(
                sender_email=current_user.email
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve email statistics: {str(e)}"
            )
