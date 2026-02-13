-- Создание таблицы для пользователей
CREATE TABLE IF NOT EXISTS users
(
    telegram_user_id bigint PRIMARY KEY,  -- Это теперь основной ключ
    username        varchar(255),
    created_at      timestamp DEFAULT CURRENT_TIMESTAMP,
    last_activity   timestamp DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска по telegram_user_id
CREATE INDEX IF NOT EXISTS idx_telegram_user_id ON users (telegram_user_id);

-- Создание таблицы для запросов пользователей
CREATE TABLE IF NOT EXISTS interactions (
    id              bigserial PRIMARY KEY,        -- Это уникальный идентификатор запроса
    user_id         bigint REFERENCES users(telegram_user_id), -- Ссылаемся на telegram_user_id
    query_type      varchar(255) NOT NULL,         -- Тип запроса (например, 'define_by_photo' или 'search_by_name')
    query_text      text,                          -- Текст запроса (например, название цветка)
    flower_image  bytea,                         -- Фото (если запрос был с изображением)
    created_at      timestamp DEFAULT CURRENT_TIMESTAMP -- Дата и время запроса
);

-- Индекс для быстрого поиска по user_id
CREATE INDEX IF NOT EXISTS idx_user_id ON interactions (user_id);
