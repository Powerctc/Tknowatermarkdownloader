import os
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
    text = (
        "👋 **မင်္ဂလာပါ သယ်ရင်းရေ...**\n\n"
        "🚀 **TikTok No Watermark Downloader Bot** မှ ကြိုဆိုပါတယ်။\n\n"
        "TikTok Link ကို တိုက်ရိုက် Paste လုပ်ပြီး ပို့လိုက်ပါ။"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
        InlineKeyboardButton("👤 Admin FB", url="https://www.facebook.com/share/17c7QqLEUA/")
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

# ====================== TIKTOK DOWNLOADER ======================
@bot.message_handler(func=lambda message: True)
def handle_tiktok(message):
    if not message.text or message.text.startswith('/'):
        return

    original_link = message.text.strip()

    if "tiktok.com" not in original_link.lower() and "vt.tiktok.com" not in original_link.lower():
        bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")
        return

    status_msg = bot.reply_to(message, "⏳ ဗီဒီယို ရှာနေပါတယ်... ခဏစောင့်ပါ။")

    video_url = None
    title = "TikTok Video"

    try:
        urls_to_try = [
            ("https://www.tikwm.com/api/", {"url": original_link, "hd": 1}),
            (f"https://api.tiklydown.eu.org/api/download?url={original_link}", None),
            (f"https://api.tmate.to/download?url={original_link}", None),
            (f"https://api.ssstik.io/download?url={original_link}", None),
        ]

        for api_url, payload in urls_to_try:
            if not video_url:
                try:
                    if payload:  # POST
                        r = requests.post(api_url, data=payload, headers=HEADERS, timeout=12)
                    else:  # GET
                        r = requests.get(api_url, headers=HEADERS, timeout=12)
                    
                    data = r.json()
                    
                    # Different API structures
                    if "data" in data:
                        if isinstance(data["data"], dict):
                            video_url = data["data"].get("play") or data["data"].get("video") or data["data"].get("noWatermark")
                            title = data["data"].get("title", title)
                    elif "video" in data:
                        video_url = data.get("video")
                except:
                    continue

        if video_url:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("👥 Admin Group Join", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
                InlineKeyboardButton("👤 Admin FB Follow", url="https://www.facebook.com/share/17c7QqLEUA/")
            )
            
            bot.send_video(
                message.chat.id, 
                video_url, 
                caption=f"🎬 {title}\n\n✨ Powered by Forever Study",
                reply_markup=markup
            )
            
            try:
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.delete_message(message.chat.id, message.message_id)
            except:
                pass
        else:
            bot.edit_message_text("❌ ဗီဒီယို ရှာမတွေ့ပါ။ ခဏနေမှ ပြန်စမ်းကြည့်ပါ။", 
                                message.chat.id, status_msg.message_id)

    except Exception as e:
        print(f"General Error: {e}")
        try:
            bot.edit_message_text("⚠️ စနစ်မှာ ခဏ ပြဿနာရှိနေပါတယ်။ ခဏနေမှ ပြန်ကြိုးစားပါ။", 
                                message.chat.id, status_msg.message_id)
        except:
            pass

handler = app
