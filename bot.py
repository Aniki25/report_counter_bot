import logging
import os
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен из переменной окружения
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("Переменная окружения TELEGRAM_TOKEN не установлена")

# Глобальные переменные для бота и счётчика
application = None
counter = 0
counter_lock = asyncio.Lock()

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Подписать отчет", callback_data='sign')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Нажмите кнопку, чтобы подписать отчет.",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    global counter
    async with counter_lock:
        counter += 1
        current = counter

        await query.message.reply_text(f"Подписан отчет №{current}")

        if current == 9:
            await query.message.reply_text("Внимание! Следующий отчет пройдет экспертную проверку.")
        elif current == 10:
            await query.message.reply_text("Отчет отправлен на экспертную проверку!")
            counter = 0

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global counter
    async with counter_lock:
        counter = 0
    await update.message.reply_text("Счётчик сброшен.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global counter
    async with counter_lock:
        current = counter
    await update.message.reply_text(f"Текущее значение счётчика: {current}")

# --- Flask приложение (для health checks) ---
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "OK", 200

@flask_app.route('/start-bot')
def start_bot():
    """Эндпоинт для запуска бота в фоне."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(run_bot())
    return "Bot started", 200

# --- Запуск бота ---
async def run_bot():
    global application
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CallbackQueryHandler(button_callback, pattern='sign'))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("Бот успешно запущен!")

    # Бесконечное ожидание
    while True:
        await asyncio.sleep(3600)

# Главная функция для gunicorn
if __name__ != "__main__":
    # При импорте этого файла (gunicorn это делает) запускаем бота в фоне
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(run_bot())