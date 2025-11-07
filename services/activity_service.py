"""
Activity service for business logic.
Handles all business rules and orchestrates operations for activities.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, Query, joinedload

from repositories.activity_repository import ActivityRepository
from models.activity import Activity
from models.contact import Contact
from models.user import UserProfile
from models.custom_field import EntityType
from schemas.activity import (
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivityWithRelations
)
from custom_field_service import CustomFieldService


class ActivityService:
    """
    Service class for Activity business logic.

    This service layer handles all business rules, validations, and orchestration
    for activity-related operations. It uses the repository for data access and
    coordinates with other services as needed.
    """

    def __init__(self, db: Session):
        """
        Initialize the activity service.

        Args:
            db: Database session
        """
        self.db = db
        self.repository = ActivityRepository(db)

    def get_activity_by_id(
        self,
        activity_id: UUID,
        *,
        include_custom_fields: bool = True
    ) -> Optional[ActivityWithRelations]:
        """
        Retrieve an activity by ID with all relations and custom fields.

        Args:
            activity_id: UUID of the activity
            include_custom_fields: Whether to include custom fields in response

        Returns:
            Activity with relations and custom fields, or None if not found
        """
        activity = self.repository.get_with_relations(activity_id)

        if not activity:
            return None

        return self._build_activity_response_with_relations(
            activity,
            include_custom_fields=include_custom_fields
        )

    def get_activities(
        self,
        *,
        filtered_query: Optional[Query] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[ActivityResponse]:
        """
        Retrieve activities with optional filtering.

        Args:
            filtered_query: Pre-filtered query (e.g., with permission filters)
            limit: Maximum number of records to return
            skip: Number of records to skip

        Returns:
            List of activities
        """
        if filtered_query is not None:
            activities = (
                filtered_query
                .order_by(Activity.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
        else:
            activities = self.repository.get_recent_activities(
                limit=limit,
                load_relations=True
            )

        return [
            self._build_activity_response(activity)
            for activity in activities
        ]

    def get_activities_with_relations(
        self,
        *,
        filtered_query: Optional[Query] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[ActivityWithRelations]:
        """
        Retrieve activities with relations (contact, deal, user).

        Args:
            filtered_query: Pre-filtered query (e.g., with permission filters)
            limit: Maximum number of records to return
            skip: Number of records to skip

        Returns:
            List of activities with relations
        """
        if filtered_query is not None:
            # Load activities with relations using joinedload
            activities = (
                filtered_query
                .options(
                    joinedload(Activity.contact).joinedload(Contact.company),
                    joinedload(Activity.deal),
                    joinedload(Activity.user)
                )
                .order_by(Activity.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
        else:
            activities = self.repository.get_recent_activities(
                limit=limit,
                load_relations=True
            )

        return [
            self._build_activity_response_with_relations(activity)
            for activity in activities
        ]

    def create_activity(
        self,
        activity_data: ActivityCreate,
        current_user: UserProfile
    ) -> ActivityResponse:
        """
        Create a new activity.

        Args:
            activity_data: Activity creation data
            current_user: The user creating the activity

        Returns:
            The created activity with custom fields

        Raises:
            Exception: If creation fails
        """
        try:
            # Extract custom fields
            custom_fields_data = activity_data.custom_fields or {}

            # Prepare activity data for creation
            activity_dict = activity_data.dict(exclude={'custom_fields'})
            activity_dict['user_id'] = current_user.id

            # Create activity via repository
            db_activity = self.repository.create(obj_in=activity_dict)

            # Save custom field values if provided
            if custom_fields_data:
                CustomFieldService.save_custom_field_values(
                    db=self.db,
                    entity_id=str(db_activity.id),
                    entity_type=EntityType.ACTIVITY,
                    field_values=custom_fields_data
                )

            # Commit the transaction
            self.db.commit()
            self.db.refresh(db_activity)

            return self._build_activity_response(db_activity)

        except Exception as e:
            self.db.rollback()
            raise e

    def update_activity(
        self,
        activity_id: UUID,
        activity_data: ActivityUpdate
    ) -> Optional[ActivityResponse]:
        """
        Update an existing activity.

        Args:
            activity_id: UUID of the activity to update
            activity_data: Activity update data

        Returns:
            The updated activity, or None if not found

        Raises:
            Exception: If update fails
        """
        try:
            # Get existing activity
            db_activity = self.repository.get(activity_id)

            if not db_activity:
                return None

            # Extract custom fields
            custom_fields_data = activity_data.custom_fields

            # Update activity fields (exclude unset and custom_fields)
            update_data = activity_data.dict(
                exclude_unset=True,
                exclude={'custom_fields'}
            )

            if update_data:
                db_activity = self.repository.update(
                    db_obj=db_activity,
                    obj_in=update_data
                )

            # Update custom field values if provided
            if custom_fields_data is not None:
                CustomFieldService.save_custom_field_values(
                    db=self.db,
                    entity_id=str(db_activity.id),
                    entity_type=EntityType.ACTIVITY,
                    field_values=custom_fields_data
                )

            # Commit the transaction
            self.db.commit()
            self.db.refresh(db_activity)

            return self._build_activity_response(db_activity)

        except Exception as e:
            self.db.rollback()
            raise e

    def delete_activity(self, activity_id: UUID) -> bool:
        """
        Delete an activity.

        Args:
            activity_id: UUID of the activity to delete

        Returns:
            True if deletion was successful, False if activity not found

        Raises:
            Exception: If deletion fails
        """
        try:
            result = self.repository.delete(id=activity_id)

            if result:
                self.db.commit()

            return result

        except Exception as e:
            self.db.rollback()
            raise e

    def get_user_activities(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        skip: int = 0
    ) -> List[ActivityResponse]:
        """
        Retrieve activities for a specific user.

        Args:
            user_id: UUID of the user
            limit: Maximum number of records to return
            skip: Number of records to skip

        Returns:
            List of activities for the user
        """
        activities = self.repository.get_by_user(
            user_id,
            skip=skip,
            limit=limit,
            load_relations=True
        )

        return [
            self._build_activity_response(activity)
            for activity in activities
        ]

    def get_contact_activities(
        self,
        contact_id: UUID,
        *,
        limit: int = 50,
        skip: int = 0
    ) -> List[ActivityResponse]:
        """
        Retrieve activities for a specific contact.

        Args:
            contact_id: UUID of the contact
            limit: Maximum number of records to return
            skip: Number of records to skip

        Returns:
            List of activities for the contact
        """
        activities = self.repository.get_by_contact(
            contact_id,
            skip=skip,
            limit=limit
        )

        return [
            self._build_activity_response(activity)
            for activity in activities
        ]

    def get_deal_activities(
        self,
        deal_id: UUID,
        *,
        limit: int = 50,
        skip: int = 0
    ) -> List[ActivityResponse]:
        """
        Retrieve activities for a specific deal.

        Args:
            deal_id: UUID of the deal
            limit: Maximum number of records to return
            skip: Number of records to skip

        Returns:
            List of activities for the deal
        """
        activities = self.repository.get_by_deal(
            deal_id,
            skip=skip,
            limit=limit
        )

        return [
            self._build_activity_response(activity)
            for activity in activities
        ]

    def _build_activity_response(
        self,
        activity: Activity,
        include_custom_fields: bool = True
    ) -> ActivityResponse:
        """
        Build an activity response with custom fields.

        Args:
            activity: The activity database object
            include_custom_fields: Whether to include custom fields

        Returns:
            Activity response schema
        """
        # Get custom fields
        custom_fields_dict = None
        if include_custom_fields:
            custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
                db=self.db,
                entity_id=str(activity.id),
                entity_type=EntityType.ACTIVITY
            )

        return ActivityResponse(
            id=activity.id,
            type=activity.type,
            subject=activity.subject,
            description=activity.description,
            duration_minutes=activity.duration_minutes,
            outcome=activity.outcome,
            contact_id=activity.contact_id,
            deal_id=activity.deal_id,
            user_id=activity.user_id,
            created_at=activity.created_at,
            updated_at=activity.updated_at,
            custom_fields=custom_fields_dict
        )

    def _build_activity_response_with_relations(
        self,
        activity: Activity,
        include_custom_fields: bool = True
    ) -> ActivityWithRelations:
        """
        Build an activity response with relations and custom fields.

        Args:
            activity: The activity database object with loaded relations
            include_custom_fields: Whether to include custom fields

        Returns:
            Activity response with relations
        """
        # Get custom fields
        custom_fields_dict = None
        if include_custom_fields:
            custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
                db=self.db,
                entity_id=str(activity.id),
                entity_type=EntityType.ACTIVITY
            )

        return ActivityWithRelations(
            id=activity.id,
            type=activity.type,
            subject=activity.subject,
            description=activity.description,
            duration_minutes=activity.duration_minutes,
            outcome=activity.outcome,
            contact_id=activity.contact_id,
            deal_id=activity.deal_id,
            user_id=activity.user_id,
            created_at=activity.created_at,
            updated_at=activity.updated_at,
            custom_fields=custom_fields_dict,
            contact=activity.contact,
            deal=activity.deal,
            user=activity.user
        )
