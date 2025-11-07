from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from uuid import UUID
from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import UserProfile
from ..models.company import Company
from ..models.custom_field import EntityType
from ..schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from ..services.custom_field_service import CustomFieldService

router = APIRouter()


@router.get("/", response_model=List[CompanyResponse])
async def get_all_companies(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    companies = db.query(Company).options(
        joinedload(Company.contacts),
        joinedload(Company.deals)
    ).order_by(Company.name).all()

    return companies


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company_by_id(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    company = db.query(Company).options(
        joinedload(Company.contacts),
        joinedload(Company.deals)
    ).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Get custom fields for the company
    custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
        db=db,
        entity_id=str(company.id),
        entity_type=EntityType.COMPANY
    )

    # Build response with custom fields
    response_data = {
        "id": company.id,
        "name": company.name,
        "industry": company.industry,
        "size": company.size,
        "website": company.website,
        "phone": company.phone,
        "email": company.email,
        "address": company.address,
        "city": company.city,
        "state": company.state,
        "zip_code": company.zip_code,
        "country": company.country,
        "description": company.description,
        "revenue": company.revenue,
        "created_at": company.created_at,
        "updated_at": company.updated_at,
        "custom_fields": custom_fields_dict if custom_fields_dict else None
    }

    return response_data


@router.post("/", response_model=CompanyResponse)
async def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    try:
        # Extract custom fields before creating company
        custom_fields_data = company_data.custom_fields or {}

        # Create company
        company_dict = company_data.dict(exclude={'custom_fields'})
        db_company = Company(**company_dict)

        db.add(db_company)
        db.commit()
        db.refresh(db_company)

        # Save custom field values if provided
        if custom_fields_data:
            print(
                f"DEBUG: Saving custom fields for company: {custom_fields_data}")
            result = CustomFieldService.save_custom_field_values(
                db=db,
                entity_id=str(db_company.id),
                entity_type=EntityType.COMPANY,
                field_values=custom_fields_data
            )
            print(f"DEBUG: Save result: {result}")
            db.commit()  # Commit custom field values

        # Get custom fields for response
        custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
            db=db,
            entity_id=str(db_company.id),
            entity_type=EntityType.COMPANY
        )

        # Build response with custom fields
        response_data = {
            "id": db_company.id,
            "name": db_company.name,
            "industry": db_company.industry,
            "size": db_company.size,
            "website": db_company.website,
            "phone": db_company.phone,
            "email": db_company.email,
            "address": db_company.address,
            "city": db_company.city,
            "state": db_company.state,
            "zip_code": db_company.zip_code,
            "country": db_company.country,
            "description": db_company.description,
            "revenue": db_company.revenue,
            "created_at": db_company.created_at,
            "updated_at": db_company.updated_at,
            "custom_fields": custom_fields_dict if custom_fields_dict else None
        }

        return response_data

    except Exception as e:
        db.rollback()
        print(f"Error creating company: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company: {str(e)}"
        )


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    company_data: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    try:
        # Extract custom fields before updating company
        update_data = company_data.dict(exclude_unset=True)
        custom_fields_data = update_data.pop('custom_fields', None)

        # Update company fields
        for field, value in update_data.items():
            setattr(company, field, value)

        db.commit()
        db.refresh(company)

        # Update custom field values if provided
        if custom_fields_data is not None:
            CustomFieldService.save_custom_field_values(
                db=db,
                entity_id=str(company.id),
                entity_type=EntityType.COMPANY,
                field_values=custom_fields_data
            )
            db.commit()  # Commit custom field values

        # Get custom fields for response
        custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
            db=db,
            entity_id=str(company.id),
            entity_type=EntityType.COMPANY
        )

        # Build response with custom fields
        response_data = {
            "id": company.id,
            "name": company.name,
            "industry": company.industry,
            "size": company.size,
            "website": company.website,
            "phone": company.phone,
            "email": company.email,
            "address": company.address,
            "city": company.city,
            "state": company.state,
            "zip_code": company.zip_code,
            "country": company.country,
            "description": company.description,
            "revenue": company.revenue,
            "created_at": company.created_at,
            "updated_at": company.updated_at,
            "custom_fields": custom_fields_dict if custom_fields_dict else None
        }

        return response_data

    except Exception as e:
        db.rollback()
        print(f"Error updating company: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update company: {str(e)}"
        )


@router.delete("/{company_id}")
async def delete_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    company = db.query(Company).filter(Company.id == company_id).first()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    db.delete(company)
    db.commit()

    return {"message": "Company deleted successfully"}
