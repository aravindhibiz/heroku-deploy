"""
Contact Controller - HTTP request/response handling for Contact endpoints.
Handles authentication, authorization, and HTTP-specific logic.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from services.contact_service import ContactService
from schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from models.user import UserProfile
from core.auth_helpers import (
    get_contacts_query_filter,
    check_contact_edit_permission,
    check_contact_delete_permission
)


class ContactController:
    """Controller for handling contact HTTP requests."""

    def __init__(self, db: Session):
        self.db = db
        self.service = ContactService(db)

    async def get_contacts(
        self,
        current_user: UserProfile,
        search: Optional[str] = None,
        status: Optional[str] = None,
        companies: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all contacts with filters and permission-based access.

        Args:
            current_user: Authenticated user
            search: Search term
            status: Status filter
            companies: Comma-separated company IDs

        Returns:
            List of contacts
        """
        # Parse company IDs
        company_ids = None
        if companies:
            try:
                company_ids = [
                    UUID(cid.strip())
                    for cid in companies.split(',')
                    if cid.strip()
                ]
            except ValueError:
                # Invalid UUIDs, ignore filter
                pass

        # Check permissions to determine owner filter
        from models.contact import Contact
        query = self.db.query(Contact)
        filtered_query = get_contacts_query_filter(
            self.db, current_user, query)

        # Determine if user can view all or only own
        can_view_all = filtered_query.whereclause is None or \
            str(filtered_query.whereclause).find('owner_id') == -1

        owner_id = None if can_view_all else current_user.id

        # Get contacts
        contacts = self.service.get_all_contacts(
            search=search,
            status=status,
            company_ids=company_ids,
            owner_id=owner_id
        )

        return contacts

    async def get_contacts_for_activity_filters(
        self,
        current_user: UserProfile
    ) -> List[Dict[str, Any]]:
        """
        Get contacts for activity filters, sorted by activity count.
        Counts only activities that would be shown in the current timeline.

        Args:
            current_user: Authenticated user

        Returns:
            List of contacts with activity counts sorted by activity count
        """
        # Get contacts sorted by activity count (from recent activities only)
        # Uses the same permission and filtering logic as activity timeline
        contacts = self.service.get_contacts_for_activity_filters(
            current_user=current_user,
            activity_limit=50  # Same limit as activity timeline
        )

        return contacts

    async def get_contact(
        self,
        contact_id: UUID,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Get a single contact by ID.

        Args:
            contact_id: Contact UUID
            current_user: Authenticated user

        Returns:
            Contact data with custom fields

        Raises:
            HTTPException: If contact not found or access denied
        """
        contact_data = self.service.get_contact_with_custom_fields(contact_id)

        if not contact_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )

        # Check permission
        from models.contact import Contact
        contact = self.db.query(Contact).filter(
            Contact.id == contact_id).first()

        # Use permission helper
        query = self.db.query(Contact).filter(Contact.id == contact_id)
        filtered_query = get_contacts_query_filter(
            self.db, current_user, query)

        if not filtered_query.first():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this contact"
            )

        return contact_data

    async def create_contact(
        self,
        contact_data: ContactCreate,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Create a new contact.

        Args:
            contact_data: Contact creation data
            current_user: Authenticated user

        Returns:
            Created contact data

        Raises:
            HTTPException: If creation fails
        """
        # TODO: Check 'contacts.create' permission

        try:
            return self.service.create_contact(contact_data, current_user)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create contact: {str(e)}"
            )

    async def update_contact(
        self,
        contact_id: UUID,
        contact_data: ContactUpdate,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Update an existing contact.

        Args:
            contact_id: Contact UUID
            contact_data: Update data
            current_user: Authenticated user

        Returns:
            Updated contact data

        Raises:
            HTTPException: If contact not found or update fails
        """
        # Check if contact exists
        from models.contact import Contact
        contact = self.db.query(Contact).filter(
            Contact.id == contact_id).first()

        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )

        # Check edit permission
        if not check_contact_edit_permission(self.db, current_user, contact):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this contact"
            )

        try:
            updated_data = self.service.update_contact(
                contact_id, contact_data)

            if not updated_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Contact not found"
                )

            return updated_data
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update contact: {str(e)}"
            )

    async def delete_contact(
        self,
        contact_id: UUID,
        current_user: UserProfile
    ) -> Dict[str, str]:
        """
        Delete a contact.

        Args:
            contact_id: Contact UUID
            current_user: Authenticated user

        Returns:
            Success message

        Raises:
            HTTPException: If contact not found or delete fails
        """
        # Check if contact exists
        from models.contact import Contact
        contact = self.db.query(Contact).filter(
            Contact.id == contact_id).first()

        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )

        # Check delete permission
        if not check_contact_delete_permission(self.db, current_user, contact):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this contact"
            )

        success = self.service.delete_contact(contact_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )

        return {"message": "Contact deleted successfully"}

    async def import_contacts(
        self,
        contacts_data: List[Dict[str, Any]],
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Import multiple contacts.

        Args:
            contacts_data: List of contact dictionaries
            current_user: Authenticated user

        Returns:
            Import results
        """
        # TODO: Check 'contacts.import' permission

        return self.service.import_contacts(contacts_data, current_user)
