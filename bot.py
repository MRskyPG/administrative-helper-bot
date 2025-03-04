import asyncio
import sys
import logging

from aiogram import Bot, Dispatcher, BaseMiddleware, types

#Из пакетов проекта
from app.config import bot_token, public_bot_token
from app.handlers import router, set_commands_list_private, set_bot_2
from app.public_handlers import public_router, set_commands_list_public
from app.db import Conn, shutdown_db
from app.crypt_db import get_auth_status, get_user_by_tg_id


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            message: types.Message = event
            exempt_commands = ['/start', '/auth', '/logout']

            command = message.text.split()[0] if message.text else ""

            if command in exempt_commands:
                return await handler(event, data)

            if get_user_by_tg_id(message.from_user.id) is None:
                await message.answer(
                    "Вы не зарегистрированы в системе. Пожалуйста, обратитесь к администратору для регистрации.")
                return

            if not get_auth_status(message.from_user.id):
                await message.answer("Доступ запрещён. Пожалуйста, авторизуйтесь.")
                return

        return await handler(event, data)


bot = Bot(token=bot_token)
public_bot = Bot(token=public_bot_token)

set_bot_2(public_bot)

dp = Dispatcher()
public_dp = Dispatcher()

# Подключаем middleware для приватного бота
dp.message.middleware(AuthMiddleware())

#Старт одного бота
async def start_bot(bot, dispatcher, router, func_list_commands):
    #Обработчик
    dispatcher.include_router(router)

    #Список команд для пользователя
    dispatcher.startup.register(func_list_commands)

    await dispatcher.start_polling(bot)

# Запуск двух ботов
async def main():
    await asyncio.gather(
        start_bot(bot, dp, router, set_commands_list_private),
        start_bot(public_bot, public_dp, public_router, set_commands_list_public)
    )


if __name__ == "__main__":
    try:
        # Run bots
        print("Bots were started.")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bots were stopped by user.")
    except Exception as e:
        print("An error occurred:")
        print(e)
    finally:
        shutdown_db(Conn)
        print("Database connection closed.")