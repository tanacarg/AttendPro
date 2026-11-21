from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Worker, Company, Workflow
from users import User
from dependencies import require_roles
from worker_registration import (
    approve_worker_registration,
    reject_worker_registration,
)

router = APIRouter(prefix="/employees", tags=["Employees"])


def _check_workflow_admin(db: Session, admin: User):
    if admin.workflow_id is None or admin.company_id is None:
        raise HTTPException(
            status_code=403,
            detail="Workflow Admin account is not assigned to a workflow",
        )

    workflow = db.query(Workflow).filter(
        Workflow.id == admin.workflow_id,
        Workflow.company_id == admin.company_id,
        Workflow.is_active.is_(True),
    ).first()

    if workflow is None:
        raise HTTPException(
            status_code=403,
            detail="Your workflow is inactive or unavailable",
        )

    company = db.query(Company).filter(
        Company.id == admin.company_id,
        Company.is_active.is_(True),
        Company.is_approved.is_(True),
    ).first()

    if company is None:
        raise HTTPException(
            status_code=403,
            detail="Your company is inactive or not approved",
        )


@router.get("/pending")
def get_pending_employees(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("WORKFLOW_ADMIN")),
):
    _check_workflow_admin(db, admin)

    workers = (
        db.query(Worker)
        .filter(
            Worker.company_id == admin.company_id,
            Worker.workflow_id == admin.workflow_id,
            Worker.is_approved.is_(False),
            Worker.is_active.is_(True),
        )
        .order_by(Worker.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "count": len(workers),
        "employees": [
            {
                "worker_id": worker.id,
                "attendpro_id": worker.attendpro_id,
                "employee_id": worker.employee_id,
                "full_name": worker.full_name,
                "phone": worker.phone,
                "workflow_id": worker.workflow_id,
                "created_at": worker.created_at,
            }
            for worker in workers
        ],
    }


@router.post("/{worker_id}/approve")
def approve_employee(
    worker_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("WORKFLOW_ADMIN")),
):
    _check_workflow_admin(db, admin)

    try:
        return approve_worker_registration(
            db,
            worker_id=worker_id,
            admin_user=admin,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{worker_id}/reject")
def reject_employee(
    worker_id: int,
    rejection_reason: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("WORKFLOW_ADMIN")),
):
    _check_workflow_admin(db, admin)

    try:
        return reject_worker_registration(
            db,
            worker_id=worker_id,
            admin_user=admin,
            rejection_reason=rejection_reason,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
