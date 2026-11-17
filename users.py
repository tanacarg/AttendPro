from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)

from database import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "username",
            name="uq_user_company_username",
        ),
        Index("ix_users_role", "role"),
        Index("ix_users_company_workflow", "company_id", "workflow_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)

    password_hash = Column(String(255), nullable=False)

    role = Column(String(50), nullable=False)

    # Platform Super Admin may have no company.
    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=True,
        index=True,
    )

    # Workflow Admin is assigned to a specific workflow.
    workflow_id = Column(
        Integer,
        ForeignKey("workflows.id"),
        nullable=True,
        index=True,
    )

    is_active = Column(Boolean, default=True, nullable=False)

    must_change_password = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    last_login = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
