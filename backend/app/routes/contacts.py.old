from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from ..core.database import get_db
from ..core.auth import (
    get_current_user, require_sales_user, require_any_authenticated,
    can_access_user_data, can_modify_user_data
)
from ..models.user import UserProfile
from ..models.contact import Contact
from ..models.company import Company
from ..models.custom_field import CustomFieldValue, EntityType
from ..schemas.contact import ContactCreate, ContactUpdate, ContactResponse, ContactWithRelations
from ..services.custom_field_service import CustomFieldService

router = APIRouter()


@router.get("/", response_model=List[ContactWithRelations])
async def get_user_contacts(
    search: Optional[str] = Query(
        None, description="Search by name, email, or company"),
    status: Optional[str] = Query(
        None, description="Filter by status (active/inactive)"),
    companies: Optional[str] = Query(
        None, description="Filter by company IDs (comma-separated)"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    query = db.query(Contact).options(
        joinedload(Contact.company),
        joinedload(Contact.owner),
        joinedload(Contact.deals),
        joinedload(Contact.activities),
        joinedload(Contact.tasks)
    )

    # Permission-based filtering using helper function
    from ..core.auth_helpers import get_contacts_query_filter
    query = get_contacts_query_filter(db, current_user, query)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.join(Company, Contact.company_id ==
                           Company.id, isouter=True)
        query = query.filter(
            or_(
                Contact.first_name.ilike(search_term),
                Contact.last_name.ilike(search_term),
                Contact.email.ilike(search_term),
                Company.name.ilike(search_term)
            )
        )

    # Apply status filter
    if status:
        query = query.filter(Contact.status == status)

    # Apply company filter
    if companies:
        try:
            company_ids = [UUID(cid.strip())
                           for cid in companies.split(',') if cid.strip()]
            if company_ids:
                query = query.filter(Contact.company_id.in_(company_ids))
        except ValueError:
            pass  # Invalid UUIDs, ignore filter

    contacts = query.order_by(Contact.updated_at.desc()).all()
    return contacts


@router.get("/{contact_id}", response_model=ContactWithRelations)
async def get_contact_by_id(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    contact = db.query(Contact).options(
        joinedload(Contact.company),
        joinedload(Contact.owner),
        joinedload(Contact.deals),
        joinedload(Contact.activities),
        joinedload(Contact.tasks)
    ).filter(Contact.id == contact_id, Contact.owner_id == current_user.id).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    # Get custom fields data
    custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
        db=db,
        entity_id=str(contact.id),
        entity_type=EntityType.CONTACT
    )

    # Build response with custom fields and relations
    response_data = {
        "id": contact.id,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "email": contact.email,
        "phone": contact.phone,
        "mobile": contact.mobile,
        "position": contact.position,
        "status": contact.status,
        "notes": contact.notes,
        "social_linkedin": contact.social_linkedin,
        "social_twitter": contact.social_twitter,
        "company_id": contact.company_id,
        "owner_id": contact.owner_id,
        "created_at": contact.created_at,
        "updated_at": contact.updated_at,
        "custom_fields": custom_fields_dict if custom_fields_dict else None,
        "owner": contact.owner,
        "company": contact.company
    }

    return response_data


@router.post("/", response_model=ContactResponse)
async def create_contact(
    contact_data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    try:
        # Extract custom fields before creating contact
        custom_fields_data = contact_data.custom_fields or {}

        # Create contact with current user as owner
        contact_dict = contact_data.model_dump(
            exclude={'owner_id', 'custom_fields'})
        db_contact = Contact(
            **contact_dict,
            owner_id=current_user.id
        )

        db.add(db_contact)
        db.commit()
        db.refresh(db_contact)

        # Save custom field values if provided
        if custom_fields_data:
            print(f"DEBUG: Saving custom fields: {custom_fields_data}")
            result = CustomFieldService.save_custom_field_values(
                db=db,
                entity_id=str(db_contact.id),
                entity_type=EntityType.CONTACT,
                field_values=custom_fields_data
            )
            print(f"DEBUG: Save result: {result}")
            db.commit()  # Commit custom field values

        # Get custom fields for response
        custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
            db=db,
            entity_id=str(db_contact.id),
            entity_type=EntityType.CONTACT
        )

        # Build response with custom fields
        response_data = {
            "id": db_contact.id,
            "first_name": db_contact.first_name,
            "last_name": db_contact.last_name,
            "email": db_contact.email,
            "phone": db_contact.phone,
            "mobile": db_contact.mobile,
            "position": db_contact.position,
            "status": db_contact.status,
            "notes": db_contact.notes,
            "social_linkedin": db_contact.social_linkedin,
            "social_twitter": db_contact.social_twitter,
            "company_id": db_contact.company_id,
            "owner_id": db_contact.owner_id,
            "created_at": db_contact.created_at,
            "updated_at": db_contact.updated_at,
            "custom_fields": custom_fields_dict if custom_fields_dict else None
        }

        return response_data

    except Exception as e:
        db.rollback()
        print(f"Error creating contact: {str(e)}")  # For debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create contact: {str(e)}"
        )


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    contact_data: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.owner_id == current_user.id
    ).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    try:
        # Extract custom fields before updating contact
        update_data = contact_data.model_dump(exclude_unset=True)
        custom_fields_data = update_data.pop('custom_fields', None)

        # Update contact fields
        for field, value in update_data.items():
            setattr(contact, field, value)

        db.commit()
        db.refresh(contact)

        # Update custom field values if provided
        if custom_fields_data is not None:
            CustomFieldService.save_custom_field_values(
                db=db,
                entity_id=str(contact.id),
                entity_type=EntityType.CONTACT,
                field_values=custom_fields_data
            )
            db.commit()  # Commit custom field values

        # Get custom fields for response
        custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
            db=db,
            entity_id=str(contact.id),
            entity_type=EntityType.CONTACT
        )

        # Build response with custom fields
        response_data = {
            "id": contact.id,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "email": contact.email,
            "phone": contact.phone,
            "mobile": contact.mobile,
            "position": contact.position,
            "status": contact.status,
            "notes": contact.notes,
            "social_linkedin": contact.social_linkedin,
            "social_twitter": contact.social_twitter,
            "company_id": contact.company_id,
            "owner_id": contact.owner_id,
            "created_at": contact.created_at,
            "updated_at": contact.updated_at,
            "custom_fields": custom_fields_dict if custom_fields_dict else None
        }

        return response_data

    except Exception as e:
        db.rollback()
        print(f"Error updating contact: {str(e)}")  # For debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update contact: {str(e)}"
        )


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.owner_id == current_user.id
    ).first()

    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found"
        )

    db.delete(contact)
    db.commit()

    return {"message": "Contact deleted successfully"}


