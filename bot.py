import os
import json
import logging
import random
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
NOTIFICATION_CHAT_ID = os.getenv("NOTIFICATION_CHAT_ID")
if NOTIFICATION_CHAT_ID:
    try:
        NOTIFICATION_CHAT_ID = int(NOTIFICATION_CHAT_ID)
    except ValueError:
        print("Ошибка: NOTIFICATION_CHAT_ID должен быть числом")
        NOTIFICATION_CHAT_ID = None

PRESENTATION_PATH = os.getenv("PRESENTATION_PATH", "presentation.pdf")
ABOUT_PHOTO = os.getenv("ABOUT_PHOTO", "")
ABOUT_VIDEO_NOTE = os.getenv("ABOUT_VIDEO_NOTE", "")
CUSTOM_EMOJI_ID = os.getenv("CUSTOM_EMOJI_ID", "")
CONTACTS_EMOJI_ID = os.getenv("CONTACTS_EMOJI_ID", "")

with open("texts.json", "r", encoding="utf-8") as f:
    texts = json.load(f)

DESTINATIONS = texts.get("destinations", [])
PREDICTIONS = texts.get("predictions", [])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== Клавиатуры ==========
def get_main_menu_keyboard():
    keyboard = [
        ["О нас", "Презентация"],
        ["Обсудить проект", "Задать вопрос Михаилу"],
        ["Стать подрядчиком", "Контакты"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_about_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Скачать презентацию", callback_data="download_presentation")],
        [InlineKeyboardButton("Обсудить проект", callback_data="project")],
        [InlineKeyboardButton("Проектное предсказание", callback_data="prediction")],
        [InlineKeyboardButton("Наш сайт", url="https://globalrussia.com")],
        [InlineKeyboardButton("Главное меню", callback_data="main_menu")],
    ])

def get_project_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Рулетка направлений", callback_data="roulette")],
        [InlineKeyboardButton("Главное меню", callback_data="main_menu")],
    ])

def get_presentation_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Обсудить проект", callback_data="project")],
        [InlineKeyboardButton("Рулетка направлений", callback_data="roulette")],
        [InlineKeyboardButton("Проектное предсказание", callback_data="prediction")],
        [InlineKeyboardButton("Главное меню", callback_data="main_menu")],
    ])

def get_partner_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Главное меню", callback_data="main_menu")]])

def get_roulette_keyboard(show_spin=True):
    keyboard = []
    if show_spin:
        keyboard.append([InlineKeyboardButton("🎲 Крутить рулетку", callback_data="roulette_spin")])
    else:
        keyboard.append([InlineKeyboardButton("🔄 Крутить ещё раз", callback_data="roulette_spin")])
    keyboard.append([InlineKeyboardButton("Обсудить проект", callback_data="project")])
    keyboard.append([InlineKeyboardButton("Проектное предсказание", callback_data="prediction")])
    keyboard.append([InlineKeyboardButton("Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_prediction_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪄 Ещё предсказание", callback_data="prediction_spin")],
        [InlineKeyboardButton("Главное меню", callback_data="main_menu")],
    ])

# ========== Уведомления ==========
async def notify_chat(application, user, message, feedback_type):
    if NOTIFICATION_CHAT_ID is None:
        return
    text = f"📩 Новое сообщение от @{user.username} (id={user.id}, имя: {user.full_name})\nРаздел: {feedback_type}\n\n{message}"
    try:
        await application.bot.send_message(chat_id=NOTIFICATION_CHAT_ID, text=text)
    except Exception as e:
        logger.error(f"Ошибка отправки в чат {NOTIFICATION_CHAT_ID}: {e}")

# ========== Вспомогательные функции ==========
async def send_roulette(chat_id, bot, context):
    await bot.send_message(
        chat_id=chat_id,
        text=texts["roulette_intro"],
        disable_web_page_preview=True
    )
    msg = await bot.send_message(
        chat_id=chat_id,
        text="Нажмите кнопку, чтобы начать:",
        reply_markup=get_roulette_keyboard(show_spin=True)
    )
    context.user_data["roulette_message_id"] = msg.message_id

