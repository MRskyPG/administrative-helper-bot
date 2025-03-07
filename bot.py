import asyncio
import sys
import logging

from aiogram import Bot, Dispatcher, BaseMiddleware, types, Router

# Из пакетов проекта
from app.config import bot_token, public_bot_token

# Хендлеры
from app.handlers.private_bot.authorization import router_auth, DoAuth
from app.handlers.private_bot.management import router_manage, set_private_bot
from app.handlers.private_bot.places import router_places
from app.handlers.private_bot.questions import router_questions, set_public_bot
from app.handlers.private_bot.handlers import router, set_commands_list_private
from app.handlers.public_bot.public_handlers import public_router, set_commands_list_public

from app.database.db import Conn, shutdown_db
from app.database.crypt_db import get_auth_status, get_user_by_tg_id
from aiogram.fsm.context import FSMContext


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            message: types.Message = event

            # Если есть контекст состояния, проверяем текущий state
            state: FSMContext = data.get("state")
            if state is not None:
                current_state = await state.get_state()
                # Если пользователь находится в процессе аутентификации, пропускаем проверку
                if current_state in (DoAuth.waiting_for_login.state, DoAuth.waiting_for_password.state):
                    return await handler(event, data)

            # Команды, для которых проверка не требуется
            exempt_commands = ['/start', '/auth', '/logout']
            command = message.text.split()[0] if message.text else ""
            if command in exempt_commands:
                return await handler(event, data)

            # Если пользователь не зарегистрирован, прекращаем обработку
            if get_user_by_tg_id(message.from_user.id) is None:
                await message.answer(
                    "Вы не зарегистрированы в системе. Доступ запрещен."
                )
                return

            # Если пользователь не авторизован, отправляем сообщение об ошибке
            if not get_auth_status(message.from_user.id):
                await message.answer("Доступ запрещён. Пожалуйста, авторизуйтесь - /auth")
                return

        return await handler(event, data)


bot = Bot(token=bot_token)
public_bot = Bot(token=public_bot_token)

# Установим в глобальные переменные ботов для использования в другом пакете
set_private_bot(bot)
set_public_bot(public_bot)

dp = Dispatcher()
public_dp = Dispatcher()

# Подключаем middleware для приватного бота
dp.message.middleware(AuthMiddleware())


# Старт ботов с подключением обработчиков (роутеров)
async def start_public_bot(bot, dispatcher, router, func_list_commands):

    # Обработчик
    dispatcher.include_router(router)

    # Список команд для пользователя
    dispatcher.startup.register(func_list_commands)

    await dispatcher.start_polling(bot)


async def start_private_bot(bot, dispatcher, routers: list[Router], func_list_commands):
    # Обработчики
    for router in routers:
        dispatcher.include_router(router)

    # Список команд для пользователя
    dispatcher.startup.register(func_list_commands)

    await dispatcher.start_polling(bot)


# Запуск двух ботов
async def main():

    # Обработчики передаются в определенном порядке, чтобы не нарушалась логика срабатывания команд
    private_routers = [router_auth, router_manage, router_places, router_questions, router]

    # Создаем задачи для двух ботов
    tasks = [
        asyncio.create_task(start_private_bot(bot, dp, private_routers, set_commands_list_private)),
        asyncio.create_task(start_public_bot(public_bot, public_dp, public_router, set_commands_list_public))
    ]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        # Если задачи были отменены, просто завершаем работу
        pass
    finally:
        # Отменяем все задачи
        for task in tasks:
            task.cancel()
        # Завершение работы ботов
        await bot.close()
        await public_bot.close()


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