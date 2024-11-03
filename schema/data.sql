CREATE TABLE places (
    place VARCHAR(255) NOT NULL
);

CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER,
    name VARCHAR(255),
    question VARCHAR(255),
    answer VARCHAR(255)
);

CREATE TABLE common_questions (
    id SERIAL PRIMARY KEY,
    question VARCHAR(255),
    answer VARCHAR(255)
);

INSERT INTO places(place) VALUES('Место не задано');