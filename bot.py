
import os
import sys
import asyncio
import logging
from pathlib import Path
from threading import Thread
from collections import deque

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================================
# CONFIGURATION
# ==========================================

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

BASE_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = BASE_DIR / "approved_scripts"
SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

LOG_INTERVAL = 10
MAX_LOG_CHARS = 3500

# ==========================================
# LOGGING
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)

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
# RUNTIME STATE
# ==========================================

process = None
current_script = None
current_chat_id = None

log_buffer = deque(maxlen=200)
output_task = None
log_task = None

process_lock = None


# ==========================================
# ACCESS CONTROL
# ==========================================

def is_admin(update: Update) -> bool:
    user = update.effective_user
    return (
        user is not None
        and ADMIN_ID != 0
        and user.id == ADMIN_ID
    )


async def deny_access(update: Update):
    if update.effective_message:
        await update.effective_message.reply_text(
            "⛔ You are not authorized to use this bot."
        )


# ==========================================
# SCRIPT UTILITIES
# ==========================================

def list_approved_scripts():
    return sorted(
        path for path in SCRIPT_DIR.glob("*.py")
        if path.is_file()
    )


def active_process():
    return process is not None and process.returncode is None


# ==========================================
# START / HELP
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny_access(update)
        return

    await update.effective_message.reply_text(
        "🐍 Python Script Manager\n\n"
        "/run <filename.py> - Run an approved script\n"
        "/scripts - List approved scripts\n"
        "/logs - View recent output\n"
        "/stop - Stop the running script\n"
        "/cancel - Cancel the current operation\n\n"
        "Only scripts stored in approved_scripts/ can run."
    )


# ==========================================
# LIST APPROVED SCRIPTS
# ==========================================

async def scripts_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny_access(update)
        return

    scripts = list_approved_scripts()

    if not scripts:
        await update.effective_message.reply_text(
            "📂 No approved scripts found.\n\n"
            "Add reviewed .py files to the approved_scripts directory."
        )
        return

    await update.effective_message.reply_text(
        "📂 Approved scripts:\n\n"
        + "\n".join(f"• {p.name}" for p in scripts)
    )


# ==========================================
# RUN APPROVED SCRIPT
# ==========================================

async def run_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    global process, current_script, current_chat_id
    global output_task, log_task, process_lock

    if not is_admin(update):
        await deny_access(update)
        return

    if process_lock is None:
        process_lock = asyncio.Lock()

    if not context.args:
        await update.effective_message.reply_text(
            "Usage: /run filename.py\n\n"
            "Use /scripts to list approved scripts."
        )
        return

    filename = context.args[0]

    # Only accept a plain filename, not a path.
    if (
        Path(filename).name != filename
        or not filename.endswith(".py")
        or filename in ("", ".", "..")
    ):
        await update.effective_message.reply_text(
            "❌ Please provide a valid approved .py filename."
        )
        return

    script_path = SCRIPT_DIR / filename

    if not script_path.is_file():
        await update.effective_message.reply_text(
            "❌ That script is not in approved_scripts/."
        )
        return

    async with process_lock:
        if active_process():
            await update.effective_message.reply_text(
                "⚠️ A script is already running. Use /stop first."
            )
            return

        log_buffer.clear()
        current_script = filename
        current_chat_id = update.effective_chat.id

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-u",
                str(script_path),
                cwd=str(SCRIPT_DIR),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except Exception:
            logger.exception("Could not start approved script")
            process = None
            await update.effective_message.reply_text(
                "❌ Could not start the script. Check Render logs."
            )
            return

        child = process

        log_buffer.append(
            f"Started: {filename}\n"
            f"PID: {child.pid}\n"
        )

        await update.effective_message.reply_text(
            f"🚀 Running: {filename}\n"
            "📋 Output updates arrive approximately every 10 seconds.\n"
            "⌨️ Send normal text to provide input.\n"
            "🛑 Use /stop to stop the script."
        )

        output_task = asyncio.create_task(collect_output(child))
        log_task = asyncio.create_task(
            send_periodic_logs(
                context.application,
                current_chat_id,
                child,
                filename,
            )
        )


# ==========================================
# COLLECT OUTPUT
# ==========================================

