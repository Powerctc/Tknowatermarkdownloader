import os
import time
import logging
import requests
import re
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN required")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=4)
app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.tiktok.com/"
}

def escape_markdown_v2(text: str) -> str:
    if not text: return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

# ---------- Utils ----------
def download_file(url, filename="video.mp4"):
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return filename
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

def extract_video_info_from_json(data):
    if not isinstance(data, dict): return None, None
    if data.get("code") == 0 and isinstance(data.get("data"), dict):
        d = data["data"]
        return d.get("hdplay") or d.get("play"), d.get("title")
    if data.get("video") and isinstance(data["video"], dict):
        return data["video"].get("noWatermark"), data["video"].get("title")
    for key in ("video", "url", "play", "hd"):
        v = data.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v, data.get("title")
    return None, None

# ---------- Bot handlers ----------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "👋 *မင်္ဂလာပါ သယ်ရင်းရေ*\.\n\n"
        "🚀 *TikTok No Watermark Downloader* မှ ကြိုဆိုပါတယ်။\n\n"
        "TikTok Link ကို Paste လုပ်ပြီး ပို့လိုက်ပါ။"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
        InlineKeyboardButton("👤 Admin FB", url="https://www.facebook.com/share/1D51YRzmjL/")
    )
    bot.send_message(message.chat.id, text, parse_mode="MarkdownV2", reply_markup=markup)


@app.route('/')
def index():
    return "Bot is running!"

if __name__ == "__main__":
    logger.info("Starting bot with polling...")
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
                                  
