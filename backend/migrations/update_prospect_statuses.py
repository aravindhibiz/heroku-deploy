"""Update prospect statuses to remove contacted and qualified

This migration updates all prospects with 'contacted' or 'qualified' status
to 'new' status, since we've simplified the prospect workflow to only have
new, converted, and rejected statuses.
"""

from app.core.database import engine
from sqlalchemy import text
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def upgrade():
    """Update prospect statuses to remove contacted and qualified"""
    with engine.connect() as conn:
        # First, check what enum values currently exist
        print("Checking current enum values...")
        result = conn.execute(text("""
            SELECT enumlabel
            FROM pg_enum
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'prospectstatus')
            ORDER BY enumsortorder;
        """))
        current_values = [row[0] for row in result]
        print(f"Current enum values: {current_values}")

        # Add missing enum values if needed
        required_values = ['new', 'contacted', 'qualified', 'converted', 'rejected']
        for value in required_values:
            if value not in current_values:
                print(f"Adding enum value: {value}")
                try:
                    conn.execute(text(f"ALTER TYPE prospectstatus ADD VALUE '{value}';"))
                    conn.commit()
                except Exception as e:
                    print(f"Error adding {value}: {e}")
                    conn.rollback()

        # Now update all 'contacted' and 'qualified' prospects to 'new'
        print("Updating prospect statuses...")
        result = conn.execute(text("""
            UPDATE prospects
            SET status = 'new'
            WHERE status IN ('contacted', 'qualified');
        """))

        affected_rows = result.rowcount
        conn.commit()
        print(f"Successfully updated {affected_rows} prospects from 'contacted'/'qualified' to 'new' status")

        # Note: PostgreSQL doesn't support removing enum values easily
        # The old enum values will remain in the type but won't be used
        print("Note: Old enum values remain in database type but are no longer used by the application")


def downgrade():
    """No downgrade path - we can't restore the original status values"""
    print("⚠️ No downgrade available - original status values were lost")
    pass


if __name__ == "__main__":
    print("Running migration: Update prospect statuses")
    upgrade()
    print("Migration completed successfully!")
