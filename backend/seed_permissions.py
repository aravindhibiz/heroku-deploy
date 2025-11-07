#!/usr/bin/env python3
"""
Standalone script to seed permissions and roles into the database
Run this script from the backend directory: python seed_permissions.py
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.seeds.permissions_seed import run_seed

if __name__ == "__main__":
    print("=" * 60)
    print("Permission and Role Seeder")
    print("=" * 60)
    print()

    run_seed()

    print()
    print("=" * 60)
    print("Seeding completed!")
    print("=" * 60)
