import os
import sys
import asyncio
import logging
import tempfile
import threading
from pathlib import Path
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

# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_TEXT = os.getenv("ADMIN_ID", "").strip()
PORT = int(os.getenv("PORT", "10000"))

MAX_FILE_SIZE = 100 * 1024       # 100 KB
LOG_INTERVAL = 10                # Send logs every 10 seconds
MAX_LOG_LINES = 150
MAX_RUNTIME_SECONDS = 3600       # One-hour maximum runtime

if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN environment variable.")

if not ADMIN_ID_TEXT.isdigit():
    raise RuntimeError("Set ADMIN_ID to your numeric Telegram user ID.")

ADMIN_ID = int(ADMIN_ID_TEXT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# ============================================================
# FLASK HEALTH SERVER
# ============================================================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Telegram script bot is running!", 200


@web_app.route("/healthcheck")
def healthcheck():
    return "OK", 200


def run_web_server():
    web_app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False,
    )


# ============================================================
# SCRIPT STATE
# ============================================================

BASE_DIR = Path(tempfile.gettempdir()) / "telegram_script_bot"
BASE_DIR.mkdir(parents=True, exist_ok=True)

process = None
process_lock = asyncio.Lock()

current_script = None
current_script_dir = None
current_logs = deque(maxlen=MAX_LOG_LINES)

upload_pending = False
log_task = None
runtime_task = None
script_input_queue = asyncio.Queue()

# ============================================================
# ACCESS CONTROL
# ============================================================


def is_admin(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id == ADMIN_ID


async def deny_access(update: Update):
    if update.effective_message:
        await update.effective_message.reply_text(
            "⛔ You are not authorized to use this bot."
        )


# ============================================================
# LOGGING HELPERS
# ============================================================


def add_log(line: str):
    current_logs.append(line.rstrip("\n"))


async def send_log(update: Update, text: str):
    if update.effective_message:
        await update.effective_message.reply_text(text)


async def read_stream(stream, label):
    try:
        while True:
            line = await stream.readline()

            if not line:
                break

            decoded = line.decode("utf-8", errors="replace").rstrip()

            add_log(f"{label}: {decoded}")

    except Exception as exc:
        logger.exception("Error reading process output: %s", exc)


async def stream_process_output(proc):
    await asyncio.gather(
        read_stream(proc.stdout, "OUT"),
        read_stream(proc.stderr, "ERR"),
    )


async def send_periodic_logs(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        while True:
            await asyncio.sleep(LOG_INTERVAL)

            if process is None or process.returncode is not None:
                return

            lines = list(current_logs)

            if lines:
                text = "\n".join(lines[-35:])
                message = f"📋 Live logs — {current_script}\n\n{text}"

                # Keep messages below Telegram's message-size limit.
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message[-3800:],
                )

    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Periodic log sender failed")


async def stop_background_tasks():
    global log_task, runtime_task

    for task in (log_task, runtime_task):
        if task and task is not asyncio.current_task() and not task.done():
            task.cancel()

    log_task = None
    runtime_task = None


# ============================================================
# SCRIPT EXECUTION
# ============================================================


async def enforce_runtime_limit(proc):
    try:
        await asyncio.sleep(MAX_RUNTIME_SECONDS)

        if proc.returncode is None:
            proc.terminate()

            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()

            add_log("Script stopped: maximum runtime reached.")

    except asyncio.CancelledError:
        raise


async def run_uploaded_script(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    file_path: Path,
):
    global process
    global current_script
    global current_script_dir
    global log_task
    global runtime_task

    async with process_lock:
        if process is not None and process.returncode is None:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ A script is already running. Use /stop first.",
            )
            return

        current_script = file_path.name
        current_script_dir = file_path.parent
        current_logs.clear()

        while not script_input_queue.empty():
            try:
                script_input_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        add_log(f"Starting {current_script}...")

        try:
            # This is a subprocess, NOT a security sandbox.
            # Run only trusted scripts in a dedicated environment.
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-u",
                str(file_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(file_path.parent),
            )

            proc = process

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"✅ File received: {current_script}\n"
                    f"📂 Saved successfully.\n"
                    f"▶️ Starting script...\n\n"
                    f"📋 Logs — {current_script}\n"
                    f"Started {current_script}\n"
                    f"Process ID: {proc.pid}"
                ),
            )

            log_task = asyncio.create_task(
                send_periodic_logs(chat_id, context)
            )

            runtime_task = asyncio.create_task(
                enforce_runtime_limit(proc)
            )

        except Exception as exc:
            process = None
            add_log(f"Failed to start script: {exc}")

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Could not start script:\n{exc}",
            )
            return

    try:
        await stream_process_output(proc)
        await proc.wait()

        add_log(f"Process exited with code {proc.returncode}.")

        final_lines = list(current_logs)
        final_text = "\n".join(final_lines[-35:]) or "(No output)"

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🏁 Script finished: {current_script}\n"
                f"Exit code: {proc.returncode}\n\n"
                f"📋 Final logs:\n{final_text}"
            )[-4000:],
        )

    except asyncio.CancelledError:
        raise

    except Exception as exc:
        logger.exception("Script execution error")
        add_log(f"Execution error: {exc}")

    finally:
        await stop_background_tasks()

        async with process_lock:
            if process is proc:
                process = None


