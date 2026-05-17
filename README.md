# FastMusic Bot

A Telegram music and video downloader bot.

## Features
- Search YouTube for songs (50 results with download buttons)
- Download MP3 (audio) from YouTube, Instagram, TikTok
- Download MP4 (video) from YouTube, Instagram, TikTok
- Multilingual: Uzbek, Russian, English
- Inline admin panel
- Flask keep-alive server for 24/7 uptime
- Automatic file cleanup (no storage used)

## Setup

### Requirements
Install dependencies:
```
pip install -r requirements.txt
```
ffmpeg must also be installed on the system.

### Environment Variables
| Variable | Description |
|---|---|
| TELEGRAM_BOT_TOKEN | Your Telegram bot token from @BotFather |
| ADMIN_IDS | Comma-separated Telegram user IDs for admin access |

### Run
```bash
python bot.py
```

## Commands
| Command | Description |
|---|---|
| /start | Start the bot |
| /help | Show help message |
| /lang | Change language (uz/ru/en) |
| /stats | Show bot statistics (admin only) |

## Usage
- Send any text: bot searches YouTube and shows 50 results with download buttons
- Send a YouTube/Instagram/TikTok URL: choose MP3 or MP4

## Tech Stack
- Python 3.11
- python-telegram-bot 22.x
- yt-dlp
- ffmpeg
- Flask (keep-alive server)
