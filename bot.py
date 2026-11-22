
import os
import logging

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


# AttendPro main menu
MAIN_MENU = [
    [KeyboardButton("🏢 ድርጅት ምዝገባ")],
    [KeyboardButton("👷 ሠራተኛ ምዝገባ")],
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
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    message = (
        "👋 እንኳን ወደ AttendPro በደህና መጡ!\n\n"
        "🏢 Smart Workforce & Attendance "
        "Management System\n\n"
        "የሠራተኛ ምዝገባ፣ Attendance፣ "
        "GPS ክትትል እና የሥራ አስተዳደር "
        "አገልግሎቶችን ከታች ባሉት ምናሌዎች "
        "ይምረጡ።"
    )

    await update.message.reply_text(
        message,
        reply_markup=MENU_MARKUP,
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    await update.message.reply_text(
        "ℹ️ AttendPro Help\n\n"
        "/start - ዋና ምናሌ\n"
        "/help - የእገዛ መረጃ",
        reply_markup=MENU_MARKUP,
    )


async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message or not update.message.text:
        return

    selected = update.message.text

    menu_responses = {
        "🏢 ድርጅት ምዝገባ":
            "🏢 የድርጅት ምዝገባ\n\n"
            "ይህ ክፍል ከድርጅት ምዝገባ Backend "
            "ጋር በቀጣይ ይገናኛል።",

        "👷 ሠራተኛ ምዝገባ":
            "👷 የሠራተኛ ምዝገባ\n\n"
            "ይህ ክፍል ከEmployee API ጋር "
            "በቀጣይ ይገናኛል።",

        "🕘 Attendance":
            "🕘 Attendance\n\n"
            "የሠራተኛ መገኘት መዝገብ ክፍል "
            "በቀጣይ ይዘጋጃል።",

        "📍 GPS ክትትል":
            "📍 GPS ክትትል\n\n"
            "የሥራ ቦታ እና የመገኛ ቦታ "
            "ክትትል ክፍል በቀጣይ ይዘጋጃል።",

        "📋 የሥራ ፕሮጀክቶች":
            "📋 የሥራ ፕሮጀክቶች\n\n"
            "የፕሮጀክት ምዝገባና አስተዳደር "
            "ክፍል በቀጣይ ይዘጋጃል።",

        "📊 ሪፖርቶች":
            "📊 ሪፖርቶች\n\n"
            "የAttendance እና የሠራተኞች "
            "ሪፖርት ክፍል በቀጣይ ይዘጋጃል።",

        "⚙️ አስተዳደር":
            "⚙️ የአስተዳደር ክፍል\n\n"
            "የአስተዳዳሪ ፈቃድና የድርጅት "
            "ቅንብሮች በቀጣይ ይዘጋጃሉ።",

        "ℹ️ እገዛ":
            "ℹ️ AttendPro Help\n\n"
            "/start - ዋና ምናሌ\n"
            "/help - የእገዛ መረጃ",
    }

    response = menu_responses.get(selected)

    if response:
        await update.message.reply_text(
            response,
            reply_markup=MENU_MARKUP,
        )


async def post_init(app: Application):
    bot_info = await app.bot.get_me()
    logger.info(
        "AttendPro Bot started successfully: @%s",
        bot_info.username,
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing."
        )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            menu_handler,
        )
    )

    logger.info("AttendPro Bot handlers configured.")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
