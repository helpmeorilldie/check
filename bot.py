import os
import logging
from threading import Thread

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ==========================================
# LOGGING
# ==========================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURATION
# ==========================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# ==========================================
# FLASK WEB SERVER
# ==========================================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Telegram bot is running!", 200


@web_app.route("/health")
def health():
    return {"status": "ok"}, 200


def run_web_server():
    port = int(os.environ.get("PORT", "10000"))
    web_app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
    )


# ==========================================
# TELEGRAM COMMANDS
# ==========================================

def is_admin(update: Update) -> bool:
    user = update.effective_user
    return user is not None and ADMIN_ID != 0 and user.id == ADMIN_ID


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await update.effective_message.reply_text(
            "Access denied."
        )
        return

    await update.effective_message.reply_text(
        "✅ Your Telegram bot is running!\n\n"
        "/healthcheck — Check bot status"
    )


async def healthcheck(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await update.effective_message.reply_text(
            "Access denied."
        )
        return

    await update.effective_message.reply_text(
        "✅ Bot is online and responding."
    )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error(
        "Telegram update error: %s",
        context.error,
    )


# ==========================================
# MAIN
# ==========================================

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "Missing BOT_TOKEN environment variable in Render."
        )

    if ADMIN_ID == 0:
        raise RuntimeError(
            "Missing or invalid ADMIN_ID environment variable in Render."
        )

    # Start Flask in a daemon thread.
    Thread(
        target=run_web_server,
        daemon=True,
    ).start()

    # Create the Telegram application.
    telegram_app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    telegram_app.add_handler(
        CommandHandler("start", start)
    )

    telegram_app.add_handler(
        CommandHandler("healthcheck", healthcheck)
    )

    telegram_app.add_error_handler(error_handler)

    logger.info("Starting Telegram polling...")

    # Keep the main process running.
    telegram_app.run_polling()


if __name__ == "__main__":
    main()

