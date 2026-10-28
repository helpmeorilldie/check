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

# ==========================================
# RUNTIME STATE
# ==========================================

process = None
current_script = None
current_chat_id = None

awaiting_upload = set()
log_buffer = deque(maxlen=200)
log_task = None
process_lock = asyncio.Lock()


# ==========================================
# ADMIN ACCESS
# ==========================================

def is_admin(update: Update) -> bool:
    return (
        update.effective_user is not None
        and ADMIN_ID != 0
        and update.effective_user.id == ADMIN_ID
    )


async def deny_access(update: Update):
    if update.effective_message:
        await update.effective_message.reply_text(
            "⛔ You are not authorized to use this bot."
        )


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
        "/run - Upload a Python script\n"
        "/logs - View recent logs\n"
        "/stop - Stop the running script\n"
        "/cancel - Cancel upload mode\n\n"
        "Interactive input:\n"
        "When a script is running, send a normal text "
        "message to provide input to that script.\n\n"
        "Logs are sent approximately every 10 seconds."
    )


# ==========================================
# RUN COMMAND
# ==========================================

async def run_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny_access(update)
        return

    if process is not None and process.returncode is None:
        await update.effective_message.reply_text(
            "⚠️ A script is already running. Use /stop first."
        )
        return

    awaiting_upload.add(update.effective_user.id)

    await update.effective_message.reply_text(
        "📂 Send your Python file now.\n\n"
        "Only .py files are accepted.\n"
        "Maximum size: 100 KB.\n\n"
        "Only upload scripts you trust."
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
        "Upload mode cancelled."
    )


# ==========================================
# RECEIVE PYTHON FILE
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

    if document is None:
        return

    filename = document.file_name or ""

    if not filename.lower().endswith(".py"):
        await update.effective_message.reply_text(
            "❌ Please upload a .py file."
        )
        return

    if document.file_size > MAX_FILE_SIZE:
        await update.effective_message.reply_text(
            "❌ File too large. Maximum size is 100 KB."
        )
        return

    safe_name = Path(filename).name

    if safe_name in ("", ".", ".."):
        await update.effective_message.reply_text(
            "❌ Invalid filename."
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
            f"✅ Uploaded: {safe_name}\n"
            "▶️ Starting script..."
        )

        await start_script(
            update,
            context,
            destination,
        )


# ==========================================
# START SCRIPT
# ==========================================

async def start_script(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    script_path: Path,
):
    global process
    global current_script
    global current_chat_id
    global log_task

    if process is not None and process.returncode is None:
        await update.effective_message.reply_text(
            "A script is already running."
        )
        return

    log_buffer.clear()
    current_script = script_path.name
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

    except Exception as exc:
        process = None

        await update.effective_message.reply_text(
            f"❌ Could not start script:\n{exc}"
        )
        return

    log_buffer.append(
        f"Started: {current_script}\n"
        f"PID: {process.pid}\n"
        f"Python: {sys.version.split()[0]}\n"
    )

    await update.effective_message.reply_text(
        f"🚀 Running: {current_script}\n\n"
        "📋 Logs will arrive approximately every 10 seconds.\n"
        "⌨️ Send a normal text message to provide input.\n"
        "🛑 Use /stop to terminate the script."
    )

    # Read output continuously.
    context.application.create_task(
        collect_output(process)
    )

    # Send periodic log updates.
    log_task = context.application.create_task(
        send_periodic_logs(
            context.application,
            current_chat_id,
            process,
        )
    )


# ==========================================
# COLLECT SCRIPT OUTPUT
# ==========================================

async def collect_output(child):
    try:
        while True:
            chunk = await child.stdout.read(1024)

            if not chunk:
                break

            text = chunk.decode(
                "utf-8",
                errors="replace",
            )

            if text:
                log_buffer.append(text)

    except Exception as exc:
        log_buffer.append(
            f"\n[Output reader error: {exc}]\n"
        )


# ==========================================
# SEND LOGS EVERY 10 SECONDS
# ==========================================

async def send_periodic_logs(
    application,
    chat_id,
    child,
):
    global process

    while child.returncode is None:
        await asyncio.sleep(LOG_INTERVAL)

        if log_buffer:
            output = "".join(log_buffer)[-3500:]

            try:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"📋 Logs — {current_script}\n\n"
                        f"{output}"
                    ),
                )

            except Exception as exc:
                print(f"Telegram log error: {exc}")

        # Refresh return code without blocking for process exit.
        if child.returncode is not None:
            break

    # Wait for the process and output reader to finish.
    await child.wait()

    if log_buffer:
        final_output = "".join(log_buffer)[-3500:]
    else:
        final_output = "(No output produced.)"

    try:
        await application.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🏁 Script finished: {current_script}\n"
                f"Exit code: {child.returncode}\n\n"
                f"📋 Final output:\n{final_output}"
            ),
        )

    except Exception as exc:
        print(f"Telegram final-log error: {exc}")

    process = None


# ==========================================
# SEND INPUT TO RUNNING SCRIPT
# ==========================================

async def provide_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        return

    global process

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
        child.stdin.write(
            (text + "\n").encode("utf-8")
        )

        await child.stdin.drain()

        await update.effective_message.reply_text(
            "⌨️ Input sent to the running script."
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
            "No logs available."
        )
        return

    output = "".join(log_buffer)[-3500:]

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

    try:
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
            "🛑 Script stopped."
        )

    except ProcessLookupError:
        await update.effective_message.reply_text(
            "The script has already stopped."
        )


# ==========================================
# ERROR HANDLER
# ==========================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    print(f"Bot error: {context.error}")


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
