import os
import logging
import requests
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- Config ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is not set. Exiting.")
    raise RuntimeError("BOT_TOKEN environment variable is required")

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ---------- Webhook endpoint ----------
@app.route('/', methods=['GET', 'POST'])
@app.route('/api/webhook', methods=['GET', 'POST'])
def telegram_webhook():
    if request.method == 'POST':
        try:
            raw = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(raw)
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            logger.exception("Webhook processing error")
            return 'ERROR', 500
    return "✅ Bot is Running!"

# ---------- Bot handlers ----------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "👋 **မင်္ဂလာပါ သယ်ရင်းရေ...**\n\n"
        "🚀 **TikTok No Watermark Downloader** မှ ကြိုဆိုပါတယ်။\n\n"
        "TikTok Link ကို Paste လုပ်ပြီး ပို့လိုက်ပါ။"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
        InlineKeyboardButton("👤 Admin FB", url="https://www.facebook.com/share/17c7QqLEUA/")
    )
    # Use Markdown (if your text contains characters that need escaping, consider MarkdownV2 or HTML)
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

def extract_video_info_from_json(data):
    """
    Try to extract video URL and title from a JSON response using common keys.
    Returns (video_url_or_None, title_or_None)
    """
    if not isinstance(data, dict):
        return None, None

    # Common nested "data" object
    if "data" in data and isinstance(data["data"], dict):
        d = data["data"]
        for key in ("play", "video", "noWatermark", "no_wm", "hd", "url"):
            v = d.get(key)
            if isinstance(v, str) and v.startswith("http"):
                title = d.get("title") or d.get("desc") or None
                return v, title

    # Top-level keys
    for key in ("video", "url", "download", "play", "noWatermark", "hd"):
        v = data.get(key)
        if isinstance(v, str) and v.startswith("http"):
            title = data.get("title") or data.get("desc") or None
            return v, title

    # Some APIs return lists
    if "videos" in data and isinstance(data["videos"], list) and data["videos"]:
        first = data["videos"][0]
        if isinstance(first, dict):
            for key in ("url", "play", "video"):
                v = first.get(key)
                if isinstance(v, str) and v.startswith("http"):
                    title = first.get("title") or None
                    return v, title

    return None, None

@bot.message_handler(func=lambda message: True)
def handle_tiktok(message):
    # ignore non-text or commands
    if not message.text or message.text.startswith('/'):
        return

    original_link = message.text.strip().split('?')[0]

    if "tiktok.com" not in original_link.lower():
        bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")
        return

    status_msg = bot.reply_to(message, "⏳ ဗီဒီယို ရှာနေပါတယ်... ခဏစောင့်ပါ။")

    video_url = None
    title = "TikTok Video"

    try:
        apis = [
            f"https://tdownv4.sl-bjs.workers.dev/?down={original_link}",
            f"https://api.tiklydown.eu.org/api/download?url={original_link}",
            f"https://api.tmate.to/download?url={original_link}",
            "https://www.tikwm.com/api/"
        ]

        for api_url in apis:
            if video_url:
                break

            try:
                # tikwm expects POST with form data
                if "tikwm" in api_url:
                    r = requests.post(api_url, data={"url": original_link, "hd": 1}, headers=HEADERS, timeout=15)
                else:
                    r = requests.get(api_url, headers=HEADERS, timeout=15)

                # ensure we got a successful HTTP response
                if r.status_code < 200 or r.status_code >= 300:
                    logger.info("API %s returned status %s", api_url, r.status_code)
                    continue

                # try to parse JSON safely
                try:
                    data = r.json()
                except ValueError:
                    # not JSON — skip or try to find a URL in text
                    text = r.text
                    # quick heuristic: find first http...mp4 or .m3u8 or .mpd
                    import re
                    m = re.search(r"https?://[^\s'\"<>]+(?:\.mp4|\.m3u8|\.mpd|/play/)[^\s'\"<>]*", text)
                    if m:
                        video_url = m.group(0)
                        title = None
                        break
                    continue

                v, t = extract_video_info_from_json(data)
                if v:
                    video_url = v
                    if t:
                        title = t
                    break

            except requests.RequestException as rexc:
                logger.warning("Request to %s failed: %s", api_url, rexc)
                continue
            except Exception:
                logger.exception("Unexpected error while calling %s", api_url)
                continue

        # Final fallback: try to fetch the original page and look for a video URL (best-effort)
        if not video_url:
            try:
                r = requests.get(original_link, headers=HEADERS, timeout=10)
                if r.status_code == 200:
                    import re
                    # look for common video URL patterns
                    m = re.search(r'https://.*?\.tiktokcdn\.com/.*?\.mp4', r.text)
                    if m:
                        video_url = m.group(0)
            except Exception:
                pass

        if video_url:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("👥 Admin Group Join", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
                InlineKeyboardButton("👤 Admin FB Follow", url="https://www.facebook.com/share/17c7QqLEUA/")
            )

            caption = (
                f"🎬 {title}\n\n"
                f"🔗 Original Link: {original_link}\n"
                f"✅ Watermark Free • HD Quality\n"
                f"✨ Powered by Forever Study"
            )

            try:
                # send_video accepts a URL; if Telegram rejects remote URL you may need to download and send as file
                bot.send_video(message.chat.id, video_url, caption=caption, reply_markup=markup)
            except Exception:
                # fallback: send as plain message with the direct link
                bot.send_message(message.chat.id, f"🎬 {title}\n\nDirect video URL:\n{video_url}", reply_markup=markup)

            # try to clean up messages
            try:
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass
        else:
            try:
                bot.edit_message_text("❌ ဗီဒီယို ရှာမတွေ့ပါ။ နောက်တစ်ခါ ပြန်စမ်းကြည့်ပါ။",
                                      message.chat.id, status_msg.message_id)
            except Exception:
                bot.reply_to(message, "❌ ဗီဒီယို ရှာမတွေ့ပါ။ နောက်တစ်ခါ ပြန်စမ်းကြည့်ပါ။")

    except Exception:
        logger.exception("Top-level error in handle_tiktok")
        try:
            bot.edit_message_text("⚠️ စနစ်မှာ ခဏ ပြဿနာရှိနေပါတယ်။ ခဏနေမှ ပြန်ကြိုးစားပါ။",
                                  message.chat.id, status_msg.message_id)
        except Exception:
            pass

# Expose the Flask app as WSGI callable
handler = app

if __name__ == "__main__":
    # For local testing only. In production use a proper WSGI server.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
