
import os
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if not user:
        return

    message = (
        "👋 እንኳን ወደ AttendPro በደህና መጡ!\n\n"
        "🏢 Smart Workforce & Attendance "
        "Management System\n\n"
        "በዚህ Bot የሠራተኛ ምዝገባ፣ "
        "የመገኘት መዝገብ እና የሥራ አስተዳደር "
        "አገልግሎቶችን ያገኛሉ።\n\n"
        "📌 ለመቀጠል የሚቀጥሉትን መመሪያዎች "
        "ይጠብቁ።"
    )

    await update.message.reply_text(message)


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "ℹ️ AttendPro Help\n\n"
        "/start - ዋና መጀመሪያ\n"
        "/help - የእገዛ መረጃ"
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
            "TELEGRAM_BOT_TOKEN is missing. "
            "Set it in Render Environment."
        )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Starting AttendPro Telegram Bot...")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
