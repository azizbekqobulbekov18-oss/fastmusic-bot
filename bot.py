import os
import logging
import asyncio
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import yt_dlp

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

_admin_env = os.environ.get("ADMIN_IDS", "123456789")
ADMIN_IDS: set[int] = {int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()}

# ─── Translations ────────────────────────────────────────────────────────────

TEXTS = {
    "uz": {
        "start": (
            "🎵 <b>Musiqa Bot</b>ga xush kelibsiz!\n\n"
            "• Qo'shiq nomi yuboring → qidiruv natijalari\n"
            "• YouTube/Instagram/TikTok havolasi yuboring → video yoki audio\n\n"
            "📌 Buyruqlar:\n"
            "/search [so'z] — Qidirish\n"
            "/help — Yordam\n"
            "/lang — Tilni o'zgartirish"
        ),
        "help": (
            "ℹ️ <b>Yordam</b>\n\n"
            "🎵 <b>Musiqa qidirish:</b>\n"
            "Istalgan qo'shiq nomini yozing — bot 5 ta natija ko'rsatadi.\n"
            "Bitta tugmani bosing va MP3 yuklab olinadi.\n\n"
            "🔗 <b>Havola yuborish:</b>\n"
            "YouTube, Instagram yoki TikTok havolasini yuboring.\n"
            "Video yoki audio formatini tanlang.\n\n"
            "⚠️ 50 MB dan katta fayllar yuklanmaydi."
        ),
        "choose_format": "📥 Formatni tanlang:",
        "downloading_audio": "⏳ Musiqa yuklanmoqda...",
        "downloading_video": "⏳ Video yuklanmoqda...",
        "error": "❌ Xatolik: {}",
        "too_large": "❌ Fayl juda katta (50 MB+). Boshqa formatni sinab ko'ring.",
        "stats": "📊 <b>Statistika</b>\n\nJami: <b>{total}</b>  •  Video: <b>{mp4}</b>  •  Audio: <b>{mp3}</b>",
        "lang_chosen": "✅ Til: O'zbek",
        "choose_lang": "🌐 Tilni tanlang:",
        "banned": "🚫 Siz botdan foydalana olmaysiz.",
        "maintenance": "🔧 Bot texnik ishlar uchun vaqtincha o'chirilgan.",
        "no_access": "⛔ Sizda bu buyruqni bajarish huquqi yo'q.",
        "searching": "🔍 Qidirilmoqda...",
        "no_results": "❌ Hech narsa topilmadi. Boshqa so'z bilan sinab ko'ring.",
        "search_header": "🎵 <b>Qidiruv:</b> {query}\n\n",
        "search_entry": "{n}. <b>{title}</b>\n    👤 {artist}  •  ⏱ {duration}\n",
        "expired": "⚠️ Natija eskirdi. Qayta qidiring.",
    },
    "ru": {
        "start": (
            "🎵 Добро пожаловать в <b>Music Bot</b>!\n\n"
            "• Отправьте название песни → результаты поиска\n"
            "• Отправьте ссылку YouTube/Instagram/TikTok → видео или аудио\n\n"
            "📌 Команды:\n"
            "/search [запрос] — Поиск\n"
            "/help — Справка\n"
            "/lang — Сменить язык"
        ),
        "help": (
            "ℹ️ <b>Справка</b>\n\n"
            "🎵 <b>Поиск музыки:</b>\n"
            "Напишите название песни — бот покажет 5 результатов.\n"
            "Нажмите одну кнопку и MP3 скачается.\n\n"
            "🔗 <b>Отправить ссылку:</b>\n"
            "Отправьте ссылку YouTube, Instagram или TikTok.\n"
            "Выберите видео или аудио формат.\n\n"
            "⚠️ Файлы больше 50 МБ не загружаются."
        ),
        "choose_format": "📥 Выберите формат:",
        "downloading_audio": "⏳ Загружаю музыку...",
        "downloading_video": "⏳ Загружаю видео...",
        "error": "❌ Ошибка: {}",
        "too_large": "❌ Файл слишком большой (50 МБ+). Попробуйте другой формат.",
        "stats": "📊 <b>Статистика</b>\n\nВсего: <b>{total}</b>  •  Видео: <b>{mp4}</b>  •  Аудио: <b>{mp3}</b>",
        "lang_chosen": "✅ Язык: Русский",
        "choose_lang": "🌐 Выберите язык:",
        "banned": "🚫 Вы заблокированы.",
        "maintenance": "🔧 Бот временно отключён на техническое обслуживание.",
        "no_access": "⛔ У вас нет прав для этой команды.",
        "searching": "🔍 Ищу...",
        "no_results": "❌ Ничего не найдено. Попробуйте другой запрос.",
        "search_header": "🎵 <b>Поиск:</b> {query}\n\n",
        "search_entry": "{n}. <b>{title}</b>\n    👤 {artist}  •  ⏱ {duration}\n",
        "expired": "⚠️ Результат устарел. Выполните поиск заново.",
    },
    "en": {
        "start": (
            "🎵 Welcome to <b>Music Bot</b>!\n\n"
            "• Send a song name → search results\n"
            "• Send a YouTube/Instagram/TikTok link → video or audio\n\n"
            "📌 Commands:\n"
            "/search [query] — Search\n"
            "/help — Help\n"
            "/lang — Change language"
        ),
        "help": (
            "ℹ️ <b>Help</b>\n\n"
            "🎵 <b>Music search:</b>\n"
            "Type any song name — the bot shows 5 results.\n"
            "Tap a button and the MP3 is downloaded instantly.\n\n"
            "🔗 <b>Send a link:</b>\n"
            "Send a YouTube, Instagram or TikTok URL.\n"
            "Choose video or audio format.\n\n"
            "⚠️ Files over 50 MB cannot be sent."
        ),
        "choose_format": "📥 Choose format:",
        "downloading_audio": "⏳ Downloading audio...",
        "downloading_video": "⏳ Downloading video...",
        "error": "❌ Error: {}",
        "too_large": "❌ File too large (50 MB+). Try a different format.",
        "stats": "📊 <b>Stats</b>\n\nTotal: <b>{total}</b>  •  Video: <b>{mp4}</b>  •  Audio: <b>{mp3}</b>",
        "lang_chosen": "✅ Language: English",
        "choose_lang": "🌐 Choose language:",
        "banned": "🚫 You are banned from using this bot.",
        "maintenance": "🔧 The bot is under maintenance. Try again later.",
        "no_access": "⛔ You don't have permission to use this command.",
        "searching": "🔍 Searching...",
        "no_results": "❌ No results found. Try a different query.",
        "search_header": "🎵 <b>Search:</b> {query}\n\n",
        "search_entry": "{n}. <b>{title}</b>\n    👤 {artist}  •  ⏱ {duration}\n",
        "expired": "⚠️ Result expired. Please search again.",
    },
}

