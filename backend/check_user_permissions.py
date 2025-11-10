#!/usr/bin/env python3
"""
Check user permissions
"""

from app.models.role import Role
from app.models.user import UserProfile
from app.core.database import SessionLocal
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_user():
    db = SessionLocal()
    try:
        # Find user by email
        user = db.query(UserProfile).filter(
            UserProfile.email == 'Aravindprime23@gmail.com'
        ).first()

        if not user:
            print("User not found!")
            return

        print(f"User: {user.email}")
        print(f"First Name: {user.first_name}")
        print(f"Last Name: {user.last_name}")
        print(f"Role: {user.role}")
        print(f"Active: {user.is_active}")

        # Get role object
        role = db.query(Role).filter(Role.name == user.role).first()

        if role:
            print(f"\nRole Display Name: {role.display_name}")
            print(f"Role Description: {role.description}")
            print(f"Number of permissions: {len(role.permissions)}")

            if role.permissions:
                print("\nPermissions:")
                for perm in sorted(role.permissions, key=lambda p: p.name):
                    print(f"  - {perm.name}")
            else:
                print("\n⚠️  WARNING: Role has NO permissions assigned!")
        else:
            print(f"\n⚠️  WARNING: Role '{user.role}' not found in database!")
            print("\nAvailable roles:")
            roles = db.query(Role).all()
            for r in roles:
                print(f"  - {r.name} ({r.display_name})")

    finally:
        db.close()


if __name__ == "__main__":
    check_user()
