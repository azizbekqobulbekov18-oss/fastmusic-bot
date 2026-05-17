# Telegram Music & Video Downloader Bot

A Telegram bot that downloads videos and audio from YouTube, Instagram, and TikTok, with multilingual support (Uzbek, Russian, English).

## Run & Operate

- `python artifacts/tg-bot/bot.py` — run the Telegram bot
- Required env: `TELEGRAM_BOT_TOKEN` — Telegram bot token

## Stack

- Python 3.11
- python-telegram-bot 22.x
- yt-dlp for downloading
- ffmpeg for audio conversion (MP3)

## Where things live

- `artifacts/tg-bot/bot.py` — main bot file (all logic in one file)
- `/tmp/tgbot_downloads/` — temporary download directory (per user subfolder)

## Architecture decisions

- In-memory stats and pending URL state (resets on restart) — simple approach for a single-instance bot
- Files downloaded to /tmp and streamed to Telegram, then deleted immediately to save disk space
- Max 50 MB file size limit (Telegram Bot API limit)
- Per-user language preference stored in memory dict

## Product

Users send a YouTube, Instagram, or TikTok link. The bot asks them to choose MP4 (video) or MP3 (audio). It downloads and sends the file directly in the chat. Supports /start, /help, /stats, /lang commands.

## User preferences

- Bot token stored as `TELEGRAM_BOT_TOKEN` environment variable

## Gotchas

- Telegram Bot API hard limit is 50 MB for file uploads
- yt-dlp format strings differ between platforms; `best[filesize<50M]` is used as a guard for MP4
- ffmpeg must be installed for MP3 extraction to work

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
