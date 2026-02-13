import logging
import os
import asyncio
from pathlib import Path
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
)
from telegram.constants import ParseMode
from app.services import FlowerClassifier
from app.config import settings, logger
from app.celery_tasks import classify_flower_image
from app.database import DataBase


import base64
import redis
import pickle


class TelegramBot:
    class FakeMessage:
        def __init__(self, text, user):
            self.text = text
            self.from_user = user
            self.chat = user  # Обычно chat также связан с пользователем
            self.message_id = 1  # Минимально необходимый идентификатор сообщения

        # Изменяем reply_text для возврата объекта с message_id
        async def reply_text(self, text, parse_mode=None, reply_markup=None):
            # В реальном боте этот метод отправляет текст. Здесь мы просто создаем объект для тестирования.
            print(f"Replying with text: {text}")

            # Возвращаем объект с атрибутом message_id
            return TelegramBot.FakeReply(message_id=self.message_id)

    class FakeReply:
        def __init__(self, message_id):
            self.message_id = message_id  # Имитация атрибута message_id, который нужен в handle_text

    def __init__(self, token: str, classifier: FlowerClassifier, db: DataBase):
        self.token = token
        self.classifier = classifier
        self.db = db

        self.logger = logging.getLogger("app.telegram_bot")
        self.logger.info("=" * 50)
        self.logger.info("🤖 Инициализация Telegram бота...")
        self.logger.info("=" * 50)

        self.redis_client = redis.StrictRedis(host='redis', port=6379, db=0)
        # Сохраняем модель в Redis, используя pickle для сериализации
        self.redis_client.set('FlowerClassifier', pickle.dumps(self.classifier))

        self.app = Application.builder().token(self.token).build()
        self.user_states = {}  # Для хранения состояний пользователей

        # Загружаем изображения цветков
        self.logger.info("📁 Загружаем изображения цветков...")
        self.flower_images = self._load_flower_images()
        # Регистрируем обработчики
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.send_help_message))
        self.app.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.app.add_handler(CallbackQueryHandler(self.handle_button))
        self.app.add_handler(InlineQueryHandler(self.handle_inline_query))
        self.app.add_handler(ChosenInlineResultHandler(self.handle_chosen_inline_result))

    def _load_flower_images(self):
        """Загружает все изображения из папки в память"""
        flower_images = {}

        # Пробуем несколько возможных путей к папке с изображениями
        possible_paths = [
            Path(__file__).resolve().parent.parent / "flower_photo",  # Один уровень выше (flower_photo рядом с app)
            Path(__file__).resolve().parent / "flower_photo",  # Если в той же папке что и телебот
            Path("/flower_photo"),  # Абсолютный путь в контейнере
            Path("./flower_photo"),  # Относительный путь от корня
        ]

        folder_path = None
        for path in possible_paths:
            if path.exists():
                folder_path = path
                self.logger.info(f"✅ Папка с изображениями найдена: {folder_path}")
                break

        if not folder_path:
            self.logger.error(f"❌ Папка 'flower_photo' не найдена. Проверены пути: {[str(p) for p in possible_paths]}")
            return flower_images

        # Используем os.listdir для обхода папки
        try:
            files = os.listdir(folder_path)
            self.logger.debug(f"Файлы в папке: {files}")

            for filename in files:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    file_path = str(folder_path / filename)
                    flower_name = filename.rsplit('.', 1)[0]  # Убираем расширение
                    flower_images[flower_name] = file_path
                    self.logger.debug(f"Добавлен цветок: {flower_name}")

            self.logger.info(f"✅ Успешно загружено {len(flower_images)} изображений из {folder_path}")
            if flower_images:
                self.logger.info(f"📋 Доступные цветы: {list(flower_images.keys())}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка при чтении папки {folder_path}: {e}", exc_info=True)

        return flower_images

    def _find_similar_flowers(self, query: str, limit: int = 5):
        """Находит цветки, названия которых содержат запрос (с ограничением количества)"""
        query = query.lower().strip()

        if not query:
            return []

        if not self.flower_images:
            self.logger.error("❌ База цветков пуста! Проверьте наличие папки 'flower_photo'")
            return []

        exact_matches = []
        prefix_matches = []
        substring_matches = []

        for name in self.flower_images.keys():
            name_lower = name.lower()

            # Точное совпадение
            if name_lower == query:
                exact_matches.append(name)
            # Совпадение в начале слова
            elif name_lower.startswith(query):
                prefix_matches.append(name)
            # Совпадение в любом месте
            elif query in name_lower:
                substring_matches.append(name)

        # Объединяем результаты по приоритету
        all_matches = exact_matches + sorted(prefix_matches) + sorted(substring_matches)

        # Ограничиваем результаты
        result = all_matches[:limit]

        return result

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start с проверкой и добавлением пользователя в базу данных"""
        user_id = update.message.from_user.id
        username = update.message.from_user.username

        # Проверяем, есть ли уже пользователь в базе данных
        existing_user = self.db.get_user_by_telegram_id(user_id)
        if not existing_user:
            # Если пользователя нет, добавляем его
            self.db.create_user(username, user_id)
            self.logger.info(f"Пользователь {username} с ID {user_id} добавлен в базу")

        # Отправляем приветственное сообщение пользователю
        keyboard = [
            [KeyboardButton("/start"), KeyboardButton("/help")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        welcome_text = (
            "🌸 <b>Флорист-Помощник</b> 🌸\n\n"
            "Я помогу вам определить цветы по фото или найти информацию по названию.\n\n"
            "Выберите действие или используйте команды ниже:"
        )
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )

        # inline кнопки для действия (определение цветка по фото и поиск по названию)
        inline_keyboard = [
            [InlineKeyboardButton("🔍 Определить цветок по фото", callback_data='identify')],
            [InlineKeyboardButton("📖 Найти цветок по названию", callback_data='search')]
        ]
        reply_markup_inline = InlineKeyboardMarkup(inline_keyboard)

        # Отправляем сообщение с кнопками для действия
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup_inline,
            parse_mode=ParseMode.HTML
        )

    # В обработчике inline-запроса
    async def handle_inline_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик inline-запросов для подсказок в реальном времени"""
        query = update.inline_query.query
        if not query:
            return

        user_id = update.inline_query.from_user.id

        # Сохраняем запрос в БД с типом "search_by_name_inline" (инлайн-запрос)
        query_type = "search_by_name_inline"
        # Промежуточный запрос не сохраняем, сохраняем только итоговый
        matches = self._find_similar_flowers(query, limit=10)
        results = []

        # Формируем результаты для инлайн-запроса
        for idx, name in enumerate(matches):
            results.append(
                InlineQueryResultArticle(
                    id=str(idx),
                    title=name.capitalize(),
                    input_message_content=InputTextMessageContent(
                        message_text=f"🌹 {name.capitalize()}",
                        parse_mode=ParseMode.HTML
                    ),
                    description=f"Нажмите, чтобы узнать больше о {name}"
                )
            )

        try:
            # Отправляем результаты инлайн-запроса
            await update.inline_query.answer(results, cache_time=1)
        except Exception as e:
            self.logger.error(f"Ошибка при обработке inline-запроса: {str(e)}")

        # Теперь вызовем handle_text, как будто пользователь ввел название цветка вручную
        if results:
            # Выбираем цветок по первому совпадению
            chosen_name = results[0].input_message_content.message_text.strip("🌹 ").lower()

            # Создаем фиктивный объект update для вызова handle_text
            fake_message = self.FakeMessage(chosen_name, update.inline_query.from_user)
            fake_update = type('FakeUpdate', (object,),
                               {'message': fake_message, 'from_user': update.inline_query.from_user})

            # Передаем fake_update и context в handle_text
            await self.handle_text(fake_update, context)

    async def handle_chosen_inline_result(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик выбора цветка из inline-результатов"""
        try:
            result = update.chosen_inline_result
            query = result.query.strip().lower()

            # Получаем выбранный цветок (result_id соответствует индексу в matches)
            result_id = int(result.result_id)
            matches = self._find_similar_flowers(query, limit=10)

            if not matches or result_id >= len(matches):
                return

            flower_name = matches[result_id]

            # Отправляем фото
            if flower_name in self.flower_images:
                photo_path = self.flower_images[flower_name]

                caption = (
                    f"🌹 <b>{flower_name.capitalize()}</b>\n\n"
                )

                try:
                    with open(photo_path, 'rb') as photo_file:
                        await context.bot.send_photo(
                            chat_id=result.from_user.id,
                            photo=photo_file,
                            caption=caption,
                            parse_mode=ParseMode.HTML
                        )
                except Exception as e:
                    self.logger.error(f"Ошибка при отправке фото: {str(e)}")
                    await context.bot.send_message(
                        chat_id=result.from_user.id,
                        parse_mode=ParseMode.HTML
                    )
            else:
                await context.bot.send_message(
                    chat_id=result.from_user.id,
                    text=f"❌ Фото цветка '{flower_name}' не найдено в базе.❌"
                )

        except Exception as e:
            self.logger.error(f"Ошибка в handle_chosen_inline_result: {str(e)}")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик фотографий"""
        try:
            # Отправляем сообщение, что начинаем анализ
            message = await update.message.reply_text("🔬 Анализирую изображение...")

            # Получаем изображение из сообщения
            photo_file = await update.message.photo[-1].get_file()
            photo_bytes = await photo_file.download_as_bytearray()

            # Получаем ID пользователя
            user_id = update.message.from_user.id
            user_name = update.message.from_user.username

            # Сохраняем запрос в БД с типом "define_by_photo" (по фото)
            query_type = "define_by_photo"
            flower_image = photo_bytes  # Сохраняем само изображение
            self.db.save_query(user_id, query_type, flower_image)

            # Преобразуем фото в base64 и передаем в задачу Celery для классификации
            photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            task = classify_flower_image.apply_async(args=[photo_base64])

            # Получаем результат из задачи
            predictions = task.get()

            if len(predictions) == 1 and predictions[0]['class_name'] == 'Недостаточная уверенность':
                warn = predictions[0]
                warn_msg = (
                    "⚠️ <b>Я не смог уверенно распознать цветок</b>⚠️\n\n"
                    f"Точность предсказания слишком низкая (<b>{warn['confidence']:.1f}%</b>).\n"
                    f"{warn['description']}"
                )

                # Обновляем «🔬 Анализирую…» на предупреждение
                await message.edit_text(warn_msg, parse_mode=ParseMode.HTML)

                # Кнопка «Назад»
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')]]
                await update.message.reply_text("Что дальше?", reply_markup=InlineKeyboardMarkup(keyboard))
                return

                # Формируем ответ с результатами
            response = "<b>Результаты анализа:</b>\n\n"
            for i, pred in enumerate(predictions[:5], 1):
                class_name = pred['class_name']
                confidence = pred['confidence']

                description = settings.flower_descriptions.get(
                    class_name,
                    f"{class_name}. Информация об отсутствует"
                )
                response += (
                    f"{i}. <b>{description.capitalize()}</b>\n"
                    f"<i>{class_name}</i>\n"
                    f"Точность: {confidence:.1f}%\n\n"
                )

            response += (
                "\n️ <b>Внимание!</b> Бот все еще обучается и может допускать ошибки. "
            )

            # Обновляем сообщение с результатами
            await message.edit_text(response, parse_mode=ParseMode.HTML)

            # Кнопка "Назад"
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Что дальше?",
                reply_markup=reply_markup
            )

        except Exception as e:
            logging.error(f"Ошибка обработки фото: {str(e)}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке фото. Попробуйте отправить другое изображение."
            )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений (поиск цветка по названию)"""
        try:
            user_id = update.message.from_user.id
            query = update.message.text.strip()

            # Если это команды /start или /help, обрабатываем их отдельно
            if query == "/start":
                await self.start_command(update, context)
                return  # Прерываем выполнение функции, так как команда /start обработана
            elif query == "/help":
                await self.send_help_message(update, context)
                return  # Прерываем выполнение функции, так как команда /help обработана

            # Если пользователь в режиме поиска (нажал "Найти цветок по названию")
            if self.user_states.get(user_id) == 'searching':
                matches = self._find_similar_flowers(query, limit=5)

                if not matches:
                    await update.message.reply_text(
                        "❌ Пока не найдено цветков с таким названием. Продолжайте вводить..."
                    )
                    return

                # Формируем кнопки для подсказок
                buttons = []
                for name in matches:
                    display_name = name.capitalize()
                    buttons.append([InlineKeyboardButton(display_name, callback_data=f"select_{name}")])

                # Добавляем кнопку "Назад"
                buttons.append([InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')])

                reply_markup = InlineKeyboardMarkup(buttons)

                # Отправляем сообщение с кнопками
                response = (
                    f"🔍 <b>Возможные варианты:</b>\n\n"
                    "Выберите нужный цветок из списка ниже:"
                )

                if 'last_suggestion_msg_id' in context.user_data:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=update.message.chat_id,
                            message_id=context.user_data['last_suggestion_msg_id'],
                            text=response,
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        self.logger.error(f"Ошибка обновления подсказки: {str(e)}")
                        msg = await update.message.reply_text(
                            response,
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.HTML
                        )
                        context.user_data['last_suggestion_msg_id'] = msg.message_id
                else:
                    msg = await update.message.reply_text(
                        response,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )
                    context.user_data['last_suggestion_msg_id'] = msg.message_id

                # Если введено полное совпадение - показываем результат
                if query.lower() in [m.lower() for m in matches]:
                    await self._send_flower_details(update, context, query)
                    context.user_data.pop('last_suggestion_msg_id', None)
                    self.user_states.pop(user_id, None)

            else:
                # Обычный обработчик текста
                matches = self._find_similar_flowers(query)

                if not matches:
                    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await update.message.reply_text(
                        "❌ Цветы с таким названием не найдены. Попробуйте уточнить запрос.\n\n"
                        "Например: 'роза', 'одуванчик', 'подсолнух'",
                        reply_markup=reply_markup
                    )
                    return

                if len(matches) == 1:
                    await self._send_flower_details(update, context, matches[0])
                else:
                    buttons = []
                    for name in matches[:10]:
                        display_name = name.capitalize()
                        buttons.append([InlineKeyboardButton(display_name, callback_data=f"select_{name}")])

                    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_start")])

                    reply_markup = InlineKeyboardMarkup(buttons)

                    response = (
                        f"🔎 <b>Найдено {len(matches)} вариантов по запросу '{query}':</b>\n\n"
                        "Выберите нужный цветок из списка:"
                    )

                    await update.message.reply_text(
                        response,
                        reply_markup=reply_markup,
                        parse_mode=ParseMode.HTML
                    )

        except Exception as e:
            self.logger.error(f"Ошибка обработки текста: {str(e)}", exc_info=True)
            await update.message.reply_text("❌ Произошла ошибка при обработке запроса.")

    async def send_help_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка сообщения с инструкциями по использованию бота"""
        help_text = (
            "🌹 <b>Флорист Эксперт - Помощь</b> 🌹\n\n"
            "Этот бот поможет вам определить цветы по фотографии или найти информацию о цветах по названию.\n\n"
            "<b>Как пользоваться:</b>\n\n"
            "1. Для начала работы с ботом нажмите кнопку <b>'/start'</b> или выберите команду из меню.\n"
            "2. Вы можете отправить фотографию цветка, выбрав команду <b>'🔍 Определить цветок по фото'</b>, и бот постарается определить его.\n"
            "3. Если хотите цветок по названию, выберите команду <b>'📖 Найти цветок по названию'</b>.\n"
            "4. Напишите название цветка, и бот предложит возможные совпадения.\n\n"
            "<b>Команды:</b>\n"
            "/start - Начать работу с ботом\n"
            "/help - Получить помощь\n"
            "📸 Отправьте фото цветка, чтобы получить информацию о нем.\n"
            "🔎 Напишите название цветка, чтобы найти его в базе данных."
        )

        # Добавляем кнопки для навигации
        keyboard = [[KeyboardButton("/start"), KeyboardButton("/help")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        # Отправляем сообщение с инструкциями
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if query.data == 'identify':
            # Отправляем сообщение с инструкцией по отправке фото цветка и кнопкой "Назад"
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')]  # Кнопка "Назад"
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "📸 <b>Определение цветка по фото</b>\n\n"
                "Отправьте мне четкое фото цветка",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            self.user_states[user_id] = 'identifying'

        elif query.data == 'search':
            bot_username = context.bot.username
            keyboard = [
                [InlineKeyboardButton("🔍 Начать поиск", switch_inline_query_current_chat="")],
                [InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"🔎 <b>Поиск цветка по названию</b>\n\n"
                f"Можете написать названия цветка обычным сообщением, а я попробую предложить вам возможные варианты!\n\n",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            self.user_states[user_id] = 'searching'

        elif query.data.startswith("select_"):
            flower_name = query.data[7:]

            # Сохраняем в базу данных выбранный цветок
            query_type = "search_by_name"
            self.db.save_query(user_id, query_type, query_text=f'🌹 {flower_name}')

            # Отправляем пользователю подробности о выбранном цветке
            await self._send_flower_details_query(query, context, flower_name)

            # Снимаем состояние пользователя
            self.user_states.pop(user_id, None)

        elif query.data == 'back_to_start':
            await self.start_command(query, context)
            self.user_states.pop(user_id, None)

    async def _send_flower_details(self, update, context, flower_name):
        """Отправляет детальную информацию о цветке"""
        try:
            # Нормализуем название цветка
            flower_name_lower = flower_name.lower().strip()

            # Ищем точное совпадение в словаре
            actual_flower_name = None
            for key in self.flower_images.keys():
                if key.lower() == flower_name_lower:
                    actual_flower_name = key
                    break

            if not actual_flower_name:
                await update.message.reply_text(f"❌ Цветок '{flower_name}' не найден в базе данных.")
                return

            # Получаем путь к изображению цветка
            photo_path = self.flower_images[actual_flower_name]

            formatted_desc = (
                f"🌹 <b>{actual_flower_name.upper()}</b>\n\n"
                f"Найдено в базе данных"
            )

            # Отправляем фото цветка и описание
            with open(photo_path, 'rb') as photo_file:
                await update.message.reply_photo(
                    photo=photo_file,
                    caption=formatted_desc,
                    parse_mode=ParseMode.HTML
                )

            # Кнопка "Назад"
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Что дальше?",
                reply_markup=reply_markup
            )

        except FileNotFoundError as e:
            self.logger.error(f"Файл не найден: {str(e)}")
            await update.message.reply_text(f"❌ Файл изображения не найден.")
        except Exception as e:
            self.logger.error(f"Ошибка отправки деталей цветка: {str(e)}")
            await update.message.reply_text("❌ Произошла ошибка при отправке информации о цветке.")

    async def _send_flower_details_query(self, query, context, flower_name):
        """Отправляет детальную информацию о цветке (для обработчика кнопок)"""
        try:
            # Нормализуем название цветка
            flower_name_lower = flower_name.lower().strip()

            # Ищем точное совпадение в словаре
            actual_flower_name = None
            for key in self.flower_images.keys():
                if key.lower() == flower_name_lower:
                    actual_flower_name = key
                    break

            if not actual_flower_name:
                await query.edit_message_text(f"❌ Цветок '{flower_name}' не найден в базе данных.")
                return

            photo_path = self.flower_images[actual_flower_name]

            formatted_desc = (
                f"🌹 <b>{actual_flower_name.upper()}</b>\n\n"
                f"Найдено в базе данных"
            )

            await query.message.reply_photo(
                photo=open(photo_path, 'rb'),
                caption=formatted_desc,
                parse_mode=ParseMode.HTML
            )

            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back_to_start')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "Что дальше?",
                reply_markup=reply_markup
            )

        except FileNotFoundError as e:
            self.logger.error(f"Файл не найден: {str(e)}")
            await query.edit_message_text(f"❌ Файл изображения не найден.")
        except Exception as e:
            self.logger.error(f"Ошибка отправки деталей цветка: {str(e)}")
            await query.edit_message_text("❌ Произошла ошибка при отправке информации о цветке.")

    async def _send_flower_photo(self, update, context, flower_name):
        """Отправляет фото цветка"""
        try:
            if flower_name in self.flower_images:
                with open(self.flower_images[flower_name], 'rb') as photo_file:
                    await update.message.reply_photo(
                        photo=photo_file,
                        caption=f"🌹 {flower_name.capitalize()}"
                    )
        except Exception as e:
            self.logger.error(f"Ошибка отправки фото цветка: {str(e)}")

    async def run(self):
        """Запуск бота в режиме polling"""
        if len(self.flower_images) == 0:
            self.logger.error("❌ База цветков пуста! Проверьте наличие папки 'flower_photo'")
        else:
            self.logger.info(f"✅ Бот запущен. Доступно {len(self.flower_images)} цветков")

        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        while True:
            await asyncio.sleep(3600)
