"""
Точка входа Telegram-бота «Горизонт» на базе aiogram 3.
Запускает асинхронный поллинг, регистрирует роутеры, проверяет связь с FastAPI
и настраивает меню быстрых команд в клиентах Telegram.
"""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from config import BOT_TOKEN, API_BASE_URL
from handlers import router
from api_client import api_client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("horizont_bot")


async def setup_bot_commands(bot: Bot):
    """Регистрация команд в меню Telegram."""
    commands = [
        BotCommand(command="status", description="📊 Мой баланс и гармония"),
        BotCommand(command="goals", description="🎯 Реестр целей и шагов"),
        BotCommand(command="newgoal", description="➕ Добавить новую цель"),
        BotCommand(command="login", description="🔑 Авторизоваться в системе"),
        BotCommand(command="help", description="ℹ️ Справка и возможности"),
        BotCommand(command="logout", description="🚪 Выйти из аккаунта")
    ]
    await bot.set_my_commands(commands)


async def main():
    """Основная асинхронная функция запуска бота."""
    logger.info("=" * 60)
    logger.info("🚀 Запуск Telegram-бота «Горизонт» (Dream Map Planner)")
    logger.info("=" * 60)

    # Проверка наличия токена бота
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.error(
            "❌ ОШИБКА: BOT_TOKEN не задан!\n"
            "Пожалуйста, укажите токен вашего бота:\n"
            "1. Создайте файл 'bot/.env' (или скопируйте 'bot/.env.example')\n"
            "2. Добавьте строку: BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz\n"
            "3. Получить токен можно у официального бота @BotFather в Telegram."
        )
        sys.exit(1)

    logger.info(f"🌐 Целевой адрес бэкенда FastAPI: {API_BASE_URL}")

    # Проверка доступности бэкенда при старте
    is_backend_online = await api_client.check_backend_health()
    if is_backend_online:
        logger.info("✅ Бэкенд FastAPI успешно обнаружен и отвечает на /health.")
    else:
        logger.warning(
            f"⚠️ ВНИМАНИЕ: Бэкенд FastAPI ({API_BASE_URL}) сейчас недоступен.\n"
            "Бот запустится, но команды авторизации и получения данных потребуют работающего сервера.\n"
            "Запустите бэкенд командой: uvicorn main:app --reload (в папке backend/)."
        )

    # Инициализация бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Подключение роутера обработчиков
    dp.include_router(router)

    # Установка команд в интерфейсе Telegram
    try:
        await setup_bot_commands(bot)
        logger.info("📋 Меню команд Telegram успешно зарегистрировано.")
    except Exception as e:
        logger.warning(f"Не удалось настроить меню команд: {e}")

    logger.info("🤖 Бот запущен и ожидает входящих сообщений (Polling)...")

    # Запуск поллинга
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("🛑 Telegram-бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Завершение работы по сигналу прерывания.")
