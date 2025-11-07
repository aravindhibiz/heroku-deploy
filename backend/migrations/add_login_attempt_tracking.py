"""Add login attempt tracking fields to user_profiles table

This migration adds support for max login attempts and account lockout by adding:
- failed_login_attempts: Counter for failed login attempts
- account_locked_until: Timestamp until when account is locked
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text


def upgrade():
    """Add login attempt tracking fields to user_profiles table"""
    with engine.connect() as conn:
        # Add failed_login_attempts column with default value 0
        conn.execute(text("""
            ALTER TABLE user_profiles
            ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0;
        """))

        # Add account_locked_until column (nullable)
        conn.execute(text("""
            ALTER TABLE user_profiles
            ADD COLUMN IF NOT EXISTS account_locked_until TIMESTAMP WITH TIME ZONE;
        """))

        # Create index on account_locked_until for faster queries
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_profiles_account_locked_until
            ON user_profiles(account_locked_until);
        """))

        conn.commit()
        print("Successfully added login attempt tracking fields to user_profiles table")


def downgrade():
    """Remove login attempt tracking fields from user_profiles table"""
    with engine.connect() as conn:
        # Drop the index first
        conn.execute(text("""
            DROP INDEX IF EXISTS idx_user_profiles_account_locked_until;
        """))

        # Drop failed_login_attempts column
        conn.execute(text("""
            ALTER TABLE user_profiles
            DROP COLUMN IF EXISTS failed_login_attempts;
        """))

        # Drop account_locked_until column
        conn.execute(text("""
            ALTER TABLE user_profiles
            DROP COLUMN IF EXISTS account_locked_until;
        """))

        conn.commit()
        print("Successfully removed login attempt tracking fields from user_profiles table")


if __name__ == "__main__":
    print("Running migration: Add login attempt tracking to user_profiles")
    upgrade()
    print("Migration completed successfully!")
