import os
import threading
import telebot
import requests
from flask import Flask
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is online and stable!"

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        bot.reply_to(message, "👋 မင်္ဂလာပါ သယ်ရင်း။ TikTok Link ပို့ပေးပါ၊ Watermark ဖြုတ်ပေးပါမယ်။")
    except Exception as e:
        print(f"Start CMD Error: {e}")

@bot.message_handler(func=lambda message: True)
def handle_tiktok_download(message):
    original_link = message.text.strip()
    
    if "tiktok.com" in original_link:
        # 1. စာတိုပို့ခြင်း
        try:
            msg = bot.reply_to(message, "⏳ ခဏစောင့်ပေးပါ သယ်ရင်း... ဗီဒီယို ဒေါင်းလုဒ်ဆွဲနေပါတယ်...")
        except Exception:
            return

        video_url = None
        title = "TikTok Video"

        try:
            # --------------------------------------------------
            # 💡 [လမ်းကြောင်း ၁] TikWM API သို့ လင့်ခ်ကို တိုက်ရိုက်ပို့ခြင်း (ပိုမိုငြိမ်သက်မြန်ဆန်သည်)
            # --------------------------------------------------
            try:
                api_url = "https://www.tikwm.com/api/"
                # hd: 1 စနစ်ဖြင့် တိုက်ရိုက်စမ်းသပ်သည်
                resp_api = requests.post(api_url, data={'url': original_link, 'hd': 1}, timeout=12).json()
                if resp_api.get('code') == 0:
                    data = resp_api.get('data', {})
                    video_url = data.get('play')
                    title = data.get('title', 'TikTok Video')
            except Exception as e:
                print(f"Primary API Error: {e}")

            # --------------------------------------------------
            # 💡 [လမ်းကြောင်း ၂] အကယ်၍ ပထမနည်းလမ်း မရပါက လင့်ခ်ကို ဖြည်ပြီး TikWM ဖြင့် ထပ်စမ်းခြင်း
            # --------------------------------------------------
            if not video_url:
                try:
                    print("Switching to Resolve Link Method...")
                    headers_user = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    resp_head = requests.head(original_link, allow_redirects=True, headers=headers_user, timeout=8)
                    resolved_url = resp_head.url
                    
                    api_url = "https://www.tikwm.com/api/"
                    resp_api2 = requests.post(api_url, data={'url': resolved_url, 'hd': 1}, timeout=10).json()
                    if resp_api2.get('code') == 0:
                        data = resp_api2.get('data', {})
                        video_url = data.get('play')
                        title = data.get('title', 'TikTok Video')
                except Exception as e:
                    print(f"Resolve Link Error: {e}")

            # --------------------------------------------------
            # 💡 [လမ်းကြောင်း ၃] BACKUP API (Tmate Web Scraper) စနစ်ဖြင့် နောက်ဆုံးအရန်ခံခြင်း
            # --------------------------------------------------
            if not video_url:
                try:
                    print("Switching to Backup API 2 (Tmate)...")
                    backup_url2 = f"https://api.tmate.to/download?url={original_link}"
                    resp_backup2 = requests.get(backup_url2, timeout=12).json()
                    if resp_backup2.get('success') or 'data' in resp_backup2:
                        video_url = resp_backup2.get('data', {}).get('video_hd') or resp_backup2.get('data', {}).get('video')
                        title = resp_backup2.get('data', {}).get('title') or title
                except Exception as e:
                    print(f"Backup API 2 Error: {e}")
            
            # --------------------------------------------------
            # ဗီဒီယို ပို့ခြင်းနှင့် စာဖျက်ခြင်း လုပ်ငန်းစဉ်
            # --------------------------------------------------
            if video_url:
                # 4. Buttons များ ဖန်တီးခြင်း
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(InlineKeyboardButton("🔗 View Original", url=original_link))
                markup.add(InlineKeyboardButton("👥 Admin Group", url="https://t.me/addlist/uO9JW9MOK-ZlM2M9"),
                           InlineKeyboardButton("👤 Admin Fb Acc", url="https://www.facebook.com/share/17c7QqLEUA/"))
                
                # 5. ဗီဒီယို ပို့ခြင်း
                bot.send_video(message.chat.id, video_url, caption=f"🎬 {title}\n\n✨ Powered by @{bot.get_me().username}", reply_markup=markup)
                
                # 6. User စာနှင့် Bot စာ ဖျက်ခြင်း
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.delete_message(message.chat.id, msg.message_id)
                except:
                    pass
            else:
                bot.edit_message_text("❌ ဗီဒီယို လင့်ခ်မှားနေပုံရသည်။ သို့မဟုတ် ခဏနေမှ ပြန်စမ်းကြည့်ပါ။", message.chat.id, msg.message_id)
        
        except Exception as e:
            print(f"Process Error: {e}")
            try:
                bot.edit_message_text("⚠️ Server Error တက်သွားသည်။ ခဏနေမှ ပြန်ကြိုးစားပါ။", message.chat.id, msg.message_id)
            except:
                pass
    else:
        pass

def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(timeout=60, long_polling_timeout=30, skip_pending=True)
        except Exception as e:
            print(f"Polling Crashed but Auto-Restarting: {e}")
            time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=7860)
    
