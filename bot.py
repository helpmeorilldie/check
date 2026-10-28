import os
import sys
import asyncio
from pathlib import Path
from collections import deque

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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

SCRIPT_DIR = Path("uploaded_scripts").resolve()
SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 100 * 1024
LOG_INTERVAL = 10

# Runtime state
awaiting_upload = set()
process = None
current_script = None
log_buffer = deque(maxlen=200)
log_task = None
process_lock = asyncio.Lock()


# ==========================================
# ACCESS CONTROL
# ==========================================

def is_admin(update: Update) -> bool:
    return (
        update.effective_user is not None
        and update.effective_user.id == ADMIN_ID
        and ADMIN_ID != 0
    )


async def deny_access(update: Update):
    if update.effective_message:
        await update.effective_message.reply_text(
            "⛔ You are not authorized to use this bot."
        )


# ==========================================
# COMMANDS
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
        "/run - Upload a Python script\n"
        "/logs - View recent output\n"
        "/stop - Stop the running script\n"
        "/cancel - Cancel an upload\n\n"
        "Send /run, then upload your .py file."
    )


async def run_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny_access(update)
        return

    awaiting_upload.add(update.effective_user.id)

    await update.effective_message.reply_text(
        "📂 Upload your Python file now.\n\n"
        "Only .py files are accepted.\n"
        "Maximum file size: 100 KB.\n\n"
        "⚠️ Only upload scripts you trust."
    )


async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny_access(update)
        return

    awaiting_upload.discard(update.effective_user.id)

    await update.effective_message.reply_text(
        "Upload cancelled."
    )


# ==========================================
# FILE UPLOAD
# ==========================================

async def receive_file(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    global process

    if not is_admin(update):
        await deny_access(update)
        return

    user_id = update.effective_user.id

    if user_id not in awaiting_upload:
        await update.effective_message.reply_text(
            "Send /run first, then upload your .py file."
        )
        return

    document = update.effective_message.document

    if not document:
        return

    filename = document.file_name or ""

    if not filename.lower().endswith(".py"):
        await update.effective_message.reply_text(
            "❌ Please upload a Python (.py) file."
        )
        return

    if document.file_size > MAX_FILE_SIZE:
        await update.effective_message.reply_text(
            "❌ File too large. Maximum size is 100 KB."
        )
        return

    # Use a generated filename instead of trusting the uploaded path.
    safe_name = Path(filename).name

    if safe_name in ("", ".", ".."):
        await update.effective_message.reply_text(
            "Invalid filename."
        )
        return

    async with process_lock:
        if process is not None and process.returncode is None:
            await update.effective_message.reply_text(
                "⚠️ A script is already running. Use /stop first."
            )
            return

        destination = SCRIPT_DIR / safe_name

        try:
            telegram_file = await document.get_file()
            await telegram_file.download_to_drive(
                custom_path=str(destination)
            )
        except Exception as exc:
            await update.effective_message.reply_text(
                f"❌ Upload failed: {exc}"
            )
            return

        awaiting_upload.discard(user_id)

        await update.effective_message.reply_text(
            f"✅ File received: {safe_name}\n"
            "📂 Saved successfully.\n"
            "▶️ Starting script..."
        )

        await start_script(
            update,
            context,
            destination,
        )


# ==========================================
# SCRIPT EXECUTION
# ==========================================

async def start_script(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    script_path: Path,
):
    global process, current_script, log_task

    if process is not None and process.returncode is None:
        await update.effective_message.reply_text(
            "A script is already running."
        )
        return

    log_buffer.clear()
    current_script = script_path.name

    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            str(script_path),
            cwd=str(SCRIPT_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except Exception as exc:
        process = None
        await update.effective_message.reply_text(
            f"❌ Could not start script: {exc}"
        )
        return

    log_buffer.append(
        f"Started {current_script}\n"
        f"Process ID: {process.pid}\n"
    )

    log_task = asyncio.create_task(
        collect_output(process)
    )

    context.application.create_task(
        send_periodic_logs(
            context.application,
            update.effective_chat.id,
            process,
        )
    )


async def collect_output(child):
    """Read output continuously to prevent the pipe from filling."""
    try:
        while True:
            line = await child.stdout.readline()

            if not line:
                break

            text = line.decode(
                "utf-8",
                errors="replace",
            ).rstrip()

            if text:
                log_buffer.append(text)

    except Exception as exc:
        log_buffer.append(f"Log reader error: {exc}")


async def send_periodic_logs(
    application,
    chat_id: int,
    child,
):
    """Send accumulated output every 10 seconds."""
    while child.returncode is None:
        await asyncio.sleep(LOG_INTERVAL)

        if log_buffer:
            output = "\n".join(log_buffer)
            output = output[-3500:]

            try:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=f"📋 Logs — {current_script}\n\n{output}",
                )
            except Exception:
                pass

        if child.returncode is None:
            # Refresh the return code after each interval.
            await child.wait()

    if log_buffer:
        output = "\n".join(log_buffer)[-3500:]
    else:
        output = "(No output produced.)"

    try:
        await application.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🏁 Script finished: {current_script}\n"
                f"Exit code: {child.returncode}\n\n"
                f"📋 Final output:\n{output}"
            ),
        )
    except Exception:
        pass


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
            "No script logs available yet."
        )
        return

    output = "\n".join(log_buffer)[-3500:]

    await update.effective_message.reply_text(
        f"📋 Recent logs\n\n{output}"
    )


# ==========================================
# STOP SCRIPT
# ==========================================

async def stop_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    global process

    if not is_admin(update):
        await deny_access(update)
        return

    child = process

    if child is None or child.returncode is not None:
        await update.effective_message.reply_text(
            "No script is currently running."
        )
        return

    child.terminate()

    try:
        await asyncio.wait_for(
            child.wait(),
            timeout=5,
        )
    except asyncio.TimeoutError:
        child.kill()
        await child.wait()

    await update.effective_message.reply_text(
        "🛑 Stop signal sent. The script has stopped."
    )


# ==========================================
# ERROR HANDLER
# ==========================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    print(f"Telegram bot error: {context.error}")


# ==========================================
# MAIN
# ==========================================

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "Set the BOT_TOKEN environment variable."
        )

    if ADMIN_ID == 0:
        raise RuntimeError(
            "Set ADMIN_ID to your Telegram numeric user ID."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("logs", logs_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    app.add_handler(
        MessageHandler(
            filters.Document.ALL,
            receive_file,
        )
    )

    app.add_error_handler(error_handler)

    print("Python Script Manager is running.")
    app.run_polling()


if __name__ == "__main__":
    main()

