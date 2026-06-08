import os
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

print("✅ Bot Started Successfully!")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        try:
            print("📥 Received Update")
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            print(f"❌ Webhook Error: {e}")
            return 'ERROR', 500
    return "✅ Bot is Running!"

# ==================== START ====================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    print("📤 Sending Welcome Message")
    text = (
        "👋 <b>မင်္ဂလာပါ သယ်ရင်းရေ...</b>\n\n"
        "🚀 <b>TikTok No Watermark Downloader</b>\n\n"
        "TikTok Link ကို တိုက်ရိုက် Paste လုပ်ပါ။"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"))
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

# ==================== TIKTOK DOWNLOAD ====================
@bot.message_handler(func=lambda m: True)
def handle_tiktok(message):
    if not message.text or message.text.startswith('/'):
        return

    original_link = message.text.strip()
    print(f"📨 TikTok Link Received: {original_link}")

    if "tiktok.com" not in original_link.lower():
        bot.reply_to(message, "💡 TikTok Link တစ်ခုခုကို ပို့ပေးပါ။")
        return

    status_msg = bot.reply_to(message, "⏳ ဗီဒီယို ရှာနေပါတယ်... ခဏစောင့်ပါ။")

    video_url = None
    title = "TikTok Video"

    try:
        # API 1: TikWM (Best)
        try:
            resp = requests.post("https://www.tikwm.com/api/", 
                               data={'url': original_link, 'hd': 1}, 
                               headers=HEADERS, timeout=10).json()
            if resp.get('code') == 0:
                data = resp.get('data', {})
                video_url = data.get('play')
                title = data.get('title', title)
        except Exception as e:
            print(f"TikWM Error: {e}")

        # API 2: Tiklydown
        if not video_url:
            try:
                resp = requests.get(f"https://api.tiklydown.eu.org/api/download?url={original_link}", 
                                  headers=HEADERS, timeout=10).json()
                video_url = resp.get('data', {}).get('video', {}).get('noWatermark')
            except Exception as e:
                print(f"Tiklydown Error: {e}")

        # API 3: Tmate (Backup)
        if not video_url:
            try:
                resp = requests.get(f"https://api.tmate.to/download?url={original_link}", 
                                  headers=HEADERS, timeout=10).json()
                data = resp.get('data', {})
                video_url = data.get('video_hd') or data.get('video')
            except Exception as e:
                print(f"Tmate Error: {e}")

        if video_url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔗 Original Video", url=original_link))
            bot.send_video(message.chat.id, video_url, 
                         caption=f"🎬 {title}\n\n✅ No Watermark", 
                         reply_markup=markup)
            print("✅ Video Sent Successfully")
            
            # Delete messages
            try:
                bot.delete_message(message.chat.id, status_msg.message_id)
                bot.delete_message(message.chat.id, message.message_id)
            except:
                pass
        else:
            bot.edit_message_text("❌ ဗီဒီယို ရှာမတွေ့ပါ။ နောက်တစ်ခါ ပြန်စမ်းကြည့်ပါ။", 
                                message.chat.id, status_msg.message_id)

    except Exception as e:
        print(f"General Error: {e}")
        try:
            bot.edit_message_text("⚠️ စနစ်မှာ ပြဿနာ ဖြစ်နေပါတယ်။ ခဏနေမှ ပြန်ကြိုးစားပါ။", 
                                message.chat.id, status_msg.message_id)
        except:
            pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
