
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Company
from schemas import CompanyCreate, CompanyResponse
from audit import write_audit_log


router = APIRouter(prefix="/companies", tags=["Companies"])


def generate_company_code(db: Session) -> str:
    alphabet = string.ascii_uppercase + string.digits

    for _ in range(20):
        code = "AP-" + "".join(
            secrets.choice(alphabet) for _ in range(8)
        )

        exists = db.query(Company).filter(
            Company.company_code == code
        ).first()

        if not exists:
            return code

    raise HTTPException(
        status_code=500,
        detail="Could not generate a unique company code",
    )


@router.post("/register", response_model=CompanyResponse, status_code=201)
def register_company(
    data: CompanyCreate,
    db: Session = Depends(get_db),
):
    company = Company(
        name=data.name,
        logo_url=data.logo_url,
        company_code=generate_company_code(db),
        is_active=False,
        is_approved=False,
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    return company


# Authentication and Super Admin role checks
# MUST be added before production use.
@router.get("/directory")
def company_directory(
    company_code: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Company)

    if company_code:
        query = query.filter(
            Company.company_code == company_code
        )

    companies = query.order_by(Company.id.desc()).all()

    return [
        {
            "id": item.id,
            "name": item.name,
            "company_code": item.company_code,
            "is_active": item.is_active,
            "is_approved": item.is_approved,
        }
        for item in companies
    ]


@router.post("/{company_id}/approve")
def approve_company(
    company_id: int,
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(
        Company.id == company_id
    ).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.is_approved = True
    company.is_active = True

    write_audit_log(
        db,
        action="COMPANY_APPROVED",
        company_id=company.id,
        target_type="Company",
        target_id=company.id,
        description="Company approved and activated",
    )

    db.commit()

    return {"message": "Company approved", "company_code": company.company_code}


@router.post("/{company_id}/deactivate")
def deactivate_company(
    company_id: int,
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(
        Company.id == company_id
    ).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.is_active = False

    write_audit_log(
        db,
        action="COMPANY_DEACTIVATED",
        company_id=company.id,
        target_type="Company",
        target_id=company.id,
        description="Company deactivated",
    )

    db.commit()

    return {"message": "Company deactivated"}
