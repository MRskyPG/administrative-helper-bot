from typing import List
import aiogram
from datetime import datetime, timedelta
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback, DialogCalendar, DialogCalendarCallback, \
    get_user_locale
from aiogram import F, Router
from aiogram.filters.command import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, KeyboardButton, InlineKeyboardMarkup, BotCommand,\
    ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.filters.callback_data import CallbackData
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import asyncio
import threading
import time
import pytz
import locale

# Мои библиотеки
import app.db
import app.crypt_db
from app.crypt_db import get_user_by_tg_id, register_user, verify_password, set_auth_status, get_auth_status
import app.smiles as smiles

novosibirsk_tz = pytz.timezone('Asia/Novosibirsk')

router = Router()

confirmations = [f"Да {smiles.check_mark}", f"Нет, изменить ответ {smiles.cross_mark}"]
confirmations_date = [f"Сейчас {smiles.rocket}", f"Выбрать дату и время {smiles.clock}"]


text_about_commands = "Выберите, что вас интересует:" \
                      "\n/setplace - Задать место, где вы находитесь" \
                      "\n/placesqueue - Очередь запланированных мест для добавления" \
        "\n/placeslist - Список использованных ранее мест" \
        "\n/getplace - Получить сведения о заданном ранее месте" \
        "\n/ask - Список общих вопросов/ответов" \
        "\n/staffquestions - Посмотреть вопросы сотрудников"


# Глобальная переменная для второго бота
bot_2 : aiogram.Bot

