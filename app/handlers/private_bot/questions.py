import aiogram
import time
from datetime import datetime
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,\
    ReplyKeyboardRemove, KeyboardButton, ChatMemberUpdated
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from typing import List

from app.handlers.private_bot.handlers import text_about_commands
import app.database.db as db
import app.smiles as smiles


router_questions = Router()

confirmations = [f"Да {smiles.check_mark}", f"Нет, изменить ответ {smiles.cross_mark}"]

# Глобальная переменная для ботов
bot_1: aiogram.Bot
bot_2: aiogram.Bot


def set_public_bot(bot):
    global bot_2
    bot_2 = bot


def set_private_bot_2(bot):
    global bot_1
    bot_1 = bot


def make_row_keyboard(items: List[str]) -> ReplyKeyboardMarkup:
    """
    Создаёт реплай-клавиатуру с кнопками в один ряд
    :param items: список текстов для кнопок
    :return: объект реплай-клавиатуры
    """
    row = [KeyboardButton(text=item) for item in items]
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)


class CommonQuestions(StatesGroup):
    add_question = State()
    add_answer = State()
    change_questiion = State()
    change_answer = State()
    delete_both = State()


class DoAnswer(StatesGroup):
    getting_answer = State()
    confirmation = State()


@router_questions.my_chat_member()
async def on_chat_member_update(event: ChatMemberUpdated):
    bot_id = event.bot.id
    chat_id = event.chat.id
    title = event.chat.title or "Без названия"
    now = datetime.now()

    # Бот был добавлен или получил новые права (например, стал админом)
    if event.new_chat_member.user.id == bot_id and event.new_chat_member.status in {"member", "administrator"}:
        existing_chat = db.get_group_chat_by_group_id(chat_id)
        if existing_chat:
            # Чат уже есть, обновляем название и joined_at (вдруг переименовали)
            db.update_group_chat(existing_chat[0], chat_id, title, now)
        else:
            # Чат новый — добавляем
            db.add_group_chat(chat_id, title, now)

        if event.new_chat_member.status == "member":
            await event.bot.send_message(chat_id, f"Приветствую! Сюда я смогу отправить вопросы пользователей "
                                                  f"для последующего решения.")
        if event.new_chat_member.status == "administrator":
            await event.bot.send_message(chat_id, f"Обновление: повышен до администратора.")

        print(f"✅ Бот добавлен в чат: {title} ({chat_id})")

    # Бот был удалён
    elif event.old_chat_member.user.id == bot_id and event.new_chat_member.status in {"left", "kicked"}:
        # Удаляем запись из БД
        existing_chat = db.get_group_chat_by_group_id(chat_id)
        if existing_chat:
            db.delete_group_chat(existing_chat[0])
        print(f"❌ Бот был удалён из чата: {title} ({chat_id})")


# Хэндлер на команду /staffquestions
@router_questions.message(Command("staffquestions"))
async def cmd_get_staff_questions(message: Message, state: FSMContext):
    await state.clear()
    # поля id, chat_id, name, question
    questions = db.get_staff_questions()

    if len(questions) != 0:
        buttons = []
        i = 1

        for question in questions:
            # Добавляем кнопку, по которой мы ответим нужному пользователю по id
            button = [InlineKeyboardButton(text=f"{i}. от {question[2]}: {question[3]}", callback_data=f"question_{question[0]}")]
            buttons.append(button)
            i += 1

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply("Выберите вопрос:", reply_markup=keyboard)

    else:
        await message.reply("Вопросов нет.")


@router_questions.callback_query(StateFilter(None), F.data.startswith('question_'))
async def click_answer(callback_query: CallbackQuery, state: FSMContext):
    question_chat_id = callback_query.data.split('_')[1]

    # Получение списка бесед
    #0-3 indexes: id, group_id, title, joined_at
    groups = db.get_all_group_chats()
    buttons = []
    if len(groups) != 0:
        i = 1
        messages = "Отправьте в доступную беседу на выбор для последующей отправки ботом:\n\n"

        for data in groups:
            button = [InlineKeyboardButton(text=f"{i}. {data[2]}", callback_data=f"group_{data[0]}")]
            buttons.append(button)
            i += 1

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback_query.message.answer(messages, reply_markup=keyboard)

    else:
        await message.answer("Нет доступных бесед для отправки.")

    await callback_query.message.answer(f"Так же вы можете написать ответ на вопрос пользователя. Для отмены: /cancel")

    await state.update_data(id=question_chat_id)
    # Устанавливаем состояние ожидания ответа на вопрос
    await state.set_state(DoAnswer.getting_answer)


