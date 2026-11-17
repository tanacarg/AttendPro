from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# -------------------------
# Company schemas
# -------------------------

class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    logo_url: Optional[str] = None


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company_code: str
    logo_url: Optional[str] = None
    is_active: bool
    is_approved: bool


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
    phone: str = Field(min_length=7, max_length=30)
    employee_id: str = Field(min_length=1, max_length=80)
    workflow_id: int
    photo_url: Optional[str] = None


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attendpro_id: str
    company_id: int
    workflow_id: int
    employee_id: str
    full_name: str
    phone: str
    photo_url: Optional[str] = None
    is_approved: bool
    is_active: bool
    created_at: datetime


# -------------------------
# Attendance schemas
# -------------------------

class AttendanceCreate(BaseModel):
    project_id: int
    session: str = Field(pattern="^(morning|afternoon)$")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    worker_id: int
    project_id: int
    session: str
    recorded_at: datetime
    latitude: float
    longitude: float
    distance_meters: Optional[float] = None
    gps_alert: bool
    biometric_verified: bool
    status: str
    notes: Optional[str] = None
