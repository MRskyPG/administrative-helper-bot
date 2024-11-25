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


class GetPlace(StatesGroup):
    waitingPlaces = State()

class CommonQuestions(StatesGroup):
    add_question = State()
    add_answer = State()
    change_questiion = State()
    change_answer = State()
    delete_both = State()

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


async def update_ask_text(message: Message, answer: str):
    await message.edit_text(text=f"{answer}", reply_markup=get_question_keyboard())


async def set_commands_list_private(bot):
    commands = [
        BotCommand(command="/start", description="Запуск бота"),
        BotCommand(command="/setplace", description="Задать ваше место"),
        BotCommand(command="/getplace", description="Получить сведения о заданном ранее месте"),
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
async def cmd_set_my_place(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите ваше место, которое хотите задать. Для отмены - /cancel")
    await state.set_state(GetPlace.waitingPlaces)



@router.message(GetPlace.waitingPlaces, F.content_type.in_({'text'}), F.text[0] != "/")
async def set_new_place(message: Message, state: FSMContext):
    if len(message.text) < 5:
        await message.answer("Попробуйте написать более подробно.")
    else:
        place = message.text
        app.db.set_place(place)
        await message.reply("Место обновлено!")
        await state.clear()

@router.message(GetPlace.waitingPlaces, F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_set_new_place(message: Message):
    await message.answer("Напишите текстом!")


# Хэндлер на команду /getplace
@router.message(Command("getplace"))
async def cmd_get_place(message: Message, state: FSMContext):
    await state.clear()
    place = app.db.get_place()
    await message.answer(f'Информация о моем местонахождении: {place}')


# ------------------------------------------------------------------------------------
# Ответ на вопрос сотрудника

# Хэндлер на команду /staffquestions
@router.message(Command("staffquestions"))
async def cmd_get_staff_questions(message: Message, state: FSMContext):
    await state.clear()
    # поля id, chat_id, name, question
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
    # Устанавливаем состояние ожидания ответа на вопрос
    await state.set_state(DoAnswer.getting_answer)


# message: Message - это и есть ответ на вопрос. Хэндлер сработает в состоянии получения ответа
@router.message(DoAnswer.getting_answer, F.content_type.in_({'text'}), F.text[0] != "/")
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
    # Ответ публичным ботом нужному пользователю
    await bot_2.send_message(chat_id=chat_id, text=f"Вам ответил О.Е.Аврунев!\nВаш вопрос: {question}\nОтвет: {answer}")

    # Удаление ответа из списка
    app.db.delete_question_by_id(id)

    await message.answer("Ответ отправлен!", reply_markup=ReplyKeyboardRemove())
    await state.clear()


@router.message(DoAnswer.confirmation, F.text == confirmations[1])
async def confirm_no(message: Message, state: FSMContext):

    await message.answer(f"Напишите ответ на вопрос заново.", reply_markup=ReplyKeyboardRemove())
    await state.set_state(DoAnswer.getting_answer)

# Если не правильный выбор
@router.message(DoAnswer.confirmation)
async def confirm_incorrect(message: Message):
    await message.answer(f"Неправильный выбор. Выберите из двух кнопок.")



#-----------------------------------------------------------------------------------------------------------------------

# Хэндлер на команду /ask
@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext):
    await state.clear()
    common_questions = app.db.get_common_questions()

    buttons = []
    if len(common_questions) != 0:

        i = 1

        for data in common_questions:
            button = [InlineKeyboardButton(text=f"{i}. {data[1]}", callback_data=f"common_{data[0]}")]
            buttons.append(button)
            i += 1

        buttons.append([InlineKeyboardButton(text="Добавить вопрос и ответ", callback_data="add_qa")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply("Выберите вопрос:", reply_markup=keyboard)

    else:
        buttons.append([InlineKeyboardButton(text="Добавить вопрос и ответ", callback_data="add_qa")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("Нет общих вопросов и ответов.", reply_markup=keyboard)


@router.callback_query(StateFilter(None), F.data.startswith("common_"))
async def callbacks_common_questions(callback: CallbackQuery):
    common_questions_id = callback.data.split('_')[1]

    # Получаем вопрос и ответ
    question, answer = app.db.get_common_question_answer_by_id(common_questions_id)

    text = f"Вопрос: {question}.\n\nОтвет: {answer}"

    buttons = [
        [InlineKeyboardButton(text="Редактировать вопрос", callback_data=f"changeq_{common_questions_id}")],
        [InlineKeyboardButton(text="Редактировать ответ", callback_data=f"changea_{common_questions_id}")],
        [InlineKeyboardButton(text="Удалить вопрос и ответ из списка", callback_data=f"deleteqa_{common_questions_id}")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

# --------------------------------------------------------------------------------------
# Редактирование общего вопроса
@router.callback_query(StateFilter(None), F.data.startswith("changeq_"))
async def change_common_question(callback: CallbackQuery, state: FSMContext):
    common_questions_id = callback.data.split('_')[1]

    await callback.message.answer("Введите новый вопрос заместо прошлого. Для отмены /cancel.")
    await state.update_data(common_qa_id=common_questions_id)
    await state.set_state(CommonQuestions.change_questiion)

    await callback.answer()


@router.message(CommonQuestions.change_questiion, F.content_type.in_({'text'}), F.text[0] != "/")
async def get_new_common_question(message: Message, state: FSMContext):
    data = await state.get_data()
    common_questions_id = int(data['common_qa_id'])

    question = message.text

    if len(question) >= 10:
        app.db.update_common_question_by_id(question, common_questions_id)

        await message.answer("Вопрос был обновлен. Список общих вопросов и ответов - /ask")
        await state.clear()
    else:
        message.answer("Слишком короткий вопрос. Попробуйте еще раз")


# При ошибочном типе сообщения нового вопроса
@router.message(CommonQuestions.change_questiion, F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_type_of_new_common_question(message: Message):
    await message.answer("Напишите текстом!")

# --------------------------------------------------------------------------------------
# Редактирование общего ответа
@router.callback_query(StateFilter(None), F.data.startswith("changea_"))
async def change_common_answer(callback: CallbackQuery, state: FSMContext):
    common_questions_id = callback.data.split('_')[1]

    await callback.message.answer("Введите новый ответ заместо прошлого. Для отмены /cancel.")
    await state.update_data(common_qa_id=common_questions_id)
    await state.set_state(CommonQuestions.change_answer)

    await callback.answer()


@router.message(CommonQuestions.change_answer, F.content_type.in_({'text'}), F.text[0] != "/")
async def get_new_common_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    common_questions_id = int(data['common_qa_id'])

    answer = message.text

    if len(answer) >= 10:
        app.db.update_common_answer_by_id(answer, common_questions_id)

        await message.answer("Ответ был обновлен. Список общих вопросов и ответов - /ask")
        await state.clear()
    else:
        message.answer("Слишком короткий ответ. Попробуйте еще раз")


# При ошибочном типе сообщения нового ответа
@router.message(CommonQuestions.change_answer,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_type_of_new_common_answer(message: Message):
    await message.answer("Напишите текстом!")

# --------------------------------------------------------------------------------------
# Удаление общего вопроса и ответа из списка
@router.callback_query(F.data.startswith("deleteqa_"))
async def delete_common_question_and_answer(callback: CallbackQuery, state: FSMContext):
    common_questions_id = callback.data.split('_')[1]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await callback.message.answer("Подтвердите удаление. Для отмены /cancel.", reply_markup=keyboard)
    await state.update_data(common_qa_id=common_questions_id)
    await state.set_state(CommonQuestions.delete_both)

    await callback.answer()


# Было введено что-то, а не выбрано подтверждение удаления
@router.callback_query(CommonQuestions.delete_both, F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice',
                                                                        'document', 'location', 'contact'}))
async def incorrect_deletion(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await callback.message.answer("Вы сделали не правильный выбор. Для удаления нажмите кнопку ниже."
                                  " Для отмены /cancel.", reply_markup=keyboard)


@router.callback_query(CommonQuestions.delete_both, F.data.startswith("confirm_delete"))
async def confirm_deletion(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    common_questions_id = int(data['common_qa_id'])

    app.db.delete_common_questions_by_id(common_questions_id)

    await callback.message.answer("Вопрос и ответ были удалены. Список общих вопросов и ответов - /ask")
    await state.clear()

    await callback.answer()



# --------------------------------------------------------------------------------------
# Добавление вопроса и ответа в список
@router.callback_query(StateFilter(None), F.data.startswith("add_qa"))
async def add_common_question_and_answer(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите вопрос. Для отмены - /cancel")
    await state.set_state(CommonQuestions.add_question)

    await callback.answer()


@router.message(CommonQuestions.add_question, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_common_question(message: Message, state: FSMContext):
    question = message.text
    if len(question) > 10:
        await state.update_data(question=question)
        await message.answer("Теперь введите ответ:")
        await state.set_state(CommonQuestions.add_answer)
    else:
        await message.answer("Слишком короткий вопрос. Введите подробнее.")

# При ошибочном типе сообщения нового общего вопроса
@router.message(CommonQuestions.add_question,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_new_question(message: Message):
    await message.answer("Напишите текстом!")


@router.message(CommonQuestions.add_answer, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_common_answer(message: Message, state: FSMContext):
    answer = message.text
    if len(answer) > 10:
        data = await state.get_data()
        question = data['question']

        app.db.add_common_questions(question, answer)

        await message.answer("Готово! Список общих вопросов и ответов - /ask")

        await state.clear()
    else:
        await message.answer("Слишком короткий ответ. Введите подробнее.")


# При ошибочном типе сообщения нового общего вопроса
@router.message(CommonQuestions.add_answer,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_new_answer(message: Message):
    await message.answer("Напишите текстом!")


# --------------------------------------------------------------------------------------
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

@router.message(F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def any_message(message: Message, state: FSMContext):
    await message.answer("Неизвестная команда. Попробуйте /start")

