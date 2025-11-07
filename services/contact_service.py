"""
Contact Service - Business logic layer for Contact operations.
Handles contact CRUD operations, custom fields, and import functionality.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from repositories.contact_repository import ContactRepository
from models.contact import Contact
from models.company import Company
from models.custom_field import EntityType
from models.user import UserProfile
from schemas.contact import ContactCreate, ContactUpdate, ContactWithRelations
from schemas.user import UserResponse
from schemas.company import CompanyBasicResponse
from services.custom_field_service import CustomFieldService


class ContactService:
    """Service layer for contact business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = ContactRepository(db)

    def get_all_contacts(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        company_ids: Optional[List[UUID]] = None,
        owner_id: Optional[UUID] = None,
        sort_by_activity_count: bool = False
    ) -> List[ContactWithRelations]:
        """
        Get all contacts with optional filters.

        Args:
            search: Search term for name, email, or company
            status: Filter by status
            company_ids: Filter by company IDs
            owner_id: Filter by owner
            sort_by_activity_count: Whether to sort by activity count

        Returns:
            List of contacts with relations properly serialized
        """
        if sort_by_activity_count:
            # Return contacts with activity counts as dictionaries
            return self.repository.search_contacts_with_activity_counts(
                search_term=search,
                status=status,
                company_ids=company_ids,
                owner_id=owner_id,
                sort_by_activity_count=sort_by_activity_count
            )
        else:
            contacts = self.repository.search_contacts(
                search_term=search,
                status=status,
                company_ids=company_ids,
                owner_id=owner_id
            )

            # Serialize contacts properly to avoid circular references
            return [self._build_contact_response(contact) for contact in contacts]

    def get_contacts_for_activity_filters(self, current_user, activity_limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get contacts sorted by activity count for use in activity filters.
        Counts only activities that would be shown in the current timeline view.

        Args:
            current_user: Current authenticated user (for permissions)
            activity_limit: Limit for activities (same as timeline)

        Returns:
            List of contacts with activity counts, sorted by activity count descending
        """
        from models.activity import Activity
        from core.auth_helpers import get_activities_query_filter, get_contacts_query_filter
        from models.contact import Contact

        # Get contacts using the same permission logic
        contact_query = self.db.query(Contact)
        filtered_contact_query = get_contacts_query_filter(
            self.db, current_user, contact_query)
        contacts = filtered_contact_query.filter(
            Contact.status == 'active').all()

        # Get activities using the same permission logic as activity timeline
        activity_query = self.db.query(Activity)
        filtered_activity_query = get_activities_query_filter(
            self.db, current_user, activity_query)

        # Order by created_at desc and limit (same as timeline)
        recent_activities = filtered_activity_query.order_by(
            Activity.created_at.desc()).limit(activity_limit).all()

        # Count activities per contact from the recent activities
        contact_activity_counts = {}
        for activity in recent_activities:
            if activity.contact_id:
                contact_activity_counts[activity.contact_id] = contact_activity_counts.get(
                    activity.contact_id, 0) + 1

        # Build result with activity counts from recent activities only
        contacts_with_counts = []
        for contact in contacts:
            activity_count = contact_activity_counts.get(contact.id, 0)

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

        # Sort by activity count (highest first)
        contacts_with_counts.sort(
            key=lambda x: x['activity_count'], reverse=True)

        return contacts_with_counts

    def get_contact_by_id(self, contact_id: UUID) -> Optional[Contact]:
        """
        Get a single contact with all relations and custom fields.

        Args:
            contact_id: Contact UUID

        Returns:
            Contact with relations or None
        """
        return self.repository.get_with_relations(contact_id)

    def get_contact_with_custom_fields(self, contact_id: UUID) -> Optional[ContactWithRelations]:
        """
        Get contact with custom fields populated.

        Args:
            contact_id: Contact UUID

        Returns:
            ContactWithRelations schema with contact data and custom fields
        """
        contact = self.repository.get_with_relations(contact_id)

        if not contact:
            return None

        # Use the helper method to build properly serialized response
        return self._build_contact_response(contact)

    def create_contact(
        self,
        contact_data: ContactCreate,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Create a new contact with custom fields.

        Args:
            contact_data: Contact creation data
            current_user: Current user (will be set as owner)

        Returns:
            Dictionary with created contact data
        """
        # Extract custom fields
        custom_fields_data = contact_data.custom_fields or {}

        # Create contact
        contact_dict = contact_data.model_dump(
            exclude={'owner_id', 'custom_fields'})
        contact_dict['owner_id'] = current_user.id

        created_contact = self.repository.create(obj_in=contact_dict)

        # Save custom field values
        if custom_fields_data:
            CustomFieldService.save_custom_field_values(
                db=self.db,
                entity_id=str(created_contact.id),
                entity_type=EntityType.CONTACT,
                field_values=custom_fields_data
            )
            self.db.commit()

        # Get custom fields for response
        custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
            db=self.db,
            entity_id=str(created_contact.id),
            entity_type=EntityType.CONTACT
        )

        # Build response
        return {
            "id": created_contact.id,
            "first_name": created_contact.first_name,
            "last_name": created_contact.last_name,
            "email": created_contact.email,
            "phone": created_contact.phone,
            "mobile": created_contact.mobile,
            "position": created_contact.position,
            "status": created_contact.status,
            "notes": created_contact.notes,
            "social_linkedin": created_contact.social_linkedin,
            "social_twitter": created_contact.social_twitter,
            "company_id": created_contact.company_id,
            "owner_id": created_contact.owner_id,
            "created_at": created_contact.created_at,
            "updated_at": created_contact.updated_at,
            "custom_fields": custom_fields_dict if custom_fields_dict else None
        }

    def update_contact(
        self,
        contact_id: UUID,
        contact_data: ContactUpdate
    ) -> Dict[str, Any]:
        """
        Update an existing contact.

        Args:
            contact_id: Contact UUID
            contact_data: Update data

        Returns:
            Dictionary with updated contact data
        """
        contact = self.repository.get(contact_id)

        if not contact:
            return None

        # Extract custom fields
        update_data = contact_data.model_dump(exclude_unset=True)
        custom_fields_data = update_data.pop('custom_fields', None)

        # Update contact fields
        updated_contact = self.repository.update(
            db_obj=contact, obj_in=update_data)

        # Update custom fields if provided
        if custom_fields_data is not None:
            CustomFieldService.save_custom_field_values(
                db=self.db,
                entity_id=str(contact.id),
                entity_type=EntityType.CONTACT,
                field_values=custom_fields_data
            )
            self.db.commit()

        # Get custom fields for response
        custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
            db=self.db,
            entity_id=str(contact.id),
            entity_type=EntityType.CONTACT
        )

        # Build response
        return {
            "id": updated_contact.id,
            "first_name": updated_contact.first_name,
            "last_name": updated_contact.last_name,
            "email": updated_contact.email,
            "phone": updated_contact.phone,
            "mobile": updated_contact.mobile,
            "position": updated_contact.position,
            "status": updated_contact.status,
            "notes": updated_contact.notes,
            "social_linkedin": updated_contact.social_linkedin,
            "social_twitter": updated_contact.social_twitter,
            "company_id": updated_contact.company_id,
            "owner_id": updated_contact.owner_id,
            "created_at": updated_contact.created_at,
            "updated_at": updated_contact.updated_at,
            "custom_fields": custom_fields_dict if custom_fields_dict else None
        }

    def delete_contact(self, contact_id: UUID) -> bool:
        """
        Delete a contact.

        When deleting a contact that was converted from a prospect:
        1. CASCADE delete campaign_contacts entries (handled by FK)
        2. SET NULL on prospect.converted_to_contact_id (handled by FK)

        Args:
            contact_id: Contact UUID

        Returns:
            True if deleted, False if not found
        """
        from app.models.campaign_contact import CampaignContact
        from app.models.prospect import Prospect

        # Get the contact first to verify it exists
        contact = self.repository.get(id=contact_id)
        if not contact:
            return False

        # The foreign keys should handle cleanup automatically:
        # - campaign_contacts.contact_id has ondelete="CASCADE"
        # - prospects.converted_to_contact_id has ondelete="SET NULL"
        # But we'll explicitly clean up campaign_contacts to avoid constraint issues

        # Delete campaign_contacts entries for this contact
        self.db.query(CampaignContact).filter(
            CampaignContact.contact_id == contact_id
        ).delete(synchronize_session=False)

        # Set converted_to_contact_id to NULL for any prospects
        self.db.query(Prospect).filter(
            Prospect.converted_to_contact_id == contact_id
        ).update({"converted_to_contact_id": None}, synchronize_session=False)

        # Commit the cleanup
        self.db.commit()

        # Now delete the contact
        return self.repository.delete(id=contact_id)

    def import_contacts(
        self,
        contacts_data: List[Dict[str, Any]],
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Import multiple contacts.

        Args:
            contacts_data: List of contact dictionaries
            current_user: Current user (will be set as owner)

        Returns:
            Dictionary with import results
        """
        imported_contacts = []
        errors = []

        for i, contact_dict in enumerate(contacts_data):
            try:
                # Create or find company if company_name is provided
                company_id = None
                if contact_dict.get('company_name'):
                    company = self.db.query(Company).filter(
                        Company.name == contact_dict['company_name']
                    ).first()

                    if not company:
                        # Create new company
                        company = Company(
                            name=contact_dict['company_name'],
                            owner_id=current_user.id
                        )
                        self.db.add(company)
                        self.db.flush()

                    company_id = company.id

                # Create contact
                contact = Contact(
                    first_name=contact_dict['first_name'],
                    last_name=contact_dict['last_name'],
                    email=contact_dict.get('email'),
                    phone=contact_dict.get('phone'),
                    mobile=contact_dict.get('mobile'),
                    position=contact_dict.get('position'),
                    status=contact_dict.get('status', 'active'),
                    company_id=company_id,
                    owner_id=current_user.id
                )

                imported_contacts.append(contact)

            except Exception as e:
                errors.append(f"Row {i + 1}: {str(e)}")

        # Bulk create contacts
        if imported_contacts:
            try:
                created_contacts = self.repository.bulk_create(
                    imported_contacts)
                self.db.commit()

                # Refresh to get IDs
                for contact in created_contacts:
                    self.db.refresh(contact)

            except Exception as e:
                self.db.rollback()
                return {
                    "message": f"Failed to import contacts: {str(e)}",
                    "imported_count": 0,
                    "error_count": len(contacts_data),
                    "errors": [f"Database commit failed: {str(e)}"]
                }

        return {
            "message": f"Successfully imported {len(imported_contacts)} contacts",
            "imported_count": len(imported_contacts),
            "error_count": len(errors),
            "errors": errors
        }

    def get_contact_statistics(self, owner_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get contact statistics.

        Args:
            owner_id: Optional owner filter

        Returns:
            Dictionary with statistics
        """
        return self.repository.count_by_status(owner_id)

    def _build_contact_response(self, contact: Contact) -> ContactWithRelations:
        """
        Build a properly serialized ContactWithRelations response.

        Args:
            contact: Contact model instance

        Returns:
            ContactWithRelations schema
        """
        # Get custom fields
        custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
            db=self.db,
            entity_id=str(contact.id),
            entity_type=EntityType.CONTACT
        )

        # Serialize owner properly
        owner_data = None
        if contact.owner:
            owner_data = UserResponse(
                id=contact.owner.id,
                email=contact.owner.email,
                first_name=contact.owner.first_name,
                last_name=contact.owner.last_name,
                avatar_url=contact.owner.avatar_url,
                is_active=contact.owner.is_active,
                created_at=contact.owner.created_at,
                updated_at=contact.owner.updated_at,
                role=contact.owner.role if hasattr(contact.owner, 'role') else None,
                phone=contact.owner.phone if hasattr(contact.owner, 'phone') else None
            )

        # Serialize company properly using CompanyBasicResponse to avoid circular refs
        company_data = None
        if contact.company:
            company_data = CompanyBasicResponse(
                id=contact.company.id,
                name=contact.company.name,
                industry=contact.company.industry,
                size=contact.company.size,
                website=contact.company.website,
                phone=contact.company.phone,
                email=contact.company.email,
                address=contact.company.address,
                city=contact.company.city,
                state=contact.company.state,
                zip_code=contact.company.zip_code,
                country=contact.company.country,
                description=contact.company.description,
                revenue=contact.company.revenue,
                created_at=contact.company.created_at,
                updated_at=contact.company.updated_at
            )

        # Build ContactWithRelations response
        return ContactWithRelations(
            id=contact.id,
            first_name=contact.first_name,
            last_name=contact.last_name,
            email=contact.email,
            phone=contact.phone,
            mobile=contact.mobile,
            position=contact.position,
            status=contact.status,
            notes=contact.notes,
            social_linkedin=contact.social_linkedin,
            social_twitter=contact.social_twitter,
            company_id=contact.company_id,
            owner_id=contact.owner_id,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            custom_fields=custom_fields_dict,
            owner=owner_data,
            company=company_data
        )
