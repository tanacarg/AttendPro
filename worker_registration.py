"""
AttendPro worker registration service.

Responsibilities:
- Validate a company and one of its active workflows.
- Create a pending worker registration.
- Notify the matching Workflow Admin(s) through IDs returned to the API layer.
- Allow only the assigned Workflow Admin to approve or reject the request.
- Record registration decisions in the audit log.

Important:
- This module does not send Telegram messages itself.
- The API/Bot layer must obtain telegram_user_id from the authenticated
  Telegram update, never from an untrusted form field.
- Attendance must require BOTH Worker.is_approved and Worker.is_active.
"""

from __future__ import annotations

import secrets
from typing import Any, Optional

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Company, Workflow, Worker
from users import User
from audit import write_audit_log


# ---------------------------------------------------------------------------
# Amharic messages
# ---------------------------------------------------------------------------

COMPANY_NOT_FOUND_MESSAGE = (
    "የገቡት የድርጅት ስም ወይም ኮድ አልተገኘም። "
    "እባክዎ ትክክለኛውን የድርጅት ስም ወይም ኮድ ያስገቡ።"
)

COMPANY_NOT_ACTIVE_MESSAGE = (
    "ይህ ድርጅት ገና አልጸደቀም ወይም ንቁ አይደለም።"
)

WORKFLOW_NOT_FOUND_MESSAGE = (
    "ውድ ደንበኛችን፣ ያስገቡት የሥራ ሂደት ስም "
    "በድርጅቱ ውስጥ አልተገኘም። "
    "እባክዎ የሥራ ሂደት ስሙን ያስተካክሉና እንደገና ይምረጡ።"
)

PENDING_MESSAGE = (
    "የምዝገባ ጥያቄዎ ተቀብሏል። "
    "የሥራ ሂደት አድሚኑ እስኪያጸድቅዎት ድረስ "
    "የAttendance ፊርማ መስጠት አይችሉም።"
)

APPROVED_MESSAGE = (
    "ውድ ደንበኛችን፣ ምዝገባዎን አጠናቀዋል። "
    "አሁን የAttendance ፊርማ መስጠት ይችላሉ።"
)

