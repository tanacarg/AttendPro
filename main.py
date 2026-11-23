
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from database import init_db, engine
from companies import router as companies_router
from login import router as auth_router
from employees import router as employees_router

from bot import start, help_command, menu_handler


# --------------------------------------------------
# LOGGING
# --------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("AttendPro")


# --------------------------------------------------
# ENVIRONMENT VARIABLES
# --------------------------------------------------

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

telegram_app = None


# --------------------------------------------------
# TELEGRAM ERROR HANDLER
# --------------------------------------------------

async def telegram_error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error(
        "Telegram update processing error",
        exc_info=context.error,
    )


# --------------------------------------------------
# APPLICATION LIFESPAN
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app

    # Initialize database
    init_db()
    logger.info("AttendPro database initialized.")

    # Validate environment variables
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing.")

    if not WEBHOOK_URL:
        raise RuntimeError("WEBHOOK_URL is missing.")

    if not WEBHOOK_SECRET:
        raise RuntimeError("WEBHOOK_SECRET is missing.")

    # Build Telegram application
    telegram_app = (
        Application.builder()
        .token(BOT_TOKEN)
        .updater(None)
        .build()
    )

    try:
        # Register commands
        telegram_app.add_handler(
            CommandHandler("start", start)
        )

        telegram_app.add_handler(
            CommandHandler("help", help_command)
        )

        # Register menu text handler
        telegram_app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                menu_handler,
            )
        )

        # Register error handler
        telegram_app.add_error_handler(
            telegram_error_handler
        )

        # Initialize and start Telegram application
        await telegram_app.initialize()
        await telegram_app.start()

        # Configure webhook
        webhook_address = (
            f"{WEBHOOK_URL}/telegram/webhook"
        )

        await telegram_app.bot.set_webhook(
            url=webhook_address,
            secret_token=WEBHOOK_SECRET,
            allowed_updates=Update.ALL_TYPES,
        )

        # Verify bot identity
        bot_info = await telegram_app.bot.get_me()

        logger.info(
            "AttendPro Telegram Bot is active: @%s",
            bot_info.username,
        )

        logger.info("Webhook configured successfully.")

        yield

    except Exception:
        logger.exception(
            "AttendPro startup or runtime error."
        )
        raise

    finally:
        # Stop the application but preserve the webhook.
        # Telegram can retain updates while the service restarts.
        if telegram_app is not None:
            try:
                if telegram_app.running:
                    await telegram_app.stop()

                await telegram_app.shutdown()

                logger.info(
                    "AttendPro Telegram application stopped."
                )

            except Exception:
                logger.exception(
                    "Error while stopping Telegram application."
                )

            finally:
                telegram_app = None


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="AttendPro",
    description=(
        "Smart Workforce & Attendance Management System"
    ),
    version="1.0.1",
    lifespan=lifespan,
)


# --------------------------------------------------
# REGISTER API ROUTERS
# --------------------------------------------------

app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(employees_router)


# --------------------------------------------------
# TELEGRAM WEBHOOK
# --------------------------------------------------

@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(
        default=None
    ),
):
    # Verify Telegram webhook secret
    if (
        not WEBHOOK_SECRET
        or x_telegram_bot_api_secret_token != WEBHOOK_SECRET
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook secret",
        )

    # Check bot readiness
    if telegram_app is None or not telegram_app.running:
        raise HTTPException(
            status_code=503,
            detail="Telegram bot is not ready",
        )

    try:
        data = await request.json()

        update = Update.de_json(
            data=data,
            bot=telegram_app.bot,
        )

        await telegram_app.update_queue.put(update)

        return {"ok": True}

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Failed to process Telegram webhook update."
        )

        raise HTTPException(
            status_code=400,
            detail="Could not process Telegram update",
        )


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

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

    <body style="
        font-family:Arial;
        text-align:center;
        padding:40px;
    ">

        <h1>AttendPro</h1>

        <h2>
            Smart Workforce & Attendance
            Management System
        </h2>

        <p>
            Workforce attendance and GPS verification platform.
        </p>

        <p>Application is running.</p>

        <p>Database monitoring is enabled.</p>

    </body>
    </html>
    """


# --------------------------------------------------
# APPLICATION HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "application": "AttendPro",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# --------------------------------------------------
# DATABASE HEALTH CHECK
# --------------------------------------------------

@app.get("/health/db")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "connected",
            "database": "PostgreSQL/SQLAlchemy",
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    except SQLAlchemyError:
        logger.exception(
            "Database health check failed."
        )

        raise HTTPException(
            status_code=503,
            detail="Database connection could not be verified.",
        )


# --------------------------------------------------
# API INFORMATION
# --------------------------------------------------

@app.get("/api")
def api_home():
    return {
        "message": "Welcome to AttendPro API",
        "version": "1.0.1",
    }
