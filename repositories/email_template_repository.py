"""
Email Template Repository Layer

This module provides data access operations for EmailTemplate and EmailLog entities.
Implements the Repository pattern for database interactions.

Key Features:
- CRUD operations for email templates
- Email log management
- Advanced filtering and search
- Usage tracking
- Template statistics
- Efficient querying with SQLAlchemy

Author: CRM System
Date: 2024
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session
from ..models.email_template import EmailTemplate, EmailLog, TemplateCategory, TemplateStatus


class EmailTemplateRepository:
    """
    Repository class for EmailTemplate entity database operations.

    This class encapsulates all database queries and operations for email templates,
    providing a clean interface for the service layer.

    Responsibilities:
    - Execute database queries for templates
    - Handle filtering and search
    - Manage template CRUD operations
    - Track usage statistics
    - Provide pagination support
    """

    def __init__(self, db: Session):
        """
        Initialize the EmailTemplateRepository.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db

    def get_all(
        self,
        search: Optional[str] = None,
        category: Optional[TemplateCategory] = None,
        status: Optional[TemplateStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[EmailTemplate], int]:
        """
        Get all email templates with optional filtering and pagination.

        Args:
            search (Optional[str]): Search term for name or subject
            category (Optional[TemplateCategory]): Filter by category
            status (Optional[TemplateStatus]): Filter by status
            limit (int): Maximum number of templates to return
            offset (int): Number of templates to skip

        Returns:
            tuple[List[EmailTemplate], int]: List of templates and total count
        """
        query = self.db.query(EmailTemplate)

        # Apply search filter
        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    EmailTemplate.name.ilike(search_filter),
                    EmailTemplate.subject.ilike(search_filter)
                )
            )

        # Apply category filter
        if category:
            query = query.filter(EmailTemplate.category == category)

        # Apply status filter
        if status:
            query = query.filter(EmailTemplate.status == status)

        # Get total count before pagination
        total = query.count()

        # Apply ordering and pagination
        templates = query.order_by(
            desc(EmailTemplate.updated_at)
        ).offset(offset).limit(limit).all()

        return templates, total

    def get_by_id(self, template_id: UUID) -> Optional[EmailTemplate]:
        """
        Get a template by its ID.

        Args:
            template_id (UUID): The template ID to search for

        Returns:
            Optional[EmailTemplate]: The template if found, None otherwise
        """
        return self.db.query(EmailTemplate).filter(
            EmailTemplate.id == template_id
        ).first()

    def get_by_name(self, name: str) -> Optional[EmailTemplate]:
        """
        Get a template by its name.

        Args:
            name (str): The template name to search for

        Returns:
            Optional[EmailTemplate]: The template if found, None otherwise
        """
        return self.db.query(EmailTemplate).filter(
            EmailTemplate.name == name
        ).first()

    def get_active_templates(
        self,
        category: Optional[TemplateCategory] = None
    ) -> List[EmailTemplate]:
        """
        Get all active templates.

        Args:
            category (Optional[TemplateCategory]): Filter by category

        Returns:
            List[EmailTemplate]: List of active templates
        """
        query = self.db.query(EmailTemplate).filter(
            EmailTemplate.status == TemplateStatus.ACTIVE
        )

        if category:
            query = query.filter(EmailTemplate.category == category)

        return query.order_by(desc(EmailTemplate.updated_at)).all()

    def get_by_category(self, category: TemplateCategory) -> List[EmailTemplate]:
        """
        Get all templates in a category.

        Args:
            category (TemplateCategory): The category to filter by

        Returns:
            List[EmailTemplate]: List of templates in the category
        """
        return self.db.query(EmailTemplate).filter(
            EmailTemplate.category == category
        ).order_by(desc(EmailTemplate.updated_at)).all()

    def get_by_status(self, status: TemplateStatus) -> List[EmailTemplate]:
        """
        Get all templates with a specific status.

        Args:
            status (TemplateStatus): The status to filter by

        Returns:
            List[EmailTemplate]: List of templates with the status
        """
        return self.db.query(EmailTemplate).filter(
            EmailTemplate.status == status
        ).order_by(desc(EmailTemplate.updated_at)).all()

    def get_by_creator(self, creator_id: UUID) -> List[EmailTemplate]:
        """
        Get all templates created by a specific user.

        Args:
            creator_id (UUID): The creator user ID

        Returns:
            List[EmailTemplate]: List of templates created by the user
        """
        return self.db.query(EmailTemplate).filter(
            EmailTemplate.created_by == creator_id
        ).order_by(desc(EmailTemplate.created_at)).all()

    def create(self, template: EmailTemplate) -> EmailTemplate:
        """
        Create a new email template.

        Args:
            template (EmailTemplate): The template object to create

        Returns:
            EmailTemplate: The created template with generated ID and timestamps
        """
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def update(self, template: EmailTemplate) -> EmailTemplate:
        """
        Update an existing template.

        Args:
            template (EmailTemplate): The template object with updated values

        Returns:
            EmailTemplate: The updated template
        """
        self.db.commit()
        self.db.refresh(template)
        return template

    def delete(self, template: EmailTemplate) -> None:
        """
        Delete a template (hard delete).

        Args:
            template (EmailTemplate): The template object to delete
        """
        self.db.delete(template)
        self.db.commit()

    def soft_delete(self, template: EmailTemplate) -> EmailTemplate:
        """
        Soft delete a template by setting status to INACTIVE.

        Args:
            template (EmailTemplate): The template to mark as inactive

        Returns:
            EmailTemplate: The updated template
        """
        template.status = TemplateStatus.INACTIVE
        return self.update(template)

    def increment_usage_count(self, template_id: UUID) -> None:
        """
        Increment the usage count for a template.

        Args:
            template_id (UUID): The template ID
        """
        template = self.get_by_id(template_id)
        if template:
            template.usage_count += 1
            self.db.commit()

    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics for all templates.

        Returns:
            Dict[str, Any]: Statistics including total templates, most used, etc.
        """
        total_templates = self.db.query(EmailTemplate).count()
        active_templates = self.db.query(EmailTemplate).filter(
            EmailTemplate.status == TemplateStatus.ACTIVE
        ).count()

        most_used = self.db.query(EmailTemplate).order_by(
            desc(EmailTemplate.usage_count)
        ).limit(10).all()

        category_breakdown = self.db.query(
            EmailTemplate.category,
            func.count(EmailTemplate.id)
        ).group_by(EmailTemplate.category).all()

        return {
            "total_templates": total_templates,
            "active_templates": active_templates,
            "most_used_templates": [
                {
                    "id": str(template.id),
                    "name": template.name,
                    "usage_count": template.usage_count
                }
                for template in most_used
            ],
            "category_breakdown": {
                category.value: count for category, count in category_breakdown
            }
        }

    def search_templates(
        self,
        search_term: str,
        include_inactive: bool = False
    ) -> List[EmailTemplate]:
        """
        Search templates by name, subject, or content.

        Args:
            search_term (str): The term to search for
            include_inactive (bool): Whether to include inactive templates

        Returns:
            List[EmailTemplate]: List of matching templates
        """
        search_filter = f"%{search_term}%"
        query = self.db.query(EmailTemplate).filter(
            or_(
                EmailTemplate.name.ilike(search_filter),
                EmailTemplate.subject.ilike(search_filter),
                EmailTemplate.content.ilike(search_filter)
            )
        )

        if not include_inactive:
            query = query.filter(EmailTemplate.status !=
                                 TemplateStatus.INACTIVE)

        return query.order_by(desc(EmailTemplate.updated_at)).all()


class EmailLogRepository:
    """
    Repository class for EmailLog entity database operations.

    This class encapsulates all database queries and operations for email logs,
    providing tracking and analytics for sent emails.

    Responsibilities:
    - Execute database queries for email logs
    - Track email sending history
    - Provide email analytics
    - Filter and search logs
    """

    def __init__(self, db: Session):
        """
        Initialize the EmailLogRepository.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db

    def create(self, email_log: EmailLog) -> EmailLog:
        """
        Create a new email log entry.

        Args:
            email_log (EmailLog): The email log object to create

        Returns:
            EmailLog: The created log with generated ID and timestamp
        """
        self.db.add(email_log)
        self.db.commit()
        self.db.refresh(email_log)
        return email_log

    def get_by_id(self, log_id: UUID) -> Optional[EmailLog]:
        """
        Get an email log by its ID.

        Args:
            log_id (UUID): The log ID to search for

        Returns:
            Optional[EmailLog]: The log if found, None otherwise
        """
        return self.db.query(EmailLog).filter(EmailLog.id == log_id).first()

    def get_by_template(
        self,
        template_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[EmailLog]:
        """
        Get all email logs for a specific template.

        Args:
            template_id (UUID): The template ID to filter by
            limit (int): Maximum number of logs to return
            offset (int): Number of logs to skip

        Returns:
            List[EmailLog]: List of email logs
        """
        return self.db.query(EmailLog).filter(
            EmailLog.template_id == template_id
        ).order_by(desc(EmailLog.sent_at)).offset(offset).limit(limit).all()

    def get_by_sender(
        self,
        sender_email: str,
        template_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[EmailLog]:
        """
        Get all email logs for a specific sender.

        Args:
            sender_email (str): The sender email to filter by
            template_id (Optional[UUID]): Filter by template if provided
            status (Optional[str]): Filter by status if provided
            limit (int): Maximum number of logs to return
            offset (int): Number of logs to skip

        Returns:
            List[EmailLog]: List of email logs
        """
        query = self.db.query(EmailLog).filter(
            EmailLog.sender_email == sender_email
        )

        if template_id:
            query = query.filter(EmailLog.template_id == template_id)

        if status:
            query = query.filter(EmailLog.status == status)

        return query.order_by(desc(EmailLog.sent_at)).offset(offset).limit(limit).all()

    def get_by_recipient(
        self,
        recipient_email: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[EmailLog]:
        """
        Get all email logs for a specific recipient.

        Args:
            recipient_email (str): The recipient email to filter by
            limit (int): Maximum number of logs to return
            offset (int): Number of logs to skip

        Returns:
            List[EmailLog]: List of email logs
        """
        return self.db.query(EmailLog).filter(
            EmailLog.recipient_email == recipient_email
        ).order_by(desc(EmailLog.sent_at)).offset(offset).limit(limit).all()

    def count_by_template(self, template_id: UUID) -> int:
        """
        Count email logs for a specific template.

        Args:
            template_id (UUID): The template ID to count logs for

        Returns:
            int: Number of email logs for the template
        """
        return self.db.query(EmailLog).filter(
            EmailLog.template_id == template_id
        ).count()

    def get_email_statistics(self, sender_email: Optional[str] = None) -> Dict[str, Any]:
        """
        Get email sending statistics.

        Args:
            sender_email (Optional[str]): Filter by sender if provided

        Returns:
            Dict[str, Any]: Statistics including sent, failed, opened counts
        """
        query = self.db.query(EmailLog)

        if sender_email:
            query = query.filter(EmailLog.sender_email == sender_email)

        total_sent = query.count()

        status_breakdown = query.with_entities(
            EmailLog.status,
            func.count(EmailLog.id)
        ).group_by(EmailLog.status).all()

        opened_count = query.filter(EmailLog.opened_at.isnot(None)).count()
        clicked_count = query.filter(EmailLog.clicked_at.isnot(None)).count()

        return {
            "total_sent": total_sent,
            "status_breakdown": dict(status_breakdown),
            "opened_count": opened_count,
            "clicked_count": clicked_count,
            "open_rate": round((opened_count / total_sent * 100), 2) if total_sent > 0 else 0,
            "click_rate": round((clicked_count / total_sent * 100), 2) if total_sent > 0 else 0
        }

    def mark_as_opened(self, log_id: UUID) -> Optional[EmailLog]:
        """
        Mark an email log as opened.

        Args:
            log_id (UUID): The log ID

        Returns:
            Optional[EmailLog]: The updated log if found
        """
        log = self.get_by_id(log_id)
        if log and not log.opened_at:
            log.opened_at = func.now()
            self.db.commit()
            self.db.refresh(log)
        return log

    def mark_as_clicked(self, log_id: UUID) -> Optional[EmailLog]:
        """
        Mark an email log as clicked.

        Args:
            log_id (UUID): The log ID

        Returns:
            Optional[EmailLog]: The updated log if found
        """
        log = self.get_by_id(log_id)
        if log and not log.clicked_at:
            log.clicked_at = func.now()
            self.db.commit()
            self.db.refresh(log)
        return log
