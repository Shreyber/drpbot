import os
from dotenv import load_dotenv
from telegram import (
    Update,
    WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters
)

load_dotenv()

# === Переменные окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
QUESTIONS_THEME_ID = 2
SMS_THEME_ID = 5

message_map = {}  # message_id в админ-чате -> user_id
user_state = {}  # user_id -> состояние пользователя

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.message.from_user.id] = "main_menu"
    await update.message.reply_text("Выберите действие:", reply_markup=main_menu_keyboard())

# === Обработчики кнопок ===
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "main_menu":
        user_state[query.from_user.id] = "main_menu"
        # Возвращаем пользователя в главное меню
        await query.edit_message_text(
            "Выберите действие:",
            reply_markup=main_menu_keyboard()
        )
    elif query.data == "ask":
        user_state[query.from_user.id] = "awaiting_question"
        await query.edit_message_text(f"✍️ Напишите ваш вопрос одним сообщением. По срочным вопросам связывайтесь с руководством лагеря или вожатыми отрядов напрямую. <a href='https://drpolenovo.ru/informatsija-o-lagere/chasto-zadavaemye-voprosy.html'>Часто задаваемые вопросы.</a>", reply_markup=back_keyboard(), parse_mode="HTML")
    elif query.data == "sms":
        user_state[query.from_user.id] = "awaiting_sms"
        await query.edit_message_text("🎙️Напишите ваш привет одним сообщением. Не забудьте указать фамилию и имя ребенка, провинцию, название музыкальной композиции с исполнителем.", reply_markup=back_keyboard())
    elif query.data == "merch":
        await query.message.reply_text("👕 Наш мерч можно посмотреть на сайте: drpmerch.vercel.app")

# === Обработка текстовых сообщений от пользователей ===
async def handle_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = update.effective_user

    if user_state.get(user_id) == "awaiting_question":
        user_msg = update.message
        del user_state[user_id]  # сбрасываем состояние

        text = (
            f"📩 Вопрос от {user.full_name} @{user.username}:\n"
            f"{update.message.text}"
        )

        admin_msg = await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text,
            message_thread_id=QUESTIONS_THEME_ID
        )
        message_map[admin_msg.message_id] = (user.id, user_msg.message_id)

        await update.message.reply_text("✅ Вопрос отправлен. Ожидайте ответа.")
        await start(update, context)
    elif user_state.get(user_id) == "awaiting_sms":
        user_msg = update.message
        del user_state[user_id]  # сбрасываем состояние

        text = (
            f"📩 СМС привет от {user.full_name} @{user.username}:\n"
            f"{update.message.text}"
        )

        admin_msg = await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text,
            message_thread_id=SMS_THEME_ID
        )
        #message_map[admin_msg.message_id] = (user.id, user_msg.message_id)

        await update.message.reply_text("✅ СМС принята. Все приветы обязательно будут озвучены в эфире!")
        await start(update, context)
    else:
        # Если пользователь не в режиме "задать вопрос"
        try:
            await update.message.delete()  # удаляем любое несанкционированное сообщение
        except Exception as e:
            print(f"Ошибка при удалении: {e}")

# === Обработка ответа администратора ===
async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return
    if update.message.message_thread_id != QUESTIONS_THEME_ID:
        await update.message.reply_text("❌ Ответы можно отправлять только на вопросы в теме вопросов.")
        return

    replied_id = update.message.reply_to_message.message_id

    if replied_id is None:
        await update.message.reply_text("❌ Не удалось найти пользователя для этого вопроса.")
        return

    try:
        user_id, user_msg_id = message_map.get(replied_id)
        await context.bot.send_message(chat_id=user_id, text=update.message.text, reply_to_message_id=user_msg_id)
        await update.message.reply_text("✅ Ответ отправлен пользователю.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке: {e}")

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💬 СМСочки для деточки", callback_data="sms")
        ],
        [
            InlineKeyboardButton("👕 Посмотреть мерч",  web_app=WebAppInfo(url="https://drpmerch.vercel.app"))
        ],
        [
            InlineKeyboardButton("❓ Задать вопрос", callback_data="ask")
        ]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")]])

# === Инициализация приложения ===
def setup():
    telegram_app = Application.builder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CallbackQueryHandler(handle_buttons))
    telegram_app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, handle_user_text))
    telegram_app.add_handler(MessageHandler(filters.Chat(ADMIN_CHAT_ID) & filters.REPLY & filters.TEXT, handle_reply))
    telegram_app.run_polling()

# === Запуск ===
if __name__ == "__main__":
    setup()