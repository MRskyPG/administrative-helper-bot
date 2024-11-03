from aiogram import F, Router
from aiogram.filters.command import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

import app.db

public_router = Router()

async def set_commands_list_public(bot):
    commands = [
        BotCommand(command="/start", description="Запуск бота")
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


@public_router.message(F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def any_message(message: Message):
    await message.answer("Неизвестная команда. Попробуйте /start")