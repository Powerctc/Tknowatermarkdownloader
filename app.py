import os
import time
import logging
import requests
import re
import threading
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from functools import lru_cache
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable required")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=4)
app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Referer": "https://www.tiktok.com/",
    "Accept": "application/json, text/plain, */*",
}

# ---------- Simple Cache (rate limit လျှော့ချရန်) ----------
cache = {}
CACHE_TTL = 1800  # 30 minutes

def get_from_cache(url):
    item = cache.get(url)
    if item and datetime.now() < item["expire"]:
        logger.info(f"Cache hit: {url}")
        return item["data"]
    return None

def save_to_cache(url, data):
    cache[url] = {
        "data": data,
        "expire": datetime.now() + timedelta(seconds=CACHE_TTL)
    }

# ---------- Helpers ----------

def escape_html(text: str) -> str:
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def extract_hashtags_from_desc(desc):
    if not desc:
        return ""
    return ' '.join(re.findall(r'#\w+', desc))

def clean_caption(desc):
    if not desc:
        return "TikTok Video"
    desc = re.sub(r'http\S+', '', desc)
    desc = re.sub(r'@\w+', '', desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc[:150] if desc else "TikTok Video"

def expand_tiktok_url(url: str) -> str:
    try:
        url = url.strip().split('?')[0]
        if any(x in url for x in ["vt.tiktok.com", "vm.tiktok.com", "tiktok.com/t/"]):
            r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=12)
            final = r.url.split('?')[0]
            if "/video/" in final or "/photo/" in final:
                return final
        return url
    except Exception as e:
        logger.warning(f"Expand failed: {e}")
        return url

def download_file(url, filename="video.mp4"):
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return filename
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

def extract_from_tikwm(data):
    if data.get("code") == 0 and isinstance(data.get("data"), dict):
        d = data["data"]
        video_url = d.get("hdplay") or d.get("play") or d.get("wmplay")
        title = d.get("title") or d.get("desc") or ""
        author = (d.get("author") or {}).get("nickname") or (d.get("author") or {}).get("unique_id") or ""
        return video_url, title, title, author
    return None, None, "", ""

def extract_from_tdown(data):
    if isinstance(data, dict) and data.get("download_url"):
        video_url = data.get("download_url")
        title = data.get("title") or ""
        author = (data.get("author") or {}).get("nickname") or (data.get("author") or {}).get("username") or ""
        return video_url, title, title, author
    return None, None, "", ""

# ---------- Core Download Function ----------

def get_video_info(original_link: str):
    # 1. Check cache first
    cached = get_from_cache(original_link)
    if cached:
        return cached

    apis = [
        # Primary
        {
            "name": "tikwm",
            "url": f"https://www.tikwm.com/api/?url={original_link}&hd=1",
            "method": "GET",
            "extractor": extract_from_tikwm
        },
        # Backup
        {
            "name": "tdownv4",
            "url": f"https://tdownv4.sl-bjs.workers.dev/?down={original_link}",
            "method": "GET",
            "extractor": extract_from_tdown
        },
        # tikwm POST as last try
        {
            "name": "tikwm-post",
            "url": "https://www.tikwm.com/api/",
            "method": "POST",
            "data": {"url": original_link, "hd": 1},
            "extractor": extract_from_tikwm
        },
    ]

    last_error = "unknown"

    for api in apis:
        try:
            if api["method"] == "POST":
                r = requests.post(api["url"], data=api.get("data"), headers=HEADERS, timeout=18)
            else:
                r = requests.get(api["url"], headers=HEADERS, timeout=18)

            logger.info(f"[{api['name']}] HTTP {r.status_code}")

            if r.status_code != 200:
                last_error = f"HTTP {r.status_code}"
                continue

            data = r.json()

            # Rate limit detection
            msg = str(data.get("msg", "")).lower()
            if "limit" in msg or "rate" in msg or data.get("code") == -1 and "limit" in msg:
                last_error = "rate_limit"
                logger.warning(f"[{api['name']}] Rate limited")
                continue

            video_url, title, desc, author = api["extractor"](data)

            if video_url:
                result = {
                    "video_url": video_url,
                    "title": title or "TikTok Video",
                    "desc": desc or title,
                    "author": author
                }
                save_to_cache(original_link, result)
                logger.info(f"Success with {api['name']}")
                return result

            last_error = data.get("msg") or "no_video"

        except Exception as e:
            last_error = str(e)
            logger.error(f"[{api['name']}] Error: {e}")
            continue

    return {"error": last_error}