# ============================================================
# TELEGRAM COMMANDS
# ============================================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny_access(update)
        return

    await update.effective_message.reply_text(
        "🤖 Script Manager Bot\n\n"
        "/run - Upload a Python script\n"
        "/logs - View recent output\n"
        "/stop - Stop the running script\n"
        "/cancel - Cancel an upload\n"
        "/healthcheck - Check bot status\n\n"
        "Send /run, then upload your .py file.\n"
        "Maximum file size: 100 KB.\n"
        "Only upload scripts you trust."
    )


async def healthcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny_access(update)
        return

    await update.effective_message.reply_text(
        "✅ Your Telegram bot is running!"
    )


async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global upload_pending

    if not is_admin(update):
        await deny_access(update)
        return

    if process is not None and process.returncode is None:
        await update.effective_message.reply_text(
            "⚠️ A script is already running. Use /stop first."
        )
        return

    upload_pending = True

    await update.effective_message.reply_text(
        "📂 Upload your Python file now.\n\n"
        "Only .py files are accepted.\n"
        "Maximum file size: 100 KB.\n\n"
        "⚠️ Only upload scripts you trust.\n"
        "Send /cancel to cancel the upload."
    )


async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    global upload_pending

    if not is_admin(update):
        await deny_access(update)
        return

    upload_pending = False

    await update.effective_message.reply_text(
        "❎ Upload cancelled."
    )


async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny_access(update)
        return

    if not current_logs:
        await update.effective_message.reply_text(
            "📋 No logs available yet."
        )
        return

    text = "\n".join(list(current_logs)[-50:])

    await update.effective_message.reply_text(
        f"📋 Logs — {current_script or 'Script'}\n\n{text}"[-4000:]
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global process

    if not is_admin(update):
        await deny_access(update)
        return

    proc = process

    if proc is None or proc.returncode is not None:
        await update.effective_message.reply_text(
            "ℹ️ No script is currently running."
        )
        return

    try:
        proc.terminate()

        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()

        add_log("Script stopped by administrator.")

        await update.effective_message.reply_text(
            "🛑 Script stopped."
        )

    except ProcessLookupError:
        await update.effective_message.reply_text(
            "ℹ️ The script has already stopped."
        )


# ============================================================
# FILE UPLOAD HANDLER
# ============================================================


async def handle_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    global upload_pending

    if not is_admin(update):
        await deny_access(update)
        return

    if not upload_pending:
        await update.effective_message.reply_text(
            "Send /run before uploading a Python file."
        )
        return

    document = update.effective_message.document

    if document is None:
        return

    filename = Path(document.file_name or "").name

    if not filename.lower().endswith(".py"):
        await update.effective_message.reply_text(
            "❌ Only .py files are accepted."
        )
        return

    if document.file_size is None or document.file_size > MAX_FILE_SIZE:
        await update.effective_message.reply_text(
            "❌ Maximum file size is 100 KB."
        )
        return

    if process is not None and process.returncode is None:
        upload_pending = False

        await update.effective_message.reply_text(
            "⚠️ A script is already running. Use /stop first."
        )
        return

    upload_pending = False

    # Give each upload its own working directory.
    safe_dir = Path(tempfile.mkdtemp(prefix="upload_", dir=BASE_DIR))
    file_path = safe_dir / filename

    try:
        telegram_file = await context.bot.get_file(document.file_id)
        await telegram_file.download_to_drive(custom_path=str(file_path))

        # Check the actual downloaded size too.
        if file_path.stat().st_size > MAX_FILE_SIZE:
            file_path.unlink(missing_ok=True)

            await update.effective_message.reply_text(
                "❌ File exceeds the 100 KB limit."
            )
            return

        await update.effective_message.reply_text(
            f"✅ File received: {filename}\n"
            "📂 Saved successfully.\n"
            "▶️ Starting script..."
        )

        await run_uploaded_script(
            update.effective_chat.id,
            context,
            file_path,
        )

    except Exception as exc:
        logger.exception("File upload failed")

        await update.effective_message.reply_text(
            f"❌ Upload or execution failed:\n{exc}"
        )


# ============================================================
# TEXT INPUT HANDLER
# ============================================================


async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    message = update.effective_message
    if message is None or not message.text:
        return

    # Do not feed bot commands into the script's stdin.
    if message.text.startswith("/"):
        return

    proc = process

    if proc is None or proc.returncode is not None:
        return

    try:
        proc.stdin.write((message.text + "\n").encode("utf-8"))
        await proc.stdin.drain()

        await message.reply_text(
            "✉️ Input sent to the running script."
        )

    except (BrokenPipeError, ConnectionResetError, AttributeError):
        await message.reply_text(
            "⚠️ The script is not accepting input."
        )

    except Exception as exc:
        logger.exception("Could not send script input")

        await message.reply_text(
            f"❌ Could not send input: {exc}"
        )


# ============================================================
# APPLICATION STARTUP
# ============================================================


def main():
    threading.Thread(
        target=run_web_server,
        daemon=True,
        name="flask-health-server",
    ).start()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("healthcheck", healthcheck))
    application.add_handler(CommandHandler("run", run_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            handle_document,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    logger.info("Starting Telegram bot...")
    application.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
