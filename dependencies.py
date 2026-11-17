
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from auth import decode_access_token
from users import User
from models import Company


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (ValueError, TypeError, KeyError):
        raise unauthorized

    user = db.query(User).filter(
        User.id == user_id,
        User.is_active.is_(True),
    ).first()

    if not user:
        raise unauthorized

    # Confirm token scope still matches the database account.
    if payload.get("role") != user.role:
        raise unauthorized

    if payload.get("company_id") != user.company_id:
        raise unauthorized

    if payload.get("workflow_id") != user.workflow_id:
        raise unauthorized

    # Platform Super Admin is not attached to a company.
    if user.role == "PLATFORM_SUPER_ADMIN":
        if user.company_id is not None:
            raise unauthorized
    else:
        if user.company_id is None:
            raise unauthorized

        company = db.query(Company).filter(
            Company.id == user.company_id,
            Company.is_active.is_(True),
            Company.is_approved.is_(True),
        ).first()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Company is inactive or not approved",
            )

    return user


def require_roles(*allowed_roles):
    def role_checker(
        current_user: User = Depends(get_current_user),
    ):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission for this action",
            )

        return current_user

    return role_checker
