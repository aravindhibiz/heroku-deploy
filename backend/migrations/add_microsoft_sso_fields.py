"""Add Microsoft SSO fields to user_profiles table

This migration adds support for Microsoft SSO authentication by adding:
- microsoft_id: Unique Microsoft user identifier (oid claim)
- auth_provider: Authentication provider ('local' or 'microsoft')
- Makes hashed_password optional for SSO users
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text


def upgrade():
    """Add Microsoft SSO fields to user_profiles table"""
    with engine.connect() as conn:
        # Add microsoft_id column with unique constraint
        conn.execute(text("""
            ALTER TABLE user_profiles
            ADD COLUMN IF NOT EXISTS microsoft_id VARCHAR UNIQUE;
        """))

        # Create index on microsoft_id for faster lookups
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_profiles_microsoft_id
            ON user_profiles(microsoft_id);
        """))

        # Add auth_provider column with default value 'local'
        conn.execute(text("""
            ALTER TABLE user_profiles
            ADD COLUMN IF NOT EXISTS auth_provider VARCHAR NOT NULL DEFAULT 'local';
        """))

        # Make hashed_password nullable for SSO users
        conn.execute(text("""
            ALTER TABLE user_profiles
            ALTER COLUMN hashed_password DROP NOT NULL;
        """))

        conn.commit()
        print("Successfully added Microsoft SSO fields to user_profiles table")


def downgrade():
    """Remove Microsoft SSO fields from user_profiles table"""
    with engine.connect() as conn:
        # Drop the index first
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_user_profiles_microsoft_id;
        """))

        # Drop microsoft_id column
        conn.execute(text("""
            ALTER TABLE user_profiles
            DROP COLUMN IF EXISTS microsoft_id;
        """))

        # Drop auth_provider column
        conn.execute(text("""
            ALTER TABLE user_profiles
            DROP COLUMN IF EXISTS auth_provider;
        """))

        # Make hashed_password NOT NULL again
        # Note: This will fail if there are SSO users without passwords
        conn.execute(text("""
            ALTER TABLE user_profiles
            ALTER COLUMN hashed_password SET NOT NULL;
        """))

        conn.commit()
        print("Successfully removed Microsoft SSO fields from user_profiles table")


if __name__ == "__main__":
    print("Running migration: Add Microsoft SSO fields to user_profiles")
    upgrade()
    print("Migration completed successfully!")
