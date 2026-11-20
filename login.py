
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from users import User
from models import Company
from auth import verify_password, create_access_token, hash_password


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1)
    company_code: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in_minutes: int = 30


class BootstrapAdminRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=12)
    bootstrap_key: str = Field(..., min_length=32)


class ResetSuperAdminPasswordRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    new_password: str = Field(..., min_length=12)
    recovery_key: str = Field(..., min_length=32)


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    username = request.username.strip()

    company_code = (
        request.company_code.strip().upper()
        if request.company_code
        else None
    )

    if not company_code:
        user = db.query(User).filter(
            User.username == username,
            func.lower(User.role) == "platform_super_admin",
            User.company_id.is_(None),
            User.is_active.is_(True),
        ).first()

    else:
        company = db.query(Company).filter(
            func.upper(Company.company_code) == company_code,
            Company.is_active.is_(True),
            Company.is_approved.is_(True),
        ).first()

        if not company:
            raise HTTPException(
                status_code=401,
                detail="Invalid company code or login details",
            )

        user = db.query(User).filter(
            User.username == username,
            User.company_id == company.id,
            func.lower(User.role) != "platform_super_admin",
            User.is_active.is_(True),
        ).first()

    if not user or not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(
        subject=str(user.id),
        role=user.role,
        company_id=user.company_id,
        workflow_id=user.workflow_id,
    )

    return LoginResponse(
        access_token=access_token,
        role=user.role,
    )


@router.post("/bootstrap-super-admin", status_code=201)
def bootstrap_super_admin(
    request: BootstrapAdminRequest,
    db: Session = Depends(get_db),
):
    configured_key = os.getenv("ADMIN_BOOTSTRAP_KEY")

    if not configured_key or len(configured_key) < 32:
        raise HTTPException(
            status_code=503,
            detail="Admin bootstrap is not configured",
        )

    if not secrets.compare_digest(
        request.bootstrap_key,
        configured_key,
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid bootstrap key",
        )

    existing_admin = db.query(User).filter(
        func.lower(User.role) == "platform_super_admin"
    ).first()

    if existing_admin:
        raise HTTPException(
            status_code=409,
            detail="Platform Super Admin already exists",
        )

    username = request.username.strip()

    existing_username = db.query(User).filter(
        User.username == username
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=409,
            detail="Username is already in use",
        )

    admin = User(
        username=username,
        email=None,
        password_hash=hash_password(request.password),
        role="platform_super_admin",
        company_id=None,
        workflow_id=None,
        is_active=True,
        must_change_password=True,
    )

    try:
        db.add(admin)
        db.commit()
        db.refresh(admin)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not create Platform Super Admin",
        )

    return {
        "status": "created",
        "message": "Platform Super Admin created successfully",
        "user_id": admin.id,
        "username": admin.username,
        "role": admin.role,
    }


@router.post("/reset-super-admin-password")
def reset_super_admin_password(
    request: ResetSuperAdminPasswordRequest,
    db: Session = Depends(get_db),
):
    configured_key = os.getenv("ADMIN_PASSWORD_RESET_KEY")

    if not configured_key or len(configured_key) < 32:
        raise HTTPException(
            status_code=503,
            detail="Password reset is not configured",
        )

    if not secrets.compare_digest(
        request.recovery_key,
        configured_key,
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid recovery key",
        )

    admin = db.query(User).filter(
        User.username == request.username.strip(),
        func.lower(User.role) == "platform_super_admin",
        User.company_id.is_(None),
        User.is_active.is_(True),
    ).first()

    if not admin:
        raise HTTPException(
            status_code=404,
            detail="Super Admin not found",
        )

    try:
        admin.password_hash = hash_password(request.new_password)
        admin.must_change_password = True
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not reset Super Admin password",
        )

    return {
        "status": "success",
        "message": "Super Admin password reset successfully",
    }
