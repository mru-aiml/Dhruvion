#!/usr/bin/env python
"""Seed script for demo user.

Creates the demo user account for demonstration purposes.
This script is idempotent - it can be run multiple times without creating duplicates.
"""

import os
from sqlalchemy.orm import Session

from app.core.database import engine, Base
from app.core.models import User
from app.core.security import hash_password

# Demo user credentials (matching the frontend login page hint)
DEMO_USER_EMAIL = "demo@dhruvion.io"
DEMO_USER_PASSWORD = "Mission2026!"
DEMO_USER_FULL_NAME = "Demo Operator"


def seed_demo_user(db: Session) -> bool:
    """Seed demo user idempotently. Returns True if created, False if already existed."""
    
    # Check if demo user already exists
    existing = db.query(User).filter(User.email == DEMO_USER_EMAIL).first()
    if existing:
        print(f"Demo user already exists: {existing.email} (ID: {existing.id})")
        return False
    
    # Create demo user with hashed password
    password_hash = hash_password(DEMO_USER_PASSWORD)
    demo_user = User(
        email=DEMO_USER_EMAIL,
        full_name=DEMO_USER_FULL_NAME,
        password_hash=password_hash,
        is_active=True,
    )
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)
    
    print(f"Created demo user: {demo_user.email} (ID: {demo_user.id})")
    return True


def main():
    """Main entry point for script execution."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    with Session(engine) as db:
        created = seed_demo_user(db)
        if created:
            print("Demo user created successfully")
        else:
            print("Demo user already existed, no changes made")


if __name__ == "__main__":
    main()