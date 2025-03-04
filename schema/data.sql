CREATE TABLE IF NOT EXISTS places (
    place VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS places_list (
    id SERIAL PRIMARY KEY,
    place VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS places_queue (
    id SERIAL PRIMARY KEY,
    place VARCHAR(255) NOT NULL,
    execute_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER,
    name VARCHAR(255),
    question VARCHAR(255),
    answer VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS common_questions (
    id SERIAL PRIMARY KEY,
    question VARCHAR(255),
    answer VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    encrypted_password TEXT NOT NULL,
    role VARCHAR(10) NOT NULL CHECK (role IN ('owner', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_auth (
    telegram_id BIGINT PRIMARY KEY,
    auth_status BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO places(place) VALUES('Место не задано');