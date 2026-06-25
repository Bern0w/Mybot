from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = "8523326826:AAER43UPhRIZleTyd1IrJRoTPNWrJ3OY7Og"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn = KeyboardButton(
        text="📱 ارسال شماره تماس",
        request_contact=True
    )

    keyboard = ReplyKeyboardMarkup(
        [[btn]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(
        "🇮🇷 برای استفاده از ربات ابتدا شماره تلفن خود را ارسال کنید:",
        reply_markup=keyboard
    )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact

    if not contact:
        return

    phone = contact.phone_number

    if phone.startswith("+98") or phone.startswith("98") or phone.startswith("09"):
        await update.message.reply_text(
            f"✅ تایید شد\n\nشماره شما:\n{phone}\n\nبه ربات خوش آمدید."
        )

    else:
        await update.message.reply_text(
            "❌ فقط کاربران دارای شماره ایرانی مجاز به استفاده از ربات هستند."
        )

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

print("Bot Started...")
app.run_polling()
