"""Make email and last_name optional in prospects table

This migration makes the email and last_name columns nullable in the prospects table,
since we only require first_name and at least one contact method (email or phone).
"""

from app.core.database import engine
from sqlalchemy import text
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def upgrade():
    """Make email and last_name nullable in prospects table"""
    with engine.connect() as conn:
        # Make email nullable
        conn.execute(text("""
            ALTER TABLE prospects
            ALTER COLUMN email DROP NOT NULL;
        """))

        # Make last_name nullable
        conn.execute(text("""
            ALTER TABLE prospects
            ALTER COLUMN last_name DROP NOT NULL;
        """))

        conn.commit()
        print("Successfully made email and last_name nullable in prospects table")


def downgrade():
    """Make email and last_name required again in prospects table"""
    with engine.connect() as conn:
        # Make email required (this will fail if there are NULL values)
        conn.execute(text("""
            ALTER TABLE prospects
            ALTER COLUMN email SET NOT NULL;
        """))

        # Make last_name required (this will fail if there are NULL values)
        conn.execute(text("""
            ALTER TABLE prospects
            ALTER COLUMN last_name SET NOT NULL;
        """))

        conn.commit()
        print("Successfully made email and last_name required in prospects table")


if __name__ == "__main__":
    print("Running migration: Make prospect fields optional")
    upgrade()
    print("Migration completed successfully!")