# Для хранения состояний
class DoAuth(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()


class DoRegister(StatesGroup):
    waiting_for_tg_id = State()
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_role = State()


class DoAnswer(StatesGroup):
    getting_answer = State()
    confirmation = State()

class GetPlace(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_place = State()
    waiting_for_type_new_place = State()
    waiting_for_confirmation = State()
    waiting_for_cancel = State()
    delete_from_queue = State()
    delete_from_list = State()

class CommonQuestions(StatesGroup):
    add_question = State()
    add_answer = State()
    change_questiion = State()
    change_answer = State()
    delete_both = State()

def set_bot_2(bot):
    global bot_2
    bot_2 = bot


def make_row_keyboard(items: List[str]) -> ReplyKeyboardMarkup:
    """
    Создаёт реплай-клавиатуру с кнопками в один ряд
    :param items: список текстов для кнопок
    :return: объект реплай-клавиатуры
    """
    row = [KeyboardButton(text=item) for item in items]
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)


async def update_ask_text(message: Message, answer: str):
    await message.edit_text(text=f"{answer}", reply_markup=get_question_keyboard())


def schedule_task(place, execute_at):
    app.db.add_place_to_queue(place, execute_at)


def execute_scheduled_tasks():
    while True:
        now = datetime.now()
        places = app.db.get_places_from_queue()  # Получаем все места из очереди
        for place in places:
            place_id, place_name, execute_at = place
            if now >= execute_at:
                app.db.set_place(place_name)  # Обновляем место в БД (таблица с одним местом, которое выводится и в публичном боте)
                # Добавить и в таблицу всех мест.
                app.db.add_place_to_list(place_name)
                print(f"Место '{place_name}' добавлено в БД.")
                app.db.remove_place_from_queue(place_id)  # Удаляем выполненную задачу
        time.sleep(60)  # Проверяем каждые 60 сек

# Запускаем фоновую задачу для выполнения запланированных задач
threading.Thread(target=execute_scheduled_tasks, daemon=True).start()

def get_places_list():
    list_of_places = app.db.get_places_from_list()

    buttons = []
    if len(list_of_places) != 0:

        i = 1

        for place in list_of_places:
            button = [InlineKeyboardButton(text=f"{i}. {place[1]}", callback_data=f"listplace_{place[0]}")]
            buttons.append(button)
            i += 1

        buttons.append([InlineKeyboardButton(text=f"Задать место {smiles.pencil}", callback_data="new_place")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)


    else:
        buttons.append([InlineKeyboardButton(text=f"Задать место {smiles.pencil}", callback_data="new_place")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)


    return keyboard, buttons


def get_users_list(role: str):
    list_of_users = []
    is_empty = False

    if role == "owner":
        list_of_users = app.crypt_db.get_owners()

    elif role == "admin":
        list_of_users = app.crypt_db.get_admins()

    buttons = []
    if len(list_of_users) != 0:

        i = 1

        for user in list_of_users:
            created_at = user[2]

            button = [InlineKeyboardButton(text=f"{i}. Tg_id: {user[1]}. Создан: {created_at.strftime('%d-%m-%Y %H:%M')}", callback_data=f"{role}_{user[0]}")]
            buttons.append(button)
            i += 1

        buttons.append(
            [InlineKeyboardButton(text=f"Зарегистрировать {smiles.pencil}", callback_data="register_user")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        return keyboard, buttons, is_empty
    else:
        buttons.append(
            [InlineKeyboardButton(text=f"Зарегистрировать {smiles.pencil}", callback_data="register_user")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        is_empty = True

        return keyboard, buttons, is_empty


async def set_commands_list_private(bot):
    commands = [
        BotCommand(command="/start", description="Запуск бота"),
        BotCommand(command="/auth", description="Авторизоваться в системе"),
        BotCommand(command="/setplace", description="Задать место, где вы находитесь"),
        BotCommand(command="/placesqueue", description="Очередь запланированных мест для добавления"),
        BotCommand(command="/placeslist", description="Список использованных ранее мест"),
        BotCommand(command="/getplace", description="Получить сведения о заданном ранее месте"),
        BotCommand(command="/ask", description="Список общих вопросов/ответов"),
        BotCommand(command="/staffquestions", description="Посмотреть вопросы сотрудников"),
        BotCommand(command="/cancel", description="Отмена действия"),
        BotCommand(command="/register", description="Регистрация пользователя (только для owner, не для admin)"),
        BotCommand(command="/logout", description="Выйти из системы")
    ]
    await bot.set_my_commands(commands)


# Хэндлер на команду /start
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    # Проверяем, есть ли пользователь в базе
    user = get_user_by_tg_id(message.from_user.id)
    if user is None:
        await message.answer(
            "Вы не зарегистрированы в системе. Доступ запрещен.")
        return

    # Проверяем статус авторизации пользователя в базе
    if not get_auth_status(message.from_user.id):
        await message.answer("Доступ запрещён. Пожалуйста, пройдите авторизацию командой /auth")
        return

    start_text = f'Привет, {message.from_user.full_name}! Данный бот поможет Вам удобно взаимодействовать с сотрудниками. ' \
                 f'\n\nЗдесь Вы можете:' \
                 f'\n\t- Задать ваше текущее место сейчас или запланировать его позже {smiles.clock}' \
                 f'\n\t- Редактировать список запланированных и использованных ранее мест {smiles.pencil}' \
                 f'\n\t- Отвечать на вопросы сотрудников {smiles.letter}' \
                 f'\n\t- Редактировать общие ответы и вопросы! {smiles.save_emoji}' \
                 f'\n\nСотрудники будут взаимодействовать с вами через другого бота, ' \
                 f'по которому смогут перейти по QR-коду.\n\n'
    final_text = start_text + text_about_commands
    await message.answer(final_text, reply_markup=ReplyKeyboardRemove())


# ---------------------------------------------------------------
# Хэндлер на команду /auth
@router.message(Command("auth"))
async def cmd_auth(message: Message, state: FSMContext):
    if get_auth_status(message.from_user.id):
        await message.answer("Вы уже авторизованы!")
        return

    user = get_user_by_tg_id(message.from_user.id)
    if user is None:
        await message.answer(
            "Вы не зарегистрированы в системе. Доступ запрещен.")
        return

    await message.answer("Введите ваш никнейм (логин). Для отмены - /cancel")
    await state.set_state(DoAuth.waiting_for_login)


@router.message(DoAuth.waiting_for_login, F.content_type.in_({'text'}), F.text[0] != "/")
async def enter_login(message: Message, state: FSMContext):
    login = message.text
    await state.update_data(login=login)
    await message.answer("Теперь введите пароль:")
    await state.set_state(DoAuth.waiting_for_password)


# При ошибочном типе сообщения логина
@router.message(DoAuth.waiting_for_login,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_enter_login(message: Message):
    await message.answer("Напишите текстом!")


@router.message(DoAuth.waiting_for_password, F.content_type.in_({'text'}), F.text[0] != "/")
async def enter_password(message: Message, state: FSMContext):
    password = message.text

    data = await state.get_data()
    login = data['login']

    user = get_user_by_tg_id(message.from_user.id)

    if user[2] == login and verify_password(user[3], password):
        set_auth_status(message.from_user.id, True)
        await message.reply("Авторизация прошла успешно!")

        start_text = f'Привет, {message.from_user.full_name}! Данный бот поможет Вам удобно взаимодействовать с сотрудниками. ' \
                     f'\n\nЗдесь Вы можете:' \
                     f'\n\t- Задать ваше текущее место сейчас или запланировать его позже {smiles.clock}' \
                     f'\n\t- Редактировать список запланированных и использованных ранее мест {smiles.pencil}' \
                     f'\n\t- Отвечать на вопросы сотрудников {smiles.letter}' \
                     f'\n\t- Редактировать общие ответы и вопросы! {smiles.save_emoji}' \
                     f'\n\nСотрудники будут взаимодействовать с вами через другого бота, ' \
                     f'по которому смогут перейти по QR-коду.\n\n'

        final_text = start_text + text_about_commands

        time.sleep(2)
        await message.answer(final_text, reply_markup=ReplyKeyboardRemove())

    else:
        await message.reply("Неверные данные авторизации.")

    await state.clear()


# При ошибочном типе сообщения пароля
@router.message(DoAuth.waiting_for_password,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_enter_password(message: Message):
    await message.answer("Напишите текстом!")

# --------------------------------------------------


@router.message(Command("logout"))
async def cmd_logout(message: Message):
    user = get_user_by_tg_id(message.from_user.id)
    if user is None:
        await message.answer(
            "Вы не зарегистрированы в системе. Пожалуйста, обратитесь к администратору для регистрации.")
        return

    if not get_auth_status(message.from_user.id):
        await message.answer("Вы еще не в системе. Пройдите авторизацию командой /auth <username> <password>.")
        return

    set_auth_status(message.from_user.id, False)
    await message.reply("Вы вышли из системы.")


# Хэндлер на команду /register для регистрации новых пользователей. Доступно только владельцу (owner).
@router.message(Command("register"))
async def cmd_register(message: Message):
    button = [[InlineKeyboardButton(text="Зарегистрировать пользователя", callback_data="register_user")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=button)
    await message.answer("Нажмите, чтобы начать регистрацию", reply_markup=keyboard)


# Хэндлер на команду /manage
@router.message(Command("manage"))
async def cmd_manage(message: Message):
    # Проверяем, является ли отправитель владельцем
    user = get_user_by_tg_id(message.from_user.id)

    if user is None or user[4] != 'owner':
        await message.reply("У вас нет прав для управления пользователями.")
        return

    text = "Выберите, что вас интересует:"

    buttons = [
        [InlineKeyboardButton(text=f"Список владельцев", callback_data=f"list_owners")],
        [InlineKeyboardButton(text=f"Список админов", callback_data=f"list_admins")],
        [InlineKeyboardButton(text=f"Зарегистрировать нового пользователя", callback_data=f"register_user")],
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(text, reply_markup=keyboard)


# Посмотреть список пользователей-владельцев
@router.callback_query(F.data.startswith("list_owners"))
async def callbacks_owners_list(callback: CallbackQuery):
    owners_list_keyboard, _, is_empty = get_users_list("owner")
    if is_empty:
        await callback.message.answer("Список владельцев пуст.", reply_markup=owners_list_keyboard)
    else:
        await callback.message.answer("Список владельцев:", reply_markup=owners_list_keyboard)
    await callback.answer()


# Посмотреть список пользователей-админов
@router.callback_query(F.data.startswith("list_admins"))
async def callbacks_admins_list(callback: CallbackQuery):
    admins_list_keyboard, _, is_empty = get_users_list("admin")
    if is_empty:
        await callback.message.answer("Список админов пуст.", reply_markup=admins_list_keyboard)
    else:
        await callback.message.answer("Список админов:", reply_markup=admins_list_keyboard)
    await callback.answer()


# ----------------------------------------------------------------------------------------------
# Зарегистрировать пользователя
@router.callback_query(F.data.startswith("register_user"))
async def callbacks_register(callback: CallbackQuery, state: FSMContext):
    # Проверяем, является ли отправитель владельцем
    user = get_user_by_tg_id(callback.from_user.id)

    if user is None or user[4] != 'owner':
        await callback.message.reply("У вас нет прав для управления пользователями.")
        return

    await callback.message.answer("Введите Telegram ID пользователя (Через TestAttach Bot). Для отмены - /cancel")
    await state.set_state(DoRegister.waiting_for_tg_id)


@router.message(DoRegister.waiting_for_tg_id, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_tg_id(message: Message, state: FSMContext):
    tg_id = message.text

    try:
        new_tg_id = int(tg_id)
    except ValueError:
        await message.reply("telegram id должен быть числом. Попробуйте еще раз.")
        return

    await state.update_data(tg_id=tg_id)
    await message.answer("Теперь введите username пользователя:")
    await state.set_state(DoRegister.waiting_for_login)


# При ошибочном типе сообщения tg_id
@router.message(DoRegister.waiting_for_tg_id,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_tg_id(message: Message):
    await message.answer("Напишите числовое значение!")


@router.message(DoRegister.waiting_for_login, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_login(message: Message, state: FSMContext):
    login = message.text
    if len(login) < 5:
        await message.answer("Логин слишком короткий. Попробуйте еще раз.")
        return

    await state.update_data(login=login)
    await message.answer("Теперь введите пароль пользователя:")
    await state.set_state(DoRegister.waiting_for_password)


# При ошибочном типе сообщения login
@router.message(DoRegister.waiting_for_login,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_login(message: Message):
    await message.answer("Напишите текстом!")


@router.message(DoRegister.waiting_for_password, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_password(message: Message, state: FSMContext):
    password = message.text
    if len(password) < 5:
        await message.answer("Пароль слишком короткий. Попробуйте еще раз.")
        return


    await state.update_data(password=password)
    await message.answer("Теперь введите роль пользователя (owner или admin):")
    await state.set_state(DoRegister.waiting_for_role)


# При ошибочном типе сообщения password
@router.message(DoRegister.waiting_for_password,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_password(message: Message):
    await message.answer("Напишите текстом!")


@router.message(DoRegister.waiting_for_role, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_role(message: Message, state: FSMContext):
    role = message.text

    if role not in ('owner', 'admin'):
        await message.reply("Роль должна быть 'owner' или 'admin'.")
        return

    data = await state.get_data()
    tg_id = int(data['tg_id'])
    login = data['login']
    password = data['password']

    if register_user(tg_id, login, password, role):
        await message.reply(f"Пользователь с telegram id {tg_id} зарегистрирован с ролью {role}.")
    else:
        await message.reply(f"Пользователь с telegram id {tg_id} уже существует.")

    await state.clear()


# При ошибочном типе сообщения role
@router.message(DoRegister.waiting_for_role,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_role(message: Message):
    await message.answer("Напишите текстом!")


# TODO: Исправить под действия с админами и овнерами (?)
# @router.callback_query(StateFilter(None), F.data.startswith("common_"))
# async def callbacks_common_questions(callback: CallbackQuery):
#     common_questions_id = callback.data.split('_')[1]
#
#     # Получаем вопрос и ответ
#     question, answer = app.db.get_common_question_answer_by_id(common_questions_id)
#
#     text = f"{smiles.question_sign}Вопрос: {question}.\n\n{smiles.check_mark} Ответ: {answer}"
#
#     buttons = [
#         [InlineKeyboardButton(text="Редактировать вопрос", callback_data=f"changeq_{common_questions_id}")],
#         [InlineKeyboardButton(text="Редактировать ответ", callback_data=f"changea_{common_questions_id}")],
#         [InlineKeyboardButton(text="Удалить вопрос и ответ из списка", callback_data=f"deleteqa_{common_questions_id}")],
#     ]
#     keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
#
#     await callback.message.answer(text, reply_markup=keyboard)
#     await callback.answer()


#------------------------------------------------------------------------------------------------------
# Хэндлер на команду /setplace
@router.message(Command("setplace"))
async def cmd_set_my_place(message: Message, state: FSMContext):
    list_places_keyboard, _ = get_places_list()
    await message.answer("Выберите доступное место или добавьте новое:", reply_markup=list_places_keyboard)
    await state.set_state(GetPlace.waiting_for_place)


# Использовать выбранное место из списка
@router.callback_query(GetPlace.waiting_for_place, F.data.startswith("listplace_"))
async def callbacks_place_from_list(callback: CallbackQuery, state: FSMContext):
    place_id = callback.data.split('_')[1]

    place_text = app.db.get_place_from_list_by_id(place_id)

    # Сохраняем это место для дальнейшего использования
    await state.update_data(place=place_text)
    await state.update_data(if_old_place=1)
    await callback.message.answer("Выберите, когда хотите обновить ваше место:",
                         reply_markup=make_row_keyboard(confirmations_date))

    # Переход к выбору, когда добавить это место
    await state.set_state(GetPlace.waiting_for_confirmation)
    await callback.answer()


# Выбрано было ввести новое место
@router.callback_query(F.data.startswith("new_place"))
async def cmd_set_my_place(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое место. Для отмены - /cancel")
    await state.set_state(GetPlace.waiting_for_type_new_place)
    await callback.answer()


# Ввести новое место
@router.message(GetPlace.waiting_for_type_new_place, F.text[0] != "/")
async def set_new_place(message: Message, state: FSMContext):
    place = message.text
    if len(place) < 5:
        await message.answer("Попробуйте написать более подробно.")
    else:
        await state.update_data(place=place)
        await state.update_data(if_old_place=0)
        await message.answer("Выберите, когда хотите обновить ваше место:", reply_markup=make_row_keyboard(confirmations_date))

        await state.set_state(GetPlace.waiting_for_confirmation)


@router.message(GetPlace.waiting_for_place, F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_type_of_place(message: Message):
    await message.answer("Напишите текстом!")


# Сейчас
@router.message(GetPlace.waiting_for_confirmation, F.text==confirmations_date[0])
async def confirm_date_now(message: Message, state: FSMContext):
    data = await state.get_data()
    place = str(data['place'])
    check_status_of_place = int(data['if_old_place'])
    app.db.set_place(place)

    if check_status_of_place == 0:
        app.db.add_place_to_list(place)

    await message.answer("Место обновлено!", reply_markup=ReplyKeyboardRemove())
    await state.clear()

# Новая дата
@router.message(GetPlace.waiting_for_confirmation, F.text == confirmations_date[1])
async def confirm_set_new_date(message: Message, state: FSMContext):
    # on Ubuntu server use "ru_RU.UTF-8" after setting it in "sudo dpkg-reconfigure locales" and rebooting system
    await message.answer(
            "Хорошо, теперь выберите дату: ",
            reply_markup=await SimpleCalendar(locale="ru_RU").start_calendar()
        )
    await state.set_state(GetPlace.waiting_for_date)


# Если не правильный выбор
@router.message(GetPlace.waiting_for_confirmation)
async def confirm_date_incorrect(message: Message):
    await message.answer(f"Неправильный выбор. Выберите из двух кнопок.")


@router.callback_query(GetPlace.waiting_for_date, SimpleCalendarCallback.filter())
async def process_simple_calendar(callback_query: CallbackQuery, callback_data: CallbackData, state: FSMContext):
    # on Ubuntu server use "ru_RU.UTF-8" after setting it in "sudo dpkg-reconfigure locales" and rebooting system
    calendar = SimpleCalendar(locale="ru_RU", show_alerts=True)
    selected, date = await calendar.process_selection(callback_query, callback_data)
    if selected:
        await callback_query.message.answer(f'Вы выбрали {date.strftime("%d/%m/%Y")}. Теперь введите ваше время в формате HH:mm:', reply_markup=ReplyKeyboardRemove())

        await state.set_state(GetPlace.waiting_for_time)

        await state.update_data(date=date)
        await callback_query.answer()

@router.message(GetPlace.waiting_for_time, F.content_type.in_({'text'}))
async def set_new_time(message: Message, state: FSMContext):

    try:
        # Разделяем строку на часы и минуты
        h, m = map(int, message.text.split(":"))

        # Проверяем, что часы и минуты находятся в допустимых пределах
        if 0 <= h < 24 and 0 <= m < 60:
            # Извлекаем нужные данные
            data = await state.get_data()
            date = data['date']
            place = data['place']

            new_time = timedelta(hours=h, minutes=m)

            execute_at = date + new_time  # Время выполнения задачи

            if execute_at > datetime.now():
                schedule_task(place, execute_at)  # Запланируем задачу
                await message.answer(f"Место '{place}' будет добавлено в {execute_at.strftime('%d-%m-%Y %H:%M')}.")
            else:
                await message.answer("Выбранная дата уже прошла. Пожалуйста, выберите другую дату.")

            await state.clear()

        else:
            await message.answer("Пожалуйста, введите время в формате HH:mm (часы от 00 до 23, минуты от 00 до 59).")
    except ValueError:
        await message.answer("Неверный формат. Пожалуйста, введите время в формате HH:mm.")


# Хэндлер на команду /getplace
@router.message(Command("getplace"))
async def cmd_get_place(message: Message, state: FSMContext):
    await state.clear()
    place = app.db.get_place()
    await message.answer(f'Информация о Вашем местонахождении: {place}')
    time.sleep(1)
    await message.answer(text=text_about_commands)


# ------------------------------------------------------------------------------------
# Посмотреть список доступных мест
@router.message(Command("placeslist"))
async def cmd_get_places_list(message: Message, state: FSMContext):
    await state.clear()
    _, buttons = get_places_list()


    if len(buttons) == 1:
        await message.answer("Использованных ранее мест нет. Задайте в /setplace")  # Если только одна кнопка "Задать место"
    else:
        buttons.pop()
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("Выберите доступное место:", reply_markup=keyboard)


@router.callback_query(StateFilter(None), F.data.startswith("listplace_"))
async def action_with_place_from_list(callback: CallbackQuery, state: FSMContext):
    place_id = callback.data.split('_')[1]

    place_text = app.db.get_place_from_list_by_id(place_id)



    text = f"{place_text}."

    buttons = [
        [InlineKeyboardButton(text="Удалить место из списка", callback_data=f"deleteplacefromlist_{place_id}")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("deleteplacefromlist_"))
async def delete_place_from_list(callback: CallbackQuery, state: FSMContext):
    place_id = callback.data.split('_')[1]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await callback.message.answer("Подтвердите удаление. Для отмены /cancel.", reply_markup=keyboard)
    await state.update_data(place_list_id=place_id)
    await state.set_state(GetPlace.delete_from_list)

    await callback.answer()


# Было введено что-то, а не выбрано подтверждение удаления
@router.message(GetPlace.delete_from_list, F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice',
                                                                        'document', 'location', 'contact'}), F.text[0] != "/")
async def incorrect_deletion_place_from_list(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await message.answer("Вы сделали не правильный выбор. Для удаления нажмите кнопку ниже."
                                  " Для отмены /cancel.", reply_markup=keyboard)


@router.callback_query(GetPlace.delete_from_list, F.data.startswith("confirm_delete"))
async def confirm_deletion_place_from_list(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    place_id = int(data['place_list_id'])

    app.db.delete_place_from_list(place_id)

    await callback.message.answer("Место было удалено из списка.\nСписок мест - /placeslist\nЗадать место - /setplace")
    await state.clear()

    await callback.answer()

# ------------------------------------------------------------------------------------
# Работа с очередь запланированных для добавления мест
# Хэндлер на команду /placesqueue
@router.message(Command("placesqueue"))
async def cmd_get_places_queue(message: Message, state: FSMContext):
    await state.clear()
    places = app.db.get_places_from_queue()
    if len(places) != 0:
        buttons = []
        i = 1

        for place in places:
            date = place[2]
            format_date = date.strftime('%d-%m-%Y %H:%M')
            button = [InlineKeyboardButton(text=f"{i}. {place[1]}. Время: {format_date}", callback_data=f"placesqueue_{place[0]}")]
            buttons.append(button)
            i += 1

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply("Выберите запланированное место:", reply_markup=keyboard)

    else:
        await message.reply("Запланированных для добавления мест нет. Запланировать - /setplace")


@router.callback_query(StateFilter(None), F.data.startswith("placesqueue_"))
async def callbacks_places_queue(callback: CallbackQuery):
    place_queue_id = callback.data.split('_')[1]

    place, execute_at = app.db.get_places_from_queue_by_id(place_queue_id)

    text = f"{place}.\n\nЗапланировано на: {execute_at.strftime('%d-%m-%Y %H:%M')}"

    buttons = [
        [InlineKeyboardButton(text="Удалить место из очереди", callback_data=f"deleteplacefromq_{place_queue_id}")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


# Удаление места из очереди на добавление
@router.callback_query(F.data.startswith("deleteplacefromq_"))
async def delete_place_from_queue(callback: CallbackQuery, state: FSMContext):
    place_queue_id = callback.data.split('_')[1]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await callback.message.answer("Подтвердите удаление. Для отмены /cancel.", reply_markup=keyboard)
    await state.update_data(place_queue_id=place_queue_id)
    await state.set_state(GetPlace.delete_from_queue)

    await callback.answer()


# Было введено что-то, а не выбрано подтверждение удаления
@router.message(GetPlace.delete_from_queue, F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice',
                                                                        'document', 'location', 'contact'}), F.text[0] != "/")
async def incorrect_deletion_place_from_queue(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await message.answer("Вы сделали не правильный выбор. Для удаления нажмите кнопку ниже."
                                  " Для отмены /cancel.", reply_markup=keyboard)


@router.callback_query(GetPlace.delete_from_queue, F.data.startswith("confirm_delete"))
async def confirm_deletion_place_from_queue(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    place_queue_id = int(data['place_queue_id'])

    app.db.remove_place_from_queue(place_queue_id)

    await callback.message.answer("Место было удалено из очереди. Посмотреть очередь запланированных для добавления мест - /placesqueue")
    await state.clear()

    await callback.answer()
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
            button = [InlineKeyboardButton(text=f"{i}. от {question[2]}: {question[3]}", callback_data=f"question_{question[0]}")]
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
    await bot_2.send_message(chat_id=chat_id, text=f"Вам ответил О.Е.Аврунев!\n\n{smiles.question_sign} Ваш вопрос: {question}\n\n{smiles.check_mark} Ответ: {answer}")

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
    await message.answer(f"Неправильный выбор {smiles.cross_mark}. Выберите из двух кнопок.")



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

        buttons.append([InlineKeyboardButton(text=f"Добавить вопрос и ответ {smiles.pencil}", callback_data="add_qa")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply("Выберите вопрос:", reply_markup=keyboard)

    else:
        buttons.append([InlineKeyboardButton(text=f"Добавить вопрос и ответ {smiles.pencil}", callback_data="add_qa")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("Нет общих вопросов и ответов.", reply_markup=keyboard)


@router.callback_query(StateFilter(None), F.data.startswith("common_"))
async def callbacks_common_questions(callback: CallbackQuery):
    common_questions_id = callback.data.split('_')[1]

    # Получаем вопрос и ответ
    question, answer = app.db.get_common_question_answer_by_id(common_questions_id)

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
        await message.answer("Слишком короткий вопрос. Попробуйте еще раз")


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
        await message.answer("Слишком короткий ответ. Попробуйте еще раз")


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
@router.message(CommonQuestions.delete_both, F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice',
                                                                        'document', 'location', 'contact'}), F.text[0] != "/")
async def incorrect_deletion(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await message.answer("Вы сделали не правильный выбор. Для удаления нажмите кнопку ниже."
                                  " Для отмены /cancel.", reply_markup=keyboard)


@router.callback_query(CommonQuestions.delete_both, F.data.startswith("confirm_delete"))
async def confirm_deletion(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    common_questions_id = int(data['common_qa_id'])

    app.db.delete_common_questions_by_id(common_questions_id)

    text = "Вопрос и ответ были удалены.\n\n"
    text += text_about_commands
    await callback.message.answer(text)
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
        await message.answer(f"Слишком короткий вопрос. Введите подробнее {smiles.pencil}")

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

        text = "Готово!\n\n"
        text += text_about_commands
        await message.answer(text)

        await state.clear()
    else:
        await message.answer(f"Слишком короткий ответ. Введите подробнее {smiles.pencil}")


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
    time.sleep(1)
    await message.answer(text=text_about_commands)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="Действие отменено",
        reply_markup=ReplyKeyboardRemove()
    )
    time.sleep(1)
    await message.answer(text=text_about_commands)

@router.message(F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def any_message(message: Message, state: FSMContext):
    await message.answer("Неизвестная команда. Попробуйте /start")

