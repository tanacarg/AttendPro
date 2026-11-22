
import logging

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import ContextTypes


# --------------------------------------------------
# LOGGING
# --------------------------------------------------

logger = logging.getLogger(__name__)


# --------------------------------------------------
# ATTENDPRO MAIN REPLY KEYBOARD
# --------------------------------------------------

MAIN_MENU = [
    [
        KeyboardButton("🏢 ድርጅት ምዝገባ"),
    ],
    [
        KeyboardButton("👷 ሠራተኛ ምዝገባ"),
    ],
    [
        KeyboardButton("🕘 Attendance"),
        KeyboardButton("📍 GPS ክትትል"),
    ],
    [
        KeyboardButton("📋 የሥራ ፕሮጀክቶች"),
        KeyboardButton("📊 ሪፖርቶች"),
    ],
    [
        KeyboardButton("⚙️ አስተዳደር"),
        KeyboardButton("ℹ️ እገዛ"),
    ],
]

MENU_MARKUP = ReplyKeyboardMarkup(
    MAIN_MENU,
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="የAttendPro አገልግሎት ይምረጡ",
)


# --------------------------------------------------
# START COMMAND
# --------------------------------------------------

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    user = update.effective_user

    first_name = (
        user.first_name
        if user and user.first_name
        else "ደንበኛ"
    )

    message = (
        f"👋 ሰላም {first_name}!\n\n"
        "እንኳን ወደ AttendPro በደህና መጡ!\n\n"
        "🏢 Smart Workforce & Attendance "
        "Management System\n\n"
        "AttendPro የድርጅት፣ የሠራተኛ፣ "
        "የመገኘት እና የሥራ አስተዳደር "
        "ስርዓት ነው።\n\n"
        "📌 ለመቀጠል ከታች ያሉትን "
        "ቋሚ ምናሌዎች ይጠቀሙ።"
    )

    await update.message.reply_text(
        message,
        reply_markup=MENU_MARKUP,
    )

    logger.info(
        "Start command used by user ID: %s",
        user.id if user else "Unknown",
    )


# --------------------------------------------------
# HELP COMMAND
# --------------------------------------------------

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    message = (
        "ℹ️ AttendPro የእገዛ መረጃ\n\n"
        "🏢 ድርጅት ምዝገባ - ድርጅት ለመመዝገብ\n"
        "👷 ሠራተኛ ምዝገባ - ሠራተኛ ለመመዝገብ\n"
        "🕘 Attendance - የመገኘት መዝገብ\n"
        "📍 GPS ክትትል - የሥራ ቦታ ክትትል\n"
        "📋 የሥራ ፕሮጀክቶች - የፕሮጀክት አስተዳደር\n"
        "📊 ሪፖርቶች - የሥራ ሪፖርቶች\n"
        "⚙️ አስተዳደር - የአስተዳደር አገልግሎቶች\n\n"
        "/start - ዋና ምናሌ\n"
        "/help - የእገዛ መረጃ"
    )

    await update.message.reply_text(
        message,
        reply_markup=MENU_MARKUP,
    )


# --------------------------------------------------
# REPLY KEYBOARD MENU HANDLER
# --------------------------------------------------

async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    selected = update.message.text

    if not selected:
        return

    menu_responses = {
        "🏢 ድርጅት ምዝገባ": (
            "🏢 የድርጅት ምዝገባ\n\n"
            "የድርጅት ምዝገባ ቅጽ በቀጣይ "
            "ከAttendPro Backend API ጋር ይገናኛል።"
        ),

        "👷 ሠራተኛ ምዝገባ": (
            "👷 የሠራተኛ ምዝገባ\n\n"
            "የሠራተኛ ምዝገባ ቅጽ በቀጣይ "
            "ከEmployee API ጋር ይገናኛል።"
        ),

        "🕘 Attendance": (
            "🕘 Attendance\n\n"
            "የሠራተኛ መገኘት መዝገብ "
            "ክፍል በቀጣይ ከAttendance "
            "ስርዓት ጋር ይገናኛል።"
        ),

        "📍 GPS ክትትል": (
            "📍 GPS ክትትል\n\n"
            "የሥራ ቦታ እና የመገኛ ቦታ "
            "ክትትል ክፍል በቀጣይ ይገናኛል።"
        ),

        "📋 የሥራ ፕሮጀክቶች": (
            "📋 የሥራ ፕሮጀክቶች\n\n"
            "የፕሮጀክት ምዝገባና አስተዳደር "
            "ክፍል በቀጣይ ይገናኛል።"
        ),

        "📊 ሪፖርቶች": (
            "📊 ሪፖርቶች\n\n"
            "የAttendance እና የሠራተኞች "
            "ሪፖርት ክፍል በቀጣይ ይገናኛል።"
        ),

        "⚙️ አስተዳደር": (
            "⚙️ የአስተዳደር ክፍል\n\n"
            "ይህ ክፍል የአስተዳዳሪ ፈቃድ "
            "እና የድርጅት ቅንብሮችን "
            "በቀጣይ ይይዛል።"
        ),

        "ℹ️ እገዛ": (
            "ℹ️ AttendPro የእገዛ ክፍል\n\n"
            "ለመመሪያ የሚከተለውን ይጠቀሙ፦\n"
            "/start - ዋና ምናሌ\n"
            "/help - የእገዛ መረጃ"
        ),
    }

    response = menu_responses.get(selected)

    if response is None:
        return

    await update.message.reply_text(
        response,
        reply_markup=MENU_MARKUP,
    )

    user = update.effective_user

    logger.info(
        "Menu selected: %s | User ID: %s",
        selected,
        user.id if user else "Unknown",
    )