class ImportContactData(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    position: Optional[str] = None
    company_name: Optional[str] = None
    status: str = "active"


@router.post("/import")
async def import_contacts(
    contacts_data: List[ImportContactData],
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Import multiple contacts"""
    print(f"Import request received for {len(contacts_data)} contacts")
    print(f"Current user: {current_user.email}")

    imported_contacts = []
    errors = []

    for i, contact_data in enumerate(contacts_data):
        try:
            print(
                f"Processing contact {i+1}: {contact_data.first_name} {contact_data.last_name}")

            # Create or find company if company_name is provided
            company_id = None
            if contact_data.company_name:
                company = db.query(Company).filter(
                    Company.name == contact_data.company_name
                ).first()

                if not company:
                    # Create new company
                    print(f"Creating new company: {contact_data.company_name}")
                    company = Company(
                        name=contact_data.company_name,
                        owner_id=current_user.id
                    )
                    db.add(company)
                    db.flush()  # Flush to get the ID

                company_id = company.id

            # Create contact
            db_contact = Contact(
                first_name=contact_data.first_name,
                last_name=contact_data.last_name,
                email=contact_data.email,
                phone=contact_data.phone,
                mobile=contact_data.mobile,
                position=contact_data.position,
                status=contact_data.status,
                company_id=company_id,
                owner_id=current_user.id
            )

            db.add(db_contact)
            imported_contacts.append(db_contact)
            print(f"Contact {i+1} added to session")

        except Exception as e:
            error_msg = f"Row {i + 1}: {str(e)}"
            print(f"Error processing contact {i+1}: {str(e)}")
            errors.append(error_msg)

    if imported_contacts:
        try:
            print(
                f"Committing {len(imported_contacts)} contacts to database...")
            db.commit()
            print("Commit successful!")

            # Refresh objects to ensure they have IDs
            for contact in imported_contacts:
                db.refresh(contact)
                print(
                    f"Refreshed contact: {contact.id} - {contact.first_name} {contact.last_name}")

        except Exception as e:
            print(f"Commit failed: {str(e)}")
            import traceback
            traceback.print_exc()
            db.rollback()
            return {
                "message": f"Failed to import contacts: {str(e)}",
                "imported_count": 0,
                "error_count": len(contacts_data),
                "errors": [f"Database commit failed: {str(e)}"]
            }

    print(
        f"Import complete: {len(imported_contacts)} imported, {len(errors)} errors")

    # Verify the contacts were actually saved
    if imported_contacts:
        saved_count = db.query(Contact).filter(
            Contact.id.in_([c.id for c in imported_contacts])
        ).count()
        print(f"Verification: {saved_count} contacts found in database")

    return {
        "message": f"Successfully imported {len(imported_contacts)} contacts",
        "imported_count": len(imported_contacts),
        "error_count": len(errors),
        "errors": errors
    }
