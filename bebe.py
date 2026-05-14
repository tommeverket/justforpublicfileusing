# bot.py

import os
import uuid
import asyncio
import subprocess

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


async def convert_to_mp3(input_path: str, output_path: str):
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vn",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-b:a",
        "192k",
        output_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    await process.communicate()

    return process.returncode == 0


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    media = None
    extension = "mp4"

    if message.video:
        media = message.video
        extension = "mp4"

    elif message.audio:
        media = message.audio
        extension = "mp3"

    elif message.document:
        media = message.document

        filename = media.file_name.lower()

        if filename.endswith(".mp4"):
            extension = "mp4"
        elif filename.endswith(".mkv"):
            extension = "mkv"
        elif filename.endswith(".webm"):
            extension = "webm"
        elif filename.endswith(".mp3"):
            extension = "mp3"
        elif filename.endswith(".wav"):
            extension = "wav"
        else:
            await message.reply_text(
                "Неподдерживаемый формат файла."
            )
            return

    else:
        return

    if media.file_size > MAX_FILE_SIZE:
        await message.reply_text(
            "Файл слишком большой. Максимум: 50 MB."
        )
        return

    status = await message.reply_text(
        "⏳ Конвертирую файл..."
    )

    unique_id = str(uuid.uuid4())

    input_path = os.path.join(
        TEMP_DIR,
        f"{unique_id}.{extension}"
    )

    output_path = os.path.join(
        TEMP_DIR,
        f"{unique_id}.mp3"
    )

    try:
        telegram_file = await media.get_file()
        await telegram_file.download_to_drive(input_path)

        success = await convert_to_mp3(
            input_path,
            output_path
        )

        if not success or not os.path.exists(output_path):
            await status.edit_text(
                "❌ Ошибка конвертации."
            )
            return

        await message.reply_audio(
            audio=open(output_path, "rb"),
            title="converted.mp3"
        )

        await status.delete()

    except Exception as e:
        await status.edit_text(
            f"❌ Ошибка:\n{e}"
        )

    finally:
        for file_path in [input_path, output_path]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass


def main():
    if not TOKEN:
        raise Exception(
            "BOT_TOKEN не найден!"
        )

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.VIDEO |
            filters.AUDIO |
            filters.Document.ALL,
            handle_media
        )
    )

    print("Bot started.")

    app.run_polling()


if __name__ == "__main__":
    main()