SUPPORTED_DOMAINS = re.compile(
    r"(youtube\.com|youtu\.be|instagram\.com|tiktok\.com|vm\.tiktok\.com)",
    re.IGNORECASE,
)

# ─── State ───────────────────────────────────────────────────────────────────

user_langs: dict[int, str] = {}
stats = {"total": 0, "mp4": 0, "mp3": 0}
pending_urls: dict[int, str] = {}
registered_users: dict[int, dict] = {}
banned_users: set[int] = set()
bot_enabled: bool = True
awaiting_broadcast: set[int] = set()

# user_id -> list of {title, artist, duration, duration_sec, url}
search_cache: dict[int, list[dict]] = {}

DOWNLOAD_DIR = Path("/tmp/tgbot_downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_lang(uid: int) -> str:
    return user_langs.get(uid, "en")


def t(uid: int, key: str) -> str:
    return TEXTS[get_lang(uid)][key]


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


def is_url(text: str) -> bool:
    return bool(SUPPORTED_DOMAINS.search(text))


def fmt_duration(secs: int) -> str:
    m, s = divmod(secs, 60)
    return f"{m}:{s:02d}"


def register_user(user) -> None:
    if user.id not in registered_users:
        registered_users[user.id] = {
            "username": user.username or user.first_name or str(user.id),
            "joined": datetime.now(),
        }
    elif user.username:
        registered_users[user.id]["username"] = user.username or user.first_name or str(user.id)


def check_access(uid: int) -> str | None:
    if uid in banned_users:
        return "banned"
    if not bot_enabled and not is_admin(uid):
        return "maintenance"
    return None


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


# ─── YouTube search ──────────────────────────────────────────────────────────

def yt_search(query: str, count: int = 50) -> list[dict]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
    results = []
    for e in (info.get("entries") or []):
        dur = int(e.get("duration") or 0)
        artist = e.get("channel") or e.get("uploader") or "Unknown"
        results.append({
            "title": e.get("title", "Unknown"),
            "artist": artist,
            "duration": fmt_duration(dur) if dur else "?",
            "duration_sec": dur,
            "url": e.get("url") or e.get("webpage_url", ""),
        })
    return results


# ─── Download: audio with metadata + thumbnail ───────────────────────────────

def download_audio(url: str, uid: int) -> tuple[str, str | None, str, str, int]:
    """Returns (mp3_path, thumb_path_or_None, title, artist, duration_sec)."""
    out_dir = DOWNLOAD_DIR / str(uid)
    out_dir.mkdir(exist_ok=True)

    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(out_dir / "%(title)s.%(ext)s"),
        "writethumbnail": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
            {"key": "FFmpegMetadata", "add_metadata": True},
            {"key": "EmbedThumbnail"},
        ],
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "Unknown")
        artist = info.get("channel") or info.get("uploader") or info.get("artist") or "Unknown"
        duration_sec = int(info.get("duration") or 0)
        base = Path(ydl.prepare_filename(info)).stem

    mp3_path: str | None = None
    for f in out_dir.iterdir():
        if f.suffix == ".mp3" and base in f.stem:
            mp3_path = str(f)
            break
    if not mp3_path:
        for f in out_dir.iterdir():
            if f.suffix == ".mp3":
                mp3_path = str(f)
                break

    if not mp3_path:
        raise FileNotFoundError("MP3 file not found after download")

    thumb_path: str | None = None
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        cand = out_dir / f"{base}{ext}"
        if cand.exists():
            thumb_path = str(cand)
            break
    if not thumb_path:
        for f in out_dir.iterdir():
            if f.suffix in (".jpg", ".jpeg", ".png", ".webp"):
                thumb_path = str(f)
                break

    return mp3_path, thumb_path, title, artist, duration_sec


