
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables when the application starts.
    init_db()
    yield


app = FastAPI(
    title="AttendPro",
    description="Smart Workforce & Attendance Management System",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>AttendPro</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f3f6fa;
                margin: 0;
                padding: 40px 16px;
                text-align: center;
            }
            .card {
                max-width: 600px;
                margin: 40px auto;
                padding: 32px;
                background: white;
                border-radius: 16px;
                box-shadow: 0 4px 18px rgba(0,0,0,.08);
            }
            h1 { color: #174a75; }
            p { color: #526171; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>AttendPro</h1>
            <h2>Smart Workforce & Attendance Management System</h2>
            <p>Workforce attendance and GPS verification platform.</p>
            <p>Application is running.</p>
        </div>
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


@app.get("/api")
def api_home():
    return {
        "message": "Welcome to AttendPro API",
        "version": "1.0.0",
    }
