import time
import requests
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)

# === Telegram Bot Token ===
token = "YOUR_NEW_TOKEN_HERE"  # ⚠️ Replace this with your real Telegram bot token

# === Spam Protection ===
MAX_REQUESTS = 12
TIME_WINDOW = 60
blocked_users = set()
user_requests = defaultdict(list)

def check_and_block(user_id: int) -> bool:
    """Basic anti-spam protection."""
    if user_id in blocked_users:
        return False
    now = time.time()
    user_requests[user_id] = [t for t in user_requests[user_id] if now - t < TIME_WINDOW]
    if len(user_requests[user_id]) >= MAX_REQUESTS:
        blocked_users.add(user_id)
        return False
    user_requests[user_id].append(now)
    return True


# === Instagram Config ===
INSTA_URL = "https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/"
HEADERS = {
    'authority': 'www.instagram.com',
    'accept': '*/*',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://www.instagram.com',
    'referer': 'https://www.instagram.com/accounts/password/reset/?source=fxcal',
    'user-agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    'x-asbd-id': '129477',
    'x-csrftoken': 'BbJnjd.Jnw20VyXU0qSsHLV',
    'x-ig-app-id': '1217981644879628',
    'x-instagram-ajax': '1015181662',
    'x-requested-with': 'XMLHttpRequest',
    'cookie': 'csrftoken="BbJnjd.Jnw20VyXU0qSsHLV"; mid="ZpZMygABAAH0176Z6fWvYiNly3y2"; ig_did="BBBA0292-07BC-49C8-ACF4-AE242AE19E97"; datr="ykyWZhA9CacxerPITDOHV5AE"'
}


# === Conversation States ===
ASK_USERNAME = 1


# === Common Instagram request logic ===
async def send_recovery_request(update: Update, target: str):
    """Handles sending the password recovery request."""
    await update.message.reply_text("🔄 Sending recovery request...")

    try:
        data = {'email_or_username': target, 'flow': 'fxcal'}
        response = requests.post(INSTA_URL, headers=HEADERS, data=data, timeout=10)

        if response.status_code == 200 and response.json().get("status") == "ok":
            await update.message.reply_text("✅ Recovery link sent successfully!")
        else:
            await update.message.reply_text("⚠️ Failed to send recovery request.")
    except Exception:
        await update.message.reply_text("💥 Error occurred while sending request.")


# === Inline (DM) Flow ===
async def reset_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered in private chat — shows inline button."""
    if update.effective_chat.type != "private":
        await update.message.reply_text("⚠️ Use /rst in group chats instead.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    if not check_and_block(user_id):
        await update.message.reply_text("🚫 You are blocked for spam.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton("➡️ Enter Username / Email", callback_data="enter_username")]]
    await update.message.reply_text(
        "📩 Click below to start the Instagram recovery process:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASK_USERNAME


async def ask_username_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """After pressing the inline button, ask for username/email."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📝 Please send your *Instagram username or email address*:", parse_mode="Markdown")
    return ASK_USERNAME


async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the user’s reply after inline click."""
    target = update.message.text.strip()
    if len(target) < 3:
        await update.message.reply_text("❌ Invalid input. Try again.")
        return ASK_USERNAME

    await send_recovery_request(update, target)
    return ConversationHandler.END


# === Group Flow (/rst command) ===
async def rst_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered in group chats — expects /rst <username>"""
    if update.effective_chat.type == "private":
        await update.message.reply_text("ℹ️ Use /reset in private chat for inline flow.")
        return

    user_id = update.effective_user.id
    if not check_and_block(user_id):
        await update.message.reply_text("🚫 You are blocked for spam.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/rst <email_or_username>`", parse_mode="Markdown")
        return

    target = context.args[0].strip()
    if len(target) < 3:
        await update.message.reply_text("❌ Invalid input.")
        return

    await send_recovery_request(update, target)


# === Cancel command (for inline flow) ===
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


# === Start message ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔰 *Instagram Recovery Bot*\n\n"
        "📩 Use:\n"
        "• `/reset` in *DMs* (shows inline button)\n"
        "• `/rst <email_or_username>` in *groups*\n\n"
        "⚠️ Don’t spam requests.",
        parse_mode="Markdown"
    )


# === Main ===
def main():
    app = Application.builder().token(token).build()

    # Inline (DM) handler
    reset_conv = ConversationHandler(
        entry_points=[CommandHandler("reset", reset_start)],
        states={
            ASK_USERNAME: [
                CallbackQueryHandler(ask_username_callback, pattern="enter_username"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username),
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(reset_conv)
    app.add_handler(CommandHandler("rst", rst_command))

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
