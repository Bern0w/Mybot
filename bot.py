import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("8523326826:AAER43UPhRIZleTyd1IrJRoTPNWrJ3OY7Og", "8523326826:AAER43UPhRIZleTyd1IrJRoTPNWrJ3OY7Og")
CHANNEL_USERNAME = "@IranG1veaway"
CHANNEL_LINK = "https://t.me/IranG1veaway"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_membership(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_member = await check_membership(user.id, context)
    if is_member:
        await update.message.reply_text(f"✅ سلام {user.first_name}!\nخوش اومدی 🎉")
    else:
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check")],
        ]
        await update.message.reply_text(
            f"👋 سلام {user.first_name}!\n\n⛔️ اول باید عضو کانال بشی:\n{CHANNEL_LINK}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    is_member = await check_membership(user.id, context)
    if is_member:
        await query.edit_message_text(f"✅ {user.first_name} عضویتت تایید شد! 🎉")
    else:
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check")],
        ]
        await query.edit_message_text(
            "❌ هنوز عضو نشدی!\nاول عضو بشو بعد بزن ✅",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_callback, pattern="^check$"))
    print("ربات شروع به کار کرد!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
