import os
import requests
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# ====================== CONFIG ======================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

# ====================== WEBHOOK ======================
@app.route('/', methods=['GET', 'POST'])
def telegram_webhook():
    if request.method == 'POST':
        if request.headers.get('content-type') == 'application/json':
            try:
                json_string = request.get_data().decode('utf-8')
                update = telebot.types.Update.de_json(json_string)
                bot.process_new_updates([update])
                return 'OK', 200
            except Exception as e:
                print(f"Webhook Error: {e}")
                return 'Error', 500
        return 'Invalid content type', 400
    return "✅ TikTok No Watermark Bot is Running Successfully on Vercel!"


# ====================== START / HELP ======================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        welcome_text = (
            "👋 <b>မင်္ဂလာပါ သယ်ရင်းရေ...</b>\n\n"
            "🚀 <b>TikTok No Watermark Downloader Bot</b> မှ ကြိုဆိုပါတယ်။\n\n"
            "<b>အသုံးပြုနည်း:</b>\n"
            "1. TikTok ဗီဒီယို Link ကို Copy လုပ်ပါ\n"
            "2. ဒီ Chat ထဲကို Paste & Send လုပ်ပါ\n"
            "3. Watermark မပါတဲ့ HD Video ကို ချက်ချင်း ရရှိပါမယ်\n\n"
            "<i>Powered by Vercel • 24/7 Fast & Stable</i>"
        )
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
            InlineKeyboardButton("👤 Developer", url="https://www.facebook.com/share/17c7QqLEUA/")
        )
        bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        print(f"Welcome Error: {e}")


# ====================== NEW MEMBER ======================
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    try:
        for member in message.new_chat_members:
            text = (
                f"👋 <b>မင်္ဂလာပါ {member.first_name}!</b>\n\n"
                "TikTok No Watermark Group မှ ကြိုဆိုပါတယ်။\n"
                "ဗီဒီယိုဒေါင်းလုဒ်ဆွဲဖို့ Bot ကို စတင်ပါ။"
            )
            markup = InlineKeyboardMarkup()
            bot_user = bot.get_me().username
            markup.add(InlineKeyboardButton("🤖 Bot ဖွင့်ရန်", url=f"https://t.me/{bot_user}?start"))
            bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)
    except Exception as e:
        print(f"New Member Welcome Error: {e}")


# ====================== TIKTOK DOWNLOAD ======================
@bot.message_handler(func=lambda m: True)
def handle_tiktok_download(message):
    if not message.text or message.text.startswith('/'):
        return

    original_link = message.text.strip()

    if "tiktok.com" not in original_link:
        bot.reply_to(message, "💡 TikTok ဗီဒီယို Link တစ်ခုခုကို ပို့ပေးပါ။")
        return

    status_msg = bot.reply_to(message, "⏳ ဗီဒီယို ရှာနေပါတယ်... ခဏစောင့်ပါ။")

    video_url = None
    title = "TikTok Video"

    try:
        # ==================== API 1: TikWM (Primary) ====================
        try:
            resp = requests.post(
                "https://www.tikwm.com/api/",
                data={'url': original_link, 'hd': 1},
                headers=HEADERS,
                timeout=8
            ).json()
            
            if resp.get('code') == 0:
                data = resp.get('data', {})
                video_url = data.get('play')
                title = data.get('title', title)
        except Exception as e:
            print(f"TikWM Error: {e}")

        # ==================== API 2: Tiklydown (Backup) ====================
        if not video_url:
            try:
                resp = requests.get(
                    f"https://api.tiklydown.eu.org/api/download?url={original_link}",
                    headers=HEADERS,
                    timeout=8
                ).json()
                
                video_url = resp.get('data', {}).get('video', {}).get('noWatermark')
                title = resp.get('data', {}).get('title', title)
            except Exception as e:
                print(f"Tiklydown Error: {e}")

        # ==================== API 3: Tmate (Backup 2) ====================
        if not video_url:
            try:
                resp = requests.get(
                    f"https://api.tmate.to/download?url={original_link}",
                    headers=HEADERS,
                    timeout=8
                ).json()
                
                data = resp.get('data', {})
                video_url = data.get('video_hd') or data.get('video')
                title = data.get('title', title)
            except Exception as e:
                print(f"Tmate Error: {e}")

        # ==================== FINAL SEND ====================
        if video_url:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("🔗 Original Link", url=original_link),
                InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9")
            )
            
            bot.send_video(
                message.chat.id,
                video_url,
                caption=f"🎬 {title}\n\n✨ Powered by Foreverstudy",
                reply_markup=markup,
                supports_streaming=True
            )
            
            # Clean up
            try:
                bot.delete_message(message.chat.id, message.message_id)
                bot.delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
        else:
            bot.edit_message_text(
                "❌ ဗီဒီယို ရှာမတွေ့ပါ။ လင့်ခ်အသစ်တစ်ခု ပြန်စမ်းကြည့်ပါ။",
                message.chat.id,
                status_msg.message_id
            )

    except Exception as e:
        print(f"General Error: {e}")
        try:
            bot.edit_message_text(
                "⚠️ စနစ်အလုပ်များနေပါတယ်။ ခဏနေမှ ပြန်ကြိုးစားပါ။",
                message.chat.id,
                status_msg.message_id
            )
        except:
            pass


# ====================== KEEP ALIVE (Optional) ======================
@app.route('/health')
def health():
    return "Bot is healthy!", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
