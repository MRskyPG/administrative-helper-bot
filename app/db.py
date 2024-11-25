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

#Соединение с базой данных с контейнера
Conn = connect_db()


# Установка места
def set_place(place: str):
    global Conn
    #TODO: проверка на sql атаки
    cursor = Conn.cursor()
    cplace = escape_string(place)

    cursor.execute("UPDATE places SET place=%s WHERE 1=1", (cplace, ))
    #Зафиксировать изменение
    Conn.commit()
    cursor.close()

def get_place() -> str:
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT * FROM places")
    #Одна запись о месте
    data = cursor.fetchone()

    place = str(data[0])

    cursor.close()
    return place

#-------------------------------------------------------------------------

#Вопросы сотрудников

def add_staff_question(question: str, chat_id: int, full_name):
    global Conn
    #TODO: проверка на sql атаки
    cursor = Conn.cursor()
    cquestion = escape_string(question)

    cursor.execute("INSERT INTO questions(question, chat_id, name) VALUES(%s, %s, %s)", (cquestion, chat_id, full_name, ))
    # Зафиксировать изменение
    Conn.commit()
    cursor.close()

def get_staff_questions() -> list[tuple[int, int, str, str]]:
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

#-------------------------------------------------------------------------

def shutdown_db(conn):
    try:
        conn.close()
    except Exception as e:
        print(e)
        sys.exit(1)


