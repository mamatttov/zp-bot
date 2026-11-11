"""Настройки бота из файла .env."""
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", "data/zp.db")
NOTIFY_INTERVAL = int(os.getenv("NOTIFY_INTERVAL", "30"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

if not BOT_TOKEN or BOT_TOKEN.startswith("123456"):
    raise RuntimeError("Впишите настоящий BOT_TOKEN в файл .env")