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
def handle_tiktok_bot3(message):
    if not message.text or message.text.startswith('/'): return
    raw_link = message.text.strip()
    original_link = raw_link.split('?')[0]
    if "tiktok.com" not in original_link.lower():
        return bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")

    status_msg = bot.reply_to(message, "⏳ ဗီဒီယို ရှာနေပါတယ်...")
    video_url = None
    title = "TikTok Video"
    desc = ""
    author = ""

    apis = [
        ("https://www.tikwm.com/api/", "POST"),
        (f"https://api.tiklydown.eu.org/api/download?url={original_link}", "GET")
    ]

    for api_url, method in apis:
        try:
            if method == "POST": r = requests.post(api_url, data={"url": original_link, "hd": 1}, headers=HEADERS, timeout=25)
            else: r = requests.get(api_url, headers=HEADERS, timeout=25)
            if r.status_code != 200: continue
            data = r.json()
            if data.get("code") == 0 and isinstance(data.get("data"), dict):
                d = data["data"]
                video_url = d.get("hdplay") or d.get("play")
                desc = d.get("desc", "") or d.get("title", "")
                author = d.get("author", {}).get("nickname", "")
            elif data.get("video"):
                v = data["video"]
                video_url = v.get("noWatermark")
                desc = v.get("title", "")
                author = data.get("author", {}).get("nickname", "")
            if video_url: break
        except: continue

    if not video_url:
        return bot.edit_message_text("❌ ဗီဒီယို ရှာမတွေ့ပါ။", message.chat.id, status_msg.message_id)

    clean_desc = clean_caption(desc or title)
    original_hashtags = extract_hashtags_from_desc(desc)
    author_line = f"👤 <b>{escape_html(author)}</b>\n" if author else ""
    
    # Caption Formatting 
    caption = f"{author_line}🎬 <b>{escape_html(clean_desc)}</b>\n\nFrom original #bfaAi #bfastream {original_hashtags}"

    # Buttons ပြင်ဆင်ခြင်း
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🔗 Original Link", url=original_link),
        InlineKeyboardButton("👥 Join Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9")
    )

    try:
        filename = download_file(video_url)
        if filename:
            with open(filename, 'rb') as video:
                # ဗီဒီယို အောင်မြင်စွာ ပို့နိုင်လျှင် Button ပါတစ်ခါတည်း ထည့်ပေးမည်
                bot.send_video(message.chat.id, video, caption=caption, parse_mode="HTML", reply_markup=markup)
            os.remove(filename)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            raise Exception("Download returned None")
            
    except Exception as e:
        logger.error(f"Send failed: {e}")
        # ဒေါင်းလို့မရတဲ့ အခြေအနေ (Fallback) မှာ Link အရှည်ကြီး မပြတော့ဘဲ စာသားထဲမှာ ဝှက်ပြီး ပို့ပေးပါမယ်
        fallback_text = (
            f"⚠️ ဗီဒီယိုကို တိုက်ရိုက်ပေးပို့ရန် အဆင်မပြေပါသဖြင့် အောက်ပါ <a href='{video_url}'><b>[ ဒေါင်းလုဒ် Link ]</b></a> ကို နှိပ်၍ ရယူနိုင်ပါသည်။\n\n"
            f"{caption}"
        )
        bot.send_message(message.chat.id, fallback_text, parse_mode="HTML", reply_markup=markup)
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
                                  
