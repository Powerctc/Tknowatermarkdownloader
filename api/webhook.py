import os
import requests
import telebot
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# 🎯 Telegram Webhook ဝင်ပေါက်
@app.route('/', methods=['GET', 'POST'])
def telegram_webhook():
    if request.method == 'POST':
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return 'OK', 200
        return 'Invalid JSON', 400
    else:
        return "TikTok Bot Webhook Server is Running Smoothly!"

# 🌟 1. /start Command Handler
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 **မင်္ဂလာပါ သယ်ရင်းရေ...**\n\n"
        "🚀 **TikTok No Watermark Downloader Bot** မှ ကြိုဆိုပါတယ်ဗျာ။\n\n"
        "📌 **အသုံးပြုနည်း -**\n"
        "၁။ TikTok လင့်ခ်ကို ကူးယူပါ။\n"
        "၂။ ဒီ Chat ထဲကို လင့်ခ် တိုက်ရိုက် လှမ်းပို့ပါ။\n"
        "🤖 _Powered by Vercel Webhook_"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
        InlineKeyboardButton("👤 Developer Acc", url="https://www.facebook.com/share/17c7QqLEUA/")
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

# 🆕 2. New Member Join Handler (သီးခြား function အဖြစ် ပြင်လိုက်ပါပြီ)
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        text = (
            f"👋 မင်္ဂလာပါ {new_member.first_name} ရေ!\n\n"
            f"TikTok Downloader Group သို့ ကြိုဆိုပါတယ်ဗျာ။"
        )
        markup = InlineKeyboardMarkup()
        # Bot username ကို အမှန်ကန်ဆုံးဖြစ်အောင် ပြင်ထားပါတယ်
        bot_user = bot.get_me().username
        markup.add(InlineKeyboardButton("🤖 Bot စတင်ရန် (/start)", url=f"https://t.me/{bot_user}?start=start"))
        bot.send_message(message.chat.id, text, reply_markup=markup)

# 🎬 3. Download Handler ကို ဒီအတိုင်းလေး ပြင်ပေးလိုက်ပါ
@bot.message_handler(func=lambda message: True)
def handle_tiktok_download(message):
    # အကယ်၍ Command ဖြစ်နေရင် (သို့) Tiktok လင့်ခ်မပါရင် ဘာမှမလုပ်ဘဲ ထွက်သွားပါ
    if message.text.startswith('/') or "tiktok.com" not in message.text:
        return 
    
    # ကျန်တဲ့ TikTok download logic အပိုင်းကို ဒီအောက်မှာ ဆက်ရေးပါ
    msg = bot.reply_to(message, "⏳ ခဏစောင့်ပေးပါ သယ်ရင်း... ဗီဒီယို ဒေါင်းလုဒ်ဆွဲနေပါတယ်...")
    # ... (ကျန်တဲ့ ကုဒ်များ)
    video_url = None
    title = "TikTok Video"

    try:
        # API logic (ယခင်ကအတိုင်း)
        api_url = "https://www.tikwm.com/api/"
        resp_api = requests.post(api_url, data={'url': message.text.strip(), 'hd': 1}, timeout=6).json()
        if resp_api.get('code') == 0:
            data = resp_api.get('data', {})
            video_url = data.get('play')
            title = data.get('title', 'TikTok Video')
        
        if video_url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔗 View Original", url=message.text.strip()))
            bot.send_video(message.chat.id, video_url, caption=f"🎬 {title}\n\n✨ Foreverstudy", reply_markup=markup)
            bot.delete_message(message.chat.id, msg.message_id)
        else:
            bot.edit_message_text("❌ ဗီဒီယို ဆွဲမရဖြစ်နေသည်။", message.chat.id, msg.message_id)
    except Exception as e:
        print(e)
        
