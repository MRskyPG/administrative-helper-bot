import asyncio
import sys
import logging

from aiogram import Bot, Dispatcher

#Из пакетов проекта
from app.config import bot_token, public_bot_token
from app.handlers import router, set_commands_list_private, set_bot_2
from app.public_handlers import public_router, set_commands_list_public
from app.db import Conn, shutdown_db

bot = Bot(token=bot_token)
public_bot = Bot(token=public_bot_token)

set_bot_2(public_bot)

dp = Dispatcher()
public_dp = Dispatcher()

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
    print("Bot were started.")
    try:
        # Запуск бота
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user.")
    except Exception as e:
        print("An error occurred:")
        print(e)
    finally:
        shutdown_db(Conn)
        print("Database connection closed.")