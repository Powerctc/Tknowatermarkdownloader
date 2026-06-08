import os
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise Exception("BOT_TOKEN environment variable is missing!")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        try:
            update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            print("Webhook Error:", e)
            return 'ERROR', 500
    return "✅ No Watermark TikTok Bot is Running on Vercel!"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 <b>မင်္ဂလာပါ!</b>\n\n"
        "🚀 <b>No Watermark TikTok Downloader</b>\n\n"
        "TikTok Link ကို တိုက်ရိုက် Paste လုပ်ပြီး ပို့လိုက်ပါ။"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
        InlineKeyboardButton("👤 Developer", url="https://www.facebook.com/share/17c7QqLEUA/")
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup)

# TikTok Handler (အတိုချုံး ဗားရှင်း)
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    if not message.text or message.text.startswith('/'):
        return
    if "tiktok.com" in message.text:
        bot.reply_to(message, "⏳ ဗီဒီယို ရှာနေပါတယ်...")
    else:
        bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")

@app.route('/health')
def health():
    return "Bot is alive!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
