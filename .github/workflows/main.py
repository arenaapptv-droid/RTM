import os
import subprocess
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

BOT_TOKEN = "8062783729:AAFeaUaMdYXc4rfslHvagBhNuXmYrjzByGE"

# تحميل إعدادات البث
with open("streams.json") as f:
    STREAMS = json.load(f)

processes = {}
control_messages = {}

# لوحة التحكم المحدثة
def update_control_message(context, chat_id, message_id):
    keyboard = []
    text_lines = []
    for stream_id, info in STREAMS.items():
        status = "✅ ON" if stream_id in processes else "❌ OFF"
        hls_link = f"https://YOUR-APP.railway.app/{info['output']}/index.m3u8" if stream_id in processes else "-"
        text_lines.append(f"{info['name']} [{status}]\nHLS: {hls_link}")
        keyboard.append([InlineKeyboardButton("تشغيل / إيقاف", callback_data=f"toggle|{stream_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        context.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                      text="\n\n".join(text_lines),
                                      reply_markup=reply_markup)
    except:
        pass

def start(update, context):
    update.message.reply_text("بوت البث المتعدد جاهز.\nاستخدم /control لفتح لوحة التحكم.")

def control(update, context):
    chat_id = update.message.chat_id
    keyboard = []
    text_lines = []
    for stream_id, info in STREAMS.items():
        status = "✅ ON" if stream_id in processes else "❌ OFF"
        hls_link = f"https://YOUR-APP.railway.app/{info['output']}/index.m3u8" if stream_id in processes else "-"
        text_lines.append(f"{info['name']} [{status}]\nHLS: {hls_link}")
        keyboard.append([InlineKeyboardButton("تشغيل / إيقاف", callback_data=f"toggle|{stream_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = update.message.reply_text("\n\n".join(text_lines), reply_markup=reply_markup)
    control_messages[chat_id] = msg.message_id

def button(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data.startswith("toggle|"):
        stream_id = data.split("|")[1]
        info = STREAMS[stream_id]
        if stream_id in processes:
            processes[stream_id].kill()
            del processes[stream_id]
        else:
            os.makedirs(info["output"], exist_ok=True)
            cmd = [
                "ffmpeg",
                "-re",
                "-i", info["source"],
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-tune", "zerolatency",
                "-c:a", "aac",
                "-ar", "44100",
                "-b:a", "128k",
                "-f", "hls",
                "-hls_time", "2",
                "-hls_list_size", "5",
                "-hls_flags", "delete_segments",
                f"{info['output']}/index.m3u8"
            ]
            process = subprocess.Popen(cmd)
            processes[stream_id] = process
        # تحديث لوحة التحكم فوراً
        update_control_message(context, query.message.chat_id, query.message.message_id)

def auto_update(context):
    for chat_id, message_id in control_messages.items():
        update_control_message(context, chat_id, message_id)

updater = Updater(BOT_TOKEN)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("control", control))
dp.add_handler(CallbackQueryHandler(button))

job_queue = updater.job_queue
job_queue.run_repeating(auto_update, interval=2, first=2)

updater.start_polling()
updater.idle()
