
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import Company
from users import User
from auth import verify_password, create_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    company_code: str | None = Field(default=None, max_length=30)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int = 30
    role: str


@router.post("/login", response_model=LoginResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    query = db.query(User).filter(
        User.username == data.username,
        User.is_active.is_(True),
    )

    # Super Admin is a platform-level account.
    if data.company_code is None:
        query = query.filter(
            User.role == "PLATFORM_SUPER_ADMIN",
            User.company_id.is_(None),
        )
    else:
        company = db.query(Company).filter(
            Company.company_code == data.company_code,
            Company.is_active.is_(True),
            Company.is_approved.is_(True),
        ).first()

        if not company:
            raise HTTPException(
                status_code=401,
                detail="Invalid login details",
            )

        query = query.filter(
            User.company_id == company.id,
            User.role != "PLATFORM_SUPER_ADMIN",
        )

    user = query.first()

    if not user or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid login details",
        )

    token = create_access_token(
        subject=str(user.id),
        role=user.role,
        company_id=user.company_id,
        workflow_id=user.workflow_id,
    )

    return LoginResponse(
        access_token=token,
        role=user.role,
    )
