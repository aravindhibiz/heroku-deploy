from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from uuid import UUID

from core.database import get_db
from core.auth import get_current_user
from models.user import UserProfile
from models.email_template import EmailTemplate, EmailLog, TemplateCategory, TemplateStatus
from schemas.email_template import (
    EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateResponse,
    EmailTemplateListResponse, SendEmailRequest, SendEmailResponse,
    EmailLogResponse, MergeFieldsResponse, MergeField,
    TemplatePreviewRequest, TemplatePreviewResponse
)
from services.email_template_service import EmailTemplateService

router = APIRouter()


@router.get("/merge-fields", response_model=MergeFieldsResponse)
async def get_merge_fields(
    db: Session = Depends(get_db)
):
    """Get available merge fields including custom fields"""
    fields = EmailTemplateService.get_available_merge_fields(db=db)
    return MergeFieldsResponse(
        fields=[MergeField(**field) for field in fields]
    )


@router.get("/", response_model=EmailTemplateListResponse)
async def get_templates(
    search: Optional[str] = Query(
        None, description="Search templates by name or subject"),
    category: Optional[TemplateCategory] = Query(
        None, description="Filter by category"),
    status: Optional[TemplateStatus] = Query(
        None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get email templates with optional filtering"""

    query = db.query(EmailTemplate)

    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                EmailTemplate.name.ilike(search_filter),
                EmailTemplate.subject.ilike(search_filter)
            )
        )

    if category:
        query = query.filter(EmailTemplate.category == category)

    if status:
        query = query.filter(EmailTemplate.status == status)

    # Get total count
    total = query.count()

    # Apply pagination and ordering
    templates = query.order_by(EmailTemplate.updated_at.desc()).offset(
        offset).limit(limit).all()

    return EmailTemplateListResponse(
        templates=[EmailTemplateResponse.model_validate(
            template) for template in templates],
        total=total
    )


@router.get("/{template_id}", response_model=EmailTemplateResponse)
async def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get a specific email template"""

    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return EmailTemplateResponse.model_validate(template)


@router.post("/", response_model=EmailTemplateResponse)
async def create_template(
    template_data: EmailTemplateCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Create a new email template"""

    # Validate merge fields
    invalid_fields = EmailTemplateService.validate_merge_fields(
        template_data.subject + " " + template_data.content)
    if invalid_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid merge fields: {', '.join(invalid_fields)}"
        )

    # Check for duplicate template name
    existing = db.query(EmailTemplate).filter(
        EmailTemplate.name == template_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template with this name already exists"
        )

    template = EmailTemplate(
        **template_data.model_dump(),
        created_by=current_user.id
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    return EmailTemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=EmailTemplateResponse)
async def update_template(
    template_id: UUID,
    template_data: EmailTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Update an email template"""

    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Validate merge fields if content is being updated
    if template_data.subject or template_data.content:
        subject_text = template_data.subject or template.subject
        content_text = template_data.content or template.content
        invalid_fields = EmailTemplateService.validate_merge_fields(
            subject_text + " " + content_text)
        if invalid_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid merge fields: {', '.join(invalid_fields)}"
            )

    # Check for duplicate name if name is being updated
    if template_data.name and template_data.name != template.name:
        existing = db.query(EmailTemplate).filter(
            EmailTemplate.name == template_data.name,
            EmailTemplate.id != template_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template with this name already exists"
            )

    # Update template
    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    db.commit()
    db.refresh(template)

    return EmailTemplateResponse.model_validate(template)


@router.delete("/{template_id}")
async def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Delete an email template"""

    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == template_id).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    # Check if template is being used (has logs)
    usage_count = db.query(EmailLog).filter(
        EmailLog.template_id == template_id).count()
    if usage_count > 0:
        # Soft delete by setting status to inactive
        template.status = TemplateStatus.INACTIVE
        db.commit()
        return {"message": "Template marked as inactive due to existing usage"}

    # Hard delete if no usage
    db.delete(template)
    db.commit()

    return {"message": "Template deleted successfully"}


@router.post("/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    preview_data: TemplatePreviewRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Preview a template with merge data"""

    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == preview_data.template_id).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    processed = EmailTemplateService.process_template(
        template=template,
        merge_data=preview_data.merge_data,
        db=db,
        sender=current_user
    )

    return TemplatePreviewResponse(
        subject=processed["subject"],
        content=processed["content"]
    )


@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    email_data: SendEmailRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Send an email using a template or custom content"""

    template = None
    processed_subject = email_data.subject or ""
    processed_content = email_data.content or ""

    # If template is specified, process it
    if email_data.template_id:
        template = db.query(EmailTemplate).filter(
            EmailTemplate.id == email_data.template_id,
            EmailTemplate.status == TemplateStatus.ACTIVE
        ).first()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active template not found"
            )

        # Process template
        processed = EmailTemplateService.process_template(
            template=template,
            merge_data=email_data.merge_data or {},
            db=db,
            sender=current_user
        )

        # Use processed content or override if provided
        processed_subject = email_data.subject or processed["subject"]
        processed_content = email_data.content or processed["content"]

        # Increment usage count
        EmailTemplateService.increment_usage_count(
            db, str(email_data.template_id))

    if not processed_subject or not processed_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject and content are required"
        )

    try:
        # Here you would integrate with your actual email service
        # For now, we'll just log the email as "sent"

        email_log = EmailTemplateService.log_email_sent(
            db=db,
            template_id=str(
                email_data.template_id) if email_data.template_id else None,
            sender_email=current_user.email,
            recipient_email=email_data.to,
            subject=processed_subject,
            content=processed_content,
            status="sent",
            cc=email_data.cc,
            bcc=email_data.bcc
        )

        return SendEmailResponse(
            success=True,
            message="Email sent successfully",
            email_log_id=email_log.id
        )

    except Exception as e:
        # Log failed email
        email_log = EmailTemplateService.log_email_sent(
            db=db,
            template_id=str(
                email_data.template_id) if email_data.template_id else None,
            sender_email=current_user.email,
            recipient_email=email_data.to,
            subject=processed_subject,
            content=processed_content,
            status="failed",
            cc=email_data.cc,
            bcc=email_data.bcc
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )


@router.get("/logs/", response_model=List[EmailLogResponse])
async def get_email_logs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    template_id: Optional[UUID] = Query(
        None, description="Filter by template"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get email logs"""

    query = db.query(EmailLog).filter(
        EmailLog.sender_email == current_user.email)

    if template_id:
        query = query.filter(EmailLog.template_id == template_id)

    if status:
        query = query.filter(EmailLog.status == status)

    logs = query.order_by(EmailLog.sent_at.desc()).offset(
        offset).limit(limit).all()

    return [EmailLogResponse.model_validate(log) for log in logs]
