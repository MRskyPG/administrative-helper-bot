import aiogram
from aiogram import F, Router
from aiogram.filters.command import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup, BotCommand, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State


import app.db

router = Router()

confirmations = ["Да", "Нет, изменить ответ"]

# Глобальная переменная для второго бота
bot_2 : aiogram.Bot

# Для хранения состояния при ответе на вопрос сотрудника
class DoAnswer(StatesGroup):
    getting_answer = State()
    confirmation = State()

def set_bot_2(bot):
    global bot_2
    bot_2 = bot

def make_row_keyboard(items: list[str]) -> ReplyKeyboardMarkup:
    """
    Создаёт реплай-клавиатуру с кнопками в один ряд
    :param items: список текстов для кнопок
    :return: объект реплай-клавиатуры
    """
    row = [KeyboardButton(text=item) for item in items]
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)

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
        BotCommand(command="/ask", description="Список общих вопросов/ответов"),
        BotCommand(command="/staffquestions", description="Посмотреть вопросы сотрудников")
    ]
    await bot.set_my_commands(commands)

# Хэндлер на команду /start
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(f'Привет, {message.from_user.full_name}! Здесь мы зададим твое местоположение.', reply_markup=ReplyKeyboardRemove())

# Хэндлер на команду /setplace
@router.message(Command("setplace"))
async def cmd_set_my_place(message: Message, command: CommandObject):
    if command.args is None:
        await message.answer("Не были введены аргументы\nПример: /setplace description of your place")
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


#Ответ на вопрос сотрудника

# Хэндлер на команду /staffquestions
@router.message(StateFilter(None), Command("staffquestions"))
async def cmd_get_staff_questions(message: Message, state: FSMContext):
    #поля id, chat_id, name, question
    questions = app.db.get_staff_questions()

    if len(questions) != 0:
        buttons = []
        i = 1

        for question in questions:
            # Добавляем кнопку, по которой мы ответим нужному пользователю по id
            button = [InlineKeyboardButton(text=f"{i}. {question[3]}", callback_data=f"question_{question[0]}")]
            buttons.append(button)
            i += 1

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply("Выберите вопрос:", reply_markup=keyboard)

    else:
        await message.reply("Вопросов нет.")


@router.callback_query(StateFilter(None), F.data.startswith('question_'))
async def click_answer(callback_query: CallbackQuery, state: FSMContext):
    question_chat_id = callback_query.data.split('_')[1]

    await callback_query.message.answer(f"Напишите ответ на вопрос. Для отмены: /cancel")

    await state.update_data(id=question_chat_id)
    #Устанавливаем состояние ожидания ответа на вопрос
    await state.set_state(DoAnswer.getting_answer)

@router.message(StateFilter(None), Command("cancel"))
async def cmd_cancel_no_state(message: Message, state: FSMContext):
    await state.set_data({})
    await message.answer(
        text="Нечего отменять",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="Действие отменено",
        reply_markup=ReplyKeyboardRemove()
    )

#message: Message - это и есть ответ на вопрос. Хэндлер сработает в состоянии получения ответа
@router.message(DoAnswer.getting_answer, F.content_type.in_({'text'}))
async def answer_written(message: Message, state: FSMContext):
    await state.update_data(answer=message.text)

    await message.answer("Подтвердите отправку ответа:", reply_markup=make_row_keyboard(confirmations))

    await state.set_state(DoAnswer.confirmation)

@router.message(DoAnswer.getting_answer, F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_type_of_answer(message: Message):
    await message.answer("Напишите текстом!")


@router.message(DoAnswer.confirmation, F.text==confirmations[0])
async def confirm_yes(message: Message, state: FSMContext):
    data = await state.get_data()
    id = int(data['id'])
    answer = data['answer']

    chat_id = app.db.get_chat_id_by_id(id)

    app.db.update_answer_by_id(answer, id)

    question = app.db.get_question_by_id(id)
    #Ответ публичным ботом нужному пользователю
    await bot_2.send_message(chat_id=chat_id, text=f"Вам ответил О.Е.Аврунев!\nВаш вопрос: {question}\nОтвет: {answer}")

    #Удаление ответа из списка
    app.db.delete_question_by_id(id)

    await message.answer("Ответ отправлен!", reply_markup=ReplyKeyboardRemove())
    await state.clear()


@router.message(DoAnswer.confirmation, F.text == confirmations[1])
async def confirm_no(message: Message, state: FSMContext):

    await message.answer(f"Напишите ответ на вопрос заново.", reply_markup=ReplyKeyboardRemove())
    await state.set_state(DoAnswer.getting_answer)

#Если не правильный выбор
@router.message(DoAnswer.confirmation)
async def confirm_incorrect(message: Message):
    await message.answer(f"Неправильный выбор. Выберите из двух кнопок.")



#-----------------------------------------------------------------------------------------------------------------------

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

