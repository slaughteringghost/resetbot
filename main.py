import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)
import sqlite3
import os
import secrets
import string
import threading
from PIL import Image  # Pillow replaces deprecated imghdr

# === CONFIGURATION ===
BOT_TOKEN = "8242862841:AAHGn9y3SnoWGdjustOMyY8Bm9Ja2Vyj6Vg"
PRIVATE_CHANNEL = "-1002628211220"
BACKUP_CHANNEL = "@pytimebruh"
CHAT_GC = "@HazyGC"
BOT_USERNAME = "HazyFileRoBot"
ADMIN_USER_ID = 8275649347

CHANNELS = [
    {"name": "🔒 Main Channel", "url": "https://t.me/+YEObPfKXsK1hNjU9", "id": PRIVATE_CHANNEL},
    {"name": "📢 Backup Channel", "url": "https://t.me/pytimebruh", "id": BACKUP_CHANNEL},
    {"name": "💬 Chat Group", "url": "https://t.me/HazyGC", "id": CHAT_GC}
]

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'file_links.db')
db_lock = threading.Lock()

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= DATABASE ====================
def init_db():
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS file_links
                            (file_id TEXT PRIMARY KEY, file_type TEXT, start_param TEXT)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS users
                            (user_id INTEGER PRIMARY KEY)''')

def generate_start_param():
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))

def save_file_link(file_id, file_type, start_param):
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT OR REPLACE INTO file_links VALUES (?, ?, ?)",
                         (file_id, file_type, start_param))

def get_file_info(start_param):
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT file_id, file_type FROM file_links WHERE start_param=?", (start_param,))
            return cursor.fetchone()

def save_user(user_id):
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

def get_all_users():
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT user_id FROM users")
            return [row[0] for row in cursor.fetchall()]

def is_admin(user_id):
    return user_id == ADMIN_USER_ID

# ================= HELPERS ====================
def check_channel_membership(bot, user_id):
    try:
        for channel in CHANNELS:
            member = bot.get_chat_member(channel["id"], user_id)
            if member.status in ['left', 'kicked']:
                return False
        return True
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False

def send_file_by_type(bot, chat_id, file_id, file_type, caption=None):
    if file_type == 'photo':
        bot.send_photo(chat_id, file_id, caption=caption)
    elif file_type == 'video':
        bot.send_video(chat_id, file_id, caption=caption)
    elif file_type == 'document':
        bot.send_document(chat_id, file_id, caption=caption)
    elif file_type == 'audio':
        bot.send_audio(chat_id, file_id, caption=caption)
    elif file_type == 'voice':
        bot.send_voice(chat_id, file_id, caption=caption)
    else:
        bot.send_document(chat_id, file_id, caption=caption)

# ================= HANDLERS ====================
def start(update: Update, context):
    user_id = update.effective_user.id
    save_user(user_id)

    args = context.args
    if args:
        start_param = args[0]
        file_info = get_file_info(start_param)
        if file_info:
            file_id, file_type = file_info
            if not check_channel_membership(context.bot, user_id):
                keyboard = [
                    [InlineKeyboardButton(CHANNELS[0]["name"], url=CHANNELS[0]["url"]),
                     InlineKeyboardButton(CHANNELS[1]["name"], url=CHANNELS[1]["url"])],
                    [InlineKeyboardButton(CHANNELS[2]["name"], url=CHANNELS[2]["url"])],
                    [InlineKeyboardButton("✅ I've Joined All Channels", callback_data=f"verify_{start_param}")]
                ]
                update.message.reply_text(
                    "⚠️ *Join All Channels to Access File!*\n\n"
                    "1. Join all 3 channels above\n"
                    "2. Click 'I've Joined All Channels'\n"
                    "3. Get your file automatically",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                return
            try:
                send_file_by_type(context.bot, user_id, file_id, file_type)
            except Exception as e:
                logger.error(f"File send error: {e}")
                update.message.reply_text("❌ File not available.")
            return

    if is_admin(user_id):
        update.message.reply_text("👑 *Admin Mode* - Send files to create links", parse_mode='Markdown')
    else:
        update.message.reply_text("🤖 *Welcome!* Send /start with a link to download files.", parse_mode='Markdown')

def handle_verification(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    start_param = query.data.split('_')[1]

    if check_channel_membership(context.bot, user_id):
        file_info = get_file_info(start_param)
        if file_info:
            file_id, file_type = file_info
            try:
                send_file_by_type(context.bot, user_id, file_id, file_type)
                query.edit_message_text("✅ *File sent successfully!*", parse_mode='Markdown')
                return
            except Exception as e:
                query.edit_message_text("❌ Failed to send file")
                logger.error(f"Callback file error: {e}")
                return

    keyboard = [
        [InlineKeyboardButton(CHANNELS[0]["name"], url=CHANNELS[0]["url"]),
         InlineKeyboardButton(CHANNELS[1]["name"], url=CHANNELS[1]["url"])],
        [InlineKeyboardButton(CHANNELS[2]["name"], url=CHANNELS[2]["url"])],
        [InlineKeyboardButton("🔄 Try Again", callback_data=f"verify_{start_param}")]
    ]
    query.edit_message_text(
        "❌ *Please join all channels and try again*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def handle_file(update: Update, context):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        try:
            update.message.delete()
        except:
            pass
        return

    message = update.message
    file_id, file_type, file_name = None, None, "File"

    if message.document:
        file_id = message.document.file_id
        file_type = 'document'
        file_name = message.document.file_name or "Document"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'
        file_name = "Photo"
    elif message.video:
        file_id = message.video.file_id
        file_type = 'video'
        file_name = message.video.file_name or "Video"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = 'audio'
        file_name = message.audio.file_name or "Audio"
    elif message.voice:
        file_id = message.voice.file_id
        file_type = 'voice'
        file_name = "Voice Message"
    else:
        message.reply_text("❌ *Unsupported file type!*", parse_mode='Markdown')
        return

    loading_msg = message.reply_text("🔄 *Creating share link...*", parse_mode='Markdown')
    start_param = generate_start_param()
    save_file_link(file_id, file_type, start_param)
    share_link = f"https://t.me/{BOT_USERNAME}?start={start_param}"

    loading_msg.edit_text(
        f"✅ *Share Link Created!*\n\n"
        f"📁 *File:* `{file_name}`\n"
        f"🔗 *Share Link:*\n`{share_link}`\n\n"
        f"*Copy and share this link with users* 📤",
        parse_mode='Markdown'
    )

def broadcast(update: Update, context):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if not update.message.reply_to_message:
        update.message.reply_text("📢 Reply to a message with /broadcast", parse_mode='Markdown')
        return

    replied = update.message.reply_to_message
    users = get_all_users()
    if not users:
        update.message.reply_text("❌ No users found", parse_mode='Markdown')
        return

    success, failed = 0, 0
    msg = update.message.reply_text("📨 Starting broadcast...", parse_mode='Markdown')

    for i, uid in enumerate(users):
        try:
            if replied.text:
                context.bot.send_message(uid, replied.text)
            elif replied.photo:
                context.bot.send_photo(uid, replied.photo[-1].file_id, caption=replied.caption)
            elif replied.video:
                context.bot.send_video(uid, replied.video.file_id, caption=replied.caption)
            elif replied.document:
                context.bot.send_document(uid, replied.document.file_id, caption=replied.caption)
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast error: {e}")

        if i % 20 == 0:
            msg.edit_text(f"📨 Broadcasting...\n✅ {success} | ❌ {failed}\nProgress: {i+1}/{len(users)}",
                          parse_mode='Markdown')

    msg.edit_text(f"✅ *Broadcast Done!*\n\n✅ {success}\n❌ {failed}", parse_mode='Markdown')

def stats(update: Update, context):
    if not is_admin(update.effective_user.id):
        return
    with db_lock:
        with sqlite3.connect(DB_PATH) as conn:
            files_count = conn.execute("SELECT COUNT(*) FROM file_links").fetchone()[0]
            users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    update.message.reply_text(
        f"📊 *Bot Stats*\n👥 Users: {users_count}\n📁 Files: {files_count}",
        parse_mode='Markdown'
    )

# ================= MAIN ====================
def main():
    init_db()
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("broadcast", broadcast))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CallbackQueryHandler(handle_verification, pattern="^verify_"))
    dp.add_handler(MessageHandler(
        Filters.document | Filters.photo | Filters.video | Filters.audio | Filters.voice,
        handle_file
    ))

    print("🚀 Bot is running on Python 3.13...")
    updater.start_polling(clean=True)
    updater.idle()

if __name__ == "__main__":
    main()

