import os
import uuid
import string
import random
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Bot configuration
BOT_TOKEN = "8256075803:AAEBqIpIC514IcY-9HptJyAJA4XIdP8CDog"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class InstagramResetBot:
    def __init__(self):
        self.user_states = {}

    async def send_password_reset(self, target: str) -> dict:
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

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send welcome message"""
        welcome_text = """🔓 Reset your Instagram account password.
        
        by @yaplol"""
        
        keyboard = self.create_start_keyboard()
        
        await update.message.reply_text(
            welcome_text, 
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data == "start_reset" or query.data == "reset_again":
            await self.show_reset_input(update, context)

    async def show_reset_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show reset input instructions"""
        user_id = update.callback_query.from_user.id
        self.user_states[user_id] = "waiting_target"
        
        text = """Send username, email, or phone number:"""
        
        await update.callback_query.edit_message_text(text)

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages"""
        user_id = update.effective_user.id
        state = self.user_states.get(user_id)
        
        if state == "waiting_target":
            await self.process_reset(update, context)
        else:
            keyboard = self.create_start_keyboard()
            await update.message.reply_text(
                "Use the button below:",
                reply_markup=keyboard
            )

    async def process_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process account reset"""
        user_id = update.effective_user.id
        target = update.message.text.strip()
        
        self.user_states[user_id] = None
        
        processing_msg = await update.message.reply_text(f"🔄 Processing `{target}`...", parse_mode='Markdown')
        
        result = await self.send_password_reset(target)
        keyboard = self.create_reset_again_keyboard()
        
        await processing_msg.edit_text(
            result['message'],
            parse_mode='Markdown',
            reply_markup=keyboard
        )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log errors"""
        logger.error(f"Exception: {context.error}")

def main() -> None:
    """Start the bot"""
    print("🤖 Starting Instagram Reset Bot...")
    
    bot = InstagramResetBot()
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text_message))
    application.add_error_handler(bot.error_handler)
    
    print("🚀 Bot running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
