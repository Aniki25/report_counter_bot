import logging
import os
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

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

# Порт, который назначает Render
PORT = int(os.environ.get("PORT", 10000))

# Счётчик и блокировка
counter = 0
counter_lock = asyncio.Lock()

# --- Обработчики команд Telegram ---
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

# --- Запуск бота ---
async def run_bot(app: Application):
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("✅ Бот успешно запущен и слушает сообщения!")

# --- HTTP endpoints для Render (health checks) ---
async def health(request):
    return web.Response(text="OK")

async def start_bot_handler(request):
    # Просто подтверждаем, что бот работает (он уже запущен)
    return web.Response(text="Bot is running")

# --- Главная функция ---
async def main():
    # Создаём приложение бота
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CallbackQueryHandler(button_callback, pattern='sign'))

    # Запускаем бота в фоновой задаче
    asyncio.create_task(run_bot(application))

    # Создаём aiohttp приложение
    web_app = web.Application()
    web_app.router.add_get('/', health)
    web_app.router.add_get('/health', health)
    web_app.router.add_get('/start-bot', start_bot_handler)

    # Запускаем HTTP сервер
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"🌐 HTTP сервер запущен на порту {PORT}")

    # Держим процесс активным
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