# ─── Download: video ─────────────────────────────────────────────────────────

def download_video(url: str, uid: int) -> str:
    out_dir = DOWNLOAD_DIR / str(uid)
    out_dir.mkdir(exist_ok=True)

    opts = {
        "format": "best[filesize<50M]/best[height<=720]/best",
        "outtmpl": str(out_dir / "%(title)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    mp4 = Path(filename)
    if mp4.exists():
        return str(mp4)
    for f in out_dir.iterdir():
        if f.suffix in (".mp4", ".mkv", ".webm"):
            return str(f)
    raise FileNotFoundError("Video file not found after download")


# ─── Send helpers ─────────────────────────────────────────────────────────────

async def send_audio(message, uid: int, url: str, status_msg) -> None:
    out_dir = DOWNLOAD_DIR / str(uid)
    try:
        mp3_path, thumb_path, title, artist, dur = await asyncio.get_event_loop().run_in_executor(
            None, lambda: download_audio(url, uid)
        )

        if os.path.getsize(mp3_path) > 50 * 1024 * 1024:
            clean_dir(out_dir)
            await status_msg.edit_text(t(uid, "too_large"))
            return

        await status_msg.delete()

        thumb_file = open(thumb_path, "rb") if thumb_path else None
        with open(mp3_path, "rb") as audio_file:
            await message.reply_audio(
                audio=audio_file,
                title=title,
                performer=artist,
                duration=dur,
                thumbnail=thumb_file,
            )
        if thumb_file:
            thumb_file.close()

        stats["mp3"] += 1
        stats["total"] += 1
    except Exception as e:
        logger.exception("Audio download failed")
        await status_msg.edit_text(t(uid, "error").format(str(e)[:200]))
    finally:
        clean_dir(out_dir)


async def send_video(message, uid: int, url: str, status_msg) -> None:
    out_dir = DOWNLOAD_DIR / str(uid)
    try:
        video_path = await asyncio.get_event_loop().run_in_executor(
            None, lambda: download_video(url, uid)
        )

        if os.path.getsize(video_path) > 50 * 1024 * 1024:
            clean_dir(out_dir)
            await status_msg.edit_text(t(uid, "too_large"))
            return

        await status_msg.delete()

        with open(video_path, "rb") as f:
            await message.reply_video(video=f, supports_streaming=True)

        stats["mp4"] += 1
        stats["total"] += 1
    except Exception as e:
        logger.exception("Video download failed")
        await status_msg.edit_text(t(uid, "error").format(str(e)[:200]))
    finally:
        clean_dir(out_dir)


# ─── Search display ──────────────────────────────────────────────────────────

BATCH = 25  # results per message


def build_search_batch(results: list[dict], offset: int, header: str = "") -> tuple[str, InlineKeyboardMarkup]:
    chunk = results[offset:offset + BATCH]
    lines = [header] if header else []
    for i, r in enumerate(chunk):
        n = offset + i + 1
        title = r["title"][:45] + "…" if len(r["title"]) > 45 else r["title"]
        artist = r["artist"][:25] + "…" if len(r["artist"]) > 25 else r["artist"]
        lines.append(f"{n}. <b>{title}</b>\n    👤 {artist}  ⏱ {r['duration']}")
    text = "\n".join(lines)

    btns = [
        InlineKeyboardButton(f"🎵 {offset + i + 1}", callback_data=f"srch_{offset + i}")
        for i in range(len(chunk))
    ]
    rows = [btns[i:i + 5] for i in range(0, len(btns), 5)]
    return text, InlineKeyboardMarkup(rows)


async def run_search(uid: int, query: str, reply_to) -> None:
    status = await reply_to.reply_text(t(uid, "searching"))
    results = await asyncio.get_event_loop().run_in_executor(
        None, lambda: yt_search(query)
    )
    if not results:
        await status.edit_text(t(uid, "no_results"))
        return

    search_cache[uid] = results
    header = t(uid, "search_header").format(query=query).strip()

    # First batch (1-25) edits the "searching" status message
    text1, kb1 = build_search_batch(results, 0, header=header)
    await status.edit_text(text1, reply_markup=kb1, parse_mode="HTML")

    # Second batch (26-50) sent as a follow-up if there are more results
    if len(results) > BATCH:
        text2, kb2 = build_search_batch(results, BATCH)
        await reply_to.reply_html(text2, reply_markup=kb2)


# ─── User commands ────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    register_user(update.effective_user)
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return
    await update.message.reply_html(t(uid, "start"))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return
    await update.message.reply_html(t(uid, "help"))


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return
    await update.message.reply_html(t(uid, "stats").format(**stats))


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]])
    await update.message.reply_text(t(uid, "choose_lang"), reply_markup=kb)


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    register_user(update.effective_user)
    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return
    query = " ".join(context.args).strip() if context.args else ""
    if not query:
        await update.message.reply_text("Usage: /search <song name>")
        return
    await run_search(uid, query, update.message)


