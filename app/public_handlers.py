from aiogram import F, Router
from aiogram.filters.command import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,\
    BotCommand, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
import app.db


public_router = Router()


class AskSomething(StatesGroup):
    waiting_question = State()


async def set_commands_list_public(bot):
    commands = [
        BotCommand(command="/start", description="Запуск бота"),
        BotCommand(command="/getplace", description="Информация о местонахождении преподавателя"),
        BotCommand(command="/ask", description="Задать вопрос")
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
@public_router.message(StateFilter(None), Command("ask"))
async def cmd_ask(message: Message, state: FSMContext):
    await message.answer("Введите ваш вопрос, который хотите задать. Для отмены - /cancel")
    await state.set_state(AskSomething.waiting_question)


@public_router.message(AskSomething.waiting_question, F.content_type.in_({'text'}), F.text[0] != "/")
async def set_new_place(message: Message, state: FSMContext):
    if len(message.text) < 5:
        await message.answer("Попробуйте написать ваш вопрос более подробно.")
    else:
        question = message.text
        app.db.add_staff_question(question, message.from_user.id, message.from_user.full_name)
        await message.reply("Вопрос отправлен! Ожидайте ответа.")
        await state.clear()


@public_router.message(AskSomething.waiting_question, F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice',
                                                                          'document', 'location', 'contact'}))
async def incorrect_set_new_place(message: Message):
    await message.answer("Напишите текстом!")


@public_router.message(StateFilter(None), Command("cancel"))
async def cmd_cancel_no_state(message: Message, state: FSMContext):
    await state.set_data({})
    await message.answer(
        text="Нечего отменять",
        reply_markup=ReplyKeyboardRemove()
    )


@public_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="Действие отменено",
        reply_markup=ReplyKeyboardRemove()
    )

@public_router.message(F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice', 'document',
                                           'location', 'contact'}))
async def any_message(message: Message):
    await message.answer("Неизвестная команда. Попробуйте /start")
