"""
Contact API routes.
Clean endpoint definitions using the controller layer.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..controllers.contact_controller import ContactController
from ..schemas.contact import ContactCreate, ContactUpdate, ContactResponse, ContactWithRelations
from ..core.database import get_db
from ..core.auth import get_current_user, require_any_authenticated
from ..models.user import UserProfile


router = APIRouter()


@router.get(
    "/",
    response_model=List[ContactWithRelations],
    summary="Get all contacts",
    description="Retrieve contacts with optional filters (search, status, companies)"
)
async def get_user_contacts(
    search: Optional[str] = Query(
        None,
        description="Search by name, email, or company name"
    ),
    status: Optional[str] = Query(
        None,
        description="Filter by status: active or inactive"
    ),
    companies: Optional[str] = Query(
        None,
        description="Filter by company IDs (comma-separated UUIDs)"
    ),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Retrieve all contacts for the current user with optional filters.

    - **search**: Search in first name, last name, email, or company name
    - **status**: Filter by status (active/inactive)
    - **companies**: Filter by one or more company IDs (comma-separated)

    Returns contacts with company, owner, deals, activities, and tasks relations.
    """
    controller = ContactController(db)
    return await controller.get_contacts(current_user, search, status, companies)


@router.get(
    "/activity-filters",
    summary="Get contacts for activity filters",
    description="Retrieve contacts sorted by activity count for activity filter dropdowns"
)
async def get_contacts_for_activity_filters(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Retrieve contacts sorted by activity count for use in activity filters.

    Returns active contacts sorted by number of activities (most active first).
    Includes activity_count field for each contact.
    """
    controller = ContactController(db)
    return await controller.get_contacts_for_activity_filters(current_user)


@router.get(
    "/{contact_id}",
    response_model=ContactWithRelations,
    summary="Get contact by ID",
    description="Retrieve a single contact with all relations and custom fields"
)
async def get_contact_by_id(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieve a specific contact by ID.

    Returns the contact with:
    - Company information
    - Owner details
    - Associated deals
    - Associated activities
    - Associated tasks
    - Custom field values
    """
    controller = ContactController(db)
    return await controller.get_contact(contact_id, current_user)


@router.post(
    "/",
    response_model=ContactResponse,
    status_code=201,
    summary="Create a new contact",
    description="Create a new contact with optional custom fields"
)
async def create_contact(
    contact_data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new contact.

    The current user will be automatically set as the owner.
    Custom fields can be provided in the `custom_fields` dictionary.

    Example:
    ```json
    {
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "phone": "+1234567890",
      "position": "CEO",
      "company_id": "uuid-here",
      "status": "active",
      "custom_fields": {
        "field_key": "field_value"
      }
    }
    ```
    """
    controller = ContactController(db)
    return await controller.create_contact(contact_data, current_user)


@router.put(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Update a contact",
    description="Update an existing contact's information"
)
async def update_contact(
    contact_id: UUID,
    contact_data: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update an existing contact.

    Only provided fields will be updated (partial update).
    Custom fields can be updated via the `custom_fields` dictionary.

    Requires permission to edit the contact (owner or appropriate role).
    """
    controller = ContactController(db)
    return await controller.update_contact(contact_id, contact_data, current_user)


@router.delete(
    "/{contact_id}",
    summary="Delete a contact",
    description="Delete a contact permanently"
)
async def delete_contact(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete a contact.

    This will permanently remove the contact from the database.
    Requires permission to delete the contact (owner or appropriate role).

    Returns a success message upon deletion.
    """
    controller = ContactController(db)
    return await controller.delete_contact(contact_id, current_user)


# Import schema for bulk import
class ImportContactData(BaseModel):
    """Schema for importing a single contact."""
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    position: Optional[str] = None
    company_name: Optional[str] = None
    status: str = "active"


@router.post(
    "/import",
    summary="Import multiple contacts",
    description="Bulk import contacts from a list"
)
async def import_contacts(
    contacts_data: List[ImportContactData],
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Import multiple contacts at once.

    This endpoint allows bulk creation of contacts from an array.
    If a `company_name` is provided and doesn't exist, it will be created automatically.

    Returns statistics about the import:
    - Number of successfully imported contacts
    - Number of errors
    - List of error messages for failed imports

    Example:
    ```json
    [
      {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "company_name": "Acme Corp"
      },
      {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@example.com"
      }
    ]
    ```
    """
    controller = ContactController(db)

    # Convert Pydantic models to dictionaries
    contacts_dict = [contact.model_dump() for contact in contacts_data]

    return await controller.import_contacts(contacts_dict, current_user)
