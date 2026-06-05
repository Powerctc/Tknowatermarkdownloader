import os
import requests
import telebot
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=False) # Vercel မှာ Thread မရလို့ False ထားရပါမည်

# Telegram ဘက်က လှမ်းပို့မည့် Route
@app.route('/api/webhook', methods=['POST'])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Invalid Request', 403

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        bot.reply_to(message, "👋 မင်္ဂလာပါ သယ်ရင်း။ TikTok Link ပို့ပေးပါ၊ Watermark ဖြုတ်ပေးပါမယ်။ (Vercel Webhook စနစ်)")
    except Exception as e:
        print(f"Start Error: {e}")

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
            # လမ်းကြောင်း ၁ - TikWM API တိုက်ရိုက်ပို့ခြင်း
            try:
                api_url = "https://www.tikwm.com/api/"
                resp_api = requests.post(api_url, data={'url': original_link, 'hd': 1}, timeout=10).json()
                if resp_api.get('code') == 0:
                    data = resp_api.get('data', {})
                    video_url = data.get('play')
                    title = data.get('title', 'TikTok Video')
            except Exception as e:
                print(f"API 1 Error: {e}")

            # လမ်းကြောင်း ၂ - Tmate API အရန်စနစ်
            if not video_url:
                try:
                    backup_url = f"https://api.tmate.to/download?url={original_link}"
                    resp_backup = requests.get(backup_url, timeout=10).json()
                    if resp_backup.get('success') or 'data' in resp_backup:
                        video_url = resp_backup.get('data', {}).get('video_hd') or resp_backup.get('data', {}).get('video')
                        title = resp_backup.get('data', {}).get('title') or title
                except Exception as e:
                    print(f"API 2 Error: {e}")
            
            # ဗီဒီယို ပို့ခြင်း
            if video_url:
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(InlineKeyboardButton("🔗 View Original", url=original_link))
                markup.add(InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
                           InlineKeyboardButton("👤 Admin Fb Acc", url="https://www.facebook.com/share/17c7QqLEUA/"))
                
                bot.send_video(message.chat.id, video_url, caption=f"🎬 {title}\n\n✨ Powered by Vercel Webhook", reply_markup=markup)
                
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.delete_message(message.chat.id, msg.message_id)
                except:
                    pass
            else:
                bot.edit_message_text("❌ ဗီဒီယို လင့်ခ်မှားနေပုံရသည်။ သို့မဟုတ် ခဏနေမှ ပြန်စမ်းကြည့်ပါ။", message.chat.id, msg.message_id)
        
        except Exception as e:
            try:
                bot.edit_message_text("⚠️ Server Error တက်သွားသည်။ ခဏနေမှ ပြန်ကြိုးစားပါ။", message.chat.id, msg.message_id)
            except:
                pass

# Vercel Serverless အတွက် အဓိက ဝင်ပေါက်
@app.route('/')
def index():
    return "Webhook Server is Active!"
                  
