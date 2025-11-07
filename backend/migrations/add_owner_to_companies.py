"""Add owner_id to companies table

This migration adds the owner_id foreign key column to the companies table
to track which user owns each company.
"""

from app.core.database import engine
from sqlalchemy import text
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def upgrade():
    """Add owner_id column to companies table"""
    with engine.connect() as conn:
        # Add the owner_id column (nullable at first)
        conn.execute(text("""
            ALTER TABLE companies 
            ADD COLUMN IF NOT EXISTS owner_id UUID;
        """))

        # Add foreign key constraint
        conn.execute(text("""
            ALTER TABLE companies
            ADD CONSTRAINT fk_companies_owner
            FOREIGN KEY (owner_id) REFERENCES user_profiles(id)
            ON DELETE SET NULL;
        """))

        conn.commit()
        print("✅ Successfully added owner_id column to companies table")


def downgrade():
    """Remove owner_id column from companies table"""
    with engine.connect() as conn:
        # Drop foreign key constraint first
        conn.execute(text("""
            ALTER TABLE companies
            DROP CONSTRAINT IF EXISTS fk_companies_owner;
        """))

        # Drop the column
        conn.execute(text("""
            ALTER TABLE companies 
            DROP COLUMN IF EXISTS owner_id;
        """))

        conn.commit()
        print("✅ Successfully removed owner_id column from companies table")


if __name__ == "__main__":
    print("Running migration: Add owner_id to companies")
    upgrade()
    print("Migration completed successfully!")
