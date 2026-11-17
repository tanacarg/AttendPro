from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Who performed the action?
    actor_id = Column(Integer, nullable=True, index=True)
    actor_role = Column(String(50), nullable=True)

    # Company isolation
    company_id = Column(Integer, nullable=True, index=True)

    # What happened?
    action = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True, index=True)

    # Additional explanation
    description = Column(Text, nullable=True)

    # When did it happen?
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


def write_audit_log(
    db,
    action: str,
    actor_id: Optional[int] = None,
    actor_role: Optional[str] = None,
    company_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    description: Optional[str] = None,
):
    log = AuditLog(
        actor_id=actor_id,
        actor_role=actor_role,
        company_id=company_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        description=description,
    )

    db.add(log)
    db.flush()

    return log
