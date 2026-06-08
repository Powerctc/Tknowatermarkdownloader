import os
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN is missing!")
    # ဒီနေရာမှာ ရပ်သွားအောင် လုပ်ထားတာ

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            print("Webhook Error:", str(e))
            return 'ERROR', 500
    return "✅ TikTok No Watermark Bot is Running on Vercel!"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = "👋 <b>မင်္ဂလာပါ!</b>\n\n🚀 <b>No Watermark TikTok Downloader</b> အဆင်သင့်ဖြစ်နေပါပြီ။\nTikTok Link ကို ပို့လိုက်ပါ။"
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"))
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_tiktok(message):
    if not message.text or message.text.startswith('/'):
        return
    if "tiktok.com" in message.text.lower():
        bot.reply_to(message, "⏳ ဗီဒီယို ရှာနေပါတယ်... ခဏစောင့်ပါ။")
    else:
        bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")

@app.route('/health')
def health():
    return "Bot is healthy!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
