
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from users import User
from models import Company
from auth import verify_password, create_access_token


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

    # Platform Super Admin login
    if not company_code:
        user = db.query(User).filter(
            User.username == username,
            func.lower(User.role) == "platform_super_admin",
            User.company_id.is_(None),
            User.is_active.is_(True),
        ).first()

    else:
        # Company login
        company = db.query(Company).filter(
            func.upper(Company.company_code) == company_code,
            Company.is_active.is_(True),
            Company.is_approved.is_(True),
        ).first()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Update last login time
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
        token_type="bearer",
        role=user.role,
        expires_in_minutes=30,
    )
