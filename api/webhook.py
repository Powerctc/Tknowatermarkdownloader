import os
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.tiktok.com/"
}

@app.route('/', methods=['GET', 'POST'])
@app.route('/api/webhook', methods=['GET', 'POST'])
def telegram_webhook():
    if request.method == 'POST':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            print(f"Webhook Error: {e}")
            return 'ERROR', 500
    return "✅ Bot is Running!"

# ====================== START ======================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = "👋 **မင်္ဂလာပါ သယ်ရင်းရေ...**\n\n🚀 **TikTok No Watermark Downloader** မှ ကြိုဆိုပါတယ်။\n\nTikTok Link ကို Paste လုပ်ပြီး ပို့လိုက်ပါ။"
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
        InlineKeyboardButton("👤 Admin FB", url="https://www.facebook.com/share/17c7QqLEUA/")
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

# ====================== TIKTOK DOWNLOADER ======================
def resolve_tiktok_url(url):
    """
    vm.tiktok.com, vt.tiktok.com လင့်အတိုတွေကို
    tiktok.com/@user/video/xxx အရှည်လင့် ပြောင်းပေးမယ်
    """
    try:
        # HEAD request နဲ့ redirect ပဲ စစ်မယ်၊ မြန်တယ်
        r = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=10)
        final_url = r.url
        # tiktok.com video link ဟုတ်မဟုတ် စစ်မယ်
        if "/video/" in final_url or "/photo/" in final_url:
            return final_url
        # HEAD မရရင် GET နဲ့ ထပ်စမ်း
        r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=10)
        return r.url
    except Exception as e:
        print(f"Resolve URL Error: {e}")
        return url # မရရင် မူရင်းလင့် ပြန်ပေး

@bot.message_handler(func=lambda message: True)
def handle_tiktok(message):
    if not message.text or message.text.startswith('/'):
        return

    original_link = message.text.strip().split('?')[0]

    if "tiktok.com" not in original_link.lower():
        bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")
        return

    status_msg = bot.reply_to(message, "⏳ ဗီဒီယို ရှာနေပါတယ်... ခဏစောင့်ပါ။")

    # 1. vm.tiktok.com လင့်ကို အရှည်လင့် ပြောင်းမယ်
    resolved_link = resolve_tiktok_url(original_link)
    print(f"Original: {original_link} -> Resolved: {resolved_link}")

    video_url = None
    title = "TikTok Video"

    try:
        apis = [
            f"https://tdownv4.sl-bjs.workers.dev/?down={resolved_link}",
            f"https://api.tiklydown.eu.org/api/download?url={resolved_link}",
            f"https://api.tmate.to/download?url={resolved_link}",
            "https://www.tikwm.com/api/",
        ]

        for api_url in apis:
            if video_url:
                break
            try:
                if "tikwm" in api_url:
                    # tikwm က POST သုံးရတယ်
                    r = requests.post(api_url, data={"url": resolved_link, "hd": 1}, headers=HEADERS, timeout=15)
                else:
                    r = requests.get(api_url, headers=HEADERS, timeout=15)

                data = r.json()

                if "data" in data:
                    d = data.get("data", {})
                    video_url = d.get("play") or d.get("video") or d.get("noWatermark") or d.get("hd") or d.get("wmplay")
                    title = d.get("title", title)
                    # Photo carousel ဆိုရင်
                    if d.get("images"):
                        bot.edit_message_text("❌ ဒါက ဗီဒီယိုမဟုတ်ဘဲ ပုံအတွဲလိုက် Post ဖြစ်နေပါတယ်။",
                                            message.chat.id, status_msg.message_id)
                        return
                else:
                    video_url = data.get("video") or data.get("url")

                if video_url and isinstance(video_url, str) and video_url.startswith("http"):
                    break
            except Exception as e:
                print(f"API {api_url} Error: {e}")
                continue

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

            bot.send_video(
                message.chat.id,
                video_url,
                caption=caption,
                reply_markup=markup
            )

            try:
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.delete_message(message.chat.id, message.message_id)
            except:
                pass
        else:
            bot.edit_message_text("❌ ဗီဒီယို ရှာမတွေ့ပါ။ Private ဖြစ်နေတာ (သို့) ဖျက်ပြီးသားဖြစ်နိုင်ပါတယ်။",
                                message.chat.id, status_msg.message_id)

    except Exception as e:
        print(f"Error: {e}")
        try:
            bot.edit_message_text("⚠️ စနစ်မှာ ခဏ ပြဿနာရှိနေပါတယ်။ ခဏနေမှ ပြန်ကြိုးစားပါ။",
                                message.chat.id, status_msg.message_id)
        except:
            pass

handler = app
