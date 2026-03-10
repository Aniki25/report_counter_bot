import logging
import os
import asyncio
import threading
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

# --- Обработчики команд (без изменений) ---
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

# --- Функция для запуска бота (будет выполнена в отдельном потоке) ---
def run_bot():
    """Запускает бота в новом событийном цикле asyncio."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Создаём приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(button_callback, pattern='sign'))
    
    # Запускаем бота
    loop.run_until_complete(app.initialize())
    loop.run_until_complete(app.start())
    loop.run_until_complete(app.updater.start_polling())
    logger.info("✅ Бот успешно запущен и слушает сообщения!")
    
    # Держим поток живым
    loop.run_forever()

# --- Flask приложение (для health checks) ---
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "OK", 200

@flask_app.route('/start-bot')
def start_bot():
    """Эндпоинт для запуска бота в фоне (если вдруг не запустился автоматически)."""
    if not any(isinstance(t, threading.Thread) and t.name == "BotThread" for t in threading.enumerate()):
        thread = threading.Thread(target=run_bot, name="BotThread", daemon=True)
        thread.start()
        return "Bot started", 200
    else:
        return "Bot already running", 200

# --- Автоматический запуск бота при старте gunicorn ---
# Запускаем бота в фоновом потоке сразу при импорте модуля
bot_thread = threading.Thread(target=run_bot, name="BotThread", daemon=True)
bot_thread.start()
