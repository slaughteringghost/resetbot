import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import sqlite3
import secrets
import string
import asyncio
from threading import Lock
import os

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8242862841:AAHGn9y3SnoWGdjustOMyY8Bm9Ja2Vyj6Vg"
PRIVATE_CHANNEL = "-1002628211220"  # Main channel
BACKUP_CHANNEL = "@pytimebruh"  # Backup channel
CHAT_GC = "@HazyGC"  # Group chat
BOT_USERNAME = "HazyFileRoBot"
ADMIN_USER_ID = 8275649347

# Channel configurations
CHANNELS = [
    {"name": "🔒 Main Channel", "url": "https://t.me/+YEObPfKXsK1hNjU9", "id": PRIVATE_CHANNEL},
    {"name": "📢 Backup Channel", "url": "https://t.me/pytimebruh", "id": BACKUP_CHANNEL},
    {"name": "💬 Chat Group", "url": "https://t.me/HazyGC", "id": CHAT_GC}
]

db_lock = Lock()

def init_db():
    with db_lock:
        if os.path.exists('file_links.db'):
            try:
                with sqlite3.connect('file_links.db') as conn:
                    cursor = conn.execute("PRAGMA table_info(file_links)")
                    columns = [row[1] for row in cursor.fetchall()]
                    if len(columns) != 3 or columns != ['file_id', 'file_type', 'start_param']:
                        os.remove('file_links.db')
                        logger.info("Old database removed, creating new one...")
            except Exception as e:
                logger.error(f"Database check error: {e}")
                os.remove('file_links.db')
        
        with sqlite3.connect('file_links.db') as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS file_links
                         (file_id TEXT PRIMARY KEY, file_type TEXT, start_param TEXT)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS users
                         (user_id INTEGER PRIMARY KEY)''')
            logger.info("Database initialized successfully")

def generate_start_param():
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))

def save_file_link(file_id, file_type, start_param):
    with db_lock:
        with sqlite3.connect('file_links.db') as conn:
            conn.execute("INSERT OR REPLACE INTO file_links VALUES (?, ?, ?)",
                       (file_id, file_type, start_param))

def get_file_info(start_param):
    with db_lock:
        with sqlite3.connect('file_links.db') as conn:
            cursor = conn.execute("SELECT file_id, file_type FROM file_links WHERE start_param = ?", (start_param,))
            return cursor.fetchone()

def save_user(user_id):
    with db_lock:
        with sqlite3.connect('file_links.db') as conn:
            conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

def get_all_users():
    with db_lock:
        with sqlite3.connect('file_links.db') as conn:
            cursor = conn.execute("SELECT user_id FROM users")
            return [row[0] for row in cursor.fetchall()]

def is_admin(user_id):
    return user_id == ADMIN_USER_ID

async def check_channel_membership(user_id: int, context: CallbackContext) -> bool:
    """Check if user is member of all required channels"""
    try:
        for channel in CHANNELS:
            member = await context.bot.get_chat_member(channel["id"], user_id)
            if member.status in ['left', 'kicked']:
                return False
        return True
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False

async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    save_user(user_id)
    
    if context.args:
        start_param = context.args[0]
        file_info = get_file_info(start_param)
        
        if file_info:
            file_id, file_type = file_info
            
            if not await check_channel_membership(user_id, context):
                # Create buttons in 2-1 layout
                keyboard = [
                    [InlineKeyboardButton(CHANNELS[0]["name"], url=CHANNELS[0]["url"]),
                     InlineKeyboardButton(CHANNELS[1]["name"], url=CHANNELS[1]["url"])],
                    [InlineKeyboardButton(CHANNELS[2]["name"], url=CHANNELS[2]["url"])],
                    [InlineKeyboardButton("✅ I've Joined All Channels", callback_data=f"verify_{start_param}")]
                ]
                await update.message.reply_text(
                    "⚠️ *Join All Channels to Access File!*\n\n"
                    "1. Join all 3 channels above\n"
                    "2. Click 'I've Joined All Channels'\n"
                    "3. Get your file automatically",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                return
            
            # User is member of all channels, send file directly
            try:
                await send_file_by_type(update.message, file_id, file_type)
                return
            except Exception as e:
                await update.message.reply_text("❌ File not available")
                logger.error(f"File send error: {e}")
                return
    
    # Normal start command
    if is_admin(user_id):
        await update.message.reply_text("👑 *Admin Mode* - Send files to create links", parse_mode='Markdown')
    else:
        await update.message.reply_text("🤖 *Welcome!* Send /start with file link to download files.", parse_mode='Markdown')

async def send_file_by_type(message, file_id, file_type):
    """Send file based on type - optimized function"""
    send_methods = {
        'photo': message.reply_photo,
        'video': message.reply_video,
        'document': message.reply_document,
        'audio': message.reply_audio,
        'voice': message.reply_voice
    }
    
    method = send_methods.get(file_type, message.reply_document)
    await method(file_id)

async def handle_verification(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    start_param = query.data.split('_')[1]
    
    if await check_channel_membership(user_id, context):
        file_info = get_file_info(start_param)
        if file_info:
            file_id, file_type = file_info
            try:
                await send_file_by_type(context.bot, user_id, file_id, file_type)
                await query.edit_message_text("✅ *File sent successfully!*", parse_mode='Markdown')
                return
            except Exception as e:
                await query.edit_message_text("❌ Failed to send file")
                logger.error(f"Callback file error: {e}")
                return
    
    # User hasn't joined all channels
    keyboard = [
        [InlineKeyboardButton(CHANNELS[0]["name"], url=CHANNELS[0]["url"]),
         InlineKeyboardButton(CHANNELS[1]["name"], url=CHANNELS[1]["url"])],
        [InlineKeyboardButton(CHANNELS[2]["name"], url=CHANNELS[2]["url"])],
        [InlineKeyboardButton("🔄 Try Again", callback_data=f"verify_{start_param}")]
    ]
    await query.edit_message_text(
        "❌ *Please join all channels and try again*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def send_file_by_type(bot, chat_id, file_id, file_type):
    """Send file based on type - for bot context"""
    send_methods = {
        'photo': bot.send_photo,
        'video': bot.send_video,
        'document': bot.send_document,
        'audio': bot.send_audio,
        'voice': bot.send_voice
    }
    
    method = send_methods.get(file_type, bot.send_document)
    await method(chat_id=chat_id, **{file_type: file_id})

async def handle_file(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        try:
            await update.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
        return
    
    message = update.message
    
    try:
        # Quick file detection
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
            await message.reply_text("❌ *Unsupported file type!*", parse_mode='Markdown')
            return
        
        # Fast processing without multiple loading messages
        loading_msg = await message.reply_text("🔄 *Creating share link...*", parse_mode='Markdown')
        
        start_param = generate_start_param()
        save_file_link(file_id, file_type, start_param)
        
        share_link = f"https://t.me/{BOT_USERNAME}?start={start_param}"
        
        await loading_msg.edit_text(
            f"✅ *Share Link Created!*\n\n"
            f"📁 *File:* `{file_name}`\n"
            f"🔗 *Share Link:*\n`{share_link}`\n\n"
            f"*Copy and share this link with users* 📤",
            parse_mode='Markdown'
        )
        
        logger.info(f"Link generated: {share_link}")
        
    except Exception as e:
        logger.error(f"Error in handle_file: {e}")
        await message.reply_text("❌ *Error generating link! Please try again.*", parse_mode='Markdown')

async def broadcast(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("📢 Reply to a message with /broadcast", parse_mode='Markdown')
        return
    
    replied_message = update.message.reply_to_message
    users = get_all_users()
    
    if not users:
        await update.message.reply_text("❌ No users found", parse_mode='Markdown')
        return
    
    progress_msg = await update.message.reply_text(f"📨 *Starting broadcast...*\n\n0/{len(users)} users", parse_mode='Markdown')
    
    success = 0
    failed = 0
    
    # Batch processing for better performance
    for i, user_id in enumerate(users):
        try:
            if replied_message.text:
                await context.bot.send_message(user_id, replied_message.text)
            elif replied_message.photo:
                await context.bot.send_photo(user_id, replied_message.photo[-1].file_id, caption=replied_message.caption)
            elif replied_message.video:
                await context.bot.send_video(user_id, replied_message.video.file_id, caption=replied_message.caption)
            elif replied_message.document:
                await context.bot.send_document(user_id, replied_message.document.file_id, caption=replied_message.caption)
            elif replied_message.audio:
                await context.bot.send_audio(user_id, replied_message.audio.file_id, caption=replied_message.caption)
            elif replied_message.voice:
                await context.bot.send_voice(user_id, replied_message.voice.file_id, caption=replied_message.caption)
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast error for user {user_id}: {e}")
        
        # Update progress every 20 users to reduce API calls
        if i % 20 == 0 or i == len(users) - 1:
            try:
                await progress_msg.edit_text(
                    f"📨 *Broadcasting...*\n\n"
                    f"✅ Success: {success}\n"
                    f"❌ Failed: {failed}\n"
                    f"📊 Progress: {i+1}/{len(users)}",
                    parse_mode='Markdown'
                )
            except Exception:
                pass
        
        # Small delay to avoid rate limits
        await asyncio.sleep(0.03)
    
    await progress_msg.edit_text(
        f"✅ *Broadcast Completed!*\n\n"
        f"✅ Success: {success}\n"
        f"❌ Failed: {failed}\n"
        f"📨 Total: {len(users)} users",
        parse_mode='Markdown'
    )

async def stats(update: Update, context: CallbackContext):
    if not is_admin(update.effective_user.id):
        return
    
    with db_lock:
        with sqlite3.connect('file_links.db') as conn:
            files_count = conn.execute("SELECT COUNT(*) FROM file_links").fetchone()[0]
            users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    
    await update.message.reply_text(
        f"📊 *Bot Statistics*\n\n"
        f"👥 Total Users: {users_count}\n"
        f"📁 Shared Files: {files_count}",
        parse_mode='Markdown'
    )

def main():
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(handle_verification, pattern="^verify_"))
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE,
        handle_file
    ))
    
    print("🚀 Bot is running smoothly...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
