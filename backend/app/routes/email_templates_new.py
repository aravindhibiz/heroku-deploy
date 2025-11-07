"""
Email Template Routes

This module defines the RESTful API endpoints for Email Template operations.
Provides clean, well-documented routes for template management and email sending.

Key Features:
- RESTful API design
- Comprehensive OpenAPI documentation
- Input validation with Pydantic
- JWT authentication
- Error handling
- Merge field processing
- Email sending with logging

Endpoints:
- GET /merge-fields - Get available merge fields
- GET / - List templates with filtering
- GET /{template_id} - Get a specific template
- POST / - Create a template
- PUT /{template_id} - Update a template
- DELETE /{template_id} - Delete a template
- POST /preview - Preview template with merge data
- POST /send - Send email using template
- GET /logs/ - Get email logs
- GET /statistics/templates - Get template statistics
- GET /statistics/emails - Get email statistics

Author: CRM System
Date: 2024
"""

from typing import List, Optional, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import UserProfile
from ..models.email_template import TemplateCategory, TemplateStatus
from ..schemas.email_template import (
    EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateResponse,
    EmailTemplateListResponse, SendEmailRequest, SendEmailResponse,
    EmailLogResponse, MergeFieldsResponse,
    TemplatePreviewRequest, TemplatePreviewResponse
)
from ..controllers.email_template_controller import EmailTemplateController


router = APIRouter(tags=["Email Templates"])


@router.get(
    "/merge-fields",
    response_model=MergeFieldsResponse,
    summary="Get available merge fields",
    description="""
    Get the list of available merge fields for email templates.
    
    Merge fields can be used in template subject and content to dynamically
    insert data like contact names, company details, deal information, etc.
    
    **Format:** Use {{field_name}} in templates
    
    **Example merge fields:**
    - {{first_name}} - Contact first name
    - {{company_name}} - Company name
    - {{deal_value}} - Deal value
    - {{current_date}} - Today's date
    
    **Returns:**
    - List of merge fields with descriptions and examples
    
    **Errors:**
    - 500: Internal server error
    """
)
async def get_merge_fields(db: Session = Depends(get_db)):
    """Get available merge fields for templates"""
    controller = EmailTemplateController(
        db)  # Pass DB session to fetch custom fields
    return controller.get_merge_fields()


