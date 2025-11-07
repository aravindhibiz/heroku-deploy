"""
Company API routes.
Clean endpoint definitions using the controller layer.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..controllers.company_controller import CompanyController
from ..schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import UserProfile


router = APIRouter()


@router.get("/", response_model=List[CompanyResponse])
def get_companies(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieve all companies with pagination.

    **Required Permission:** companies:view

    Returns a list of companies ordered by name. Each company includes:
    - Basic company information
    - Owner details (if assigned)
    - Related contacts and deals count

    **Performance Note:** This endpoint uses optimized queries with eager loading
    to prevent N+1 query issues.
    """
    return CompanyController.get_companies(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit
    )


@router.get("/statistics")
def get_company_statistics(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get company statistics.

    **Required Permission:** companies:view

    Returns statistics including:
    - Total company count
    - Breakdown by industry
    - Breakdown by company size
    """
    return CompanyController.get_company_statistics(
        db=db,
        current_user=current_user
    )


@router.get("/search", response_model=List[CompanyResponse])
def search_companies(
    q: str = Query(..., min_length=1, description="Search term"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Search companies by multiple fields including name, industry, location, and size.

    **Required Permission:** companies:view

    Performs a case-insensitive search across multiple company fields:
    - Company name
    - Industry
    - Location (city, state, country)
    - Company size

    Use this endpoint for comprehensive search functionality.
    """
    return CompanyController.search_companies(
        search_term=q,
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit
    )


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieve a single company by ID.

    **Required Permission:** companies:view

    Returns complete company details including:
    - All company fields
    - Custom field values
    - Owner information
    - Related contacts
    - Related deals
    """
    return CompanyController.get_company(
        company_id=company_id,
        db=db,
        current_user=current_user
    )


@router.post("/", response_model=CompanyResponse, status_code=201)
def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new company.

    **Required Permission:** companies:create

    Accepts company data including:
    - Required: name
    - Optional: industry, size, website, contact info, address, revenue
    - Optional: custom_fields (key-value pairs)

    **Custom Fields:**
    Custom fields should be provided as a dictionary where keys are field names
    and values can be strings, numbers, booleans, or dates depending on the field type.

    Example:
    ```json
    {
        "name": "Acme Corp",
        "industry": "Technology",
        "custom_fields": {
            "account_manager": "John Doe",
            "contract_value": 50000
        }
    }
    ```
    """
    return CompanyController.create_company(
        company_data=company,
        db=db,
        current_user=current_user
    )


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: UUID,
    company: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update an existing company.

    **Required Permission:** companies:update

    All fields are optional. Only provided fields will be updated.

    **Partial Updates:**
    This endpoint supports partial updates - you only need to include
    the fields you want to change.

    **Custom Fields:**
    - Providing custom_fields will replace all custom field values
    - To update specific custom fields, include all existing ones you want to keep
    """
    return CompanyController.update_company(
        company_id=company_id,
        company_data=company,
        db=db,
        current_user=current_user
    )


@router.delete("/{company_id}")
def delete_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete a company.

    **Required Permission:** companies:delete

    **Warning:** This action cannot be undone. The company and all associated
    custom field values will be permanently deleted.

    **Note:** This will not delete related contacts or deals, but will remove
    the association with this company.
    """
    return CompanyController.delete_company(
        company_id=company_id,
        db=db,
        current_user=current_user
    )