REJECTED_MESSAGE = (
    "የምዝገባ ጥያቄዎ አልተቀበለም። "
    "የተሰጠው ምክንያት፦ "
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _role_value(user: Any) -> str:
    role = getattr(user, "role", "")
    role = getattr(role, "value", role)
    return str(role).strip().upper()


def _actor_role(user: Any) -> str:
    return _role_value(user)


def _new_attendpro_id() -> str:
    # High-entropy ID; the database unique constraint remains the final guard.
    return f"AP-{secrets.token_hex(6).upper()}"


def _find_company(db: Session, company_name_or_code: str) -> Optional[Company]:
    value = company_name_or_code.strip()
    if not value:
        return None

    return (
        db.query(Company)
        .filter(
            or_(
                Company.company_code == value,
                func.lower(Company.name) == value.lower(),
            )
        )
        .first()
    )


def _find_workflow(
    db: Session,
    company_id: int,
    workflow_name: str,
) -> Optional[Workflow]:
    value = workflow_name.strip()
    if not value:
        return None

    return (
        db.query(Workflow)
        .filter(
            Workflow.company_id == company_id,
            func.lower(Workflow.name) == value.lower(),
            Workflow.is_active.is_(True),
        )
        .first()
    )


def _get_worker_by_telegram_id(
    db: Session,
    telegram_user_id: str,
) -> Optional[Worker]:
    return (
        db.query(Worker)
        .filter(Worker.telegram_user_id == telegram_user_id)
        .first()
    )


def _require_workflow_admin(
    db: Session,
    admin_user: User,
    worker: Worker,
) -> None:
    if _role_value(admin_user) != "WORKFLOW_ADMIN":
        raise PermissionError("ይህን የምዝገባ ጥያቄ ለማስተናገድ ፈቃድ የለዎትም።")

    if getattr(admin_user, "company_id", None) != worker.company_id:
        raise PermissionError("ይህ ሰራተኛ የእርስዎ ድርጅት አባል አይደለም።")

    if getattr(admin_user, "workflow_id", None) != worker.workflow_id:
        raise PermissionError("ይህ ሰራተኛ በእርስዎ የሥራ ሂደት ስር አይደለም።")

    if hasattr(admin_user, "is_active") and not admin_user.is_active:
        raise PermissionError("የአድሚኑ መለያ ንቁ አይደለም።")

    company = db.query(Company).filter(Company.id == worker.company_id).first()
    workflow = db.query(Workflow).filter(Workflow.id == worker.workflow_id).first()

    if company is None or not company.is_approved or not company.is_active:
        raise PermissionError("የሰራተኛው ድርጅት ንቁና የጸደቀ አይደለም።")

    if workflow is None or not workflow.is_active or workflow.company_id != company.id:
        raise PermissionError("የሰራተኛው የሥራ ሂደት ንቁ አይደለም።")


def _is_pending(worker: Worker) -> bool:
    # Current Worker model has no separate registration_status field.
    # Pending = not approved but still active.
    return worker.is_approved is False and worker.is_active is True


def _audit(
    db: Session,
    *,
    action: str,
    actor: Optional[User],
    worker: Worker,
    description: str,
) -> None:
    write_audit_log(
        db,
        action=action,
        actor_id=getattr(actor, "id", None),
        actor_role=_actor_role(actor) if actor is not None else "SYSTEM",
        company_id=worker.company_id,
        target_type="Worker",
        target_id=worker.id,
        description=description,
    )


# ---------------------------------------------------------------------------
# Registration request
# ---------------------------------------------------------------------------

def register_worker(
    db: Session,
    *,
    company_name_or_code: str,
    workflow_name: str,
    employee_id: str,
    full_name: str,
    phone: str,
    telegram_user_id: str,
    photo_url: Optional[str] = None,
) -> dict[str, Any]:
    """
    Create a pending worker registration.

    telegram_user_id MUST be obtained from the verified Telegram update
    (effective_user.id), not trusted from user-submitted form data.
    """

    required_values = {
        "የድርጅት ስም/ኮድ": company_name_or_code,
        "የሥራ ሂደት ስም": workflow_name,
        "የሰራተኛ መለያ ቁጥር": employee_id,
        "ሙሉ ስም": full_name,
        "ስልክ ቁጥር": phone,
        "የTelegram መለያ": telegram_user_id,
    }
    for label, value in required_values.items():
        if value is None or not str(value).strip():
            raise ValueError(f"{label} ያስፈልጋል።")

    company_name_or_code = company_name_or_code.strip()
    workflow_name = workflow_name.strip()
    employee_id = employee_id.strip()
    full_name = full_name.strip()
    phone = phone.strip()
    telegram_user_id = str(telegram_user_id).strip()

    if len(full_name) < 2 or len(full_name) > 150:
        raise ValueError("ሙሉ ስም ከ2 እስከ 150 ቁምፊ መሆን አለበት።")

    if len(phone) < 7 or len(phone) > 30:
        raise ValueError("የስልክ ቁጥሩ ከ7 እስከ 30 ቁምፊ መሆን አለበት።")

    if len(employee_id) > 80:
        raise ValueError("የሰራተኛ መለያ ቁጥሩ ከ80 ቁምፊ መብለጥ የለበትም።")

    company = _find_company(db, company_name_or_code)
    if company is None:
        raise ValueError(COMPANY_NOT_FOUND_MESSAGE)

    if not company.is_approved or not company.is_active:
        raise ValueError(COMPANY_NOT_ACTIVE_MESSAGE)

    workflow = _find_workflow(db, company.id, workflow_name)
    if workflow is None:
        raise ValueError(WORKFLOW_NOT_FOUND_MESSAGE)

    if _get_worker_by_telegram_id(db, telegram_user_id) is not None:
        raise ValueError("ይህ የTelegram መለያ አስቀድሞ ተመዝግቧል።")

    workflow_admin_ids = [
        row.id
        for row in (
            db.query(User.id)
            .filter(
                User.company_id == company.id,
                User.workflow_id == workflow.id,
                User.role.in_(["WORKFLOW_ADMIN", "workflow_admin"]),
            )
            .all()
        )
    ]
    if not workflow_admin_ids:
        raise ValueError(
            "ለዚህ የሥራ ሂደት የተመደበ Workflow Admin የለም። "
            "እባክዎ የድርጅት አስተዳዳሪውን ያነጋግሩ።"
        )

    existing_employee = (
        db.query(Worker)
        .filter(
            Worker.company_id == company.id,
            Worker.employee_id == employee_id,
        )
        .first()
    )
    if existing_employee is not None:
        raise ValueError("ይህ የሰራተኛ መለያ ቁጥር በድርጅቱ ውስጥ አስቀድሞ ተጠቅሟል።")

    worker = Worker(
        attendpro_id=_new_attendpro_id(),
        company_id=company.id,
        workflow_id=workflow.id,
        employee_id=employee_id,
        full_name=full_name,
        phone=phone,
        telegram_user_id=telegram_user_id,
        photo_url=photo_url.strip() if photo_url and photo_url.strip() else None,
        is_approved=False,
        is_active=True,
    )

    try:
        db.add(worker)
        db.flush()

        _audit(
            db,
            action="WORKER_REGISTRATION_SUBMITTED",
            actor=None,
            worker=worker,
            description=(
                f"Worker registration submitted for employee_id={employee_id}; "
                f"workflow_id={workflow.id}. Awaiting Workflow Admin approval."
            ),
        )

        db.commit()
        db.refresh(worker)

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "የምዝገባ መረጃው ከነባር መረጃ ጋር ተደጋግሟል። "
            "የሰራተኛ መለያና Telegram መለያውን ያረጋግጡ።"
        ) from exc
    except Exception:
        db.rollback()
        raise

    # The API/Bot layer uses these IDs to send the pending notification.
    return {
        "success": True,
        "status": "pending",
        "message": PENDING_MESSAGE,
        "worker_id": worker.id,
        "attendpro_id": worker.attendpro_id,
        "company_id": company.id,
        "workflow_id": workflow.id,
        "workflow_name": workflow.name,
        "workflow_admin_ids": workflow_admin_ids,
        "attendance_allowed": False,
    }