# ─── Admin commands ───────────────────────────────────────────────────────────

def build_admin_text() -> str:
    status = "🟢 Yoqilgan" if bot_enabled else "🔴 O'chirilgan"
    return (
        "🛡 <b>Admin Panel</b>\n\n"
        f"Holat: {status}\n"
        f"Foydalanuvchilar: <b>{len(registered_users)}</b>\n"
        f"Bloklangan: <b>{len(banned_users)}</b>\n"
        f"Yuklamalar: <b>{stats['total']}</b>  (🎬 {stats['mp4']}  🎵 {stats['mp3']})"
    )


def build_admin_kb() -> InlineKeyboardMarkup:
    toggle = (
        InlineKeyboardButton("✅ Bot yoqish", callback_data="admin_boton")
        if not bot_enabled
        else InlineKeyboardButton("🚫 Bot o'chirish", callback_data="admin_botoff")
    )
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users"),
            InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            toggle,
        ],
    ])


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(t(uid, "no_access"))
        return
    await update.message.reply_html(build_admin_text(), reply_markup=build_admin_kb())


async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(t(uid, "no_access"))
        return
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /ban [user_id]")
        return
    target = int(args[0])
    if target in ADMIN_IDS:
        await update.message.reply_text("⛔ Cannot ban an admin.")
        return
    banned_users.add(target)
    pending_urls.pop(target, None)
    name = registered_users.get(target, {}).get("username", str(target))
    await update.message.reply_html(f"🚫 <code>{target}</code> (@{name}) banned.")


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(t(uid, "no_access"))
        return
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /unban [user_id]")
        return
    target = int(args[0])
    if target in banned_users:
        banned_users.discard(target)
        name = registered_users.get(target, {}).get("username", str(target))
        await update.message.reply_html(f"✅ <code>{target}</code> (@{name}) unbanned.")
    else:
        await update.message.reply_text(f"ℹ️ User {target} is not banned.")


