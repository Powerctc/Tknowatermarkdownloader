import os
import requests
import telebot
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

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

# 🌟 Welcome Message (/start) ကို အသစ်ပြန်ပြင်ဆင်ထားသော နေရာ
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        # လှပသပ်ရပ်သော Welcome စာသားပုံစံ
        welcome_text = (
            "👋 **မင်္ဂလာပါ သယ်ရင်းရေ...**\n\n"
            "🚀 **TikTok No Watermark Downloader Bot** မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်ဗျာ။\n\n"
            "📌 **အသုံးပြုနည်းကတော့ အရမ်းရိုးရှင်းပါတယ် -**\n"
            "၁။ TikTok ထဲက ကြိုက်တဲ့ ဗီဒီယိုလင့်ခ်ကို ကူးယူပါ (Copy Link)။\n"
            "၂။ ဒီ Chat ထဲကို လင့်ခ် တိုက်ရိုက် လှမ်းပို့လိုက်ပါ (Paste & Send)။\n"
            "၃။ စက္ကန့်ပိုင်းအတွင်း Watermark မပါတဲ့ HD ဗီဒီယိုကို ချက်ချင်း ရရှိပါလိမ့်မယ်။\n\n"
            "🤖 _Powered by Vercel Webhook (24/7 Lightning Fast)_"
        )
        # 🆕 New Member ဝင်လာလျှင် Welcome Message ပို့ပေးခြင်း
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        # Welcome message ပုံစံ
        text = (
            f"👋 မင်္ဂလာပါ {new_member.first_name} ရေ!\n\n"
            f"TikTok No Watermark Downloader Group သို့ ကြိုဆိုပါတယ်ဗျာ။\n"
            f"ဗီဒီယို ဒေါင်းလုဒ်ဆွဲဖို့ အောက်ကခလုတ်ကို နှိပ်ပြီး Bot ကို စတင်လိုက်ပါဦး။"
        )
        
        # Bot စတင်ရန် ခလုတ်
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🤖 Bot စတင်ရန် (/start)", url=f"https://t.me/{bot.get_me().username}?start=start"))
        
        bot.send_message(message.chat.id, text, reply_markup=markup)
        # စာသားအောက်တွင် ပြသမည့် ခလုတ်များ
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
            InlineKeyboardButton("👤 Developer Acc", url="https://www.facebook.com/share/17c7QqLEUA/")
        )
        
        # Markdown စနစ်ဖြင့် စာသားများကို အထူ/အစောင်း လှမ်းလုပ်ပြီး ပို့ခြင်း
        bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)
        
    except Exception as e:
        print(f"Welcome Error: {e}")

# 🎬 TikTok Links များအား ဖမ်းယူပြီး ဒေါင်းလုဒ်ဆွဲပေးခြင်း
@bot.message_handler(func=lambda message: True)
def handle_tiktok_download(message):
    original_link = message.text.strip()
    
    if "tiktok.com" in original_link:
        try:
            msg = bot.reply_to(message, "⏳ ခဏစောင့်ပေးပါ သယ်ရင်း... ဗီဒီယို ဒေါင်းလုဒ်ဆွဲနေပါတယ်...")
        except Exception:
            return

        video_url = None
        title = "TikTok Video"

        try:
            # လမ်းကြောင်း ၁ - TikWM API
            try:
                api_url = "https://www.tikwm.com/api/"
                resp_api = requests.post(api_url, data={'url': original_link, 'hd': 1}, timeout=6).json()
                if resp_api.get('code') == 0:
                    data = resp_api.get('data', {})
                    video_url = data.get('play')
                    title = data.get('title', 'TikTok Video')
            except Exception as e:
                print(f"Primary API Error: {e}")

            # လမ်းကြောင်း ၂ - Tmate API (Backup)
            if not video_url:
                try:
                    backup_url = f"https://api.tmate.to/download?url={original_link}"
                    resp_backup = requests.get(backup_url, timeout=5).json()
                    if resp_backup.get('success') or 'data' in resp_backup:
                        video_url = resp_backup.get('data', {}).get('video_hd') or resp_backup.get('data', {}).get('video')
                        title = resp_backup.get('data', {}).get('title') or title
                except Exception as e:
                    print(f"Backup API Error: {e}")
            
            # ဗီဒီယို ပြန်လည်ပေးပို့ခြင်း
            if video_url:
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(InlineKeyboardButton("🔗 View Original", url=original_link))
                markup.add(InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
                           InlineKeyboardButton("👤 Admin Fb Acc", url="https://www.facebook.com/share/p/1beY6aEAqN/"))
                
                bot.send_video(message.chat.id, video_url, caption=f"🎬 {title}\n\n✨ Powered by Foreverstudy", reply_markup=markup)
                
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.delete_message(message.chat.id, msg.message_id)
                except:
                    pass
            else:
                bot.edit_message_text("❌ ဗီဒီယို ဆွဲမရဖြစ်နေသည်။ ခဏနေမှ ပြန်စမ်းကြည့်ပါ။", message.chat.id, msg.message_id)
        
        except Exception as e:
            try:
                bot.edit_message_text("⚠️ Server အလုပ်များနေသည်။ ခဏနေမှ ပြန်ကြိုးစားပါ။", message.chat.id, msg.message_id)
            except:
                pass
                
