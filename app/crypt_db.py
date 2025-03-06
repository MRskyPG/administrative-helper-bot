import psycopg2
import bcrypt
from app.db import Conn, escape_string
from app.config import owner_tg_id, owner_username, owner_password


def insert_owner():
    global Conn

    if owner_exists():
        print("Owner already exists in DB")
        return
    else:
        hashed_password = hash_password(owner_password)
        cursor = Conn.cursor()

        cursor.execute("""
            INSERT INTO users (telegram_id, username, encrypted_password, role)
            VALUES (%s, %s, %s, 'owner')
        """, (owner_tg_id, owner_username, hashed_password,))

        Conn.commit()

        print("Owner was added to DB")

def owner_exists() -> bool:
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT * FROM users WHERE role=%s and telegram_id=%s", ("owner", owner_tg_id,))
    data = cursor.fetchall()
    cursor.close()
    if data:
        return True
    else:
        return False


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def verify_password(hashed_password: str, provided_password: str) -> bool:
    return bcrypt.checkpw(provided_password.encode(), hashed_password.encode())


def register_user(telegram_id: int, username: str, password: str, role: str) -> bool:
    global Conn
    hashed_password = hash_password(password)
    cursor = Conn.cursor()
    try:
        new_username = escape_string(username)
        cursor.execute("""
            INSERT INTO users (telegram_id, username, encrypted_password, role)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (telegram_id) DO NOTHING
            RETURNING id;
        """, (telegram_id, new_username, hashed_password, role,))
        inserted_row = cursor.fetchone()
        Conn.commit()
        # Если запись вставлена, inserted_row не будет None, возвращаем True
        return inserted_row is not None
    except psycopg2.Error as e:
        Conn.rollback()
        print(f"Ошибка при регистрации: {e}")
        return False
    finally:
        cursor.close()


def set_auth_status(telegram_id: int, status: bool):
    """
    Устанавливает статус авторизации пользователя.
    Если записи для данного telegram_id ещё нет, вставляет её,
    иначе обновляет существующую.
    """
    global Conn
    cursor = Conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO user_auth (telegram_id, auth_status, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (telegram_id) DO UPDATE
            SET auth_status = EXCLUDED.auth_status, updated_at = CURRENT_TIMESTAMP;
        """, (telegram_id, status,))
        Conn.commit()
    except psycopg2.Error as e:
        Conn.rollback()
        print(f"Ошибка при обновлении статуса авторизации: {e}")
    finally:
        cursor.close()


def get_auth_status(telegram_id: int) -> bool:
    """
    Возвращает True, если пользователь с данным telegram_id авторизован, иначе False.
    """
    global Conn
    cursor = Conn.cursor()
    try:
        cursor.execute("SELECT auth_status FROM user_auth WHERE telegram_id = %s", (telegram_id,))
        result = cursor.fetchone()
        return result[0] if result else False
    except psycopg2.Error as e:
        print(f"Ошибка при получении статуса авторизации: {e}")
        return False
    finally:
        cursor.close()


def get_user_by_tg_id(telegram_id: int):
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cursor.fetchone()
    cursor.close()
    return user


def get_user_by_id(id: str):
    global Conn
    cursor = Conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (id,))
    user = cursor.fetchone()
    cursor.close()
    return user



def delete_user_by_tg_id(telegram_id: int):
    global Conn

    cursor = Conn.cursor()

    cursor.execute("DELETE FROM users WHERE telegram_id=%s", (telegram_id,))
    # Зафиксировать изменение
    Conn.commit()
    cursor.close()


def get_owners():
    global Conn
    cursor = Conn.cursor()

    cursor.execute("SELECT id, telegram_id, created_at FROM users where role='owner'")

    owners = cursor.fetchall()
    return owners


def get_admins():
    global Conn
    cursor = Conn.cursor()

    cursor.execute("SELECT id, telegram_id, created_at FROM users where role='admin'")

    admins = cursor.fetchall()
    return admins


# Run insertion
insert_owner()