async def cmd_botoff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global bot_enabled
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(t(uid, "no_access"))
        return
    bot_enabled = False
    await update.message.reply_html("🔴 Bot <b>o'chirildi</b> (texnik ish rejimi).")


async def cmd_boton(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global bot_enabled
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(t(uid, "no_access"))
        return
    bot_enabled = True
    await update.message.reply_html("🟢 Bot <b>yoqildi</b>.")


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    if uid in awaiting_broadcast:
        awaiting_broadcast.discard(uid)
        await update.message.reply_text("❌ Broadcast bekor qilindi.")
    else:
        await update.message.reply_text("Bekor qilish uchun hech narsa yo'q.")


# ─── Message handler ──────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    register_user(update.effective_user)

    # Broadcast: admin is sending the message to forward
    if uid in awaiting_broadcast and is_admin(uid):
        awaiting_broadcast.discard(uid)
        if not registered_users:
            await update.message.reply_text("Foydalanuvchilar yo'q.")
            return
        ok, fail = 0, 0
        status = await update.message.reply_text(f"📢 {len(registered_users)} ta foydalanuvchiga yuborilmoqda...")
        for tid in list(registered_users):
            if tid in banned_users:
                continue
            try:
                await update.message.forward(chat_id=tid)
                ok += 1
                await asyncio.sleep(0.05)
            except Exception:
                fail += 1
        await status.edit_text(f"📢 Broadcast tugadi.\n✅ {ok}  ❌ {fail}")
        return

    if blk := check_access(uid):
        await update.message.reply_text(t(uid, blk))
        return

    text = (update.message.text or "").strip()

    # URL → ask format
    if is_url(text):
        pending_urls[uid] = text
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎬 Video", callback_data="fmt_mp4"),
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data="fmt_mp3"),
        ]])
        await update.message.reply_text(t(uid, "choose_format"), reply_markup=kb)
        return

    # Plain text → music search
    await run_search(uid, text, update.message)


