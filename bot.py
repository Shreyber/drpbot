import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

# Связь: ID сообщения в админ-чате -> ID пользователя
message_map = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Чтобы задать вопрос, напишите команду:\n\n/ask ваш вопрос")

# Команда /ask
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if not args:
        await update.message.reply_text("Пожалуйста, напишите вопрос после команды /ask.")
        return

    question = " ".join(args)

    # Формируем сообщение для админов
    text = (
        f"📩 Новый вопрос от @{user.username or 'без ника'} (ID: {user.id}):\n\n"
        f"{question}"
    )

    admin_msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)
    message_map[admin_msg.message_id] = user.id

    await update.message.reply_text("Ваш вопрос отправлен! Мы скоро ответим.")

# Ответ модератора в админ-чате
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    original_msg_id = update.message.reply_to_message.message_id
    user_id = message_map.get(original_msg_id)

    if user_id:
        try:
            await context.bot.send_message(chat_id=user_id, text=update.message.text)
            await update.message.reply_text("✅ Ответ отправлен пользователю.")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при отправке ответа: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(MessageHandler(filters.Chat(ADMIN_CHAT_ID) & filters.TEXT, handle_admin_reply))

    app.run_polling()

if __name__ == "__main__":
    main()
