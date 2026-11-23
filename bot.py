"""
AttendPro Telegram Bot
----------------------
This file is designed to be imported by main.py:

    from bot import start, help_command, menu_handler

It does not start polling or create a second Telegram Application.
FastAPI/main.py owns the webhook lifecycle.

Implemented:
- Start/help and clear Amharic main menu
- Company registration request through the existing POST /companies/register API
- Safe API error handling and user-friendly messages
- Basic menu navigation

Important integration limits:
- The supplied backend does not yet expose an employee-registration API endpoint.
- The supplied backend does not expose an attendance submission endpoint.
- Finger-drawn signatures require a Telegram Web App/Mini App and backend storage.
- Role-specific admin actions must be connected to authenticated backend endpoints;
  the bot must not trust a user's self-selected role.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import ContextTypes

logger = logging.getLogger("AttendPro.Bot")

API_BASE_URL = os.getenv(
    "ATTENDPRO_API_URL",
    os.getenv("WEBHOOK_URL", "https://attendpro-utdg.onrender.com"),
).rstrip("/")

# Keep this bot UI aligned with the current AttendPro workflow.
BTN_COMPANY_REGISTER = "🏢 ድርጅት ማስመዝገብ"
BTN_EMPLOYEE_REGISTER = "👷 ሠራተኛ ማስመዝገብ"
BTN_ATTENDANCE = "🕒 Attendance"
BTN_MY_PROFILE = "👤 የእኔ መረጃ"
BTN_HELP = "❓ እገዛ"
BTN_ABOUT = "ℹ️ ስለ AttendPro"
BTN_HOME = "🏠 መጀመሪያ ገፅ"
BTN_CANCEL = "❌ ሰርዝ"

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_COMPANY_REGISTER)],
        [KeyboardButton(BTN_EMPLOYEE_REGISTER)],
        [KeyboardButton(BTN_ATTENDANCE)],
        [KeyboardButton(BTN_MY_PROFILE)],
        [KeyboardButton(BTN_HELP), KeyboardButton(BTN_ABOUT)],
    ],
    resize_keyboard=True,
    input_field_placeholder="ከምናሌው ይምረጡ",
)

CANCEL_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton(BTN_CANCEL)]],
    resize_keyboard=True,
)

HOME_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton(BTN_HOME)]],
    resize_keyboard=True,
)

# Per-user conversation states stored in PTB context.user_data.
STATE_KEY = "attendpro_state"
COMPANY_NAME_KEY = "attendpro_company_name"


def _set_state(context: ContextTypes.DEFAULT_TYPE, state: Optional[str]) -> None:
    if state is None:
        context.user_data.pop(STATE_KEY, None)
    else:
        context.user_data[STATE_KEY] = state


async def _send_company_registration(
    company_name: str,
    telegram_user_id: int,
) -> tuple[bool, str]:
    """
    Submit the company name to the existing backend endpoint.
    The current CompanyCreate schema supports name and logo_url only.
    Telegram applicant ID/phone notification is not yet supported by that API.
    """
    url = f"{API_BASE_URL}/companies/register"
    payload = {
        "name": company_name,
        "logo_url": None,
    }
    headers = {
        "X-AttendPro-Telegram-Applicant": str(telegram_user_id),
    }

    timeout = httpx.Timeout(25.0, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code in (200, 201):
            return True, "success"

        if response.status_code == 409:
            return False, "duplicate"

        logger.warning(
            "Company registration API returned %s: %s",
            response.status_code,
            response.text[:500],
        )
        return False, "server_error"

    except httpx.TimeoutException:
        logger.warning("Company registration request timed out.")
        return False, "timeout"
    except httpx.HTTPError:
        logger.exception("Company registration API connection failed.")
        return False, "connection_error"


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_message or not update.effective_user:
        return

    _set_state(context, None)
    context.user_data.pop(COMPANY_NAME_KEY, None)

    await update.effective_message.reply_text(
        "👋 እንኳን ወደ AttendPro በደህና መጡ!\n\n"
        "AttendPro – Smart Workforce & Attendance Management System\n\n"
        "ከታች ካሉት ምናሌዎች ይምረጡ።",
        reply_markup=MAIN_MENU,
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_message:
        return

    await update.effective_message.reply_text(
        "📌 AttendPro እገዛ\n\n"
        "🏢 ድርጅት ማስመዝገብ — አዲስ ድርጅት የምዝገባ ጥያቄ ለመላክ።\n"
        "👷 ሠራተኛ ማስመዝገብ — የሠራተኛ ምዝገባ መመሪያ።\n"
        "🕒 Attendance — የAttendance መስፈርቶችን ለማወቅ።\n\n"
        "ለድጋፍ የድርጅትዎን አስተዳዳሪ ያነጋግሩ።",
        reply_markup=MAIN_MENU,
    )


async def _begin_company_registration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    _set_state(context, "awaiting_company_name")
    context.user_data.pop(COMPANY_NAME_KEY, None)

    await update.effective_message.reply_text(
        "🏢 የድርጅትዎን ሙሉ ስም ያስገቡ።\n\n"
        "ምሳሌ፦ ABC Construction PLC\n\n"
        "ለመተው ❌ ሰርዝ ይጫኑ።",
        reply_markup=CANCEL_MENU,
    )


async def _handle_company_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> None:
    company_name = text.strip()

    if len(company_name) < 2 or len(company_name) > 150:
        await update.effective_message.reply_text(
            "የድርጅት ስም ከ2 እስከ 150 ቁምፊ መሆን አለበት። እንደገና ያስገቡ።",
            reply_markup=CANCEL_MENU,
        )
        return

    context.user_data[COMPANY_NAME_KEY] = company_name
    _set_state(context, "confirm_company_registration")

    confirm_menu = ReplyKeyboardMarkup(
        [
            [KeyboardButton("✅ ጥያቄውን ላክ")],
            [KeyboardButton(BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )

    await update.effective_message.reply_text(
        "እባክዎ የድርጅት ስሙን ያረጋግጡ፦\n\n"
        f"🏢 {company_name}\n\n"
        "የምዝገባ ጥያቄውን ለመላክ «✅ ጥያቄውን ላክ» ይጫኑ።",
        reply_markup=confirm_menu,
    )


async def _confirm_company_registration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user = update.effective_user
    company_name = context.user_data.get(COMPANY_NAME_KEY)

    if not user or not company_name:
        _set_state(context, None)
        await update.effective_message.reply_text(
            "የምዝገባ መረጃው ጊዜው አልፎበታል። እባክዎ እንደገና ይጀምሩ።",
            reply_markup=MAIN_MENU,
        )
        return

    await update.effective_message.reply_text(
        "⏳ የድርጅት ምዝገባ ጥያቄዎን በመላክ ላይ...",
        reply_markup=ReplyKeyboardRemove(),
    )

    ok, reason = await _send_company_registration(
        company_name=company_name,
        telegram_user_id=user.id,
    )

    _set_state(context, None)
    context.user_data.pop(COMPANY_NAME_KEY, None)

    if ok:
        message = (
            "✅ የድርጅት ምዝገባ ጥያቄዎ ተልኳል።\n\n"
            "የPlatform Super Admin ጥያቄዎን ከገመገመ በኋላ "
            "የሚቀጥለውን መረጃ ይደርስዎታል።"
        )
    elif reason == "timeout":
        message = (
            "⌛ የBackend ምላሽ ለመቀበል ጊዜ ወስዷል። "
            "አገልግሎቱ ከእንቅልፉ እስኪነቃ ትንሽ ቆይተው እንደገና ይሞክሩ።"
        )
    elif reason == "connection_error":
        message = (
            "⚠️ Backend ላይ መድረስ አልተቻለም። "
            "የInternet ግንኙነትዎን ያረጋግጡና በኋላ ይሞክሩ።"
        )
    elif reason == "duplicate":
        message = "⚠️ ይህ የድርጅት ምዝገባ ጥያቄ አስቀድሞ ተመዝግቦ ሊሆን ይችላል።"
    else:
        message = (
            "❌ የምዝገባ ጥያቄውን መላክ አልተሳካም። "
            "እባክዎ ቆይተው እንደገና ይሞክሩ።"
        )

    await update.effective_message.reply_text(
        message,
        reply_markup=MAIN_MENU,
    )


async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not update.effective_message or not update.effective_user:
        return

    text = (update.effective_message.text or "").strip()
    state = context.user_data.get(STATE_KEY)

    # Handle cancellation and navigation before form-state processing.
    if text == BTN_CANCEL:
        _set_state(context, None)
        context.user_data.pop(COMPANY_NAME_KEY, None)
        await update.effective_message.reply_text(
            "የነበረው ሂደት ተሰርዟል።",
            reply_markup=MAIN_MENU,
        )
        return

    if text in (BTN_HOME, "/start"):
        await start(update, context)
        return

    if state == "awaiting_company_name":
        await _handle_company_name(update, context, text)
        return

    if state == "confirm_company_registration":
        if text == "✅ ጥያቄውን ላክ":
            await _confirm_company_registration(update, context)
        else:
            await update.effective_message.reply_text(
                "እባክዎ «✅ ጥያቄውን ላክ» ወይም «❌ ሰርዝ» ይምረጡ።"
            )
        return

    if text == BTN_COMPANY_REGISTER:
        await _begin_company_registration(update, context)
        return

    if text == BTN_EMPLOYEE_REGISTER:
        await update.effective_message.reply_text(
            "👷 የሠራተኛ ምዝገባ\n\n"
            "የሠራተኛ ምዝገባ ከድርጅት ኮድ፣ የሥራ ሂደት እና "
            "የTelegram መለያ ጋር መገናኘት አለበት።\n\n"
            "በተላኩት Backend ፋይሎች ውስጥ ይህን ጥያቄ የሚቀበል "
            "API endpoint ገና ስላልተገኘ፣ እዚህ ላይ የተሳካ ምዝገባ እንዳለ "
            "በሐሰት አናሳይም። የBackend endpoint ከተጨመረ በኋላ ይህን "
            "ምናሌ እናገናኘዋለን።",
            reply_markup=MAIN_MENU,
        )
        return

    if text == BTN_ATTENDANCE:
        await update.effective_message.reply_text(
            "🕒 Attendance\n\n"
            "የAttendance መላኪያ ከGPS 100 ሜትር የድርጅት ክልል፣ "
            "የጠዋት/ከሰዓት ጊዜ ገደብ እና አዲስ የዲጂታል ፊርማ ጋር "
            "መገናኘት አለበት።\n\n"
            "በተላኩት Backend ፋይሎች ውስጥ Attendance submit API "
            "እና የፊርማ ማስቀመጫ አልተካተቱም። ስለዚህ እስኪገናኙ "
            "ድረስ የAttendance መላኪያ አይነቃም።",
            reply_markup=MAIN_MENU,
        )
        return

    if text == BTN_MY_PROFILE:
        username = (
            f"@{update.effective_user.username}"
            if update.effective_user.username
            else "የTelegram username የለም"
        )
        await update.effective_message.reply_text(
            "👤 የTelegram መረጃዎ\n\n"
            f"Telegram ID: {update.effective_user.id}\n"
            f"Username: {username}\n\n"
            "ይህ የTelegram መረጃ ብቻ ነው፤ የድርጅት ሠራተኛ "
            "ምዝገባ ወይም ማጽደቅ አያሳይም።",
            reply_markup=MAIN_MENU,
        )
        return

    if text in (BTN_HELP, "/help"):
        await help_command(update, context)
        return

    if text == BTN_ABOUT:
        await update.effective_message.reply_text(
            "ℹ️ AttendPro\n\n"
            "Smart Workforce & Attendance Management System\n"
            "የድርጅቶችን የሠራተኞች ምዝገባና Attendance "
            "ሂደት ለማስተዳደር የተዘጋጀ ስርዓት።",
            reply_markup=MAIN_MENU,
        )
        return

    await update.effective_message.reply_text(
        "እባክዎ ከምናሌው ውስጥ አንዱን ይምረጡ።",
        reply_markup=MAIN_MENU,
    )
