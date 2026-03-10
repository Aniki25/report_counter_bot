import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен и URL вашего сервиса на Render
TOKEN = os.environ.get("TELEGRAM_TOKEN")
RENDER_URL = os.environ.get("RENDER_URL")  # Например: https://your-service.onrender.com

if not TOKEN or not RENDER_URL:
    raise ValueError("TELEGRAM_TOKEN и RENDER_URL должны быть установлены")

# Создаём приложение Flask
app = Flask(__name__)

# Глобальный счётчик
counter = 0

# Создаём Application
application = Application.builder().token(TOKEN).build()

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Подписать отчет", callback_data='sign')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Нажмите кнопку, чтобы подписать отчет.",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global counter
    query = update.callback_query
    await query.answer()

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
    counter = 0
    await update.message.reply_text("Счётчик сброшен.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global counter
    await update.message.reply_text(f"Текущее значение счётчика: {counter}")

# Регистрируем обработчики
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("reset", reset))
application.add_handler(CommandHandler("status", status))
application.add_handler(CallbackQueryHandler(button_callback, pattern='sign'))

# --- Функция установки вебхука ---
def set_webhook():
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(application.bot.set_webhook(webhook_url))
    logger.info(f"Вебхук установлен на {webhook_url}")

# Устанавливаем вебхук при старте
set_webhook()

# --- Flask endpoint для приёма обновлений ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "OK", 200

@app.route("/")
def index():
    return "Bot is running", 200

# --- Запуск Flask (без gunicorn) ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
