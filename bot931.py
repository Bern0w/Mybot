import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# تنظیمات
BOT_TOKEN = "8523326826:AAER43UPhRIZleTyd1IrJRoTPNWrJ3OY7Og"
CHANNEL_USERNAME = "@IranG1veaway"
CHANNEL_LINK = "https://t.me/IranG1veaway"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        # به جای ChatMemberStatus از status string استفاده می‌کنیم
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_member = await check_membership(user.id, context)

    if is_member:
        await update.message.reply_text(
            f"✅ سلام {user.first_name} عزیز!\n\n"
            "به ربات خوش اومدی! 🎉\n"
            "الان می‌تونی از امکانات ربات استفاده کنی."
        )
    else:
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ عضو شدم، بررسی کن", callback_data="check_membership")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"👋 سلام {user.first_name} عزیز!\n\n"
            "⛔️ برای استفاده از ربات باید ابتدا در کانال ما عضو بشی.\n\n"
            f"📢 کانال: {CHANNEL_LINK}\n\n"
            "بعد از عضویت، روی دکمه «عضو شدم» بزن تا بررسی بشه ✅",
            reply_markup=reply_markup,
        )


async def check_membership_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    is_member = await check_membership(user.id, context)

    if is_member:
        await query.edit_message_text(
            f"✅ سلام {user.first_name} عزیز!\n\n"
            "عضویتت تایید شد! 🎉\n"
            "الان می‌تونی از امکانات ربات استفاده کنی."
        )
    else:
        keyboard = [
            [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ عضو شدم، بررسی کن", callback_data="check_membership")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "❌ هنوز عضو کانال نشدی!\n\n"
            "لطفاً ابتدا در کانال عضو بشو و بعد دوباره بررسی کن 👇",
            reply_markup=reply_markup,
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_membership_callback, pattern="^check_membership$"))
    logger.info("ربات شروع به کار کرد...")
    app.run_polling()


if __name__ == "__main__":
    main()