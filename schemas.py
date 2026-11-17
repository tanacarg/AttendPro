
from datetime import datetime, date
from typing import Optional, Literal

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    model_validator,
)


# -------------------------
# Company schemas
# -------------------------

class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    logo_url: Optional[str] = Field(default=None, max_length=500)


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company_code: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool
    is_approved: bool


# -------------------------
# Office location schemas
# -------------------------

class OfficeLocationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    address: Optional[str] = Field(default=None, max_length=300)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class OfficeLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    address: Optional[str] = None
    latitude: float
    longitude: float
    is_active: bool
    created_at: datetime


# -------------------------
# Workflow schemas
# -------------------------

class WorkflowCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    is_active: bool


# -------------------------
# Project schemas
# -------------------------

class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    description: Optional[str] = None
    is_active: bool


class ProjectLocationCreate(BaseModel):
    label: str = Field(min_length=1, max_length=150)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ProjectLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    label: str
    latitude: float
    longitude: float


# -------------------------
# Worker schemas
# -------------------------

class WorkerCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    phone: Optional[str] = Field(default=None, min_length=7, max_length=30)
    employee_id: str = Field(min_length=1, max_length=80)
    workflow_id: int
    photo_url: Optional[str] = Field(default=None, max_length=500)


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attendpro_id: str
    company_id: int
    workflow_id: int
    employee_id: str
    full_name: str
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    is_approved: bool
    is_active: bool
    created_at: datetime


# -------------------------
# Attendance schemas
# -------------------------

class AttendanceCreate(BaseModel):
    attendance_type: Literal["office", "site"]

    # Required for site attendance.
    # Office branch is selected automatically using GPS distance.
    project_id: Optional[int] = None

    session: Literal["morning", "afternoon"]

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def validate_attendance_type(self):
        if self.attendance_type == "site" and self.project_id is None:
            raise ValueError(
                "Project ID is required for site attendance"
            )

        if self.attendance_type == "office" and self.project_id is not None:
            raise ValueError(
                "Project ID must not be provided for office attendance"
            )

        return self


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    worker_id: int
    attendance_type: Literal["office", "site"]

    project_id: Optional[int] = None
    office_location_id: Optional[int] = None

    session: str
    attendance_date: date
    recorded_at: datetime

    latitude: float
    longitude: float

    distance_meters: Optional[float] = None
    gps_alert: bool
    biometric_verified: bool
    status: str
    notes: Optional[str] = None
