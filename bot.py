import os
import time
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests

# === Spam Protection (Silent) ===
MAX_REQUESTS = 12
TIME_WINDOW = 60
blocked_users = set()
user_requests = defaultdict(list)

def check_and_block(user_id: int) -> bool:
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
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://www.instagram.com',
    'referer': 'https://www.instagram.com/accounts/password/reset/?source=fxcal',
    'user-agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    'x-asbd-id': '129477',
    'x-csrftoken': 'YOUR_CSRF_TOKEN_HERE',  # ⚠️ REPLACE
    'x-ig-app-id': '1217981644879628',
    'x-instagram-ajax': '1015181662',
    'x-requested-with': 'XMLHttpRequest',
    'cookie': 'csrftoken=YOUR_CSRF_TOKEN_HERE; mid=...; ig_did=...; datr=...'  # ⚠️ REPLACE
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use: /rst <email_or_username>")

async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not check_and_block(user_id):
        return  # Silent block

    if not context.args:
        await update.message.reply_text("UsageId: /rst <email_or_username>")
        return

    target = context.args[0].strip()
    if len(target) < 3:
        await update.message.reply_text("Invalid input.")
        return

    try:
        data = {'email_or_username': target, 'flow': 'fxcal'}
        response = requests.post(INSTA_URL, headers=HEADERS, data=data, timeout=10)
        if response.status_code == 200 and response.json().get("status") == "ok":
            await update.message.reply_text("✅ Done.")
        else:
            await update.message.reply_text("⚠️ Failed.")
    except Exception:
        await update.message.reply_text("💥 Error.")

# Optional admin unblock
async def unblock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    YOUR_USER_ID = 123456789  # 👈 Replace with your Telegram ID
    if update.effective_user.id != YOUR_USER_ID:
        return
    if context.args:
        try:
            uid = int(context.args[0])
            blocked_users.discard(uid)
            user_requests.pop(uid, None)
            await update.message.reply_text(f"✅ Unblocked {uid}")
        except:
            await update.message.reply_text("UsageId: /unblock <user_id>")
    else:
        await update.message.reply_text("UsageId: /unblock <user_id>")

# === Main ===
def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rst", reset_handler))
    app.add_handler(CommandHandler("unblock", unblock))

    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
        # v21+ uses .run_webhook() same as before
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8443)),
            webhook_url=f"{webhook_url}/{token}",
            secret_token=None  # optional
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
