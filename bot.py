import os
import yt_dlp

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8602338004:AAGcoLuP24X_IyFeh2bXkcBEjIQlnoqD9vg"

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text

    await update.message.reply_text("⏳ درحال دانلود...")

    filename = os.path.join(DOWNLOAD_FOLDER, "%(id)s.%(ext)s")

    ydl_opts = {
        "outtmpl": filename,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            file = ydl.prepare_filename(info)

            if not os.path.exists(file):
                base = os.path.splitext(file)[0]
                if os.path.exists(base + ".mp4"):
                    file = base + ".mp4"

        with open(file, "rb") as video:
            await update.message.reply_video(
                video=video,
                caption="✅ دانلود شد."
            )

        os.remove(file)

    except Exception as e:
        await update.message.reply_text(f"❌ خطا:\n{e}")


app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, download)
)

print("Bot Started...")
app.run_polling()
