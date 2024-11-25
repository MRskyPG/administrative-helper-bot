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
        BotCommand(command="/common_questions", description="Список вопросов/ответов"),
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


@public_router.message(StateFilter(None), Command("common_questions"))
async def cmd_common(message: Message):
    common_questions = app.db.get_common_questions()

    if len(common_questions) != 0:
        buttons = []
        i = 1

        for data in common_questions:
            button = [InlineKeyboardButton(text=f"{i}. {data[1]}", callback_data=f"common_{data[0]}")]
            buttons.append(button)
            i += 1

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply("Выберите вопрос:", reply_markup=keyboard)

    else:
        # TODO: добавить кнопку "добавить вопрос и ответ"
        await message.answer("Нет общих вопросов и ответов.")


@public_router.callback_query(StateFilter(None), F.data.startswith("common_"))
async def callbacks_common_questions(callback: CallbackQuery):
    common_questions_id = callback.data.split('_')[1]

    # Получаем вопрос и ответ
    question, answer = app.db.get_common_question_answer_by_id(common_questions_id)

    text = f"Вопрос: {question}.\n\nОтвет: {answer}"


    await callback.message.answer(text)
    await callback.answer()


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
async def any_message(message: Message, state: FSMContext):
    await message.answer("Неизвестная команда. Попробуйте /start")
    await state.clear()
