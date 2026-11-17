
import os
import sys

from database import SessionLocal, init_db
from users import User
from auth import hash_password


def create_superadmin():
    username = os.getenv("SUPERADMIN_USERNAME", "").strip()
    password = os.getenv("SUPERADMIN_PASSWORD", "")

    if not username or not password:
        print("ERROR: SUPERADMIN_USERNAME and SUPERADMIN_PASSWORD are required.")
        sys.exit(1)

    if len(password) < 12:
        print("ERROR: Password must contain at least 12 characters.")
        sys.exit(1)

    init_db()
    db = SessionLocal()

    try:
        existing_admin = db.query(User).filter(
            User.role == "PLATFORM_SUPER_ADMIN"
        ).first()

        if existing_admin:
            print("A Platform Super Admin already exists. No account created.")
            return

        existing_username = db.query(User).filter(
            User.username == username
        ).first()

        if existing_username:
            print("ERROR: This username is already in use.")
            sys.exit(1)

        admin = User(
            username=username,
            password_hash=hash_password(password),
            role="PLATFORM_SUPER_ADMIN",
            company_id=None,
            workflow_id=None,
            is_active=True,
            must_change_password=True,
        )

        db.add(admin)
        db.commit()

        print("Platform Super Admin created successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    create_superadmin()