# ─── Callback handler ─────────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    uid = query.from_user.id
    data = query.data

    # ── Language ──
    if data.startswith("lang_"):
        lang = data[5:]
        user_langs[uid] = lang
        await query.answer()
        await query.edit_message_text(t(uid, "lang_chosen"))
        return

    # ── Admin panel ──
    if data.startswith("admin_"):
        if not is_admin(uid):
            await query.answer("⛔ Access denied.", show_alert=True)
            return
        action = data[6:]
        await query.answer()

        if action == "users":
            if not registered_users:
                await query.message.reply_text("👥 Hali foydalanuvchilar yo'q.")
                return
            lines = [f"👥 <b>Foydalanuvchilar ({len(registered_users)} ta)</b>\n"]
            for uid2, info in registered_users.items():
                mark = " 🚫" if uid2 in banned_users else ""
                lines.append(
                    f"• <code>{uid2}</code> @{info['username']}{mark}"
                    f" — {info['joined'].strftime('%Y-%m-%d %H:%M')}"
                )
            txt = "\n".join(lines)
            for i in range(0, len(txt), 4000):
                await query.message.reply_html(txt[i:i + 4000])
            return

        if action == "stats":
            await query.message.reply_html(
                "📊 <b>Statistika</b>\n\n"
                f"Jami yuklamalar: <b>{stats['total']}</b>\n"
                f"🎬 Video: <b>{stats['mp4']}</b>\n"
                f"🎵 Audio: <b>{stats['mp3']}</b>\n"
                f"Foydalanuvchilar: <b>{len(registered_users)}</b>\n"
                f"Bloklangan: <b>{len(banned_users)}</b>"
            )
            return

        if action == "broadcast":
            awaiting_broadcast.add(uid)
            await query.message.reply_text(
                "📢 Barcha foydalanuvchilarga yuboriladigan xabarni yozing.\n\n"
                "Bekor qilish: /cancel"
            )
            return

        if action == "botoff":
            global bot_enabled
            bot_enabled = False
            await query.edit_message_text(build_admin_text(), reply_markup=build_admin_kb(), parse_mode="HTML")
            return

        if action == "boton":
            bot_enabled = True
            await query.edit_message_text(build_admin_text(), reply_markup=build_admin_kb(), parse_mode="HTML")
            return

        return

    # ── Search result: direct MP3 download ──
    if data.startswith("srch_"):
        if blk := check_access(uid):
            await query.answer(t(uid, blk), show_alert=True)
            return

        idx = int(data[5:])
        results = search_cache.get(uid, [])
        if idx >= len(results):
            await query.answer(t(uid, "expired"), show_alert=True)
            return

        url = results[idx]["url"]
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)
        status = await query.message.reply_text(t(uid, "downloading_audio"))
        await send_audio(query.message, uid, url, status)
        return

    # ── URL format choice ──
    if data.startswith("fmt_"):
        if blk := check_access(uid):
            await query.answer(t(uid, blk), show_alert=True)
            return

        fmt = data[4:]
        url = pending_urls.get(uid)
        if not url:
            await query.answer("No URL. Please send a link first.", show_alert=True)
            return

        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)

        if fmt == "mp3":
            status = await query.message.reply_text(t(uid, "downloading_audio"))
            await send_audio(query.message, uid, url, status)
        else:
            status = await query.message.reply_text(t(uid, "downloading_video"))
            await send_video(query.message, uid, url, status)

        pending_urls.pop(uid, None)
        return


# ─── Keep-alive web server ────────────────────────────────────────────────────

flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "OK", 200

@flask_app.route("/health")
def health_check():
    return {
        "status": "running",
        "users": len(registered_users),
        "downloads": stats["total"],
        "bot_enabled": bot_enabled,
    }, 200

def run_flask() -> None:
    flask_app.run(host="0.0.0.0", port=5000, use_reloader=False)


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set!")

    logger.info(f"Admin IDs: {ADMIN_IDS}")

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Keep-alive server started on port 5000")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("search", cmd_search))

    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("botoff", cmd_botoff))
    app.add_handler(CommandHandler("boton", cmd_boton))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
