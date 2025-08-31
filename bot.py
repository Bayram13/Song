import os import tempfile from typing import List

from yt_dlp import YoutubeDL from mutagen.mp3 import MP3 from mutagen.id3 import ID3, APIC, error from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

====== Environment (Render Secrets) ======

BOT_TOKEN = os.getenv("BOT_TOKEN")                    # @BotFather token COOKIES_TEXT = os.getenv("COOKIES", "")              # Paste Netscape cookie text into Render secret

Optional: stable ffmpeg path via imageio-ffmpeg (bundled binary)

try: import imageio_ffmpeg FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe() except Exception: FFMPEG_PATH = None

====== Helpers ======

def _write_cookies_to_temp() -> str | None: """Write cookies from env to a temp file and return its path.""" if not COOKIES_TEXT: return None tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt") tmp.write(COOKIES_TEXT.encode()) tmp.close() return tmp.name

def _ydl_opts(output_tmpl: str = "%(title)s.%(ext)s", cookiefile: str | None = None): opts = { 'format': 'bestaudio/best', 'noplaylist': True, 'default_search': 'ytsearch10',  # fetch up to 10 entries for selection 'outtmpl': output_tmpl, 'quiet': True, 'postprocessors': [ { 'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320', } ] } if cookiefile: opts['cookiefile'] = cookiefile if FFMPEG_PATH: opts['ffmpeg_location'] = FFMPEG_PATH return opts

async def _send_search_menu(update: Update, results: List[dict]): """Send a numbered list (1..10) and inline keyboard to pick.""" lines = ["🔎 Search results:"] for i, it in enumerate(results, start=1): title = it.get('title') or 'Unknown title' uploader = it.get('uploader') if uploader: line = f"{i}. {title} — {uploader}" else: line = f"{i}. {title}" lines.append(line)

keyboard = [
    [InlineKeyboardButton(str(i), callback_data=f"pick:{i-1}") for i in range(1, 6)],
    [InlineKeyboardButton(str(i), callback_data=f"pick:{i-1}") for i in range(6, 11)],
    [
        InlineKeyboardButton("↻ Refresh", callback_data="refresh"),
        InlineKeyboardButton("✖ Cancel", callback_data="cancel"),
    ]
]
text = "\n".join(lines)
await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

====== Handlers ======

async def song_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE): if not context.args: await update.message.reply_text("İstifadə: /song Mahnı adı — məsələn: /song Röya Bahar") return

query = " ".join(context.args)
await update.message.reply_text(f"🔍 Axtarıram: {query}")

cookiefile = _write_cookies_to_temp()

try:
    with YoutubeDL(_ydl_opts(cookiefile=cookiefile)) as ydl:
        info = ydl.extract_info(query, download=False)  # only search, do not download yet

    # info may be a playlist-style dict with 'entries'
    entries = info.get('entries') if isinstance(info, dict) else None
    if not entries:
        await update.message.reply_text("Heç nə tapılmadı 😕")
        return

    # Save results in user_data for selection step
    context.user_data['search_results'] = entries[:10]
    context.user_data['query'] = query

    await _send_search_menu(update, context.user_data['search_results'])

except Exception as e:
    await update.message.reply_text(f"❌ Axtarışda xəta: {e}")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer()

data = query.data
if data == 'cancel':
    await query.edit_message_text("❌ Ləğv edildi")
    context.user_data.pop('search_results', None)
    return

if data == 'refresh':
    # Re-run search using the saved query
    saved_q = context.user_data.get('query')
    if not saved_q:
        await query.edit_message_text("Yeniləmək üçün sorğu yoxdur")
        return
    cookiefile = _write_cookies_to_temp()
    try:
        with YoutubeDL(_ydl_opts(cookiefile=cookiefile)) as ydl:
            info = ydl.extract_info(saved_q, download=False)
        entries = info.get('entries') if isinstance(info, dict) else None
        if not entries:
            await query.edit_message_text("Heç nə tapılmadı 😕")
            return
        context.user_data['search_results'] = entries[:10]
        # Replace message content
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.delete()
        await _send_search_menu(update, context.user_data['search_results'])
    except Exception as e:
        await query.edit_message_text(f"❌ Yeniləmədə xəta: {e}")
    return

if data.startswith('pick:'):
    idx = int(data.split(':')[1])
    results = context.user_data.get('search_results') or []
    if idx < 0 or idx >= len(results):
        await query.edit_message_text("Seçim etibarsızdır")
        return

    item = results[idx]
    video_url = item.get('webpage_url') or item.get('url')
    title = item.get('title', 'Audio')
    await query.edit_message_text(f"⬇️ Yüklənir: {title}")

    # Prepare cookie & download options
    cookiefile = _write_cookies_to_temp()
    safe_template = "%(title)s.%(ext)s"  # yt-dlp will sanitize filename
    opts = _ydl_opts(output_tmpl=safe_template, cookiefile=cookiefile)

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            # Ensure we know the produced filename (mp3 after postprocess)
            # prepare_filename gives pre-pp filename; replace ext with mp3
            base = ydl.prepare_filename(info)
            mp3_path = os.path.splitext(base)[0] + ".mp3"

        # Embed cover art if possible
        thumb_url = (info.get('thumbnail') or item.get('thumbnail'))
        cover_path = None
        if thumb_url:
            # download thumbnail
            cover_path = os.path.join(tempfile.gettempdir(), "cover.jpg")
            os.system(f"wget -q -O '{cover_path}' '{thumb_url}'")

        try:
            audio = MP3(mp3_path, ID3=ID3)
            try:
                audio.add_tags()
            except error:
                pass
            if cover_path and os.path.exists(cover_path):
                with open(cover_path, 'rb') as imgf:
                    audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=imgf.read()))
            audio.save()
        except Exception:
            # If tagging fails, continue anyway
            pass

        # Send audio
        await query.message.reply_audio(
            audio=open(mp3_path, 'rb'),
            title=info.get('title') or title,
            performer=info.get('uploader') or item.get('uploader')
        )

    except Exception as e:
        await query.message.reply_text(f"❌ Yükləmədə xəta: {e}")
    finally:
        # Cleanup
        try:
            if 'mp3_path' in locals() and os.path.exists(mp3_path):
                os.remove(mp3_path)
        except Exception:
            pass
        try:
            if 'cover_path' in locals() and cover_path and os.path.exists(cover_path):
                os.remove(cover_path)
        except Exception:
            pass

def main(): app = Application.builder().token(BOT_TOKEN).build() app.add_handler(CommandHandler('song', song_cmd)) app.add_handler(CallbackQueryHandler(callback_handler)) app.run_polling()

if name == 'main': main()

