from aiogram import F, Router
from aiogram.filters.command import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand


import app.db

router = Router()

# Кнопки для команды /ask
def get_question_keyboard():
    buttons = [
        [InlineKeyboardButton(text="Вопрос 1", callback_data="q_1")],
        [InlineKeyboardButton(text="Вопрос 2", callback_data="q_2")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

async def update_ask_text(message: Message, answer: str):
    await message.edit_text(text=f"{answer}", reply_markup=get_question_keyboard())

async def set_commands_list_private(bot):
    commands = [
        BotCommand(command="/start", description="Запуск бота"),
        BotCommand(command="/setplace", description="Задать ваше место (ваш текст места идет после команды)."),
        BotCommand(command="/getplace", description="Получить сведения о заданном ранее месте."),
        BotCommand(command="/ask", description="Список общих вопросов/ответов")
    ]
    await bot.set_my_commands(commands)

# Хэндлер на команду /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(f'Привет, {message.from_user.full_name}! Здесь мы зададим твое местоположение.')

# Хэндлер на команду /setplace
@router.message(Command("setplace"))
async def cmd_set_my_place(message: Message, command: CommandObject):
    if command.args is None:
        await message.answer("Не были введены аргументы\nПример: /setplace <description_of_your_place>")
        return
    data = command.args

    app.db.set_place(data)
    await message.reply("Место обновлено!")

# Хэндлер на команду /getplace
@router.message(Command("getplace"))
async def cmd_get_place(message: Message):
    place = app.db.get_place()
    await message.answer(f'Информация о моем местонахождении: {place}')

# Хэндлер на команду /ask
@router.message(Command("ask"))
async def cmd_ask(message: Message):
   await message.answer("Выберите ваш вопрос:", reply_markup=get_question_keyboard())





@router.callback_query(F.data.startswith("q_"))
async def callbacks_questions(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    if action == "1":
        await update_ask_text(callback.message, "Ответ 1")
    elif action == "2":
        await update_ask_text(callback.message, "Ответ 2")
    await callback.answer()


@router.message(F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def any_message(message: Message):
    await message.answer("Неизвестная команда. Попробуйте /start")

