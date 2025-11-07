#!/usr/bin/env python3
"""
Database initialization script
This script creates all the database tables needed for the CRM application.
"""

import sys
import os

# Add the backend directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from app.core.database import Base, engine
from app.models import user, contact, deal, company, activity

def init_db():
    """Create all database tables"""
    load_dotenv()
    
    print("Creating database tables...")
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        # Test database connection
        from app.core.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            print("✅ Database connection test successful!")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if init_db():
        print("Database initialization completed successfully!")
    else:
        print("Database initialization failed!")
        sys.exit(1)