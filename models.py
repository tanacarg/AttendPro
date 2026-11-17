
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    Float,
    ForeignKey,
    Text,
    UniqueConstraint,
    Index,
)

from sqlalchemy.orm import relationship

from database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)

    # Assigned by Platform Super Admin during approval.
    company_code = Column(
        String(30),
        unique=True,
        index=True,
        nullable=True,
    )

    logo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    workflows = relationship("Workflow", back_populates="company")
    projects = relationship("Project", back_populates="company")
    workers = relationship("Worker", back_populates="company")

    office_locations = relationship(
        "OfficeLocation",
        back_populates="company",
    )


class OfficeLocation(Base):
    """
    Each company can register multiple office branches.
    Office attendance is allowed within 100 meters
    of any active office location belonging to the company.
    """

    __tablename__ = "office_locations"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "name",
            name="uq_office_company_name",
        ),
        Index(
            "ix_office_company_active",
            "company_id",
            "is_active",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    name = Column(String(150), nullable=False)
    address = Column(String(300), nullable=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    company = relationship(
        "Company",
        back_populates="office_locations",
    )

    attendance_records = relationship(
        "Attendance",
        back_populates="office_location",
    )


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    name = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    company = relationship("Company", back_populates="workflows")
    workers = relationship("Worker", back_populates="workflow")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    company = relationship("Company", back_populates="projects")

    locations = relationship(
        "ProjectLocation",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    attendance_records = relationship(
        "Attendance",
        back_populates="project",
    )


class ProjectLocation(Base):
    """
    A project can have multiple GPS points:
    start, middle, end, and other work sections.
    """

    __tablename__ = "project_locations"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False,
        index=True,
    )

    label = Column(String(150), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    project = relationship("Project", back_populates="locations")


class Worker(Base):
    __tablename__ = "workers"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "employee_id",
            name="uq_worker_company_employee",
        ),
        UniqueConstraint(
            "attendpro_id",
            name="uq_worker_attendpro_id",
        ),
        Index(
            "ix_worker_company_workflow",
            "company_id",
            "workflow_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    attendpro_id = Column(
        String(40),
        unique=True,
        nullable=False,
        index=True,
    )

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    workflow_id = Column(
        Integer,
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )

    employee_id = Column(String(80), nullable=False)
    full_name = Column(String(200), nullable=False)
    phone = Column(String(30), nullable=True)

    telegram_user_id = Column(
        String(40),
        nullable=True,
        unique=True,
    )

    photo_url = Column(String(500), nullable=True)

    is_approved = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    company = relationship("Company", back_populates="workers")
    workflow = relationship("Workflow", back_populates="workers")

    attendance_records = relationship(
        "Attendance",
        back_populates="worker",
    )


class Attendance(Base):
    __tablename__ = "attendance"

    __table_args__ = (
        # One attendance record per worker, date and session.
        UniqueConstraint(
            "worker_id",
            "attendance_date",
            "session",
            name="uq_attendance_worker_date_session",
        ),
        Index(
            "ix_attendance_date_session",
            "attendance_date",
            "session",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    worker_id = Column(
        Integer,
        ForeignKey("workers.id"),
        nullable=False,
        index=True,
    )

    # "office" or "site"
    attendance_type = Column(
        String(20),
        nullable=False,
    )

    # Used for site attendance.
    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
    )

    # Used for office attendance.
    office_location_id = Column(
        Integer,
        ForeignKey("office_locations.id"),
        nullable=True,
        index=True,
    )

    session = Column(String(20), nullable=False)

    # Ethiopian local calendar date, calculated by backend.
    attendance_date = Column(Date, nullable=False)

    recorded_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    distance_meters = Column(Float, nullable=True)

    gps_alert = Column(Boolean, default=False, nullable=False)

    # This field must only be set after real biometric verification.
    biometric_verified = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    status = Column(
        String(30),
        default="present",
        nullable=False,
    )

    notes = Column(Text, nullable=True)

    worker = relationship(
        "Worker",
        back_populates="attendance_records",
    )

    project = relationship(
        "Project",
        back_populates="attendance_records",
    )

    office_location = relationship(
        "OfficeLocation",
        back_populates="attendance_records",
    )
