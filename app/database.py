import psycopg2
import logging
import os
from dotenv import load_dotenv
import time

load_dotenv()

class DataBase:
    def __init__(self):import psycopg2
import logging
import os
from dotenv import load_dotenv
import time

load_dotenv()

class DataBase:
    def __init__(self):
        # Загружаем параметры из .env
        self.name_db = os.getenv("POSTGRES_DB")
        self.host = os.getenv("POSTGRES_HOST")
        self.user = os.getenv("POSTGRES_USER")
        self.password = os.getenv("POSTGRES_PASSWORD")
        self.port = os.getenv("POSTGRES_PORT")

        # Настройка логирования
        logging.basicConfig(
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )

    def get_user_by_telegram_id(self, telegram_user_id):
        """Получить пользователя по Telegram ID"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                logging.info(f"Запрос на получение пользователя с Telegram ID: {telegram_user_id}")
                cursor.execute(
                    "SELECT telegram_user_id FROM users WHERE telegram_user_id = %s",  # Используем telegram_user_id
                    (telegram_user_id,)
                )
                user = cursor.fetchone()
                if user:
                    logging.info(f"Пользователь найден с Telegram ID: {user[0]}")
                    return user
                logging.info(f"Пользователь с Telegram ID {telegram_user_id} не найден.")
                return None
        except Exception as e:
            logging.error(f"Ошибка при получении пользователя: {e}")
            return None
        finally:
            conn.close()

    def create_user(self, username, telegram_user_id):
        """Добавить пользователя в базу данных, если его нет"""
        # Исключаем бота с ID 7372528514
        if telegram_user_id == 7372528514:
            logging.info(f"Бот с Telegram ID {telegram_user_id} не добавляется в базу данных.")
            return None  # Возвращаем None, чтобы указать, что бот не был добавлен

        existing_user = self.get_user_by_telegram_id(telegram_user_id)
        if existing_user:
            logging.info(f"Пользователь с Telegram ID {telegram_user_id} уже существует.")
            return existing_user[0]  # Возвращаем ID существующего пользователя

        conn = self.get_connection()
        try:
            logging.info(f"Создание нового пользователя с Telegram ID {telegram_user_id} и username {username}")
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (telegram_user_id, username)
                    VALUES (%s, %s)
                    RETURNING telegram_user_id;
                    """,
                    (telegram_user_id, username)
                )
                conn.commit()  # Обязательно вызывайте commit, чтобы изменения были зафиксированы
                user_id = cursor.fetchone()[0]  # Получаем telegram_user_id, а не внутренний ID
                logging.info(f"Новый пользователь добавлен с Telegram ID: {user_id}")
                return user_id  # Возвращаем telegram_user_id
        except Exception as e:
            logging.error(f"Ошибка добавления пользователя: {e}")
            raise
        finally:
            conn.close()

    def get_connection(self, database=None, max_retries=5, retry_delay=5):
        """Улучшенная функция подключения с повторами"""
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=database if database else self.name_db,
                    port=self.port,
                    connect_timeout=5
                )
                logging.info(f"Успешное подключение к БД {database or self.name_db}")
                return conn
            except psycopg2.OperationalError as e:
                logging.warning(
                    f"Попытка {attempt + 1}/{max_retries}: Ошибка подключения к {self.host}:{self.port}. "
                    f"Ошибка: {e}. Повтор через {retry_delay} сек..."
                )
                if attempt == max_retries - 1:
                    logging.error(f"Не удалось подключиться после {max_retries} попыток")
                    raise
                time.sleep(retry_delay)
            except psycopg2.Error as e:
                logging.error(f"Критическая ошибка подключения: {e}")
                raise

    def save_query(self, user_id, query_type, flower_image=None, query_text=None):
        """Сохраняем запрос в базу данных"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # Проверяем, существует ли пользователь в таблице users по telegram_user_id
                cursor.execute("SELECT telegram_user_id FROM users WHERE telegram_user_id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    logging.error(f"Пользователь с Telegram ID {user_id} не найден в таблице users.")
                    raise ValueError(f"Пользователь с Telegram ID {user_id} не найден в базе.")

            # Сохраняем запрос
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO interactions (user_id, query_type, query_text, flower_image)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (user_id, query_type, query_text, flower_image)
                )
                conn.commit()
                query_id = cursor.fetchone()[0]  # Получаем ID нового запроса
                logging.info(f"Новый запрос сохранен с ID: {query_id}")
                return query_id
        except Exception as e:
            logging.error(f"Ошибка сохранения запроса: {e}")
            raise
        finally:
            conn.close()
        # Загружаем параметры из .env
        self.name_db = os.getenv("POSTGRES_DB")
        self.host = os.getenv("POSTGRES_HOST")
        self.user = os.getenv("POSTGRES_USER")
        self.password = os.getenv("POSTGRES_PASSWORD")
        self.port = os.getenv("POSTGRES_PORT")

        # Настройка логирования
        logging.basicConfig(
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )

    def get_user_by_telegram_id(self, telegram_user_id):
        """Получить пользователя по Telegram ID"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                logging.info(f"Запрос на получение пользователя с Telegram ID: {telegram_user_id}")
                cursor.execute(
                    "SELECT telegram_user_id FROM users WHERE telegram_user_id = %s",  # Используем telegram_user_id
                    (telegram_user_id,)
                )
                user = cursor.fetchone()
                if user:
                    logging.info(f"Пользователь найден с Telegram ID: {user[0]}")
                    return user
                logging.info(f"Пользователь с Telegram ID {telegram_user_id} не найден.")
                return None
        except Exception as e:
            logging.error(f"Ошибка при получении пользователя: {e}")
            return None
        finally:
            conn.close()

    def create_user(self, username, telegram_user_id):
        """Добавить пользователя в базу данных, если его нет"""
        # Исключаем бота с ID 7372528514
        if telegram_user_id == 7372528514:
            logging.info(f"Бот с Telegram ID {telegram_user_id} не добавляется в базу данных.")
            return None  # Возвращаем None, чтобы указать, что бот не был добавлен

        existing_user = self.get_user_by_telegram_id(telegram_user_id)
        if existing_user:
            logging.info(f"Пользователь с Telegram ID {telegram_user_id} уже существует.")
            return existing_user[0]  # Возвращаем ID существующего пользователя

        conn = self.get_connection()
        try:
            logging.info(f"Создание нового пользователя с Telegram ID {telegram_user_id} и username {username}")
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (telegram_user_id, username)
                    VALUES (%s, %s)
                    RETURNING telegram_user_id;
                    """,
                    (telegram_user_id, username)
                )
                conn.commit()  # Обязательно вызывайте commit, чтобы изменения были зафиксированы
                user_id = cursor.fetchone()[0]  # Получаем telegram_user_id, а не внутренний ID
                logging.info(f"Новый пользователь добавлен с Telegram ID: {user_id}")
                return user_id  # Возвращаем telegram_user_id
        except Exception as e:
            logging.error(f"Ошибка добавления пользователя: {e}")
            raise
        finally:
            conn.close()

    def get_connection(self, database=None, max_retries=5, retry_delay=5):
        """Улучшенная функция подключения с повторами"""
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    database=database if database else self.name_db,
                    port=self.port,
                    connect_timeout=5
                )
                logging.info(f"Успешное подключение к БД {database or self.name_db}")
                return conn
            except psycopg2.OperationalError as e:
                logging.warning(
                    f"Попытка {attempt + 1}/{max_retries}: Ошибка подключения к {self.host}:{self.port}. "
                    f"Ошибка: {e}. Повтор через {retry_delay} сек..."
                )
                if attempt == max_retries - 1:
                    logging.error(f"Не удалось подключиться после {max_retries} попыток")
                    raise
                time.sleep(retry_delay)
            except psycopg2.Error as e:
                logging.error(f"Критическая ошибка подключения: {e}")
                raise

    def save_query(self, user_id, query_type, flower_image=None, query_text=None):
        """Сохраняем запрос в базу данных"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # Проверяем, существует ли пользователь в таблице users по telegram_user_id
                cursor.execute("SELECT telegram_user_id FROM users WHERE telegram_user_id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    logging.error(f"Пользователь с Telegram ID {user_id} не найден в таблице users.")
                    raise ValueError(f"Пользователь с Telegram ID {user_id} не найден в базе.")

            # Сохраняем запрос
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO interactions (user_id, query_type, query_text, flower_image)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (user_id, query_type, query_text, flower_image)
                )
                conn.commit()
                query_id = cursor.fetchone()[0]  # Получаем ID нового запроса
                logging.info(f"Новый запрос сохранен с ID: {query_id}")
                return query_id
        except Exception as e:
            logging.error(f"Ошибка сохранения запроса: {e}")
            raise
        finally:
            conn.close()