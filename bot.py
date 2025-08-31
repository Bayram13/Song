import os
import subprocess
from yt_dlp import YoutubeDL
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")  # Render-də secret kimi saxlanılacaq

async def song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("İstifadə: /song Mahnı adı")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🔎 Axtarıram: {query}")

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'default_search': 'ytsearch1',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }
        ]
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            title = info['title']
            filename = f"{title}.mp3"
            thumbnail_url = info.get('thumbnail')

        # Thumbnail yüklə
        thumb_file = "cover.jpg"
        if thumbnail_url:
            os.system(f"wget -O '{thumb_file}' '{thumbnail_url}'")

        # MP3-ə cover əlavə et
        audio = MP3(filename, ID3=ID3)
        try:
            audio.add_tags()
        except error:
            pass

        if os.path.exists(thumb_file):
            with open(thumb_file, 'rb') as img:
                audio.tags.add(APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=img.read()
                ))
            audio.save()

        # Cavab olaraq göndər
        await update.message.reply_audio(
            audio=open(filename, "rb"),
            title=title,
            thumb=open(thumb_file, "rb") if os.path.exists(thumb_file) else None
        )

        # Faylları sil
        os.remove(filename)
        if os.path.exists(thumb_file):
            os.remove(thumb_file)

    except Exception as e:
        await update.message.reply_text(f"❌ Xəta baş verdi: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("song", song))
    app.run_polling()

if __name__ == "__main__":
    main()
