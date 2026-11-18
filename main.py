
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import init_db, engine
from companies import router as companies_router
from login import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    init_db()
    yield


app = FastAPI(
    title="AttendPro",
    description="Smart Workforce & Attendance Management System",
    version="1.0.0",
    lifespan=lifespan,
)

# Register existing API routers
app.include_router(auth_router)
app.include_router(companies_router)


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1">
        <title>AttendPro</title>
    </head>
    <body style="font-family:Arial;text-align:center;padding:40px;">
        <h1>AttendPro</h1>
        <h2>Smart Workforce & Attendance Management System</h2>
        <p>Workforce attendance and GPS verification platform.</p>
        <p>Application is running.</p>
        <p>Database monitoring is enabled.</p>
    </body>
    </html>
    """


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "application": "AttendPro",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health/db")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "connected",
            "database": "PostgreSQL/SQLAlchemy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except SQLAlchemyError:
        return {
            "status": "error",
            "database": "connection_failed",
            "message": "Database connection could not be verified.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@app.get("/api")
def api_home():
    return {
        "message": "Welcome to AttendPro API",
        "version": "1.0.0",
    }
