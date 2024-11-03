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


def shutdown_db(conn):
    try:
        conn.close()
    except Exception as e:
        print(e)
        sys.exit(1)


