"""Add calendar fields to activities table

This migration adds support for calendar and Outlook integration by adding:
- scheduled_at: Start date/time for scheduled activities (meetings, calls)
- end_time: End date/time for scheduled activities
- outlook_event_id: Unique Microsoft Outlook event identifier for sync
- sync_source: Source of the activity ('crm', 'outlook', 'manual')
- sync_status: Sync status ('synced', 'pending', 'error', 'not_synced')
- location: Physical or virtual location for meetings
- meeting_link: URL for video meetings (Teams, Zoom, etc.)
- attendees: JSON array of attendee email addresses
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text


def upgrade():
    """Add calendar fields to activities table"""
    with engine.connect() as conn:
        # Add scheduled_at column for activity start time
        conn.execute(text("""
            ALTER TABLE activities
            ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP WITH TIME ZONE;
        """))

        # Add end_time column for activity end time
        conn.execute(text("""
            ALTER TABLE activities
            ADD COLUMN IF NOT EXISTS end_time TIMESTAMP WITH TIME ZONE;
        """))

        # Add outlook_event_id column with unique constraint for sync mapping
        conn.execute(text("""
            ALTER TABLE activities
            ADD COLUMN IF NOT EXISTS outlook_event_id VARCHAR(255) UNIQUE;
        """))

        # Add sync_source column to track origin of activity
        conn.execute(text("""
            ALTER TABLE activities
            ADD COLUMN IF NOT EXISTS sync_source VARCHAR(20) DEFAULT 'crm';
        """))

        # Add sync_status column to track sync state
        conn.execute(text("""
            ALTER TABLE activities
            ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'not_synced';
        """))

        # Add location column for meeting location
        conn.execute(text("""
            ALTER TABLE activities
            ADD COLUMN IF NOT EXISTS location VARCHAR(500);
        """))

        # Add meeting_link column for virtual meeting URLs
        conn.execute(text("""
            ALTER TABLE activities
            ADD COLUMN IF NOT EXISTS meeting_link TEXT;
        """))

        # Add attendees column for storing attendee emails as JSON
        conn.execute(text("""
            ALTER TABLE activities
            ADD COLUMN IF NOT EXISTS attendees TEXT;
        """))

        # Create index on scheduled_at for faster calendar queries
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_activities_scheduled_at
            ON activities(scheduled_at);
        """))

        # Create index on outlook_event_id for sync lookups
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_activities_outlook_event_id
            ON activities(outlook_event_id);
        """))

        # Create index on user_id + scheduled_at for user calendar queries
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_activities_user_scheduled
            ON activities(user_id, scheduled_at);
        """))

        conn.commit()
        print("Successfully added calendar fields to activities table")


def downgrade():
    """Remove calendar fields from activities table"""
    with engine.connect() as conn:
        # Drop indexes first
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_activities_scheduled_at;
        """))
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_activities_outlook_event_id;
        """))
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_activities_user_scheduled;
        """))

        # Drop columns
        conn.execute(text("""
            ALTER TABLE activities
            DROP COLUMN IF EXISTS scheduled_at;
        """))
        conn.execute(text("""
            ALTER TABLE activities
            DROP COLUMN IF EXISTS end_time;
        """))
        conn.execute(text("""
            ALTER TABLE activities
            DROP COLUMN IF EXISTS outlook_event_id;
        """))
        conn.execute(text("""
            ALTER TABLE activities
            DROP COLUMN IF EXISTS sync_source;
        """))
        conn.execute(text("""
            ALTER TABLE activities
            DROP COLUMN IF EXISTS sync_status;
        """))
        conn.execute(text("""
            ALTER TABLE activities
            DROP COLUMN IF EXISTS location;
        """))
        conn.execute(text("""
            ALTER TABLE activities
            DROP COLUMN IF EXISTS meeting_link;
        """))
        conn.execute(text("""
            ALTER TABLE activities
            DROP COLUMN IF EXISTS attendees;
        """))

        conn.commit()
        print("Successfully removed calendar fields from activities table")


if __name__ == "__main__":
    print("Running migration: Add calendar fields to activities")
    upgrade()
    print("Migration completed successfully!")
