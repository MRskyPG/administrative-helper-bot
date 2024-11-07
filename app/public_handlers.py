from aiogram import F, Router
from aiogram.filters.command import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

import app.db

public_router = Router()

async def set_commands_list_public(bot):
    commands = [
        BotCommand(command="/start", description="Запуск бота"),
        BotCommand(command="/getplace", description="Информация о местонахождении преподавателя"),
        BotCommand(command="/ask", description="Задать вопрос (ваш вопрос идет после команды)")
    ]
    await bot.set_my_commands(commands)

# Хэндлер на команду /start
@public_router.message(Command("start"))
async def public_cmd_start(message: Message):
    await message.answer(f'Привет, {message.from_user.full_name}! Здесь ты можешь узнать, где О.Е.Аврунев')

# Хэндлер на команду /getplace
@public_router.message(Command("getplace"))
async def cmd_get_place(message: Message):
    place = app.db.get_place()
    await message.answer(f'Информация о местонахождении О.Е.Аврунева: {place}')


# Хэндлер на команду /ask
@public_router.message(Command("ask"))
async def cmd_ask(message: Message, command: CommandObject):
    if command.args is None:
        await message.answer("Не были введены аргументы\nПример: /ask your question?")
        return
    data = command.args

    app.db.add_staff_question(data, message.from_user.id, message.from_user.full_name)
    await message.reply("Вопрос отправлен! Ожидайте ответа.")

@public_router.message(F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def any_message(message: Message):
    await message.answer("Неизвестная команда. Попробуйте /start")