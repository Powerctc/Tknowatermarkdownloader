import os
import time
import logging
import requests
import re
import threading
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
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
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------- Helpers ----------

def escape_html(text: str) -> str:
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def extract_hashtags_from_desc(desc):
    if not desc:
        return ""
    hashtags = re.findall(r'#\w+', desc)
    return ' '.join(hashtags)

def clean_caption(desc):
    if not desc:
        return "TikTok Video"
    desc = re.sub(r'http\S+', '', desc)
    desc = re.sub(r'@\w+', '', desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc[:150] if desc else "TikTok Video"

def expand_tiktok_url(url: str) -> str:
    """Reliably expand short TikTok links (vt/vm/t)."""
    try:
        url = url.strip().split('?')[0]
        if any(x in url for x in ["vt.tiktok.com", "vm.tiktok.com", "tiktok.com/t/"]):
            r = requests.get(
                url,
                headers=HEADERS,
                allow_redirects=True,
                timeout=12
            )
            final = r.url.split('?')[0]
            if "/video/" in final or "/photo/" in final:
                logger.info(f"Expanded short link → {final}")
                return final
            logger.warning(f"Short link did not resolve to video: {final}")
        return url
    except Exception as e:
        logger.warning(f"URL expand failed: {e}")
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

def extract_video_info_from_json(data):
    """Parse various API response formats."""
    if not isinstance(data, dict):
        return None, None, "", ""

    # tikwm format (most common)
    if data.get("code") == 0 and isinstance(data.get("data"), dict):
        d = data["data"]
        video_url = d.get("hdplay") or d.get("play") or d.get("wmplay")
        title = d.get("title") or d.get("desc") or ""
        desc = d.get("desc") or title
        author_obj = d.get("author") or {}
        author = author_obj.get("nickname") or author_obj.get("unique_id") or ""
        return video_url, title, desc, author

    # Other possible formats
    if data.get("video") and isinstance(data["video"], dict):
        v = data["video"]
        video_url = v.get("noWatermark") or v.get("play") or v.get("hd") or v.get("sd")
        title = v.get("title") or data.get("title") or ""
        desc = data.get("desc") or title
        author = (data.get("author") or {}).get("nickname") or ""
        return video_url, title, desc, author

    for key in ("video", "url", "play", "hd", "downloadUrl", "nowm", "nwm"):
        v = data.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v, data.get("title", ""), data.get("desc", ""), data.get("author", "")

    return None, None, "", ""

# ---------- Main Handler ----------

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "👋 <b>မင်္ဂလာပါ သယ်ရင်းရေ</b>.\n\n"
        "🚀 <b>TikTok No Watermark Downloader</b> မှ ကြိုဆိုပါတယ်။\n\n"
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
    if not any(x in user_link.lower() for x in ["tiktok.com", "douyin.com", "vm.tiktok", "vt.tiktok"]):
        return bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")

    # Delete user message (optional)
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    status_msg = bot.send_message(message.chat.id, "⏳ ဗီဒီယို ရှာနေပါတယ်...")

    # Expand short links first
    original_link = expand_tiktok_url(user_link)
    logger.info(f"Processing link: {original_link}")

    video_url = None
    title = "TikTok Video"
    desc = ""
    author = ""
    last_error = "unknown"

    # Only reliable APIs (as of Aug 2026)
    apis = [
        # Primary - tikwm (GET is currently more stable)
        (f"https://www.tikwm.com/api/?url={original_link}&hd=1", "GET"),
        # Backup - same API with POST
        ("https://www.tikwm.com/api/", "POST"),
    ]

    for api_url, method in apis:
        try:
            if method == "POST":
                r = requests.post(
                    api_url,
                    data={"url": original_link, "hd": 1},
                    headers=HEADERS,
                    timeout=20
                )
            else:
                r = requests.get(api_url, headers=HEADERS, timeout=20)

            logger.info(f"[{method}] {api_url} → HTTP {r.status_code}")

            if r.status_code != 200:
                last_error = f"HTTP {r.status_code}"
                continue

            data = r.json()
            code = data.get("code")
            msg = data.get("msg", "")

            logger.info(f"API response → code={code} | msg={msg}")

            # Rate limit detection
            if code != 0 and ("limit" in str(msg).lower() or "rate" in str(msg).lower()):
                last_error = "rate_limit"
                logger.warning("Rate limited by tikwm")
                continue

            v, t, d, a = extract_video_info_from_json(data)
            if v:
                video_url = v
                title = t or title
                desc = d or title
                author = a or author
                logger.info(f"Successfully got video URL from {method}")
                break
            else:
                last_error = msg or "no_video_url"

        except Exception as e:
            last_error = str(e)
            logger.error(f"API call failed: {e}")
            continue

    # ---------- Failure handling ----------
    if not video_url:
        error_text = "❌ ဗီဒီယို ရှာမတွေ့ပါ။"

        if last_error == "rate_limit":
            error_text = (
                "❌ API Rate Limit ဖြစ်နေပါတယ်။\n\n"
                "ခဏစောင့်ပြီး ပြန်ကြိုးစားပါ (1-2 မိနစ်)။"
            )
        elif "private" in str(last_error).lower() or "Url parsing" in str(last_error):
            error_text = (
                "❌ ဗီဒီယို ရှာမတွေ့ပါ။\n\n"
                "• Private ဗီဒီယို ဖြစ်နိုင်ပါတယ်\n"
                "• Link မှားနေ / ဖျက်ပြီး ဖြစ်နိုင်ပါတယ်\n"
                "• Short link မှားနေနိုင်ပါတယ်"
            )
        else:
            error_text = (
                "❌ ဗီဒီယို ရှာမတွေ့ပါ။\n\n"
                "Private ဗီဒီယို သို့မဟုတ် Link မှားနေနိုင်ပါတယ်။\n"
                "နောက်တစ်ကြိမ် ပြန်ကြိုးစားကြည့်ပါ။"
            )

        try:
            bot.edit_message_text(error_text, message.chat.id, status_msg.message_id)
        except:
            bot.send_message(message.chat.id, error_text)
        return

    # ---------- Success path ----------
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔗 Original Link", url=user_link),
        InlineKeyboardButton("👥 Join Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9")
    )

    clean_desc = clean_caption(desc or title)
    original_hashtags = extract_hashtags_from_desc(desc)
    author_line = f"👤 <b>{escape_html(author)}</b>\n" if author else ""
    caption_text = escape_html(clean_desc)

    final_hashtags = "#BFA_STREAM_TV #TikTok #NoWatermark #bfaAi #bfastream"
    if original_hashtags:
        final_hashtags += f" {original_hashtags}"

    caption = f"{author_line}🎬 <b>{caption_text}</b>\n\n⚡ {final_hashtags}"

    try:
        bot.edit_message_text("📥 ဒေါင်းနေပါတယ်...", message.chat.id, status_msg.message_id)
    except:
        pass

    # Check file size first
    file_size = 0
    try:
        with requests.head(video_url, headers=HEADERS, timeout=10, allow_redirects=True) as r:
            file_size = int(r.headers.get("content-length", 0))
    except:
        pass

    # Send as video if under \~48MB (Telegram limit is 50MB)
    if 0 < file_size < 48 * 1024 * 1024:
        filename = download_file(video_url)
        if filename and os.path.exists(filename):
            try:
                with open(filename, "rb") as video:
                    bot.send_video(
                        message.chat.id,
                        video,
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

    # Fallback: send direct download link
    size_text = f"\n\n📦 <b>File size: {file_size // 1024 // 1024}MB</b>" if file_size > 0 else ""
    caption += (
        f"{size_text}\n\n"
        f'⚠️ ဗီဒီယိုကို တိုက်ရိုက်ပေးပို့ရန် အဆင်မပြေပါသဖြင့် '
        f'<a href="{video_url}"><b>[ ဒေါင်းလုဒ်ရန် နှိပ်ပါ ]</b></a>'
    )

    bot.send_message(
        message.chat.id,
        caption,
        parse_mode="HTML",
        reply_markup=markup,
        disable_web_page_preview=True
    )
    try:
        bot.delete_message(message.chat.id, status_msg.message_id)
    except:
        pass

# ---------- Health Check ----------

@app.route('/')
def index():
    return "Bot is running perfectly!"

def run_flask():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False, use_reloader=False)

if __name__ == "__main__":
    logger.info("Initializing Bot with Polling Mode...")
    bot.remove_webhook()
    time.sleep(1)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    logger.info("Bot Polling has been started successfully!")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
