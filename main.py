import os
import uuid
import string
import random
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

# Bot configuration
BOT_TOKEN = "8527703252:AAGfjfFTIZNj6ftncKn5EOm2Ky1b-zYTz5Q"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class InstagramResetBot:
    def __init__(self):
        self.user_states = {}

    def send_password_reset(self, target: str) -> dict:
        """Send password reset request to Instagram"""
        try:
            if '@' in target:
                data = {
                    '_csrftoken': ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
                    'user_email': target,
                    'guid': str(uuid.uuid4()),
                    'device_id': str(uuid.uuid4())
                }
            else: 
                data = {
                    '_csrftoken': ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
                    'username': target,
                    'guid': str(uuid.uuid4()),
                    'device_id': str(uuid.uuid4())
                }
            
            user_agent_parts = [
                ''.join(random.choices(string.ascii_lowercase + string.digits, k=16)),
                ''.join(random.choices(string.ascii_lowercase + string.digits, k=16)),
                ''.join(random.choices(string.ascii_lowercase + string.digits, k=16)),
                ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
            ]
            
            headers = {
                'user-agent': f"Instagram 150.0.0.0.000 Android (29/10; 300dpi; 720x1440; {user_agent_parts[0]}/{user_agent_parts[1]}; {user_agent_parts[2]}; {user_agent_parts[3]}; en_GB;)"
            }
            
            response = requests.post(
                'https://i.instagram.com/api/v1/accounts/send_password_reset/',
                headers=headers,
                data=data,
                timeout=30
            )
            
            if 'obfuscated_email' in response.text or 'obfuscated_phone' in response.text:
                return {"success": True, "message": f"✅ Reset sent to `{target}`"}
            else:
                return {"success": False, "message": f"❌ Failed: `{target}`"}
                
        except Exception as e:
            return {"success": False, "message": f"❌ Error: `{target}`"}

    def create_start_keyboard(self) -> InlineKeyboardMarkup:
        """Create initial start keyboard"""
        keyboard = [
            [InlineKeyboardButton("🔓 Reset", callback_data="start_reset")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_reset_again_keyboard(self) -> InlineKeyboardMarkup:
        """Create reset again keyboard after completion"""
        keyboard = [
            [InlineKeyboardButton("🔄 Reset Another Account", callback_data="reset_again")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def start_command(self, update: Update, context: CallbackContext) -> None:
        """Send welcome message"""
        welcome_text = """🔓 Reset your Instagram account password.
        
        by @yaplol"""
        
        keyboard = self.create_start_keyboard()
        
        update.message.reply_text(
            welcome_text, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    def button_callback(self, update: Update, context: CallbackContext) -> None:
        """Handle button callbacks"""
        query = update.callback_query
        query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "start_reset" or query.data == "reset_again":
            self.show_reset_input(update, context)

    def show_reset_input(self, update: Update, context: CallbackContext):
        """Show reset input instructions"""
        user_id = update.callback_query.from_user.id
        self.user_states[user_id] = "waiting_target"
        
        text = """Send username, email, or phone number:"""
        
        update.callback_query.edit_message_text(text)

    def handle_text_message(self, update: Update, context: CallbackContext) -> None:
        """Handle text messages"""
        user_id = update.effective_user.id
        state = self.user_states.get(user_id)
        
        if state == "waiting_target":
            self.process_reset(update, context)
        else:
            keyboard = self.create_start_keyboard()
            update.message.reply_text(
                "Use the button below:",
                reply_markup=keyboard
            )

    def process_reset(self, update: Update, context: CallbackContext):
        """Process account reset"""
        user_id = update.effective_user.id
        target = update.message.text.strip()
        
        self.user_states[user_id] = None
        
        processing_msg = update.message.reply_text(f"🔄 Processing `{target}`...", parse_mode='Markdown')
        
        result = self.send_password_reset(target)
        keyboard = self.create_reset_again_keyboard()
        
        processing_msg.edit_text(
            result['message'],
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    def error_handler(self, update: Update, context: CallbackContext) -> None:
        """Log errors"""
        logger.error(f"Exception: {context.error}")

def main() -> None:
    """Start the bot"""
    print("🤖 Starting Instagram Reset Bot...")
    
    bot = InstagramResetBot()
    
    # Create updater
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher
    
    # Add handlers
    dispatcher.add_handler(CommandHandler("start", bot.start_command))
    dispatcher.add_handler(CallbackQueryHandler(bot.button_callback))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, bot.handle_text_message))
    dispatcher.add_error_handler(bot.error_handler)
    
    # Get port for webhook
    PORT = int(os.environ.get('PORT', 8443))
    
    if os.environ.get('RENDER'):
        # Webhook mode for Render
        WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}"
        print(f"🌐 Starting webhook on {WEBHOOK_URL}:{PORT}")
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
        )
        updater.idle()
    else:
        # Polling mode for local development
        print("🚀 Bot running with polling...")
        updater.start_polling()
        updater.idle()

if __name__ == "__main__":
    main()
