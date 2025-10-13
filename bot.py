import os
import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import requests

# ================== CONFIG ==================
BOT_TOKEN = "8256075803:AAE6rBW0f83iQqIiVHRxRYUgUhDhoeIChZU"  # Your bot token
MAIN_CHANNEL_ID = -1002628211220
BACKUP_CHANNEL_USERNAME = "pytimebruh"

# Instagram API configuration
INSTA_URL = "https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/"
HEADERS = {
    "authority": "www.instagram.com",
    "accept": "*/*",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://www.instagram.com",
    "referer": "https://www.instagram.com/accounts/password/reset/?source=fxcal",
    "user-agent": "Mozilla/5.0 (Linux; Android 10; M2101K786) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "x-ig-app-id": "1217981644879628",
}

# Store user states with timestamps
user_states = {}
STATE_TIMEOUT = 300  # 5 minutes

# Rate limiting
user_requests = {}

# ================== UTILS ==================
def cleanup_states():
    """Clean up expired user states"""
    current_time = time.time()
    expired_users = [user_id for user_id, state_data in user_states.items() 
                    if current_time - state_data['timestamp'] > STATE_TIMEOUT]
    for user_id in expired_users:
        del user_states[user_id]

def is_rate_limited(user_id: int, limit: int = 5, window: int = 3600) -> bool:
    """Check if user is rate limited"""
    now = time.time()
    
    # Clean old requests
    if user_id in user_requests:
        user_requests[user_id] = [req_time for req_time in user_requests[user_id] 
                                 if now - req_time < window]
    
    # Check limit
    if user_id in user_requests and len(user_requests[user_id]) >= limit:
        return True
    
    # Add current request
    if user_id not in user_requests:
        user_requests[user_id] = []
    user_requests[user_id].append(now)
    return False

async def is_dm(update: Update) -> bool:
    return update.effective_chat.type == "private"

