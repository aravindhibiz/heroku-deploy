"""
Helper functions for permission-based access control in routes
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from auth import has_permission
from models.user import UserProfile


def get_deals_query_filter(db: Session, current_user: UserProfile, base_query):
    """
    Apply permission-based filtering to deals query

    Returns filtered query based on user's permissions:
    - deals.view_all: Can see all deals
    - deals.view_own: Can only see own deals
    """
    can_view_all = has_permission(db, current_user, "deals.view_all")
    can_view_own = has_permission(db, current_user, "deals.view_own")

    if not can_view_all and not can_view_own:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. You don't have permission to view deals."
        )

    if can_view_all:
        return base_query
    else:
        # Filter to own deals only
        from models.deal import Deal
        return base_query.filter(Deal.owner_id == current_user.id)


def check_deal_edit_permission(
    db: Session,
    current_user: UserProfile,
    deal
) -> bool:
    """Check if user can edit a specific deal"""
    # Check if user has edit_all permission
    if has_permission(db, current_user, "deals.edit_all"):
        return True

    # Check if user has edit_own permission and owns the deal
    if has_permission(db, current_user, "deals.edit_own") and str(current_user.id) == str(deal.owner_id):
        return True

    return False


def check_deal_delete_permission(
    db: Session,
    current_user: UserProfile,
    deal
) -> bool:
    """Check if user can delete a specific deal"""
    # Check if user has delete_all permission
    if has_permission(db, current_user, "deals.delete_all"):
        return True

    # Check if user has delete_own permission and owns the deal
    if has_permission(db, current_user, "deals.delete_own") and str(current_user.id) == str(deal.owner_id):
        return True

    return False


def get_contacts_query_filter(db: Session, current_user: UserProfile, base_query):
    """
    Apply permission-based filtering to contacts query
    """
    can_view_all = has_permission(db, current_user, "contacts.view_all")
    can_view_own = has_permission(db, current_user, "contacts.view_own")

    if not can_view_all and not can_view_own:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. You don't have permission to view contacts."
        )

    if can_view_all:
        return base_query
    else:
        # Filter to own contacts only
        from models.contact import Contact
        return base_query.filter(Contact.owner_id == current_user.id)


def get_companies_query_filter(db: Session, current_user: UserProfile, base_query):
    """
    Apply permission-based filtering to companies query

    Returns filtered query based on user's permissions:
    - companies.view_all: Can see all companies
    - companies.view_own: Can only see own companies
    """
    can_view_all = has_permission(db, current_user, "companies.view_all")
    can_view_own = has_permission(db, current_user, "companies.view_own")

    if not can_view_all and not can_view_own:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. You don't have permission to view companies."
        )

    if can_view_all:
        return base_query
    else:
        # Filter to own companies only
        from models.company import Company
        return base_query.filter(Company.owner_id == current_user.id)


def check_company_edit_permission(
    db: Session,
    current_user: UserProfile,
    company
) -> bool:
    """Check if user can edit a specific company"""
    # Check if user has edit_all permission
    if has_permission(db, current_user, "companies.edit_all"):
        return True

    # Check if user has edit_own permission and owns the company
    if has_permission(db, current_user, "companies.edit_own") and str(current_user.id) == str(company.owner_id):
        return True

    return False


def check_company_delete_permission(
    db: Session,
    current_user: UserProfile,
    company
) -> bool:
    """Check if user can delete a specific company"""
    # Check if user has delete_all permission
    if has_permission(db, current_user, "companies.delete_all"):
        return True

    # Check if user has delete_own permission and owns the company
    if has_permission(db, current_user, "companies.delete_own") and str(current_user.id) == str(company.owner_id):
        return True

    return False


def check_contact_edit_permission(
    db: Session,
    current_user: UserProfile,
    contact
) -> bool:
    """Check if user can edit a specific contact"""
    if has_permission(db, current_user, "contacts.edit_all"):
        return True

    if has_permission(db, current_user, "contacts.edit_own") and str(current_user.id) == str(contact.owner_id):
        return True

    return False


def check_contact_delete_permission(
    db: Session,
    current_user: UserProfile,
    contact
) -> bool:
    """Check if user can delete a specific contact"""
    if has_permission(db, current_user, "contacts.delete_all"):
        return True

    if has_permission(db, current_user, "contacts.delete_own") and str(current_user.id) == str(contact.owner_id):
        return True

    return False


def get_activities_query_filter(db: Session, current_user: UserProfile, base_query):
    """
    Apply permission-based filtering to activities query
    """
    can_view_all = has_permission(db, current_user, "activities.view_all")
    can_view_own = has_permission(db, current_user, "activities.view_own")

    if not can_view_all and not can_view_own:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. You don't have permission to view activities."
        )

    if can_view_all:
        return base_query
    else:
        # Filter to activities for own contacts only
        from models.activity import Activity
        return base_query.filter(Activity.user_id == current_user.id)


def check_activity_edit_permission(
    db: Session,
    current_user: UserProfile,
    activity
) -> bool:
    """Check if user can edit a specific activity"""
    if has_permission(db, current_user, "activities.edit_all"):
        return True

    if has_permission(db, current_user, "activities.edit_own") and str(current_user.id) == str(activity.user_id):
        return True

    return False


def check_activity_delete_permission(
    db: Session,
    current_user: UserProfile,
    activity
) -> bool:
    """Check if user can delete a specific activity"""
    if has_permission(db, current_user, "activities.delete_all"):
        return True

    if has_permission(db, current_user, "activities.delete_own") and str(current_user.id) == str(activity.user_id):
        return True

    return False


def get_campaigns_query_filter(db: Session, current_user: UserProfile, base_query):
    """
    Apply permission-based filtering to campaigns query

    Returns filtered query based on user's permissions:
    - campaigns.view_all: Can see all campaigns
    - campaigns.view_own: Can only see own campaigns
    """
    can_view_all = has_permission(db, current_user, "campaigns.view_all")
    can_view_own = has_permission(db, current_user, "campaigns.view_own")

    if not can_view_all and not can_view_own:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. You don't have permission to view campaigns."
        )

    if can_view_all:
        return base_query
    else:
        # Filter to own campaigns only
        from models.campaign import Campaign
        return base_query.filter(Campaign.owner_id == current_user.id)


def check_campaign_edit_permission(
    db: Session,
    current_user: UserProfile,
    campaign
) -> bool:
    """Check if user can edit a specific campaign"""
    # Check if user has edit_all permission
    if has_permission(db, current_user, "campaigns.edit_all"):
        return True

    # Check if user has edit_own permission and owns the campaign
    if has_permission(db, current_user, "campaigns.edit_own") and str(current_user.id) == str(campaign.owner_id):
        return True

    return False


def check_campaign_delete_permission(
    db: Session,
    current_user: UserProfile,
    campaign
) -> bool:
    """Check if user can delete a specific campaign"""
    # Check if user has delete_all permission
    if has_permission(db, current_user, "campaigns.delete_all"):
        return True

    # Check if user has delete_own permission and owns the campaign
    if has_permission(db, current_user, "campaigns.delete_own") and str(current_user.id) == str(campaign.owner_id):
        return True

    return False
