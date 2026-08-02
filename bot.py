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

with open("texts_gr.json", "r", encoding="utf-8") as f:
    texts = json.load(f)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== Клавиатура главного меню (новый порядок) ==========
def get_main_menu_keyboard():
    keyboard = [
        ["О нас", "Презентация"],
        ["Обсудить проект", "Задать вопрос Михаилу"],
        ["Пригласить в тендер", "Стать подрядчиком"],
        ["Проектное предсказание", "Рулетка направлений"],
        ["Контакты"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ========== Inline-клавиатуры ==========
def get_about_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Скачать презентацию", callback_data="download_presentation")],
        [InlineKeyboardButton("Пригласить в тендер", callback_data="tender")],
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

def get_tender_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Главное меню", callback_data="main_menu")]])

def get_presentation_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Обсудить проект", callback_data="project")],
        [InlineKeyboardButton("Пригласить в тендер", callback_data="tender")],
        [InlineKeyboardButton("Рулетка направлений", callback_data="roulette")],
        [InlineKeyboardButton("Проектное предсказание", callback_data="prediction")],
        [InlineKeyboardButton("Главное меню", callback_data="main_menu")],
    ])

def get_partner_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Главное меню", callback_data="main_menu")]])

def get_contacts_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Позвонить", url="tel:+78123857307")],
        [InlineKeyboardButton("✉️ Написать письмо", url="mailto:info@globalrussia.com")],
        [InlineKeyboardButton("🌐 Открыть сайт", url="https://globalrussia.com")],
        [InlineKeyboardButton("Главное меню", callback_data="main_menu")],
    ])

def get_roulette_keyboard(show_spin=True):
    keyboard = []
    if show_spin:
        keyboard.append([InlineKeyboardButton("🎲 Крутить рулетку", callback_data="roulette_spin")])
    keyboard.append([InlineKeyboardButton("🔄 Крутить ещё раз", callback_data="roulette_spin")])
    keyboard.append([InlineKeyboardButton("Обсудить проект", callback_data="project")])
    keyboard.append([InlineKeyboardButton("Проектное предсказание", callback_data="prediction")])
    keyboard.append([InlineKeyboardButton("Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_prediction_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔮 Ещё предсказание", callback_data="prediction_spin")],
        [InlineKeyboardButton("Главное меню", callback_data="main_menu")],
    ])

# ========== Списки для рулетки и предсказаний ==========
DESTINATIONS = [
    "Алтай", "Байкал", "Карелия", "Камчатка", "Сочи", "Крым", "Москва", "Санкт-Петербург",
    "Казань", "Екатеринбург", "Новосибирск", "Владивосток", "Калининград", "Мурманск",
    "Архангельск", "Псков", "Великий Новгород", "Суздаль", "Владимир", "Ростов Великий",
    "Япония", "Китай", "Таиланд", "Вьетнам", "Индия", "ОАЭ", "Турция", "Египет",
    "Греция", "Италия", "Испания", "Франция", "Германия", "Великобритания", "США",
    "Мексика", "Бразилия", "Аргентина", "Чили", "Перу", "ЮАР", "Намибия", "Кения",
    "Танзания", "Мальдивы", "Сейшелы", "Маврикий", "Фиджи", "Бали", "Сингапур"
]

PREDICTIONS = [
    "Ваш следующий проект будет связан с Азией – время для ярких впечатлений!",
    "Европа ждёт вас: культурные столицы и деловые встречи.",
    "Путешествие в Латинскую Америку принесёт неожиданные возможности.",
    "Африканские сафари вдохновят вашу команду на новые свершения.",
    "Острова Индийского океана – идеальное место для тимбилдинга.",
    "Россия – огромные просторы и новые горизонты для вашего бизнеса.",
    "Ближний Восток – сочетание роскоши и инноваций.",
    "Скандинавия – лаконичный дизайн и эффективные решения.",
    "Выберите нестандартное направление – это принесёт креативные идеи.",
    "Поездка в горы укрепит командный дух и подарит незабываемые виды."
]

async def notify_chat(application, user, message, feedback_type):
    if NOTIFICATION_CHAT_ID is None:
        return
    text = f"📩 Новое сообщение от @{user.username} (id={user.id}, имя: {user.full_name})\nРаздел: {feedback_type}\n\n{message}"
    try:
        await application.bot.send_message(chat_id=NOTIFICATION_CHAT_ID, text=text)
    except Exception as e:
        logger.error(f"Ошибка отправки в чат {NOTIFICATION_CHAT_ID}: {e}")

# ========== Команды ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        texts["start"],
        reply_markup=get_main_menu_keyboard(),
        disable_web_page_preview=True
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        texts["about"],
        reply_markup=ReplyKeyboardRemove(),
        disable_web_page_preview=True
    )
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=get_about_keyboard()
    )

async def project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_feedback"] = True
    context.user_data["feedback_type"] = "Обсуждение проекта"
    await update.message.reply_text(
        texts["project"] + "\n\n" + texts["ask_message"],
        reply_markup=ReplyKeyboardRemove(),
        disable_web_page_preview=True
    )
    await update.message.reply_text(
        "Для отмены нажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel_feedback")]])
    )

async def tender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_feedback"] = True
    context.user_data["feedback_type"] = "Приглашение в тендер"
    await update.message.reply_text(
        texts["tender"] + "\n\n" + texts["ask_message"],
        reply_markup=ReplyKeyboardRemove(),
        disable_web_page_preview=True
    )
    await update.message.reply_text(
        "Для отмены нажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel_feedback")]])
    )