async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is member of required channels"""
    try:
        member_main = await context.bot.get_chat_member(MAIN_CHANNEL_ID, user_id)
        member_backup = await context.bot.get_chat_member(f"@{BACKUP_CHANNEL_USERNAME}", user_id)
        return (member_main.status in ["member", "administrator", "creator"] and 
                member_backup.status in ["member", "administrator", "creator"])
    except Exception as e:
        logging.error(f"Membership check failed for user {user_id}: {e}")
        return False

def send_insta_reset(email: str) -> str:
    """Send Instagram password reset request"""
    data = {"email_or_username": email.strip(), "flow": "fxcal"}
    try:
        response = requests.post(INSTA_URL, headers=HEADERS, data=data, timeout=10)
        
        if response.status_code != 200:
            return f"Instagram API error: HTTP {response.status_code}"
            
        result = response.json()
        if result.get("status") == "ok":
            return "Password reset email sent successfully ✅"
        elif "errors" in result:
            errors = ", ".join([msg for sublist in result["errors"].values() for msg in sublist])
            return f"Error: {errors}"
        return "Unexpected response from Instagram"
    except requests.exceptions.Timeout:
        return "Request timeout - Instagram may be busy"
    except requests.exceptions.RequestException as e:
        return f"Connection error: {str(e)}"
    except ValueError:
        return "Invalid response from Instagram API"

# ================== COMMANDS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_dm(update):
        await update.message.reply_text("This bot only works in private messages.")
        return
    
    user_id = update.effective_user.id
    
    if not await check_membership(user_id, context):
        keyboard = [
            [InlineKeyboardButton("Main Channel", url="https://t.me/+YEObPfKXsK1hNjU9")],
            [InlineKeyboardButton("Backup Channel", url="https://t.me/pytimebruh")],
            [InlineKeyboardButton("Verify Membership", callback_data="verify_join")]
        ]
        await update.message.reply_text(
            "📋 Channel Membership Required\n\n"
            "To access Instagram Reset services, please join both channels below and verify your membership:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("📧 Start Reset", callback_data="start_reset")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    await update.message.reply_text(
        "✉️ Instagram Account Reset\n\n"
        "Professional account recovery services for Instagram.\n\n",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_dm(update):
        return
    
    keyboard = [[InlineKeyboardButton("📧 Start Reset", callback_data="start_reset")]]
    await update.message.reply_text(
        "🛠️ Service Instructions\n\n"
        "To reset an Instagram account:\n"
        "• Click 'Start Reset' button\n"
        "• Enter email or username when prompted\n"
        "• Wait for processing\n\n"
        "You can also use: /reset email@example.com",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_dm(update):
        return
    
    user_id = update.effective_user.id
    
    # Rate limiting check
    if is_rate_limited(user_id):
        await update.message.reply_text("⏳ Please wait before making another request.")
        return
    
    if not await check_membership(user_id, context):
        await start(update, context)
        return
        
    if not context.args:
        # Start the reset flow
        user_states[user_id] = {'state': 'awaiting_reset_input', 'timestamp': time.time()}
        await update.message.reply_text(
            "📧 **Enter Instagram username or email:**\n\n",
            parse_mode="Markdown"
        )
        return
        
    # Direct reset with argument
    target = " ".join(context.args)
    msg = await update.message.reply_text("🔄 Processing your reset request...")
    result = send_insta_reset(target)
    await msg.edit_text(f"**Status:** {result}", parse_mode="Markdown")

async def start_reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Rate limiting check
    if is_rate_limited(user_id):
        await query.edit_message_text("⏳ Please wait before making another request.")
        return
    
    if not await check_membership(user_id, context):
        await query.edit_message_text("Please verify your membership first using /start")
        return
    
    user_states[user_id] = {'state': 'awaiting_reset_input', 'timestamp': time.time()}
    await query.edit_message_text(
        "📧 **Enter Instagram username or email:**\n\n",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages for reset flow"""
    if not await is_dm(update):
        return
    
    user_id = update.effective_user.id
    user_message = update.message.text.strip()
    
    # Clean up old states
    cleanup_states()
    
    # Check if user is in reset flow
    if user_id in user_states and user_states[user_id]['state'] == 'awaiting_reset_input':
        # Rate limiting check
        if is_rate_limited(user_id):
            await update.message.reply_text("⏳ Please wait before making another request.")
            return
            
        # Process the reset request
        del user_states[user_id]  # Clear state
        
        msg = await update.message.reply_text("🔄 Processing your reset request...")
        result = send_insta_reset(user_message)
        
        keyboard = [[InlineKeyboardButton("🔄 Reset Another", callback_data="start_reset")]]
        await msg.edit_text(
            f"**Account:** `{user_message}`\n**Status:** {result}\n\n"
            "You can reset another account using the button below:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if await check_membership(user_id, context):
        keyboard = [
            [InlineKeyboardButton("📧 Start Reset", callback_data="start_reset")],
            [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
        ]
        await query.edit_message_text(
            "✅ **Access Granted**\n\n"
            "You now have access to Instagram Reset services.\n\n",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [
            [InlineKeyboardButton("Main Channel", url="https://t.me/+YEObPfKXsK1hNjU9")],
            [InlineKeyboardButton("Backup Channel", url="https://t.me/pytimebruh")],
            [InlineKeyboardButton("Check Again", callback_data="verify_join")]
        ]
        await query.edit_message_text(
            "❌ **Membership Not Verified**\n\n"
            "Please ensure you've joined both channels and try again:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("📧 Reset", callback_data="start_reset")]]
    await query.edit_message_text(
        "🛠️ **Service Instructions**\n\n"
        "**How to reset an Instagram account:**\n"
        "1. Click 'Start Reset' button\n"
        "2. Enter the username or email address\n"
        "3. Wait for processing\n\n"
        "**Direct command:**\n"
        "`/reset username@example.com`\n\n"
        "**Requirements:**\n"
        "• Must be member of both channels\n"
        "• Valid Instagram username/email",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== MAIN ==================
def main():
    # Configure logging for Railway
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CallbackQueryHandler(start_reset_callback, pattern="^start_reset$"))
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern="^verify_join$"))
    app.add_handler(CallbackQueryHandler(help_callback, pattern="^help$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Bot starting on Railway...")
    
    # Start the bot
    app.run_polling()

if __name__ == "__main__":
    main()
