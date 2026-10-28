import os
import time
import asyncio
import subprocess
from pathlib import Path

import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

SCRIPT_DIR = Path("approved_scripts").resolve()
SCRIPT_DIR.mkdir(exist_ok=True)

process = None
log_file = None
last_position = 0


def is_admin(update):
    return (
        update.effective_user is not None
        and update.effective_user.id == ADMIN_ID
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    await update.message.reply_text(
        "Python Script Manager\n\n"
        "/run filename.py - Run an approved script\n"
        "/logs - View recent logs\n"
        "/stop - Stop the running script"
    )


async def run_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global process, log_file, last_position

    if not is_admin(update):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /run filename.py"
        )
        return

    filename = context.args[0]

    # Only allow a filename, not an arbitrary filesystem path.
    if (
        Path(filename).name != filename
        or not filename.endswith(".py")
    ):
        await update.message.reply_text("Invalid filename.")
        return

    script_path = (SCRIPT_DIR / filename).resolve()

    if script_path.parent != SCRIPT_DIR or not script_path.is_file():
        await update.message.reply_text(
            "That script is not in the approved_scripts folder."
        )
        return

    if process is not None and process.poll() is None:
        await update.message.reply_text(
            "A script is already running. Use /stop first."
        )
        return

    log_path = SCRIPT_DIR / "latest.log"
    log_file = open(log_path, "w", encoding="utf-8")
    last_position = 0

    process = subprocess.Popen(
        ["python3", "-u", str(script_path)],
        cwd=str(SCRIPT_DIR),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        shell=False,
    )

    context.application.create_task(
        send_logs_periodically(
            context.application,
            update.effective_chat.id,
            process,
            log_path,
        )
    )

    await update.message.reply_text(
        f"Started {filename}.\n"
        "Logs will be sent every 10 seconds."
    )


async def send_logs_periodically(app, chat_id, child, log_path):
    global last_position, log_file

    while child.poll() is None:
        await asyncio.sleep(10)

        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(last_position)
                output = f.read()
                last_position = f.tell()

            if output.strip():
                # Telegram messages have a size limit.
                output = output[-3500:]
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=f"Latest logs:\n\n{output}",
                )
        except Exception:
            pass

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            output = f.read()[-3500:]

        await app.bot.send_message(
            chat_id=chat_id,
            text=(
                f"Script finished. Exit code: {child.returncode}\n\n"
                f"Final logs:\n{output or '(no output)'}"
            ),
        )
    except Exception:
        pass

    if log_file:
        log_file.close()
        log_file = None


async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    log_path = SCRIPT_DIR / "latest.log"

    if not log_path.exists():
        await update.message.reply_text("No logs found.")
        return

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        output = f.read()[-3500:]

    await update.message.reply_text(output or "The log is empty.")


async def stop_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global process

    if not is_admin(update):
        return

    if process is not None and process.poll() is None:
        process.terminate()
        await update.message.reply_text("Stop signal sent.")
    else:
        await update.message.reply_text("No script is currently running.")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("run", run_script))
    app.add_handler(CommandHandler("logs", logs))
    app.add_handler(CommandHandler("stop", stop_script))

    app.run_polling()


if __name__ == "__main__":
    main()
