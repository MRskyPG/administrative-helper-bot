from typing import List, Tuple
from datetime import datetime
import psycopg2
import sys
from app.config import postgres_user, postgres_password, postgres_database


def escape_string(s: str):
    return s.replace("'", "''")


def connect_db():
    try:
        conn = psycopg2.connect(dbname=postgres_database, user=postgres_user, password=postgres_password,
                                host="127.0.0.1", port="5439")
        print("Database connected.")
        return conn
    except Exception as e:
        print(f"Error with connection db: {e}")
        sys.exit(1)


# Соединение с базой данных с контейнера
Conn = connect_db()


# Установка места
def set_place(place: str):
    """
        Обновляет текущее место. Если запись со статусом 'current' отсутствует, вставляет новую.
    """
    global Conn

    cursor = Conn.cursor()
    cplace = escape_string(place)
    # Пытаемся обновить запись с текущим местом
    cursor.execute("UPDATE places SET place = %s, created_at = CURRENT_TIMESTAMP WHERE status = 'current'",
                   (cplace,))
    if cursor.rowcount == 0:
        # Если записи не существует, вставляем новую запись со статусом 'current'
        cursor.execute("INSERT INTO places (place, status) VALUES (%s, 'current')", (place,))
    #Зафиксировать изменение
    Conn.commit()
    cursor.close()


def get_place() -> str:
    """
       Возвращает текущее место (status = 'current').
    """
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT place FROM places WHERE status = 'current'")
    data = cursor.fetchone()
    cursor.close()
    return data[0] if data else ""


# Функции для всех добавленных мест (список)
def add_place_to_list(place: str):
    """
    Добавляет новое место в список (история) со статусом 'list'.
    Если такое место уже есть — обновляет дату created_at.
    """
    global Conn
    cursor = Conn.cursor()

    # Проверяем, существует ли уже такое место со статусом 'list'
    cursor.execute("SELECT id FROM places WHERE place = %s AND status = 'list'", (place,))
    existing = cursor.fetchone()

    if existing:
        # Обновляем дату добавления
        cursor.execute("UPDATE places SET created_at = CURRENT_TIMESTAMP WHERE id = %s", (existing[0],))
    else:
        # Вставляем новое
        cursor.execute("INSERT INTO places (place, status) VALUES (%s, 'list')", (place,))

    Conn.commit()
    cursor.close()


def get_places_from_list():
    """
        Возвращает список добавленных мест (id и place) со статусом 'list'.
    """
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT id, place FROM places WHERE status = 'list'")
    places = cursor.fetchall()
    cursor.close()
    return places


def delete_place_from_list(place_id: int):
    """
        Удаляет запись из списка мест (status = 'list').
    """
    global Conn
    cursor = Conn.cursor()
    cursor.execute("DELETE FROM places WHERE id = %s AND status = 'list'", (place_id,))
    Conn.commit()
    result = cursor.rowcount > 0
    cursor.close()
    return result


def get_place_from_list_by_id(id: int) -> str:
    """
        Возвращает место из списка мест (status = 'list').
    """
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT place FROM places where id=%s AND status = 'list'", (id,))

    data = cursor.fetchall()
    cursor.close()

    if data:
        return data[0][0]
    else:
        raise ValueError(f"No place found for places_list ID: {id}")


# Функции для работы с очередью на добавление места
def add_place_to_queue(place: str, execute_at: datetime):
    """
        Добавляет запись в очередь (status = 'queued') с указанным временем обновления.
    """
    global Conn
    cursor = Conn.cursor()
    cursor.execute("INSERT INTO places (place, status, execute_at) VALUES (%s, 'queued', %s) ON CONFLICT DO NOTHING",
                   (place, execute_at))
    Conn.commit()
    cursor.close()


# получение всех мест из очереди
def get_places_from_queue():
    """
        Возвращает все записи из очереди (status = 'queued'), отсортированные по execute_at.
    """
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT id, place, execute_at FROM places WHERE status = 'queued' ORDER BY execute_at")
    places = cursor.fetchall()
    cursor.close()
    return places