# ---------------------------------------------------------------------------
# Approve registration
# ---------------------------------------------------------------------------

def approve_worker_registration(
    db: Session,
    *,
    worker_id: int,
    admin_user: User,
) -> dict[str, Any]:
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if worker is None:
        raise ValueError("ሰራተኛው አልተገኘም።")

    _require_workflow_admin(db, admin_user, worker)

    if not _is_pending(worker):
        raise ValueError("ይህ የምዝገባ ጥያቄ Pending ሁኔታ ላይ አይደለም።")

    worker.is_approved = True
    worker.is_active = True

    try:
        _audit(
            db,
            action="WORKER_REGISTRATION_APPROVED",
            actor=admin_user,
            worker=worker,
            description=f"Worker registration approved: attendpro_id={worker.attendpro_id}.",
        )
        db.commit()
        db.refresh(worker)
    except Exception:
        db.rollback()
        raise

    return {
        "success": True,
        "status": "approved",
        "message": APPROVED_MESSAGE,
        "worker_id": worker.id,
        "attendpro_id": worker.attendpro_id,
        "attendance_allowed": True,
    }


# ---------------------------------------------------------------------------
# Reject registration
# ---------------------------------------------------------------------------

def reject_worker_registration(
    db: Session,
    *,
    worker_id: int,
    admin_user: User,
    rejection_reason: str,
) -> dict[str, Any]:
    reason = (rejection_reason or "").strip()
    if not reason:
        raise ValueError("የእምቢታ ምክንያት ያስፈልጋል።")
    if len(reason) > 1000:
        raise ValueError("የእምቢታ ምክንያቱ ከ1000 ቁምፊ መብለጥ የለበትም።")

    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if worker is None:
        raise ValueError("ሰራተኛው አልተገኘም။")

    _require_workflow_admin(db, admin_user, worker)

    if not _is_pending(worker):
        raise ValueError("ይህ የምዝገባ ጥያቄ Pending ሁኔታ ላይ አይደለም።")

    # Current Worker schema has no registration_status/rejection_reason
    # columns. is_active=False makes the rejected worker ineligible for
    # attendance; the full reason is retained in the audit log.
    worker.is_approved = False
    worker.is_active = False

    try:
        _audit(
            db,
            action="WORKER_REGISTRATION_REJECTED",
            actor=admin_user,
            worker=worker,
            description=(
                f"Worker registration rejected: attendpro_id={worker.attendpro_id}. "
                f"Reason: {reason}"
            ),
        )
        db.commit()
        db.refresh(worker)
    except Exception:
        db.rollback()
        raise

    return {
        "success": True,
        "status": "rejected",
        "message": REJECTED_MESSAGE + reason,
        "rejection_reason": reason,
        "worker_id": worker.id,
        "attendpro_id": worker.attendpro_id,
        "attendance_allowed": False,
    }
