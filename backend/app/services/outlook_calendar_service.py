"""
Outlook Calendar Service
Handles interaction with Microsoft Graph Calendar API for calendar event management
"""

import httpx
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from ..models.activity import Activity
from ..models.integration import Integration
from ..models.contact import Contact


class OutlookCalendarService:
    """Service for interacting with Microsoft Graph Calendar API"""

    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, db: Session):
        self.db = db

    async def get_calendar_events(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Fetch calendar events from Outlook for date range
        GET /me/calendar/events

        Args:
            access_token: Microsoft Graph API access token
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of calendar events
        """
        url = f"{self.GRAPH_API_BASE}/me/calendar/events"

        # Format dates to ISO 8601
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        params = {
            '$filter': f"start/dateTime ge '{start_str}' and end/dateTime le '{end_str}'",
            '$orderby': 'start/dateTime',
            '$top': 100
        }

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('value', [])

    async def create_calendar_event(
        self,
        access_token: str,
        event_data: Dict,
        create_teams_meeting: bool = False
    ) -> Dict:
        """
        Create event in Outlook calendar
        POST /me/calendar/events

        Args:
            access_token: Microsoft Graph API access token
            event_data: Event data with subject, start, end, location, attendees
            create_teams_meeting: Whether to create a Teams meeting link

        Returns:
            Created event data with ID
        """
        url = f"{self.GRAPH_API_BASE}/me/calendar/events"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Add Teams meeting if requested
        if create_teams_meeting:
            event_data['isOnlineMeeting'] = True
            event_data['onlineMeetingProvider'] = 'teamsForBusiness'

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=event_data)
            response.raise_for_status()
            return response.json()

    async def update_calendar_event(
        self,
        access_token: str,
        event_id: str,
        event_data: Dict
    ) -> Dict:
        """
        Update existing Outlook event
        PATCH /me/calendar/events/{event_id}

        Args:
            access_token: Microsoft Graph API access token
            event_id: Outlook event ID
            event_data: Updated event data

        Returns:
            Updated event data
        """
        url = f"{self.GRAPH_API_BASE}/me/calendar/events/{event_id}"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        async with httpx.AsyncClient() as client:
            response = await client.patch(url, headers=headers, json=event_data)
            response.raise_for_status()
            return response.json()

    async def delete_calendar_event(
        self,
        access_token: str,
        event_id: str
    ) -> bool:
        """
        Delete Outlook event
        DELETE /me/calendar/events/{event_id}

        Args:
            access_token: Microsoft Graph API access token
            event_id: Outlook event ID

        Returns:
            True if deleted successfully
        """
        url = f"{self.GRAPH_API_BASE}/me/calendar/events/{event_id}"

        headers = {
            'Authorization': f'Bearer {access_token}'
        }

        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()
            return True

    async def sync_outlook_to_crm(
        self,
        user_id: str,
        integration: Integration,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Sync Outlook events to CRM activities
        - Fetch events from Outlook
        - Match to existing CRM activities by outlook_event_id
        - Create new activities for new events
        - Update existing activities if changed

        Args:
            user_id: CRM user ID
            integration: Integration object with access token
            start_date: Start of sync range
            end_date: End of sync range

        Returns:
            Sync statistics
        """
        try:
            # Fetch events from Outlook
            events = await self.get_calendar_events(
                integration.access_token,
                start_date,
                end_date
            )

            created_count = 0
            updated_count = 0

            for event in events:
                outlook_event_id = event.get('id')

                # Check if activity already exists
                existing_activity = self.db.query(Activity).filter(
                    Activity.outlook_event_id == outlook_event_id
                ).first()

                if existing_activity:
                    # Update existing activity
                    self._update_activity_from_event(existing_activity, event)
                    updated_count += 1
                else:
                    # Create new activity
                    activity = self._create_activity_from_event(event, user_id)
                    self.db.add(activity)
                    created_count += 1

            self.db.commit()

            return {
                'success': True,
                'events_fetched': len(events),
                'created': created_count,
                'updated': updated_count
            }

        except Exception as e:
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    async def sync_crm_to_outlook(
        self,
        activity: Activity,
        integration: Integration,
        create_teams_meeting: bool = False
    ) -> Dict:
        """
        Sync a CRM activity to Outlook
        - Create or update Outlook event
        - Store outlook_event_id in activity
        - Update sync_status

        Args:
            activity: CRM Activity object
            integration: Integration object with access token
            create_teams_meeting: Whether to create Teams meeting

        Returns:
            Sync result with event details
        """
        try:
            event_data = self.map_activity_to_outlook_event(activity)

            if activity.outlook_event_id:
                # Update existing event
                result = await self.update_calendar_event(
                    integration.access_token,
                    activity.outlook_event_id,
                    event_data
                )
            else:
                # Create new event
                result = await self.create_calendar_event(
                    integration.access_token,
                    event_data,
                    create_teams_meeting
                )

                # Store event ID
                activity.outlook_event_id = result.get('id')

                # Store Teams link if created
                if create_teams_meeting and result.get('onlineMeeting'):
                    activity.meeting_link = result['onlineMeeting'].get('joinUrl')

            activity.sync_status = 'synced'
            activity.sync_source = 'crm'
            self.db.commit()

            return {
                'success': True,
                'event_id': result.get('id'),
                'meeting_link': result.get('onlineMeeting', {}).get('joinUrl')
            }

        except Exception as e:
            activity.sync_status = 'error'
            self.db.commit()
            return {
                'success': False,
                'error': str(e)
            }

    def map_outlook_event_to_activity(self, event: Dict, user_id: str) -> Dict:
        """
        Convert Outlook event format to CRM activity format

        Args:
            event: Outlook event data
            user_id: CRM user ID

        Returns:
            Activity data dict
        """
        # Parse start and end times
        start_time = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))

        # Extract attendee emails
        attendees = [
            attendee['emailAddress']['address']
            for attendee in event.get('attendees', [])
        ]

        # Extract location
        location = None
        if event.get('location'):
            location = event['location'].get('displayName')

        # Extract Teams meeting link
        meeting_link = None
        if event.get('onlineMeeting'):
            meeting_link = event['onlineMeeting'].get('joinUrl')

        return {
            'type': 'meeting',
            'subject': event.get('subject', 'Untitled Event'),
            'description': event.get('bodyPreview', ''),
            'scheduled_at': start_time,
            'end_time': end_time,
            'location': location,
            'meeting_link': meeting_link,
            'attendees': json.dumps(attendees) if attendees else None,
            'outlook_event_id': event.get('id'),
            'sync_source': 'outlook',
            'sync_status': 'synced',
            'user_id': user_id
        }

    def map_activity_to_outlook_event(self, activity: Activity) -> Dict:
        """
        Convert CRM activity format to Outlook event format

        Args:
            activity: CRM Activity object

        Returns:
            Outlook event data dict
        """
        # Format times for Outlook
        start_time = activity.scheduled_at.isoformat() if activity.scheduled_at else datetime.now(timezone.utc).isoformat()

        # Default end time to 1 hour after start if not specified
        if activity.end_time:
            end_time = activity.end_time.isoformat()
        else:
            end_dt = datetime.fromisoformat(start_time) + timedelta(hours=1)
            end_time = end_dt.isoformat()

        event_data = {
            'subject': activity.subject,
            'body': {
                'contentType': 'Text',
                'content': activity.description or ''
            },
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC'
            }
        }

        # Add location if specified
        if activity.location:
            event_data['location'] = {
                'displayName': activity.location
            }

        # Add attendees if specified
        if activity.attendees:
            try:
                attendee_emails = json.loads(activity.attendees)
                event_data['attendees'] = [
                    {
                        'emailAddress': {
                            'address': email
                        },
                        'type': 'required'
                    }
                    for email in attendee_emails
                ]
            except json.JSONDecodeError:
                pass

        return event_data

    def _create_activity_from_event(self, event: Dict, user_id: str) -> Activity:
        """Helper to create Activity object from Outlook event"""
        activity_data = self.map_outlook_event_to_activity(event, user_id)
        return Activity(**activity_data)

    def _update_activity_from_event(self, activity: Activity, event: Dict):
        """Helper to update Activity object from Outlook event"""
        activity_data = self.map_outlook_event_to_activity(event, str(activity.user_id))

        # Update fields
        for key, value in activity_data.items():
            if key != 'user_id' and hasattr(activity, key):
                setattr(activity, key, value)

        activity.sync_status = 'synced'

    async def match_event_to_contact(self, event: Dict, user_id: str) -> Optional[str]:
        """
        Try to match an Outlook event to a CRM contact by attendee email

        Args:
            event: Outlook event data
            user_id: CRM user ID

        Returns:
            Contact ID if match found, None otherwise
        """
        attendees = event.get('attendees', [])

        for attendee in attendees:
            email = attendee.get('emailAddress', {}).get('address')
            if not email:
                continue

            # Search for contact with this email
            contact = self.db.query(Contact).filter(
                Contact.email == email,
                Contact.owner_id == user_id
            ).first()

            if contact:
                return str(contact.id)

        return None