@router_questions.callback_query(DoAnswer.getting_answer, F.data.startswith('group_'))
async def click_send_to_group(callback_query: CallbackQuery, state: FSMContext):
    id_for_group = callback_query.data.split('_')[1]

    data = await state.get_data()
    user_chat_id = int(data['id'])

    # chat_id, name, question
    question_info = db.get_question_info_by_id(user_chat_id)

    # Получаем данные группы
    # group_id, title, joined_at
    group_data = db.get_group_chat_by_id(id_for_group)

    await bot_1.send_message(group_data[0], f"Вам был задан вопрос от {question_info[1]}: {question_info[2]}")

    await callback_query.message.answer(f"Сообщение отправлено в беседу. Можете ввести ответ на вопрос пользователя."
                                        f" Для выхода: /cancel")


# message: Message - это и есть ответ на вопрос. Хэндлер сработает в состоянии получения ответа
@router_questions.message(DoAnswer.getting_answer, F.content_type.in_({'text'}), F.text[0] != "/")
async def answer_written(message: Message, state: FSMContext):
    await state.update_data(answer=message.text)

    await message.answer("Подтвердите отправку ответа:", reply_markup=make_row_keyboard(confirmations))

    await state.set_state(DoAnswer.confirmation)

@router_questions.message(DoAnswer.getting_answer, F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_type_of_answer(message: Message):
    await message.answer("Напишите текстом!")


@router_questions.message(DoAnswer.confirmation, F.text==confirmations[0])
async def confirm_yes(message: Message, state: FSMContext):
    data = await state.get_data()
    id = int(data['id'])
    answer = data['answer']

    chat_id = db.get_chat_id_by_id(id)

    db.update_answer_by_id(answer, id)

    question = db.get_question_by_id(id)
    # Ответ публичным ботом нужному пользователю
    await bot_2.send_message(chat_id=chat_id, text=f"Вам ответил О.Е.Аврунев!\n\n{smiles.question_sign} Ваш вопрос: {question}\n\n{smiles.check_mark} Ответ: {answer}")

    # Удаление ответа из списка
    db.delete_question_by_id(id)

    await message.answer("Ответ отправлен!", reply_markup=ReplyKeyboardRemove())
    await state.clear()


@router_questions.message(DoAnswer.confirmation, F.text == confirmations[1])
async def confirm_no(message: Message, state: FSMContext):

    await message.answer(f"Напишите ответ на вопрос заново.", reply_markup=ReplyKeyboardRemove())
    await state.set_state(DoAnswer.getting_answer)

# Если не правильный выбор
@router_questions.message(DoAnswer.confirmation)
async def confirm_incorrect(message: Message):
    await message.answer(f"Неправильный выбор {smiles.cross_mark}. Выберите из двух кнопок.")


# Хэндлер на команду /ask
@router_questions.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext):
    await state.clear()
    common_questions = db.get_common_questions()

    buttons = []
    if len(common_questions) != 0:

        i = 1

        messages = "Выберите интересующий вопрос и посмотрите ответ:\n\n"

        for data in common_questions:
            messages += f"{i}. {data[1]} \n\n"
            button = [InlineKeyboardButton(text=f"Ответ {i}", callback_data=f"common_{data[0]}")]
            buttons.append(button)
            i += 1

        buttons.append([InlineKeyboardButton(text=f"Добавить вопрос и ответ {smiles.pencil}", callback_data="add_qa")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply(messages, reply_markup=keyboard)

    else:
        buttons.append([InlineKeyboardButton(text=f"Добавить вопрос и ответ {smiles.pencil}", callback_data="add_qa")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("Нет общих вопросов и ответов.", reply_markup=keyboard)


@router_questions.callback_query(StateFilter(None), F.data.startswith("common_"))
async def callbacks_common_questions(callback: CallbackQuery):
    common_questions_id = callback.data.split('_')[1]

    # Получаем вопрос и ответ
    question, answer = db.get_common_question_answer_by_id(common_questions_id)

    text = f"{smiles.question_sign}Вопрос: {question}.\n\n{smiles.check_mark} Ответ: {answer}"

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
@router_questions.callback_query(StateFilter(None), F.data.startswith("changeq_"))
async def change_common_question(callback: CallbackQuery, state: FSMContext):
    common_questions_id = callback.data.split('_')[1]

    await callback.message.answer("Введите новый вопрос заместо прошлого. Для отмены /cancel.")
    await state.update_data(common_qa_id=common_questions_id)
    await state.set_state(CommonQuestions.change_questiion)

    await callback.answer()


@router_questions.message(CommonQuestions.change_questiion, F.content_type.in_({'text'}), F.text[0] != "/")
async def get_new_common_question(message: Message, state: FSMContext):
    data = await state.get_data()
    common_questions_id = int(data['common_qa_id'])

    question = message.text

    if len(question) >= 10:
        db.update_common_question_by_id(question, common_questions_id)

        await message.answer("Вопрос был обновлен. Список общих вопросов и ответов - /ask")
        await state.clear()
    else:
        await message.answer("Слишком короткий вопрос. Попробуйте еще раз")


# При ошибочном типе сообщения нового вопроса
@router_questions.message(CommonQuestions.change_questiion, F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_type_of_new_common_question(message: Message):
    await message.answer("Напишите текстом!")

# --------------------------------------------------------------------------------------
# Редактирование общего ответа
@router_questions.callback_query(StateFilter(None), F.data.startswith("changea_"))
async def change_common_answer(callback: CallbackQuery, state: FSMContext):
    common_questions_id = callback.data.split('_')[1]

    await callback.message.answer("Введите новый ответ заместо прошлого. Для отмены /cancel.")
    await state.update_data(common_qa_id=common_questions_id)
    await state.set_state(CommonQuestions.change_answer)

    await callback.answer()


@router_questions.message(CommonQuestions.change_answer, F.content_type.in_({'text'}), F.text[0] != "/")
async def get_new_common_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    common_questions_id = int(data['common_qa_id'])

    answer = message.text

    if len(answer) >= 10:
        db.update_common_answer_by_id(answer, common_questions_id)

        await message.answer("Ответ был обновлен. Список общих вопросов и ответов - /ask")
        await state.clear()
    else:
        await message.answer("Слишком короткий ответ. Попробуйте еще раз")


# При ошибочном типе сообщения нового ответа
@router_questions.message(CommonQuestions.change_answer,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_type_of_new_common_answer(message: Message):
    await message.answer("Напишите текстом!")

# --------------------------------------------------------------------------------------
# Удаление общего вопроса и ответа из списка
@router_questions.callback_query(F.data.startswith("deleteqa_"))
async def delete_common_question_and_answer(callback: CallbackQuery, state: FSMContext):
    common_questions_id = callback.data.split('_')[1]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await callback.message.answer("Подтвердите удаление. Для отмены /cancel.", reply_markup=keyboard)
    await state.update_data(common_qa_id=common_questions_id)
    await state.set_state(CommonQuestions.delete_both)

    await callback.answer()


# Было введено что-то, а не выбрано подтверждение удаления
@router_questions.message(CommonQuestions.delete_both, F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice',
                                                                        'document', 'location', 'contact'}), F.text[0] != "/")
async def incorrect_deletion(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await message.answer("Вы сделали не правильный выбор. Для удаления нажмите кнопку ниже."
                                  " Для отмены /cancel.", reply_markup=keyboard)


@router_questions.callback_query(CommonQuestions.delete_both, F.data.startswith("confirm_delete"))
async def confirm_deletion(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    common_questions_id = int(data['common_qa_id'])

    db.delete_common_questions_by_id(common_questions_id)

    text = "Вопрос и ответ были удалены.\n\n"
    text += text_about_commands
    await callback.message.answer(text)
    await state.clear()

    await callback.answer()


# --------------------------------------------------------------------------------------
# Добавление вопроса и ответа в список
@router_questions.callback_query(StateFilter(None), F.data.startswith("add_qa"))
async def add_common_question_and_answer(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите вопрос. Для отмены - /cancel")
    await state.set_state(CommonQuestions.add_question)

    await callback.answer()


@router_questions.message(CommonQuestions.add_question, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_common_question(message: Message, state: FSMContext):
    question = message.text
    if len(question) > 10:
        await state.update_data(question=question)
        await message.answer("Теперь введите ответ:")
        await state.set_state(CommonQuestions.add_answer)
    else:
        await message.answer(f"Слишком короткий вопрос. Введите подробнее {smiles.pencil}")

# При ошибочном типе сообщения нового общего вопроса
@router_questions.message(CommonQuestions.add_question,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_new_question(message: Message):
    await message.answer("Напишите текстом!")


@router_questions.message(CommonQuestions.add_answer, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_common_answer(message: Message, state: FSMContext):
    answer = message.text
    if len(answer) > 10:
        data = await state.get_data()
        question = data['question']

        db.add_common_questions(question, answer)

        text = "Готово!\n\n"
        text += text_about_commands
        await message.answer(text)

        await state.clear()
    else:
        await message.answer(f"Слишком короткий ответ. Введите подробнее {smiles.pencil}")


# При ошибочном типе сообщения нового общего вопроса
@router_questions.message(CommonQuestions.add_answer,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_new_answer(message: Message):
    await message.answer("Напишите текстом!")
