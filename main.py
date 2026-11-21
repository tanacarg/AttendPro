
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import Worker
from dependencies import require_roles
from audit import write_audit_log


router = APIRouter(
    prefix="/employees",
    tags=["Employees"],
)


class EmployeeCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=80)
    full_name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    photo_url: str | None = Field(default=None, max_length=500)


class EmployeeUpdate(BaseModel):
    employee_id: str | None = Field(default=None, max_length=80)
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    photo_url: str | None = Field(default=None, max_length=500)


def generate_attendpro_id(db: Session) -> str:
    for _ in range(20):
        new_id = "ATD-" + secrets.token_hex(6).upper()

        exists = db.query(Worker).filter(
            Worker.attendpro_id == new_id
        ).first()

        if not exists:
            return new_id

    raise HTTPException(
        status_code=500,
        detail="Could not generate unique AttendPro ID",
    )


def get_workflow_employee(
    worker_id: int,
    admin,
    db: Session,
):
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.company_id == admin.company_id,
        Worker.workflow_id == admin.workflow_id,
    ).first()

    if not worker:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    return worker


@router.post("/", status_code=status.HTTP_201_CREATED)
def register_employee(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("workflow_admin")),
):
    if admin.workflow_id is None:
        raise HTTPException(
            status_code=403,
            detail="Workflow Admin has no assigned workflow",
        )

    duplicate = db.query(Worker).filter(
        Worker.company_id == admin.company_id,
        Worker.employee_id == data.employee_id,
    ).first()

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="Employee ID already exists in this company",
        )

    worker = Worker(
        attendpro_id=generate_attendpro_id(db),
        company_id=admin.company_id,
        workflow_id=admin.workflow_id,
        employee_id=data.employee_id,
        full_name=data.full_name,
        phone=data.phone,
        photo_url=data.photo_url,
    )

    db.add(worker)
    db.flush()

    write_audit_log(
        db,
        action="EMPLOYEE_REGISTERED",
        actor_id=admin.id,
        actor_role=admin.role,
        company_id=admin.company_id,
        target_type="Worker",
        target_id=worker.id,
        description="Employee registered by Workflow Admin",
    )

    db.commit()
    db.refresh(worker)

    return {
        "message": "Employee registered successfully",
        "employee": {
            "id": worker.id,
            "attendpro_id": worker.attendpro_id,
            "employee_id": worker.employee_id,
            "full_name": worker.full_name,
            "workflow_id": worker.workflow_id,
            "phone": worker.phone,
            "is_active": worker.is_active,
            "is_approved": worker.is_approved,
        },
    }


@router.get("/")
def list_employees(
    db: Session = Depends(get_db),
    admin=Depends(require_roles("workflow_admin")),
):
    if admin.workflow_id is None:
        raise HTTPException(
            status_code=403,
            detail="Workflow Admin has no assigned workflow",
        )

    workers = db.query(Worker).filter(
        Worker.company_id == admin.company_id,
        Worker.workflow_id == admin.workflow_id,
    ).order_by(Worker.id.desc()).all()

    return [
        {
            "id": worker.id,
            "attendpro_id": worker.attendpro_id,
            "employee_id": worker.employee_id,
            "full_name": worker.full_name,
            "workflow_id": worker.workflow_id,
            "phone": worker.phone,
            "is_active": worker.is_active,
            "is_approved": worker.is_approved,
        }
        for worker in workers
    ]


@router.get("/{worker_id}")
def get_employee(
    worker_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("workflow_admin")),
):
    worker = get_workflow_employee(worker_id, admin, db)

    return {
        "id": worker.id,
        "attendpro_id": worker.attendpro_id,
        "employee_id": worker.employee_id,
        "full_name": worker.full_name,
        "workflow_id": worker.workflow_id,
        "phone": worker.phone,
        "photo_url": worker.photo_url,
        "is_active": worker.is_active,
        "is_approved": worker.is_approved,
    }


@router.put("/{worker_id}")
def update_employee(
    worker_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("workflow_admin")),
):
    worker = get_workflow_employee(worker_id, admin, db)

    changes = data.dict(exclude_unset=True)

    for field, value in changes.items():
        if value is None and field in ("employee_id", "full_name"):
            raise HTTPException(
                status_code=400,
                detail=f"{field} cannot be empty",
            )

    if changes.get("employee_id"):
        duplicate = db.query(Worker).filter(
            Worker.company_id == admin.company_id,
            Worker.employee_id == changes["employee_id"],
            Worker.id != worker.id,
        ).first()

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Employee ID already exists in this company",
            )

    for field, value in changes.items():
        setattr(worker, field, value)

    write_audit_log(
        db,
        action="EMPLOYEE_UPDATED",
        actor_id=admin.id,
        actor_role=admin.role,
        company_id=admin.company_id,
        target_type="Worker",
        target_id=worker.id,
        description="Employee information updated",
    )

    db.commit()

    return {
        "message": "Employee updated successfully",
        "attendpro_id": worker.attendpro_id,
    }


@router.patch("/{worker_id}/deactivate")
def deactivate_employee(
    worker_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_roles("workflow_admin")),
):
    worker = get_workflow_employee(worker_id, admin, db)

    worker.is_active = False

    write_audit_log(
        db,
        action="EMPLOYEE_DEACTIVATED",
        actor_id=admin.id,
        actor_role=admin.role,
        company_id=admin.company_id,
        target_type="Worker",
        target_id=worker.id,
        description="Employee deactivated; records preserved",
    )

    db.commit()

    return {
        "message": "Employee deactivated successfully",
        "attendpro_id": worker.attendpro_id,
    }
