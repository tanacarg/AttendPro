
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models import Attendance, Worker, Project
from gps import check_project_distance


def record_attendance(
    db: Session,
    worker_id: int,
    session_name: str,
    latitude: float,
    longitude: float,
    biometric_verified: bool,
    project_id: int
):
    if session_name not in ("morning", "afternoon"):
        raise ValueError("Invalid attendance session")

    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.is_active.is_(True),
        Worker.is_approved.is_(True)
    ).first()

    if not worker:
        raise ValueError("Approved active worker not found")

    project = db.query(Project).filter(
        Project.id == project_id,
        Project.company_id == worker.company_id,
        Project.is_active.is_(True)
    ).first()

    if not project:
        raise ValueError("Project not found for this company")

    if not biometric_verified:
        raise ValueError("Biometric verification is required")

    today = datetime.now(timezone.utc).date()

    existing = db.query(Attendance).filter(
        Attendance.worker_id == worker.id,
        Attendance.session == session_name,
        Attendance.recorded_at >= datetime(
            today.year, today.month, today.day,
            tzinfo=timezone.utc
        ),
        Attendance.project_id == project.id
    ).first()

    if existing:
        raise ValueError("Attendance already recorded for this session")

    locations = [
        {
            "latitude": point.latitude,
            "longitude": point.longitude,
            "label": point.label
        }
        for point in project.locations
    ]

    distance_result = check_project_distance(
        latitude,
        longitude,
        locations
    )

    record = Attendance(
        worker_id=worker.id,
        project_id=project.id,
        session=session_name,
        recorded_at=datetime.now(timezone.utc),
        latitude=latitude,
        longitude=longitude,
        distance_meters=distance_result["distance_meters"],
        gps_alert=distance_result["gps_alert"],
        biometric_verified=True,
        status="present"
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "attendance_id": record.id,
        "worker_id": worker.attendpro_id,
        "worker_name": worker.full_name,
        "company": worker.company.name,
        "project": project.name,
        "session": session_name,
        "recorded_at": record.recorded_at.isoformat(),
        "distance_meters": distance_result["distance_meters"],
        "distance_km": distance_result["distance_km"],
        "gps_alert": distance_result["gps_alert"],
        "attendance_status": "present",
        "attendance_allowed": True
    }
