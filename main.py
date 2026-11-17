
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone

app = FastAPI(
    title="AttendPro",
    description="Smart Workforce & Attendance Management System",
    version="0.1.0"
)


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AttendPro</title>
        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f3f6fb;
                color: #17233b;
                text-align: center;
            }
            header {
                background: #123c69;
                color: white;
                padding: 45px 15px;
            }
            .container {
                max-width: 750px;
                margin: 35px auto;
                padding: 25px;
            }
            .card {
                background: white;
                padding: 30px;
                border-radius: 14px;
                box-shadow: 0 4px 18px #00000010;
            }
            .status {
                color: #16834a;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <header>
            <h1>AttendPro</h1>
            <p>Smart Workforce & Attendance Management System</p>
        </header>
        <main class="container">
            <section class="card">
                <h2>Welcome to AttendPro</h2>
                <p>Workforce Attendance and Field Location Verification Platform</p>
                <p class="status">System is running</p>
                <p>Secure attendance. Reliable field verification.</p>
            </section>
        </main>
    </body>
    </html>
    """


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "application": "AttendPro",
        "version": "0.1.0",
        "time": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api")
async def api_home():
    return {
        "message": "Welcome to AttendPro API",
        "status": "active"
    }
