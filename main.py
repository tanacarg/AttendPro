import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from telegram import Update
from telegram.ext import Application, CommandHandler

from database import init_db, engine
from companies import router as companies_router
from login import router as auth_router
from employees import router as employees_router
from bot import start, help_command

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

telegram_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app

    init_db()
    logger.info("AttendPro database initialized.")

    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing.")

    if not WEBHOOK_URL:
        raise RuntimeError("WEBHOOK_URL is missing.")

    if not WEBHOOK_SECRET:
        raise RuntimeError("WEBHOOK_SECRET is missing.")

    telegram_app = (
        Application.builder()
        .token(BOT_TOKEN)
        .updater(None)
        .build()
    )

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))

    await telegram_app.initialize()
    await telegram_app.start()

    webhook_address = f"{WEBHOOK_URL}/telegram/webhook"

    await telegram_app.bot.set_webhook(
        url=webhook_address,
        secret_token=WEBHOOK_SECRET,
    )

    bot_info = await telegram_app.bot.get_me()

    logger.info(
        "AttendPro Telegram Bot is active: @%s",
        bot_info.username,
    )
    logger.info("Webhook configured successfully.")

    yield

    if telegram_app:
        await telegram_app.bot.delete_webhook()
        await telegram_app.stop()
        await telegram_app.shutdown()
        logger.info("AttendPro Telegram Bot stopped.")


app = FastAPI(
    title="AttendPro",
    description="Smart Workforce & Attendance Management System",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(employees_router)


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=None),
):
    if x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook secret",
        )

    if telegram_app is None:
        raise HTTPException(
            status_code=503,
            detail="Telegram bot is not ready",
        )

    data = await request.json()

    update = Update.de_json(
        data=data,
        bot=telegram_app.bot,
    )

    await telegram_app.update_queue.put(update)

    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
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
