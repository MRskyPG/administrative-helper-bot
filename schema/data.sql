-- Таблица для хранения данных о местах:
-- status = 'current' – текущее место,
-- status = 'list' – добавленные ранее места,
-- status = 'queued' – записи очереди на обновление.
CREATE TABLE IF NOT EXISTS places (
    id SERIAL PRIMARY KEY,
    place VARCHAR NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('current', 'list', 'queued')),
    execute_at TIMESTAMP,  -- используется только для записей со статусом 'queued'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица вопросов пользователей
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER,
    name VARCHAR(255),
    question VARCHAR(255),
    answer VARCHAR(255)
);

-- Таблица общих вопросов-ответов
CREATE TABLE IF NOT EXISTS common_questions (
    id SERIAL PRIMARY KEY,
    question VARCHAR(255),
    answer VARCHAR(255)
);

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    encrypted_password TEXT NOT NULL,
    role VARCHAR(10) NOT NULL CHECK (role IN ('owner', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица авторизации
CREATE TABLE IF NOT EXISTS user_auth (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    auth_status BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO places(place) VALUES('Место не задано');