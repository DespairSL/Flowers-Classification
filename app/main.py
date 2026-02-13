from fastapi import FastAPI
from app.config import logger
import asyncio
from app.telegram_bot import TelegramBot
from app.services import FlowerClassifier
from app.config import settings
from app.database import DataBase  # Импортируем DataBase для добавления пользователя

app = FastAPI(
    title="Mushroom Classification API",
    description="API для классификации грибов по изображениям",
    version="1.0.3"
)

db = DataBase()  # Создаём объект для работы с БД

def read_token_from_file():
    try:
        token = settings.telegram_bot_token
        if not token:
            raise ValueError("Токен Telegram пуст")
        return token
    except Exception as e:
        logger.error(f"Ошибка чтения токена: {str(e)}")
        raise


@app.on_event("startup")
async def startup_event():
    logger.info("Запуск сервера и бота...")

    # Добавляем задержку перед подключением к БД
    await asyncio.sleep(10)  # Задержка в 10 секунд

    # Инициализируем бота с передачей объекта базы данных
    token = read_token_from_file()
    classifier = FlowerClassifier()  # Создаём экземпляр классификатора
    bot = TelegramBot(token, classifier, db)  # Передаем db и классификатор в конструктор бота

    # Запускаем бота в фоновом режиме
    asyncio.create_task(bot.run())

    logger.info("Сервер и бот успешно запущены")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
