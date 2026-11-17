
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    Float, ForeignKey, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    company_code = Column(String(30), unique=True, index=True, nullable=False)
    logo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    is_approved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    workflows = relationship("Workflow", back_populates="company")
    projects = relationship("Project", back_populates="company")
    workers = relationship("Worker", back_populates="company")


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True)

    company = relationship("Company", back_populates="workflows")
    workers = relationship("Worker", back_populates="workflow")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    company = relationship("Company", back_populates="projects")
    locations = relationship(
        "ProjectLocation", back_populates="project",
        cascade="all, delete-orphan"
    )


class ProjectLocation(Base):
    __tablename__ = "project_locations"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    label = Column(String(150), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    project = relationship("Project", back_populates="locations")


class Worker(Base):
    __tablename__ = "workers"
    __table_args__ = (
        UniqueConstraint("company_id", "employee_id"),
        UniqueConstraint("attendpro_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    attendpro_id = Column(String(40), unique=True, nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    employee_id = Column(String(80), nullable=False)
    full_name = Column(String(200), nullable=False)
    phone = Column(String(30), nullable=True)
    telegram_user_id = Column(String(40), nullable=True, unique=True)
    photo_url = Column(String(500), nullable=True)
    is_approved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    company = relationship("Company", back_populates="workers")
    workflow = relationship("Workflow", back_populates="workers")
    attendance_records = relationship(
        "Attendance", back_populates="worker"
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    session = Column(String(20), nullable=False)
    recorded_at = Column(DateTime(timezone=True), default=utc_now)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    distance_meters = Column(Float, nullable=True)
    gps_alert = Column(Boolean, default=False)
    biometric_verified = Column(Boolean, default=False)
    status = Column(String(30), default="present")
    notes = Column(Text, nullable=True)

    worker = relationship("Worker", back_populates="attendance_records")
    project = relationship("Project")