async def presentation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        texts["presentation"],
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    try:
        with open(PRESENTATION_PATH, "rb") as f:
            await update.message.reply_document(
                document=InputFile(f, filename="Global_Russia_Presentation.pdf"),
                caption="Презентация агентства Global Russia"
            )
    except FileNotFoundError:
        await update.message.reply_text("Извините, файл презентации временно недоступен.")
    await update.message.reply_text(
        "Дополнительные действия:",
        reply_markup=get_presentation_keyboard()
    )

async def partner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_feedback"] = True
    context.user_data["feedback_type"] = "Стать подрядчиком"
    await update.message.reply_text(
        texts["partner"] + "\n\n" + texts["ask_message"] + "\n\nОпишите свою компанию по пунктам выше.",
        reply_markup=ReplyKeyboardRemove(),
        disable_web_page_preview=True
    )
    await update.message.reply_text(
        "Для отмены нажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel_feedback")]])
    )

async def contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        texts["contacts"],
        reply_markup=ReplyKeyboardRemove(),
        disable_web_page_preview=True
    )
    await update.message.reply_text(
        "Свяжитесь с нами:",
        reply_markup=get_contacts_keyboard()
    )

async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        texts["roulette_intro"],
        reply_markup=ReplyKeyboardRemove(),
        disable_web_page_preview=True
    )
    await update.message.reply_text(
        "Нажмите кнопку, чтобы начать:",
        reply_markup=get_roulette_keyboard(show_spin=True)
    )

async def prediction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pred = random.choice(PREDICTIONS)
    await update.message.reply_text(
        texts["prediction_result"].format(prediction=pred),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    await update.message.reply_text(
        "Что дальше?",
        reply_markup=get_prediction_keyboard()
    )

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
        try:
            with open(PRESENTATION_PATH, "rb") as f:
                await query.message.reply_document(
                    document=InputFile(f, filename="Global_Russia_Presentation.pdf"),
                    caption="Презентация агентства Global Russia"
                )
        except FileNotFoundError:
            await query.message.reply_text("Извините, файл презентации временно недоступен.")
        return

    # Переходы между разделами через inline-кнопки
    if data == "project":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            texts["project"] + "\n\n" + texts["ask_message"],
            disable_web_page_preview=True
        )
        await query.message.reply_text(
            "Для отмены нажмите кнопку ниже:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel_feedback")]])
        )
        context.user_data["awaiting_feedback"] = True
        context.user_data["feedback_type"] = "Обсуждение проекта"
        return

    if data == "tender":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            texts["tender"] + "\n\n" + texts["ask_message"],
            disable_web_page_preview=True
        )
        await query.message.reply_text(
            "Для отмены нажмите кнопку ниже:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel_feedback")]])
        )
        context.user_data["awaiting_feedback"] = True
        context.user_data["feedback_type"] = "Приглашение в тендер"
        return

    if data == "roulette":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            texts["roulette_intro"],
            disable_web_page_preview=True
        )
        await query.message.reply_text(
            "Нажмите кнопку, чтобы начать:",
            reply_markup=get_roulette_keyboard(show_spin=True)
        )
        return

    if data == "prediction":
        await query.edit_message_reply_markup(reply_markup=None)
        pred = random.choice(PREDICTIONS)
        await query.message.reply_text(
            texts["prediction_result"].format(prediction=pred),
            parse_mode="Markdown"
        )
        await query.message.reply_text(
            "Что дальше?",
            reply_markup=get_prediction_keyboard()
        )
        return

    if data == "roulette_spin":
        dest = random.choice(DESTINATIONS)
        await query.edit_message_text(
            texts["roulette_result"].format(destination=dest),
            reply_markup=get_roulette_keyboard(show_spin=False),
            parse_mode="Markdown"
        )
        return

    if data == "prediction_spin":
        pred = random.choice(PREDICTIONS)
        await query.edit_message_text(
            texts["prediction_result"].format(prediction=pred),
            reply_markup=get_prediction_keyboard(),
            parse_mode="Markdown"
        )
        return

    await query.edit_message_text("Неизвестная команда.")

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
            "Напишите ваш вопрос для Михаила. Бот передаст его в общий чат организаторов.",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            texts["ask_message"],
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel_feedback")]])
        )
    elif text == "Пригласить в тендер":
        await tender(update, context)
    elif text == "Стать подрядчиком":
        await partner(update, context)
    elif text == "Проектное предсказание":
        await prediction(update, context)
    elif text == "Рулетка направлений":
        await roulette(update, context)
    elif text == "Контакты":
        await contacts(update, context)
    else:
        await update.message.reply_text(
            "Пожалуйста, используйте кнопки меню.",
            reply_markup=get_main_menu_keyboard()
        )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("about", about))
    application.add_handler(CommandHandler("project", project))
    application.add_handler(CommandHandler("tender", tender))
    application.add_handler(CommandHandler("presentation", presentation))
    application.add_handler(CommandHandler("partner", partner))
    application.add_handler(CommandHandler("contacts", contacts))
    application.add_handler(CommandHandler("roulette", roulette))
    application.add_handler(CommandHandler("prediction", prediction))

    application.add_handler(MessageHandler(
        filters.Regex("^(О нас|Презентация|Обсудить проект|Задать вопрос Михаилу|Пригласить в тендер|Стать подрядчиком|Проектное предсказание|Рулетка направлений|Контакты)$"),
        handle_main_menu
    ))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(button_callback))

    application.run_polling()

if __name__ == "__main__":
    main()