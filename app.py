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

def escape_html(text: str) -> str:
    if not text: return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN required")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=4)
app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Referer": "https://www.tiktok.com/",
    "Accept": "application/json, text/plain, */*"
}

def extract_hashtags_from_desc(desc):
    if not desc: return ""
    hashtags = re.findall(r'#\w+', desc)
    return ' '.join(hashtags)

def clean_caption(desc):
    if not desc: return "TikTok Video"
    desc = re.sub(r'http\S+', '', desc)
    desc = re.sub(r'@\w+', '', desc) # Remove mentions
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc[:150] if desc else "TikTok Video"

def expand_tiktok_url(url):
    """vt.tiktok.com တို့ကို full URL အဖြစ် ပြောင်း"""
    try:
        if 'vt.tiktok.com' in url or 'vm.tiktok.com' in url:
            r = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=10)
            return r.url
        return url
    except:
        return url

def download_file(url, filename="video.mp4"):
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return filename
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None

def extract_video_info_from_json(data):
    if not isinstance(data, dict): return None, None, "", ""
    
    # TikWM format
    if data.get("code") == 0 and isinstance(data.get("data"), dict):
        d = data["data"]
        video_url = d.get("hdplay") or d.get("play") or d.get("wmplay")
        title = d.get("title", "")
        desc = d.get("desc", "") or d.get("title", "")
        author = d.get("author", {}).get("nickname", "") or d.get("author", {}).get("unique_id", "")
        return video_url, title, desc, author
    
    # TikLyDown format
    if data.get("video") and isinstance(data["video"], dict):
        v = data["video"]
        video_url = v.get("noWatermark") or v.get("watermark") or v.get("hd") or v.get("sd")
        title = v.get("title", "") or data.get("title", "")
        desc = data.get("desc", "") or title
        author = data.get("author", {}).get("nickname", "") or data.get("author", {}).get("unique_id", "")
        return video_url, title, desc, author
    
    # Generic format
    for key in ("video", "url", "play", "hd", "downloadUrl", "nowm"):
        v = data.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v, data.get("title", ""), data.get("desc", ""), data.get("author", "")
    return None, None, "", ""

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
    if not message.text or message.text.startswith('/'): return

    user_link = message.text.strip()
    
    # Link စစ်ပြီး expand လုပ်
    if not any(x in user_link.lower() for x in ["tiktok.com", "douyin"]):
        return bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")
    
    # User message ကို ဖျက်မယ်
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        logger.warning(f"Cannot delete user message: {e}")

    original_link = expand_tiktok_url(user_link.split('?')[0])
    status_msg = bot.send_message(message.chat.id, "⏳ ဗီဒီယို ရှာနေပါတယ်...")

    video_url, title, desc, author = None, "TikTok Video", "", ""
    
    # API List - 4 ခုထိ တိုးထားတယ်
    apis = [
        ("https://www.tikwm.com/api/", "POST"),
        (f"https://api.tiklydown.eu.org/api/download?url={original_link}", "GET"),
        (f"https://tikdown.org/getAjax?url={original_link}", "GET"),
        (f"https://tdownv4.sl-bjs.workers.dev/?down={original_link}", "GET")
    ]

        for api_url, method in apis:
        try:
            if method == "POST":
                r = requests.post(api_url, data={"url": original_link, "hd": 1}, headers=HEADERS, timeout=20)
            else:
                r = requests.get(api_url, headers=HEADERS, timeout=20)

            if r.status_code != 200: continue
            data = r.json()
            v, t, d, a = extract_video_info_from_json(data)
            
            # ပြင်ဆင်ချက် ၁ - 'tiktokcdn' in v ဆိုတဲ့ ကန့်သတ်ချက်ကို ဖြုတ်လိုက်ပါတယ် (တခြား CDN တွေပါ အလုပ်လုပ်စေရန်)
            if v:
                video_url, title, desc, author = v, t or title, d, a
                logger.info(f"Got video from {api_url}")
                break
        except Exception as e:
            logger.warning(f"API {api_url} failed: {e}")
            continue

    if not video_url:
        try: bot.edit_message_text("❌ ဗီဒီယို ရှာမတွေ့ပါ။ Private ဗီဒီယို သို့မဟုတ် Link မှားနေနိုင်ပါတယ်။", message.chat.id, status_msg.message_id)
        except: pass
        return

    try:
        try: bot.edit_message_text("📥 ဒေါင်းနေပါတယ်...", message.chat.id, status_msg.message_id)
        except: pass

        # ပြင်ဆင်ချက် ၂ - တခြားနိုင်ငံ CDN link တွေ ဒေါင်းရင် Block မခံရအောင် download_file ထဲမှာ သုံးသလို requests stream ကို သုံးပြီး size စစ်ပါမယ်
        file_size = 0
        try:
            with requests.get(video_url, headers=HEADERS, stream=True, timeout=15) as r:
                if r.status_code == 200:
                    file_size = int(r.headers.get('content-length', 0))
        except Exception as e:
            logger.warning(f"Failed to get content-length: {e}")

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🔗 Original Link", url=user_link),
            InlineKeyboardButton("👥 Join Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9")
        )

        clean_desc = clean_caption(desc or title)
        original_hashtags = extract_hashtags_from_desc(desc)
        author_line = f"👤 <b>{escape_html(author)}</b>\n" if author else ""
        caption_text = escape_html(clean_desc)

        final_hashtags = "#BFA_STREAM_TV #TikTok #NoWatermark"
        if original_hashtags:
            final_hashtags += f" {original_hashtags}"

        caption = f"{author_line}🎬 <b>{caption_text}</b>\n\n⚡ {final_hashtags}"

        # ပြင်ဆင်ချက် ၃ - file_size စစ်မရရင်လည်း (0 ဖြစ်နေရင်လည်း) ဒေါင်းကြည့်ဖို့ ကြိုးစားခိုင်းပါမယ်
        if file_size < 50 * 1024 * 1024:
            filename = download_file(video_url)
            if filename and os.path.exists(filename):
                with open(filename, 'rb') as video:
                    bot.send_video(
                        message.chat.id,
                        video,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                os.remove(filename)
                try: bot.delete_message(message.chat.id, status_msg.message_id)
                except: pass
                return

        # File ကြီးရင် သို့မဟုတ် ဒေါင်းမရခဲ့ရင် link ပို့မည့်အပိုင်း
        if file_size > 0:
            caption += f"\n\n📦 <b>File size: {file_size // 1024 // 1024}MB</b>"
        caption += f'\n<a href="{video_url}">⬇️ ဒေါင်းလုဒ်ရန် နှိပ်ပါ</a>'

        bot.send_message(
            message.chat.id,
            caption,
            parse_mode="HTML",
            reply_markup=markup,
            disable_web_page_preview=True
        )
        try: bot.delete_message(message.chat.id, status_msg.message_id)
        except: pass

    except Exception as e:
        logger.exception(f"Send video failed: {e}")
        # ... (ကျန်တဲ့ fallback အပိုင်းအတိုင်း ထားနိုင်ပါတယ်)

            continue

    if not video_url:
        try: bot.edit_message_text("❌ ဗီဒီယို ရှာမတွေ့ပါ။ Private ဗီဒီယို သို့မဟုတ် Link မှားနေနိုင်ပါတယ်။", message.chat.id, status_msg.message_id)
        except: pass
        return

    try:
        try: bot.edit_message_text("📥 ဒေါင်းနေပါတယ်...", message.chat.id, status_msg.message_id)
        except: pass

        try:
            head = requests.head(video_url, headers=HEADERS, timeout=10, allow_redirects=True)
            file_size = int(head.headers.get('content-length', 0))
        except:
            file_size = 0

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("🔗 Original Link", url=user_link),
            InlineKeyboardButton("👥 Join Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9")
        )

        clean_desc = clean_caption(desc or title)
        original_hashtags = extract_hashtags_from_desc(desc)
        author_line = f"👤 <b>{escape_html(author)}</b>\n" if author else ""
        caption_text = escape_html(clean_desc)

        final_hashtags = "#BFA_STREAM_TV #TikTok #NoWatermark"
        if original_hashtags:
            final_hashtags += f" {original_hashtags}"

        caption = f"{author_line}🎬 <b>{caption_text}</b>\n\n⚡ {final_hashtags}"

        # 50MB အောက်ဆို video ပို့
        if 0 < file_size < 50 * 1024 * 1024:
            filename = download_file(video_url)
            if filename and os.path.exists(filename):
                with open(filename, 'rb') as video:
                    bot.send_video(
                        message.chat.id,
                        video,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                os.remove(filename)
                try: bot.delete_message(message.chat.id, status_msg.message_id)
                except: pass
                return

        # File ကြီးရင် link ပဲ ပို့
        if file_size > 0:
            caption += f"\n\n📦 <b>File size: {file_size // 1024 // 1024}MB</b>"
        caption += f'\n<a href="{video_url}">⬇️ ဒေါင်းလုဒ်ရန် နှိပ်ပါ</a>'

        bot.send_message(
            message.chat.id,
            caption,
            parse_mode="HTML",
            reply_markup=markup,
            disable_web_page_preview=True
        )
        try: bot.delete_message(message.chat.id, status_msg.message_id)
        except: pass

    except Exception as e:
        logger.exception(f"Send video failed: {e}")
        try:
            fallback_caption = f"⚠️ ဗီဒီယို တိုက်ရိုက်ပို့လို့ မရပါ။\n\n{caption}"
            bot.send_message(message.chat.id, fallback_caption, parse_mode="HTML", reply_markup=markup)
            bot.delete_message(message.chat.id, status_msg.message_id)
        except: pass

@app.route('/')
def index():
    return "Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'OK', 200

if __name__ == "__main__":
    logger.info("Starting bot with polling...")
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
