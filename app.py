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

@bot.message_handler(func=lambda m: True)
def handle_tiktok(message):
    if not message.text or message.text.startswith('/'): return

    original_link = message.text.strip().split('?')[0]
    if "tiktok.com" not in original_link.lower():
        return bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")

    status_msg = bot.reply_to(message, "⏳ ဗီဒီယို ရှာနေပါတယ်...")

    video_url, title = None, "TikTok Video"
    apis = [
        "https://www.tikwm.com/api/",
        f"https://api.tiklydown.eu.org/api/download?url={original_link}",
        f"https://tdownv4.sl-bjs.workers.dev/?down={original_link}"
    ]

    for api_url in apis:
        try:
            if "tikwm" in api_url:
                r = requests.post(api_url, data={"url": original_link, "hd": 1}, headers=HEADERS, timeout=20)
            else:
                r = requests.get(api_url, headers=HEADERS, timeout=20)

            v, t = extract_video_info_from_json(r.json())
            if v:
                video_url, title = v, t or title
                break
        except Exception as e:
            logger.warning(f"API {api_url} failed: {e}")
            continue

        # ... (အပေါ်က API ကနေ video_url ရှာတဲ့အပိုင်း)

    if not video_url:
        return bot.edit_message_text("❌ ဗီဒီယို ရှာမတွေ့ပါ။ Link မှန်ရဲ့လား စစ်ပေးပါ။", message.chat.id, status_msg.message_id)

    # 1. markup ကို try ရဲ့ အပြင်မှာ ကြိုတင် Initialize လုပ်ထားပါမယ် (Error မတက်စေရန်)
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🔗 Original Link", url=original_link),
        InlineKeyboardButton("👥 Join Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9")
    )

    try:
        bot.edit_message_text("📥 ဒေါင်းနေပါတယ်...", message.chat.id, status_msg.message_id)

        # File size စစ်မယ်
        head = requests.head(video_url, headers=HEADERS, timeout=10)
        file_size = int(head.headers.get('content-length', 0))

        # ၂။ Caption နှင့် Hashtag ပုံစံချခြင်း
        safe_title = escape_markdown_v2(title)
        caption = f"🎬 *{safe_title}*\n\nFrom original \#bfaAi \#bfastream"

        # ၅၀ MB အောက်ဆို ဗီဒီယို တိုက်ရိုက်ပို့မယ်
        if file_size < 50 * 1024 * 1024: 
            filename = download_file(video_url)
            if filename:
                with open(filename, 'rb') as video:
                    bot.send_video(message.chat.id, video, caption=caption, parse_mode="MarkdownV2", reply_markup=markup)
                os.remove(filename)
            else: raise Exception("Download failed")
        else:
            # ဗီဒီယို ဖိုင်ကြီးလွန်းရင် စာသားပဲ ပို့မယ်
            safe_video_url = escape_markdown_v2(video_url)
            caption += f"\n\n📦 File ကြီးလို့ Link ပဲပို့လိုက်ပါတယ်:\n{safe_video_url}"
            bot.send_message(message.chat.id, caption, parse_mode="MarkdownV2", reply_markup=markup)

        bot.delete_message(message.chat.id, status_msg.message_id)

    except Exception as e:
        logger.exception("Send video failed")
        safe_video_url = escape_markdown_v2(video_url)
        
        # အပေါ်မှာ markup ကို ကြိုကြေညာထားလို့ အခု except ထဲမှာ သုံးရင် Error မတက်တော့ပါဘူး
        fallback_caption = f"⚠️ ပို့လို့မရပါ။ Link:\n{safe_video_url}\n\nFrom original \#bfaAi \#bfastream"
        bot.send_message(message.chat.id, fallback_caption, parse_mode="MarkdownV2", reply_markup=markup)
        try:
            bot.delete_message(message.chat.id, status_msg.message_id)
        except: pass
    

@app.route('/')
def index():
    return "Bot is running!"

if __name__ == "__main__":
    logger.info("Starting bot with polling...")
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
                                  