async def collect_output(child):
    try:
        while True:
            chunk = await child.stdout.read(1024)
            if not chunk:
                break

            text = chunk.decode("utf-8", errors="replace")
            log_buffer.append(text)

    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Output collection failed")


# ==========================================
# SEND PERIODIC LOGS
# ==========================================

async def send_periodic_logs(
    application,
    chat_id,
    child,
    filename,
):
    global process, current_script

    try:
        while child.returncode is None:
            await asyncio.sleep(LOG_INTERVAL)

            if log_buffer:
                output = "".join(log_buffer)[-MAX_LOG_CHARS:]

                try:
                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=f"📋 Logs — {filename}\n\n{output}",
                    )
                except Exception:
                    logger.exception("Could not send periodic logs")

            if child.returncode is not None:
                break

        await child.wait()

        # Ensure all remaining output has been collected.
        if output_task and not output_task.done():
            await output_task

        output = "".join(log_buffer)[-MAX_LOG_CHARS:]
        if not output:
            output = "(No output produced.)"

        try:
            await application.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🏁 Script finished: {filename}\n"
                    f"Exit code: {child.returncode}\n\n"
                    f"📋 Final output:\n{output}"
                ),
            )
        except Exception:
            logger.exception("Could not send final logs")

    except asyncio.CancelledError:
        raise
    finally:
        if process is child:
            process = None
            current_script = None


# ==========================================
# SEND INPUT
# ==========================================

async def provide_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    child = process

    if child is None or child.returncode is not None:
        return

    if child.stdin is None:
        await update.effective_message.reply_text(
            "This process does not accept input."
        )
        return

    text = update.effective_message.text
    if not text:
        return

    try:
        child.stdin.write((text + "\n").encode("utf-8"))
        await child.stdin.drain()

        await update.effective_message.reply_text(
            "⌨️ Input sent."
        )
    except (BrokenPipeError, ConnectionResetError, OSError):
        await update.effective_message.reply_text(
            "❌ The script is no longer accepting input."
        )


# ==========================================
# VIEW LOGS
# ==========================================

async def logs_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny_access(update)
        return

    if not log_buffer:
        await update.effective_message.reply_text(
            "No script logs available."
        )
        return

    output = "".join(log_buffer)[-MAX_LOG_CHARS:]
    await update.effective_message.reply_text(
        f"📋 Recent output\n\n{output}"
    )


# ==========================================
# STOP SCRIPT
# ==========================================

async def stop_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny_access(update)
        return

    child = process

    if child is None or child.returncode is not None:
        await update.effective_message.reply_text(
            "No script is currently running."
        )
        return

    try:
        child.terminate()

        try:
            await asyncio.wait_for(child.wait(), timeout=5)
        except asyncio.TimeoutError:
            child.kill()
            await child.wait()

        await update.effective_message.reply_text(
            "🛑 Stop signal sent."
        )

    except ProcessLookupError:
        await update.effective_message.reply_text(
            "The script has already stopped."
        )


# ==========================================
# CANCEL
# ==========================================

async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny_access(update)
        return

    await update.effective_message.reply_text(
        "No pending operation. Use /run <filename.py> to start an approved script."
    )


# ==========================================
# ERROR HANDLER
# ==========================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error("Telegram error: %s", context.error)


# ==========================================
# MAIN
# ==========================================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("Set BOT_TOKEN in Render environment variables.")

    if ADMIN_ID == 0:
        raise RuntimeError("Set ADMIN_ID in Render environment variables.")

    # Start the Flask server in the background.
    Thread(target=run_web_server, daemon=True).start()

    telegram_app = Application.builder().token(BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("run", run_command))
    telegram_app.add_handler(CommandHandler("scripts", scripts_command))
    telegram_app.add_handler(CommandHandler("logs", logs_command))
    telegram_app.add_handler(CommandHandler("stop", stop_command))
    telegram_app.add_handler(CommandHandler("cancel", cancel_command))

    telegram_app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            provide_input,
        )
    )

    telegram_app.add_error_handler(error_handler)

    logger.info("Starting Telegram polling...")
    telegram_app.run_polling()


if __name__ == "__main__":
    main()
