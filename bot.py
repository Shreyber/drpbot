import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from flask import Flask, request
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например, https://yourapp.onrender.com/webhook

message_map = {}

app = Flask(__name__)
loop = asyncio.get_event_loop()

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# === Бот-команды ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Чтобы задать вопрос, напиши /ask и далее ваш вопрос.")

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("❗ Напиши вопрос после команды /ask.")
        return

    question = " ".join(context.args)

    text = (
        f"📩 Новый вопрос от @{user.username or 'без ника'} (ID: {user.id}):\n"
        f"{question}"
    )

    admin_msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)
    message_map[admin_msg.message_id] = user.id

    await update.message.reply_text("✅ Вопрос отправлен! Мы скоро ответим.")

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    replied_id = update.message.reply_to_message.message_id
    user_id = message_map.get(replied_id)

    if user_id:
        try:
            await context.bot.send_message(chat_id=user_id, text=update.message.text)
            await update.message.reply_text("✅ Ответ отправлен.")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")

# === Flask webhook endpoint ===

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run(telegram_app.process_update(update))
    return 'ok'

# === Инициализация ===

async def setup():
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("ask", ask))
    telegram_app.add_handler(MessageHandler(filters.Chat(ADMIN_CHAT_ID) & filters.TEXT, handle_reply))

    await telegram_app.bot.set_webhook(url=WEBHOOK_URL)

if __name__ == '__main__':
    loop.run_until_complete(setup())
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
