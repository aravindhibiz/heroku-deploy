from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import UserProfile
from ..models.contact import Contact
from ..models.deal import Deal
from ..models.activity import Activity
from ..models.task import Task
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Get counts
    total_contacts = db.query(Contact).filter(
        Contact.owner_id == current_user.id).count()
    total_deals = db.query(Deal).filter(
        Deal.owner_id == current_user.id).count()

    # Get pending tasks
    pending_tasks_count = db.query(Task).filter(
        Task.assigned_to == current_user.id,
        Task.status == 'pending'
    ).count()

    # Get deal values
    active_deals = db.query(Deal).filter(
        Deal.owner_id == current_user.id,
        Deal.stage.notin_(['closed_won', 'closed_lost'])
    ).all()

    won_deals = db.query(Deal).filter(
        Deal.owner_id == current_user.id,
        Deal.stage == 'closed_won'
    ).all()

    pipeline_value = sum([float(deal.value or 0) for deal in active_deals])
    won_value = sum([float(deal.value or 0) for deal in won_deals])

    # Get this month's activities
    start_of_month = datetime.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)
    activities_this_month = db.query(Activity).filter(
        Activity.user_id == current_user.id,
        Activity.created_at >= start_of_month
    ).count()

    # Get recent activities (last 5)
    recent_activities = db.query(Activity).filter(
        Activity.user_id == current_user.id
    ).order_by(Activity.created_at.desc()).limit(5).all()

    # Get upcoming tasks (next 5 due)
    upcoming_tasks = db.query(Task).filter(
        Task.assigned_to == current_user.id,
        Task.status != 'completed',
        Task.due_date.isnot(None)
    ).order_by(Task.due_date.asc()).limit(5).all()

    return {
        "metrics": {
            "total_contacts": total_contacts,
            "total_deals": total_deals,
            "pipeline_value": int(pipeline_value),
            "won_value": int(won_value),
            "pending_tasks": pending_tasks_count,
            "activities_this_month": activities_this_month
        },
        "recent_activities": [
            {
                "id": str(activity.id),
                "type": activity.type,
                "subject": activity.subject,
                "description": activity.description,
                "created_at": activity.created_at.isoformat(),
                "contact": {
                    "name": f"{activity.contact.first_name} {activity.contact.last_name}" if activity.contact else None
                } if activity.contact else None
            }
            for activity in recent_activities
        ],
        "upcoming_tasks": [
            {
                "id": str(task.id),
                "title": task.title,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "priority": task.priority,
                "status": task.status
            }
            for task in upcoming_tasks
        ]
    }


@router.get("/quick-stats")
async def get_quick_stats(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Get current month data
    now = datetime.now()
    start_of_month = now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_last_month = (start_of_month - timedelta(days=1)).replace(day=1)

    # Contacts
    contacts_this_month = db.query(Contact).filter(
        Contact.owner_id == current_user.id,
        Contact.created_at >= start_of_month
    ).count()

    contacts_last_month = db.query(Contact).filter(
        Contact.owner_id == current_user.id,
        Contact.created_at >= start_of_last_month,
        Contact.created_at < start_of_month
    ).count()

    # Deals
    deals_this_month = db.query(Deal).filter(
        Deal.owner_id == current_user.id,
        Deal.created_at >= start_of_month
    ).count()

    deals_last_month = db.query(Deal).filter(
        Deal.owner_id == current_user.id,
        Deal.created_at >= start_of_last_month,
        Deal.created_at < start_of_month
    ).count()

    # Activities
    activities_this_month = db.query(Activity).filter(
        Activity.user_id == current_user.id,
        Activity.created_at >= start_of_month
    ).count()

    activities_last_month = db.query(Activity).filter(
        Activity.user_id == current_user.id,
        Activity.created_at >= start_of_last_month,
        Activity.created_at < start_of_month
    ).count()

    def calculate_growth(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)

    return {
        "contacts": {
            "count": contacts_this_month,
            "growth": calculate_growth(contacts_this_month, contacts_last_month)
        },
        "deals": {
            "count": deals_this_month,
            "growth": calculate_growth(deals_this_month, deals_last_month)
        },
        "activities": {
            "count": activities_this_month,
            "growth": calculate_growth(activities_this_month, activities_last_month)
        }
    }