async def send_prediction(chat_id, bot, context):
    await bot.send_message(
        chat_id=chat_id,
        text="🔮:"
    )
    pred = random.choice(PREDICTIONS)
    msg = await bot.send_message(
        chat_id=chat_id,
        text=texts["prediction_result"].format(prediction=pred),
        reply_markup=get_prediction_keyboard(),
        parse_mode="Markdown"
    )
    context.user_data["prediction_message_id"] = msg.message_id

# ========== Команды ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emoji_html = f'<tg-emoji emoji-id="{CUSTOM_EMOJI_ID}">⭐</tg-emoji>' if CUSTOM_EMOJI_ID else "🌟"
    text = texts["start"].format(custom_emoji=emoji_html)
    await update.message.reply_text(
        text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ABOUT_PHOTO and os.path.exists(ABOUT_PHOTO):
        try:
            with open(ABOUT_PHOTO, "rb") as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=texts["about"],
                    reply_markup=ReplyKeyboardRemove()
                )
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
            await update.message.reply_text(
                texts["about"],
                reply_markup=ReplyKeyboardRemove(),
                disable_web_page_preview=True
            )
    else:
        await update.message.reply_text(
            texts["about"],
            reply_markup=ReplyKeyboardRemove(),
            disable_web_page_preview=True
        )
        logger.warning("Фото для раздела 'О нас' не найдено")

    if ABOUT_VIDEO_NOTE and os.path.exists(ABOUT_VIDEO_NOTE):
        try:
            with open(ABOUT_VIDEO_NOTE, "rb") as video:
                await update.message.reply_video_note(video_note=video)
        except Exception as e:
            logger.error(f"Ошибка отправки кружка: {e}")
    else:
        logger.warning("Видео-кружок для раздела 'О нас' не найден")

    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=get_about_keyboard()
    )

async def project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_feedback"] = True
    context.user_data["feedback_type"] = "Обсуждение проекта"
    await update.message.reply_text(
        texts["project"],
        reply_markup=ReplyKeyboardRemove(),
        disable_web_page_preview=True,
        parse_mode="HTML"
    )
    await update.message.reply_text(
        "Для отмены нажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel_feedback")]])
    )

async def presentation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(PRESENTATION_PATH, "rb") as f:
            await update.message.reply_document(
                document=InputFile(f, filename="Global_Russia_Presentation.pdf"),
                caption=texts["presentation"],
                reply_markup=ReplyKeyboardRemove()
            )
    except FileNotFoundError:
        await update.message.reply_text(
            texts["presentation"] + "\n\nИзвините, файл презентации временно недоступен. Попробуйте позже.",
            disable_web_page_preview=True
        )
    await update.message.reply_text(
        "Дополнительные действия:",
        reply_markup=get_presentation_keyboard()
    )

async def partner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_feedback"] = True
    context.user_data["feedback_type"] = "Стать подрядчиком"
    await update.message.reply_text(
        texts["partner"],
        reply_markup=ReplyKeyboardRemove(),
        disable_web_page_preview=True
    )
    await update.message.reply_text(
        "Для отмены нажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel_feedback")]])
    )

async def contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emoji_html = f'<tg-emoji emoji-id="{CONTACTS_EMOJI_ID}">⭐</tg-emoji>' if CONTACTS_EMOJI_ID else "🌟"
    text = texts["contacts"].format(custom_emoji=emoji_html)
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    # Главное меню остаётся видимым

async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_roulette(update.effective_chat.id, context.bot, context)

async def prediction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_prediction(update.effective_chat.id, context.bot, context)