@router.get(
    "/",
    response_model=EmailTemplateListResponse,
    summary="List email templates",
    description="""
    Get a list of email templates with optional filtering and pagination.
    
    **Query Parameters:**
    - search: Search by template name or subject (case-insensitive)
    - category: Filter by category (general, onboarding, followup, etc.)
    - status: Filter by status (draft, active, inactive)
    - limit: Maximum results (1-100, default 50)
    - offset: Pagination offset (default 0)
    
    **Authorization:**
    - Requires valid JWT authentication
    
    **Returns:**
    - List of templates matching filters
    - Total count for pagination
    
    **Errors:**
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def get_templates(
    search: Optional[str] = Query(
        None, description="Search templates by name or subject"),
    category: Optional[TemplateCategory] = Query(
        None, description="Filter by category"),
    status: Optional[TemplateStatus] = Query(
        None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = EmailTemplateController(db)
    return controller.list_templates(
        search=search,
        category=category,
        status_filter=status,
        limit=limit,
        offset=offset,
        current_user=current_user
    )


@router.get(
    "/{template_id}",
    response_model=EmailTemplateResponse,
    summary="Get a specific template",
    description="""
    Retrieve a single email template by its ID.
    
    Includes full template details: name, subject, content, category,
    status, usage count, and timestamps.
    
    **Authorization:**
    - Requires valid JWT authentication
    
    **Returns:**
    - Complete template data
    
    **Errors:**
    - 404: Template not found
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = EmailTemplateController(db)
    return controller.get_template(template_id, current_user)


@router.post(
    "/",
    response_model=EmailTemplateResponse,
    status_code=201,
    summary="Create email template",
    description="""
    Create a new email template.
    
    Templates can include merge fields ({{field_name}}) that will be
    replaced with actual data when sending emails.
    
    **Request Body:**
    - name (required): Unique template name
    - subject (required): Email subject (can include merge fields)
    - content (required): Email body content (can include merge fields)
    - category (optional): Template category (default: general)
    - status (optional): Template status (default: draft)
    
    **Validation:**
    - Template name must be unique
    - Merge fields must be valid
    - Subject and content cannot be empty
    
    **Authorization:**
    - Requires valid JWT authentication
    - User becomes template creator
    
    **Returns:**
    - Created template (201 Created)
    
    **Errors:**
    - 400: Validation error (duplicate name, invalid merge fields)
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def create_template(
    template_data: EmailTemplateCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = EmailTemplateController(db)
    return controller.create_template(template_data, current_user)


@router.put(
    "/{template_id}",
    response_model=EmailTemplateResponse,
    summary="Update email template",
    description="""
    Update an existing email template.
    
    All fields are optional - only provided fields will be updated.
    
    **Request Body:**
    - name (optional): New template name
    - subject (optional): New subject
    - content (optional): New content
    - category (optional): New category
    - status (optional): New status
    
    **Validation:**
    - Template name must be unique if changed
    - Merge fields must be valid if content updated
    
    **Authorization:**
    - Requires valid JWT authentication
    
    **Returns:**
    - Updated template
    
    **Errors:**
    - 404: Template not found
    - 400: Validation error (duplicate name, invalid merge fields)
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def update_template(
    template_id: UUID,
    template_data: EmailTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = EmailTemplateController(db)
    return controller.update_template(template_id, template_data, current_user)


@router.delete(
    "/{template_id}",
    summary="Delete email template",
    description="""
    Delete an email template.
    
    **Deletion Strategy:**
    - If template has been used (has email logs): Soft delete (status → inactive)
    - If template has never been used: Hard delete (removed from database)
    
    This preserves email history while allowing cleanup of unused templates.
    
    **Authorization:**
    - Requires valid JWT authentication
    
    **Returns:**
    - Success message indicating delete type
    
    **Errors:**
    - 404: Template not found
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = EmailTemplateController(db)
    return controller.delete_template(template_id, current_user)


@router.post(
    "/preview",
    response_model=TemplatePreviewResponse,
    summary="Preview template with merge data",
    description="""
    Preview how a template will look with actual data.
    
    This endpoint processes merge fields in the template with provided
    data, allowing you to see the final result before sending.
    
    **Request Body:**
    - template_id (required): Template to preview
    - merge_data (required): Data to substitute into merge fields
    
    **Example merge_data:**
    ```json
    {
        "first_name": "John",
        "last_name": "Doe",
        "company_name": "Acme Corp",
        "deal_value": "$50,000"
    }
    ```
    
    **Authorization:**
    - Requires valid JWT authentication
    - Sender data automatically included
    
    **Returns:**
    - Processed subject and content with merge fields replaced
    
    **Errors:**
    - 404: Template not found
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def preview_template(
    preview_data: TemplatePreviewRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = EmailTemplateController(db)
    return controller.preview_template(preview_data, current_user)


@router.post(
    "/send",
    response_model=SendEmailResponse,
    summary="Send email",
    description="""
    Send an email using a template or custom content.
    
    **Sending Methods:**
    1. **With Template:** Provide template_id and merge_data
    2. **Custom Email:** Provide subject and content directly
    3. **Template Override:** Provide template_id but override subject/content
    
    **Request Body:**
    - to (required): Recipient email address
    - template_id (optional): Template to use
    - subject (optional): Email subject (overrides template)
    - content (optional): Email content (overrides template)
    - merge_data (optional): Data for merge field substitution
    - cc (optional): CC recipients
    - bcc (optional): BCC recipients
    
    **Template Usage:**
    - Only ACTIVE templates can be used
    - Template usage count is incremented
    - Email is logged for tracking
    
    **Authorization:**
    - Requires valid JWT authentication
    - User becomes email sender
    
    **Returns:**
    - Success status
    - Email log ID for tracking
    
    **Errors:**
    - 404: Template not found or not active
    - 400: Validation error (missing subject/content)
    - 401: Not authenticated
    - 500: Failed to send email
    """
)
async def send_email(
    email_data: SendEmailRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = EmailTemplateController(db)
    return controller.send_email(email_data, current_user)


@router.post(
    "/send-with-attachments",
    response_model=SendEmailResponse,
    summary="Send email with attachments",
    description="""
    Send an email with file attachments.
    
    This endpoint accepts multipart/form-data to support file uploads.
    Email content should already be merged/prepared on the frontend.
    
    **Form Fields:**
    - to (required): Recipient email address
    - subject (required): Email subject
    - content (required): Email content/body
    - cc (optional): CC recipients (can send multiple)
    - bcc (optional): BCC recipients (can send multiple)
    - attachments (optional): Files to attach (can send multiple)
    
    **File Limits:**
    - Max file size: 10MB per file
    - Multiple files supported
    
    **Returns:**
    - Success status
    - Email log ID for tracking
    - Sender email address
    
    **Errors:**
    - 400: Validation error
    - 401: Not authenticated
    - 413: File too large
    - 500: Failed to send email
    """
)
async def send_email_with_attachments(
    to: str = Form(...),
    subject: str = Form(...),
    content: str = Form(...),
    cc: Optional[List[str]] = Form(None),
    bcc: Optional[List[str]] = Form(None),
    attachments: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Send email with file attachments"""
    # Create SendEmailRequest from form data
    email_data = SendEmailRequest(
        to=to,
        subject=subject,
        content=content,
        cc=cc,
        bcc=bcc
    )

    controller = EmailTemplateController(db)
    # Pass attachments to controller
    return await controller.send_email_with_attachments(email_data, current_user, attachments)


@router.get(
    "/logs/",
    response_model=List[EmailLogResponse],
    summary="Get email logs",
    description="""
    Get email sending history for the current user.
    
    Includes all emails sent by the authenticated user with optional filtering.
    
    **Query Parameters:**
    - template_id (optional): Filter by template
    - status (optional): Filter by status (sent, failed, pending)
    - limit: Maximum results (1-100, default 50)
    - offset: Pagination offset (default 0)
    
    **Email Log Data:**
    - Template used (if any)
    - Sender and recipient
    - Subject and content
    - Send status
    - Timestamps (sent, opened, clicked)
    
    **Authorization:**
    - Requires valid JWT authentication
    - Only shows user's own emails
    
    **Returns:**
    - List of email logs ordered by most recent
    
    **Errors:**
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def get_email_logs(
    template_id: Optional[UUID] = Query(
        None, description="Filter by template"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = EmailTemplateController(db)
    return controller.get_email_logs(
        template_id=template_id,
        status_filter=status,
        limit=limit,
        offset=offset,
        current_user=current_user
    )


@router.get(
    "/statistics/templates",
    summary="Get template statistics",
    description="""
    Get usage statistics for email templates.
    
    **Statistics Included:**
    - Total templates count
    - Active templates count
    - Most used templates (top 10)
    - Category breakdown
    
    **Use Cases:**
    - Dashboard analytics
    - Template performance tracking
    - Usage insights
    
    **Authorization:**
    - Requires valid JWT authentication
    
    **Returns:**
    - Comprehensive template statistics
    
    **Errors:**
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def get_template_statistics(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = EmailTemplateController(db)
    return controller.get_template_statistics(current_user)


@router.get(
    "/statistics/emails",
    summary="Get email statistics",
    description="""
    Get email sending statistics for the current user.
    
    **Statistics Included:**
    - Total emails sent
    - Status breakdown (sent, failed, pending)
    - Open count and rate
    - Click count and rate
    
    **Use Cases:**
    - Email campaign tracking
    - Engagement analytics
    - Performance monitoring
    
    **Authorization:**
    - Requires valid JWT authentication
    - Shows only user's email statistics
    
    **Returns:**
    - Comprehensive email statistics
    
    **Errors:**
    - 401: Not authenticated
    - 500: Internal server error
    """
)
async def get_email_statistics(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    controller = EmailTemplateController(db)
    return controller.get_email_statistics(current_user)


@router.get("/test/ping")
async def test_email_templates():
    """
    Test endpoint to verify the email templates router is working.

    Returns:
        dict: Simple test response
    """
    return {"message": "Email Templates API is working", "status": "ok"}