# удаление места из очереди по ID
def remove_place_from_queue(place_id: int):
    """
    Удаляет запись из очереди (status = 'queued').
    """
    global Conn
    cursor = Conn.cursor()
    cursor.execute("DELETE FROM places WHERE id = %s AND status = 'queued'", (place_id,))
    Conn.commit()
    cursor.close()


def get_places_from_queue_by_id(id: int):
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT place, execute_at FROM places where id=%s AND status = 'queued'", (id,))

    data = cursor.fetchall()
    cursor.close()

    if data:
        place, execute_at = data[0]
        return place, execute_at
    else:
        raise ValueError(f"No queued places found for places ID: {id}")


# Вопросы сотрудников
def add_staff_question(question: str, chat_id: int, full_name):
    global Conn
    #TODO: проверка на sql атаки
    cursor = Conn.cursor()
    cquestion = escape_string(question)

    cursor.execute("INSERT INTO questions(question, chat_id, name) VALUES(%s, %s, %s)", (cquestion, chat_id, full_name, ))
    # Зафиксировать изменение
    Conn.commit()
    cursor.close()


def get_staff_questions() -> List[Tuple[int, int, str, str]]:
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT id, chat_id, name, question FROM questions")
    #Одна запись о месте
    questions = cursor.fetchall()

    return questions


def update_answer_by_id(answer: str, id: int):
    global Conn

    cursor = Conn.cursor()
    canswer = escape_string(answer)

    cursor.execute("UPDATE questions SET answer=%s WHERE id=%s", (canswer, id,))
    # Зафиксировать изменение
    Conn.commit()
    cursor.close()


def get_chat_id_by_id(id: int):
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT chat_id FROM questions where id=%s", (id,))

    data = cursor.fetchone()
    cursor.close()

    if data is not None:
        return data[0]  # Возвращаем chat_id
    else:
        raise ValueError(f"No chat_id found for question ID: {id}")


def get_question_by_id(id: int) -> str:
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT question FROM questions where id=%s", (id,))

    data = cursor.fetchone()
    cursor.close()

    if data is not None:
        return data[0]
    else:
        raise ValueError(f"No question found for question ID: {id}")


def delete_question_by_id(id: int):
    global Conn

    cursor = Conn.cursor()

    cursor.execute("DELETE FROM questions WHERE id=%s", (id,))
    # Зафиксировать изменение
    Conn.commit()
    cursor.close()


def add_common_questions(question: str, answer: str):
    global Conn
    #TODO: проверка на sql атаки
    cursor = Conn.cursor()
    cquestion = escape_string(question)
    canswer = escape_string(answer)

    cursor.execute("INSERT INTO common_questions(question, answer) VALUES(%s, %s)", (cquestion, canswer, ))
    # Зафиксировать изменение
    Conn.commit()
    cursor.close()


def get_common_question_answer_by_id(id: int):
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT question, answer FROM common_questions where id=%s", (id,))

    data = cursor.fetchall()
    cursor.close()

    if data:
        question, answer = data[0]  # Извлекаем первый элемент (вопрос и ответ)
        return question, answer
    else:
        raise ValueError(f"No question found for question ID: {id}")


def get_common_questions() -> List[Tuple[int, str, str]]:
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT id, question, answer FROM common_questions")

    questions = cursor.fetchall()
    return questions


def update_common_answer_by_id(answer: str, id: int):
    global Conn

    cursor = Conn.cursor()
    canswer = escape_string(answer)

    cursor.execute("UPDATE common_questions SET answer=%s WHERE id=%s", (canswer, id,))
    # Зафиксировать изменение
    Conn.commit()
    cursor.close()


def update_common_question_by_id(question: str, id: int):
    global Conn

    cursor = Conn.cursor()
    cquestion = escape_string(question)

    cursor.execute("UPDATE common_questions SET question=%s WHERE id=%s", (cquestion, id,))
    # Зафиксировать изменение
    Conn.commit()
    cursor.close()


def delete_common_questions_by_id(id: int):
    global Conn

    cursor = Conn.cursor()

    cursor.execute("DELETE FROM common_questions WHERE id=%s", (id,))
    # Зафиксировать изменение
    Conn.commit()
    cursor.close()


def shutdown_db(conn):
    try:
        conn.close()
    except Exception as e:
        print(e)
        sys.exit(1)