# ========== Callback-обработчик ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard()
        )
        context.user_data.pop("awaiting_feedback", None)
        context.user_data.pop("roulette_message_id", None)
        context.user_data.pop("prediction_message_id", None)
        return

    if data == "cancel_feedback":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            texts["feedback_cancel"],
            reply_markup=get_main_menu_keyboard()
        )
        context.user_data.pop("awaiting_feedback", None)
        context.user_data.pop("feedback_type", None)
        return

    if data == "download_presentation":
        # Убираем кнопки из текущего сообщения (меню "О нас")
        await query.edit_message_reply_markup(reply_markup=None)
        try:
            with open(PRESENTATION_PATH, "rb") as f:
                await query.message.reply_document(
                    document=InputFile(f, filename="Global_Russia_Presentation.pdf"),
                    caption=texts["presentation"]
                )
        except FileNotFoundError:
            await query.message.reply_text(
                texts["presentation"] + "\n\nИзвините, файл презентации временно недоступен. Попробуйте позже."
            )
        # Отправляем дополнительное меню
        await query.message.reply_text(
            "Дополнительные действия:",
            reply_markup=get_presentation_keyboard()
        )
        return

    if data == "roulette_spin":
        dest = random.choice(DESTINATIONS)
        message_id = context.user_data.get("roulette_message_id")
        if message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    text=texts["roulette_result"].format(destination=dest),
                    reply_markup=get_roulette_keyboard(show_spin=False),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Ошибка редактирования рулетки: {e}")
        else:
            await query.edit_message_text(
                texts["roulette_result"].format(destination=dest),
                reply_markup=get_roulette_keyboard(show_spin=False),
                parse_mode="Markdown"
            )
        return

    if data == "prediction_spin":
        pred = random.choice(PREDICTIONS)
        message_id = context.user_data.get("prediction_message_id")
        if message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    text=texts["prediction_result"].format(prediction=pred),
                    reply_markup=get_prediction_keyboard(),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Ошибка редактирования предсказания: {e}")
        else:
            await query.edit_message_text(
                texts["prediction_result"].format(prediction=pred),
                reply_markup=get_prediction_keyboard(),
                parse_mode="Markdown"
            )
        return

    if data == "project":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            texts["project"],
            disable_web_page_preview=True,
            parse_mode="HTML"
        )
        await query.message.reply_text(
            "Для отмены нажмите кнопку ниже:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel_feedback")]])
        )
        context.user_data["awaiting_feedback"] = True
        context.user_data["feedback_type"] = "Обсуждение проекта"
        return

    if data == "roulette":
        await query.edit_message_reply_markup(reply_markup=None)
        await send_roulette(query.message.chat_id, context.bot, context)
        return

    if data == "prediction":
        await query.edit_message_reply_markup(reply_markup=None)
        await send_prediction(query.message.chat_id, context.bot, context)
        return

    await query.edit_message_text("Неизвестная команда.")

# ========== Обработка текста ==========
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_feedback"):
        user = update.effective_user
        msg = update.message.text
        feedback_type = context.user_data.get("feedback_type", "Неизвестно")
        await notify_chat(context.application, user, msg, feedback_type)
        await update.message.reply_text(
            texts["feedback_received"],
            reply_markup=get_main_menu_keyboard()
        )
        context.user_data.pop("awaiting_feedback", None)
        context.user_data.pop("feedback_type", None)
        return

    await update.message.reply_text(
        "Используйте кнопки меню для навигации.",
        reply_markup=get_main_menu_keyboard()
    )

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "О нас":
        await about(update, context)
    elif text == "Презентация":
        await presentation(update, context)
    elif text == "Обсудить проект":
        await project(update, context)
    elif text == "Задать вопрос Михаилу":
        context.user_data["awaiting_feedback"] = True
        context.user_data["feedback_type"] = "Вопрос Михаилу"
        await update.message.reply_text(
            texts["ask_message"],
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Напишите ваше сообщение. (Нажмите «Отмена» чтобы выйти)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel_feedback")]])
        )
    elif text == "Стать подрядчиком":
        await partner(update, context)
    elif text == "Контакты":
        await contacts(update, context)
    else:
        await update.message.reply_text(
            "Пожалуйста, используйте кнопки меню.",
            reply_markup=get_main_menu_keyboard()
        )

# ========== Запуск ==========
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("project", project))
    application.add_handler(CommandHandler("presentation", presentation))
    application.add_handler(CommandHandler("partner", partner))
    application.add_handler(CommandHandler("contacts", contacts))
    application.add_handler(CommandHandler("roulette", roulette))
    application.add_handler(CommandHandler("prediction", prediction))

    application.add_handler(MessageHandler(
        filters.Regex("^(О нас|Презентация|Обсудить проект|Задать вопрос Михаилу|Стать подрядчиком|Контакты)$"),
        handle_main_menu
    ))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(button_callback))

    application.run_polling()

if __name__ == "__main__":
    main()