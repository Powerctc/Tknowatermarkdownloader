import os
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ CRITICAL: BOT_TOKEN is missing!")
    BOT_TOKEN = "dummy"  # မရှိရင် crash မဖြစ်အောင်

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

print("✅ Bot Started Successfully!")  # Logs မှာ မြင်ရအောင်

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        try:
            print("📥 Received Update from Telegram")
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            print("✅ Update Processed")
            return 'OK', 200
        except Exception as e:
            print(f"❌ Webhook Error: {str(e)}")
            return 'ERROR', 500
    print("GET Request Received")
    return "✅ TikTok No Watermark Bot is Running!"

# Welcome Handler
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    print(f"📤 Sending Welcome to {message.chat.id}")
    try:
        text = (
            "👋 <b>မင်္ဂလာပါ!</b>\n\n"
            "🚀 <b>TikTok No Watermark Downloader</b>\n\n"
            "TikTok Link ကို ပို့လိုက်ပါ။"
        )
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9")
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)
        print("✅ Welcome Message Sent")
    except Exception as e:
        print(f"Welcome Error: {e}")

# TikTok Link Handler
@bot.message_handler(func=lambda m: True)
def handle_tiktok(message):
    print(f"📨 Received Message: {message.text}")
    if not message.text or message.text.startswith('/'):
        return
    if "tiktok.com" in message.text.lower():
        bot.reply_to(message, "⏳ ဗီဒီယို ရှာနေပါတယ်... ခဏစောင့်ပါ။")
    else:
        bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
