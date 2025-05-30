import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# === Переменные окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# === Flask-приложение для Render ===
app = Flask(__name__)

# === Telegram Application ===
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
message_map = {}  # message_id в админ-чате -> user_id

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Чтобы задать вопрос, используй команду:\n/ask ваш вопрос")

# === Команда /ask ===
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("❗ Напиши вопрос после команды /ask.")
        return

    question = " ".join(context.args)
    text = f"📩 Вопрос от @{user.username or 'без ника'} (ID: {user.id}):\n{question}"

    admin_msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)
    message_map[admin_msg.message_id] = user.id

    await update.message.reply_text("✅ Вопрос отправлен! Мы скоро ответим.")

# === Обработка ответа администратора ===
async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    replied_id = update.message.reply_to_message.message_id
    user_id = message_map.get(replied_id)

    if user_id:
        try:
            await context.bot.send_message(chat_id=user_id, text=update.message.text)
            await update.message.reply_text("✅ Ответ отправлен пользователю.")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при отправке: {e}")

# === Flask endpoint для Telegram Webhook ===
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)

    try:
        # Создаём новый event loop и устанавливаем его текущим
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Обрабатываем обновление синхронно
        loop.run_until_complete(telegram_app.process_update(update))
    finally:
        # Не закрываем loop — чтобы избежать ошибки "event loop is closed"
        # loop.close() — НЕ НАДО!
        pass

    return "ok", 200

# === Инициализация приложения ===
async def setup():
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("ask", ask))
    telegram_app.add_handler(MessageHandler(filters.Chat(ADMIN_CHAT_ID) & filters.TEXT, handle_reply))

    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=WEBHOOK_URL)
    print("✅ Webhook установлен:", WEBHOOK_URL)

# === Запуск ===
if __name__ == "__main__":
    asyncio.run(setup())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
