from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import json
from datetime import datetime, timedelta

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import UserProfile
from ..models.integration import Integration, IntegrationLog
from ..schemas.integration import (
    IntegrationResponse,
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationLogResponse,
    OAuthCallbackRequest,
    IntegrationTestRequest,
    IntegrationSyncRequest
)
from ..services.integration_service import IntegrationService

router = APIRouter()


@router.get("/", response_model=List[IntegrationResponse])
async def get_user_integrations(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get all integrations for the current user"""
    integrations = db.query(Integration).filter(
        Integration.user_id == current_user.id
    ).all()

    return integrations


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get a specific integration"""
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.user_id == current_user.id
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    return integration


@router.post("/", response_model=IntegrationResponse)
async def create_integration(
    integration_data: IntegrationCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Create a new integration"""
    # Check if integration already exists for this provider
    existing = db.query(Integration).filter(
        Integration.user_id == current_user.id,
        Integration.provider == integration_data.provider
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integration for {integration_data.provider} already exists"
        )

    integration = Integration(
        user_id=current_user.id,
        provider=integration_data.provider,
        name=integration_data.name,
        description=integration_data.description,
        config=integration_data.config,
        auto_sync=integration_data.auto_sync,
        sync_frequency=integration_data.sync_frequency
    )

    db.add(integration)
    db.commit()
    db.refresh(integration)

    return integration


@router.put("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    integration_data: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Update an integration"""
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.user_id == current_user.id
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    # Update only provided fields
    for field, value in integration_data.dict(exclude_unset=True).items():
        setattr(integration, field, value)

    integration.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(integration)

    return integration


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Delete an integration"""
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.user_id == current_user.id
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    # Disconnect before deletion
    integration_service = IntegrationService(db)
    await integration_service.disconnect_integration(integration_id, current_user.id)

    db.delete(integration)
    db.commit()

    return {"message": "Integration deleted successfully"}


@router.post("/oauth/url")
async def get_oauth_url(
    provider: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get OAuth authorization URL for a provider"""
    integration_service = IntegrationService(db)

    try:
        auth_url = await integration_service.get_oauth_url(provider, current_user.id)
        return {"auth_url": auth_url}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/oauth/callback")
async def oauth_callback(
    callback_data: OAuthCallbackRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Handle OAuth callback and store tokens"""
    integration_service = IntegrationService(db)

    try:
        integration = await integration_service.handle_oauth_callback(
            callback_data.provider,
            callback_data.code,
            current_user.id,
            callback_data.state
        )
        return {"message": "Integration connected successfully", "integration_id": integration.id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Test an integration connection"""
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.user_id == current_user.id
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    integration_service = IntegrationService(db)

    try:
        result = await integration_service.test_integration(integration_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integration test failed: {str(e)}"
        )


@router.post("/{integration_id}/sync")
async def sync_integration(
    integration_id: UUID,
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Manually trigger integration sync"""
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.user_id == current_user.id
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    integration_service = IntegrationService(db)

    try:
        result = await integration_service.sync_integration(integration_id, force)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integration sync failed: {str(e)}"
        )


@router.post("/{integration_id}/disconnect")
async def disconnect_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Disconnect an integration"""
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.user_id == current_user.id
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    integration_service = IntegrationService(db)

    try:
        await integration_service.disconnect_integration(integration_id, current_user.id)
        return {"message": "Integration disconnected successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to disconnect integration: {str(e)}"
        )


@router.get("/{integration_id}/logs", response_model=List[IntegrationLogResponse])
async def get_integration_logs(
    integration_id: UUID,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get logs for an integration"""
    # Verify integration ownership
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.user_id == current_user.id
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )

    logs = db.query(IntegrationLog).filter(
        IntegrationLog.integration_id == integration_id
    ).order_by(
        IntegrationLog.created_at.desc()
    ).offset(offset).limit(limit).all()

    return logs
