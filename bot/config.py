"""
Конфигурация Telegram-бота «Горизонт».
Загружает переменные окружения из .env и валидирует настройки.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Ищем .env сначала в папке bot/, затем в корне проекта
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api").rstrip("/")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "8.0"))

# Демо-учетные записи для быстрого тестирования
DEMO_CREDENTIALS = {
    "admin": {"username": "admin", "password": "admin", "desc": "Администратор (полный доступ)"},
    "user": {"username": "user", "password": "user", "desc": "Пользователь (баланс и цели)"}
}
