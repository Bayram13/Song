import os
import tempfile
from yt_dlp import YoutubeDL
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")          # Render secret-dən alınacaq
COOKIES = os.getenv("COOKIES", None)    # Cookie-ləri secret olaraq saxlayacağıq

async def song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("İstifadə: /song Mahnı adı")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🔎 Axtarıram: {query}")

    # Cookie faylını müvəqqəti yarat
    cookie_file_path = None
    if COOKIES:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        tmp.write(COOKIES.encode())
        tmp.close()
        cookie_file_path = tmp.name

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'default_search': 'ytsearch1',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'cookiefile': cookie_file_path if cookie_file_path else None,
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

        # Faylları təmizlə
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
    main()            title = info['title']
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
