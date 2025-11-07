"""
Contact Repository - Data access layer for Contact entity.
Handles all database operations for contacts.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func

from ..models.contact import Contact
from ..models.company import Company
from ..models.activity import Activity
from .base_repository import BaseRepository


class ContactRepository(BaseRepository[Contact]):
    """Repository for Contact entity with specialized query methods."""

    def __init__(self, db: Session):
        super().__init__(Contact, db)

    def get_with_relations(self, contact_id: UUID) -> Optional[Contact]:
        """
        Get a contact with all its relations eagerly loaded.

        Args:
            contact_id: UUID of the contact

        Returns:
            Contact with relations or None if not found
        """
        return self.db.query(Contact).options(
            joinedload(Contact.company),
            joinedload(Contact.owner),
            joinedload(Contact.deals),
            joinedload(Contact.activities),
            joinedload(Contact.tasks)
        ).filter(Contact.id == contact_id).first()

    def get_all_with_relations(self, owner_id: Optional[UUID] = None) -> List[Contact]:
        """
        Get all contacts with relations.

        Args:
            owner_id: Optional owner filter

        Returns:
            List of contacts with relations
        """
        query = self.db.query(Contact).options(
            joinedload(Contact.company),
            joinedload(Contact.owner),
            joinedload(Contact.deals),
            joinedload(Contact.activities),
            joinedload(Contact.tasks)
        )

        if owner_id:
            query = query.filter(Contact.owner_id == owner_id)

        return query.order_by(Contact.updated_at.desc()).all()

    def search_contacts(
        self,
        search_term: Optional[str] = None,
        status: Optional[str] = None,
        company_ids: Optional[List[UUID]] = None,
        owner_id: Optional[UUID] = None
    ) -> List[Contact]:
        """
        Search contacts with multiple filters.

        Args:
            search_term: Search by name, email, or company name
            status: Filter by status (active/inactive)
            company_ids: Filter by company IDs
            owner_id: Filter by owner

        Returns:
            List of matching contacts
        """
        query = self.db.query(Contact).options(
            joinedload(Contact.company),
            joinedload(Contact.owner),
            joinedload(Contact.deals),
            joinedload(Contact.activities),
            joinedload(Contact.tasks)
        )

        # Owner filter
        if owner_id:
            query = query.filter(Contact.owner_id == owner_id)

        # Search filter
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.join(Company, Contact.company_id ==
                               Company.id, isouter=True)
            query = query.filter(
                or_(
                    Contact.first_name.ilike(search_pattern),
                    Contact.last_name.ilike(search_pattern),
                    Contact.email.ilike(search_pattern),
                    Company.name.ilike(search_pattern)
                )
            )

        # Status filter
        if status:
            query = query.filter(Contact.status == status)

        # Company filter
        if company_ids:
            query = query.filter(Contact.company_id.in_(company_ids))

        return query.order_by(Contact.updated_at.desc()).all()

    def get_by_email(self, email: str) -> Optional[Contact]:
        """
        Get contact by email address.

        Args:
            email: Email address

        Returns:
            Contact or None
        """
        return self.db.query(Contact).filter(Contact.email == email).first()

    def get_by_company(self, company_id: UUID) -> List[Contact]:
        """
        Get all contacts for a specific company.

        Args:
            company_id: Company UUID

        Returns:
            List of contacts
        """
        return self.db.query(Contact).options(
            joinedload(Contact.owner)
        ).filter(Contact.company_id == company_id).all()

    def count_by_status(self, owner_id: Optional[UUID] = None) -> dict:
        """
        Count contacts by status.

        Args:
            owner_id: Optional owner filter

        Returns:
            Dictionary with status counts
        """
        query = self.db.query(Contact)

        if owner_id:
            query = query.filter(Contact.owner_id == owner_id)

        total = query.count()
        active = query.filter(Contact.status == 'active').count()
        inactive = query.filter(Contact.status == 'inactive').count()

        return {
            'total': total,
            'active': active,
            'inactive': inactive
        }

    def bulk_create(self, contacts: List[Contact]) -> List[Contact]:
        """
        Create multiple contacts in bulk.

        Args:
            contacts: List of Contact objects

        Returns:
            List of created contacts
        """
        self.db.add_all(contacts)
        self.db.commit()
        return contacts

    def search_contacts_with_activity_counts(
        self,
        search_term: Optional[str] = None,
        status: Optional[str] = None,
        company_ids: Optional[List[UUID]] = None,
        owner_id: Optional[UUID] = None,
        sort_by_activity_count: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search contacts with activity counts included.

        Args:
            search_term: Search by name, email, or company name
            status: Filter by status (active/inactive)
            company_ids: Filter by company IDs
            owner_id: Filter by owner
            sort_by_activity_count: Whether to sort by activity count

        Returns:
            List of contacts with activity counts
        """
        # Base query for contacts
        query = self.db.query(Contact)

        # Add relations
        query = query.options(
            joinedload(Contact.company),
            joinedload(Contact.owner)
        )

        # Owner filter
        if owner_id:
            query = query.filter(Contact.owner_id == owner_id)

        # Search filter
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.join(Company, Contact.company_id ==
                               Company.id, isouter=True)
            query = query.filter(
                or_(
                    Contact.first_name.ilike(search_pattern),
                    Contact.last_name.ilike(search_pattern),
                    Contact.email.ilike(search_pattern),
                    Company.name.ilike(search_pattern)
                )
            )

        # Status filter
        if status:
            query = query.filter(Contact.status == status)

        # Company filter
        if company_ids:
            query = query.filter(Contact.company_id.in_(company_ids))

        # Get contacts first
        contacts = query.all()

        # Build result with activity counts
        contacts_with_counts = []
        for contact in contacts:
            # Count activities for this contact
            activity_count = self.db.query(Activity).filter(
                Activity.contact_id == contact.id
            ).count()

            contact_dict = {
                'id': contact.id,
                'first_name': contact.first_name,
                'last_name': contact.last_name,
                'email': contact.email,
                'phone': contact.phone,
                'mobile': contact.mobile,
                'position': contact.position,
                'status': contact.status,
                'notes': contact.notes,
                'social_linkedin': contact.social_linkedin,
                'social_twitter': contact.social_twitter,
                'company_id': contact.company_id,
                'owner_id': contact.owner_id,
                'created_at': contact.created_at,
                'updated_at': contact.updated_at,
                'activity_count': activity_count,
                'company': {
                    'id': contact.company.id,
                    'name': contact.company.name,
                    'industry': contact.company.industry,
                    'website': contact.company.website
                } if contact.company else None,
                'owner': {
                    'id': contact.owner.id,
                    'first_name': contact.owner.first_name,
                    'last_name': contact.owner.last_name,
                    'email': contact.owner.email
                } if contact.owner else None
            }
            contacts_with_counts.append(contact_dict)

        # Sort by activity count if requested
        if sort_by_activity_count:
            contacts_with_counts.sort(
                key=lambda x: x['activity_count'], reverse=True)

        return contacts_with_counts