# ---------- Bot Handlers ----------

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "👋 <b>မင်္ဂလာပါ သယ်ရင်းရေ</b>\n\n"
        "🚀 <b>TikTok No Watermark Downloader</b>\n\n"
        "TikTok Link ကို Paste လုပ်ပြီး ပို့လိုက်ပါ။\n"
        "Caption + Hashtag အကုန် ပါအောင် ဆွဲပေးမယ် ✅"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
        InlineKeyboardButton("👤 Admin FB", url="https://www.facebook.com/share/1D51YRzmjL/")
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_tiktok(message):
    if not message.text or message.text.startswith('/'):
        return

    user_link = message.text.strip()
    if not any(x in user_link.lower() for x in ["tiktok.com", "douyin", "vm.tiktok", "vt.tiktok"]):
        return bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    status_msg = bot.send_message(message.chat.id, "⏳ ဗီဒီယို ရှာနေပါတယ်...")

    original_link = expand_tiktok_url(user_link)
    logger.info(f"Processing: {original_link}")

    result = get_video_info(original_link)

    if "error" in result:
        err = result["error"]
        if err == "rate_limit":
            text = (
                "❌ <b>API Rate Limit</b> ဖြစ်နေပါတယ်။\n\n"
                "ခဏစောင့်ပြီး ပြန်ကြိုးစားပါ (1-2 မိနစ်)။"
            )
        else:
            text = (
                "❌ ဗီဒီယို ရှာမတွေ့ပါ။\n\n"
                "• Private ဗီဒီယို ဖြစ်နိုင်ပါတယ်\n"
                "• Link မှားနေ / ဖျက်ပြီး ဖြစ်နိုင်ပါတယ်\n"
                "• နောက်တစ်ကြိမ် ပြန်ကြိုးစားကြည့်ပါ"
            )
        try:
            bot.edit_message_text(text, message.chat.id, status_msg.message_id, parse_mode="HTML")
        except:
            bot.send_message(message.chat.id, text, parse_mode="HTML")
        return

    video_url = result["video_url"]
    title = result["title"]
    desc = result["desc"]
    author = result["author"]

    # Caption
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔗 Original Link", url=user_link),
        InlineKeyboardButton("👥 Join Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9")
    )

    clean_desc = clean_caption(desc)
    original_hashtags = extract_hashtags_from_desc(desc)
    author_line = f"👤 <b>{escape_html(author)}</b>\n" if author else ""
    final_hashtags = "#BFA_STREAM_TV #TikTok #NoWatermark #bfaAi #bfastream"
    if original_hashtags:
        final_hashtags += f" {original_hashtags}"

    caption = f"{author_line}🎬 <b>{escape_html(clean_desc)}</b>\n\n⚡ {final_hashtags}"

    try:
        bot.edit_message_text("📥 ဒေါင်းနေပါတယ်...", message.chat.id, status_msg.message_id)
    except:
        pass

    # File size check
    file_size = 0
    try:
        head = requests.head(video_url, headers=HEADERS, timeout=10, allow_redirects=True)
        file_size = int(head.headers.get("content-length", 0))
    except:
        pass

    # Send video if not too big
    if 0 < file_size < 48 * 1024 * 1024:
        filename = download_file(video_url)
        if filename and os.path.exists(filename):
            try:
                with open(filename, "rb") as f:
                    bot.send_video(
                        message.chat.id, f,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=markup,
                        supports_streaming=True
                    )
                try:
                    bot.delete_message(message.chat.id, status_msg.message_id)
                except:
                    pass
                return
            finally:
                try:
                    os.remove(filename)
                except:
                    pass

    # Fallback - direct link
    size_info = f"\n\n📦 <b>{file_size // 1024 // 1024}MB</b>" if file_size > 0 else ""
    caption += f'{size_info}\n\n⚠️ <a href="{video_url}"><b>[ ဒေါင်းလုဒ်ရန် နှိပ်ပါ ]</b></a>'

    bot.send_message(
        message.chat.id, caption,
        parse_mode="HTML",
        reply_markup=markup,
        disable_web_page_preview=True
    )
    try:
        bot.delete_message(message.chat.id, status_msg.message_id)
    except:
        pass

# ---------- Health ----------

@app.route('/')
def index():
    return "Bot is running perfectly!"

def run_flask():
    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, use_reloader=False)

if __name__ == "__main__":
    logger.info("Bot starting...")
    bot.remove_webhook()
    time.sleep(1)

    threading.Thread(target=run_flask, daemon=True).start()
    logger.info("Polling started")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
