import aiogram
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, \
    ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback, DialogCalendar, DialogCalendarCallback, \
    get_user_locale
from datetime import datetime, timedelta
from typing import List

import asyncio
import threading
import time
import pytz
import locale

import app.database.db as db
import app.smiles as smiles
from app.handlers.private_bot.handlers import text_about_commands

router_places = Router()

confirmations_date = [f"Сейчас {smiles.rocket}", f"Выбрать дату и время {smiles.clock}"]
novosibirsk_tz = pytz.timezone('Asia/Novosibirsk')


class GetPlace(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_place = State()
    waiting_for_type_new_place = State()
    waiting_for_confirmation = State()
    waiting_for_cancel = State()
    delete_from_queue = State()
    delete_from_list = State()


def make_keyboard(items: List[str]) -> ReplyKeyboardMarkup:
    """
    Создаёт реплай-клавиатуру с кнопками в один ряд
    :param items: список текстов для кнопок
    :return: объект реплай-клавиатуры
    """
    row = [KeyboardButton(text=item) for item in items]
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)


def schedule_task(place, execute_at):
    db.add_place_to_queue(place, execute_at)


def execute_scheduled_tasks():
    while True:
        now = datetime.now()
        places = db.get_places_from_queue()  # Получаем все места из очереди
        for place in places:
            place_id, place_name, execute_at = place
            if now >= execute_at:
                db.set_place(place_name)  # Обновляем место в БД (таблица с одним местом, которое выводится и в публичном боте), (status = 'current')
                # Добавить и в таблицу всех мест.
                db.add_place_to_list(place_name) #(status = 'list')
                print(f"Место '{place_name}' добавлено в БД.")
                db.remove_place_from_queue(place_id)  # Удаляем выполненную задачу
        time.sleep(60)  # Проверяем каждые 60 сек

# Запускаем фоновую задачу для выполнения запланированных задач
threading.Thread(target=execute_scheduled_tasks, daemon=True).start()


def get_places_list():
    list_of_places = db.get_places_from_list()

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


# Хэндлер на команду /setplace
@router_places.message(Command("setplace"))
async def cmd_set_my_place(message: Message, state: FSMContext):
    list_places_keyboard, _ = get_places_list()
    await message.answer("Выберите доступное место или добавьте новое:", reply_markup=list_places_keyboard)
    await state.set_state(GetPlace.waiting_for_place)


# Использовать выбранное место из списка
@router_places.callback_query(GetPlace.waiting_for_place, F.data.startswith("listplace_"))
async def callbacks_place_from_list(callback: CallbackQuery, state: FSMContext):
    place_id = callback.data.split('_')[1]

    place_text = db.get_place_from_list_by_id(place_id)

    # Сохраняем это место для дальнейшего использования
    await state.update_data(place=place_text)
    await state.update_data(if_old_place=1)
    await callback.message.answer("Выберите, когда хотите обновить ваше место:",
                         reply_markup=make_keyboard(confirmations_date))

    # Переход к выбору, когда добавить это место
    await state.set_state(GetPlace.waiting_for_confirmation)
    await callback.answer()


# Выбрано было ввести новое место
@router_places.callback_query(F.data.startswith("new_place"))
async def cmd_set_my_place(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите новое место. Для отмены - /cancel")
    await state.set_state(GetPlace.waiting_for_type_new_place)
    await callback.answer()


# Ввести новое место
@router_places.message(GetPlace.waiting_for_type_new_place, F.text[0] != "/")
async def set_new_place(message: Message, state: FSMContext):
    place = message.text
    if len(place) < 5:
        await message.answer("Попробуйте написать более подробно.")
    else:
        await state.update_data(place=place)
        await state.update_data(if_old_place=0)
        await message.answer("Выберите, когда хотите обновить ваше место:", reply_markup=make_keyboard(confirmations_date))

        await state.set_state(GetPlace.waiting_for_confirmation)


@router_places.message(GetPlace.waiting_for_place, F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_type_of_place(message: Message):
    await message.answer("Напишите текстом!")


# Сейчас
@router_places.message(GetPlace.waiting_for_confirmation, F.text==confirmations_date[0])
async def confirm_date_now(message: Message, state: FSMContext):
    data = await state.get_data()
    place = str(data['place'])
    check_status_of_place = int(data['if_old_place'])
    db.set_place(place)

    if check_status_of_place == 0:
        db.add_place_to_list(place)

    await message.answer("Место обновлено!", reply_markup=ReplyKeyboardRemove())
    await state.clear()


# Новая дата
@router_places.message(GetPlace.waiting_for_confirmation, F.text == confirmations_date[1])
async def confirm_set_new_date(message: Message, state: FSMContext):
    # on Ubuntu server use "ru_RU.UTF-8" after setting it in "sudo dpkg-reconfigure locales" and rebooting system
    await message.answer(
            "Хорошо, теперь выберите дату: ",
            reply_markup=await SimpleCalendar(locale="ru_RU").start_calendar()
        )
    await state.set_state(GetPlace.waiting_for_date)


# Если не правильный выбор
@router_places.message(GetPlace.waiting_for_confirmation)
async def confirm_date_incorrect(message: Message):
    await message.answer(f"Неправильный выбор. Выберите из двух кнопок.")


@router_places.callback_query(GetPlace.waiting_for_date, SimpleCalendarCallback.filter())
async def process_simple_calendar(callback_query: CallbackQuery, callback_data: CallbackData, state: FSMContext):
    # on Ubuntu server use "ru_RU.UTF-8" after setting it in "sudo dpkg-reconfigure locales" and rebooting system
    calendar = SimpleCalendar(locale="ru_RU", show_alerts=True)
    selected, date = await calendar.process_selection(callback_query, callback_data)
    if selected:
        await callback_query.message.answer(f'Вы выбрали {date.strftime("%d/%m/%Y")}. Теперь введите ваше время в формате HH:mm:', reply_markup=ReplyKeyboardRemove())

        await state.set_state(GetPlace.waiting_for_time)

        await state.update_data(date=date)
        await callback_query.answer()


@router_places.message(GetPlace.waiting_for_time, F.content_type.in_({'text'}))
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
@router_places.message(Command("getplace"))
async def cmd_get_place(message: Message, state: FSMContext):
    await state.clear()
    place = db.get_place()
    await message.answer(f'Информация о Вашем местонахождении: {place}')
    time.sleep(1)
    await message.answer(text=text_about_commands)


# Посмотреть список доступных мест
@router_places.message(Command("placeslist"))
async def cmd_get_places_list(message: Message, state: FSMContext):
    await state.clear()
    _, buttons = get_places_list()


    if len(buttons) == 1:
        await message.answer("Использованных ранее мест нет. Задайте в /setplace")  # Если только одна кнопка "Задать место"
    else:
        buttons.pop()
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer("Выберите доступное место:", reply_markup=keyboard)


@router_places.callback_query(StateFilter(None), F.data.startswith("listplace_"))
async def action_with_place_from_list(callback: CallbackQuery, state: FSMContext):
    place_id = callback.data.split('_')[1]

    place_text = db.get_place_from_list_by_id(place_id)



    text = f"{place_text}."

    buttons = [
        [InlineKeyboardButton(text="Удалить место из списка", callback_data=f"deleteplacefromlist_{place_id}")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router_places.callback_query(F.data.startswith("deleteplacefromlist_"))
async def delete_place_from_list(callback: CallbackQuery, state: FSMContext):
    place_id = callback.data.split('_')[1]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await callback.message.answer("Подтвердите удаление. Для отмены /cancel.", reply_markup=keyboard)
    await state.update_data(place_list_id=place_id)
    await state.set_state(GetPlace.delete_from_list)

    await callback.answer()


# Было введено что-то, а не выбрано подтверждение удаления
@router_places.message(GetPlace.delete_from_list, F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice',
                                                                        'document', 'location', 'contact'}), F.text[0] != "/")
async def incorrect_deletion_place_from_list(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await message.answer("Вы сделали не правильный выбор. Для удаления нажмите кнопку ниже."
                                  " Для отмены /cancel.", reply_markup=keyboard)


@router_places.callback_query(GetPlace.delete_from_list, F.data.startswith("confirm_delete"))
async def confirm_deletion_place_from_list(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    place_id = int(data['place_list_id'])

    db.delete_place_from_list(place_id)

    await callback.message.answer("Место было удалено из списка.\nСписок мест - /placeslist\nЗадать место - /setplace")
    await state.clear()

    await callback.answer()


# Работа с очередью запланированных для добавления мест
# Хэндлер на команду /placesqueue
@router_places.message(Command("placesqueue"))
async def cmd_get_places_queue(message: Message, state: FSMContext):
    await state.clear()
    places = db.get_places_from_queue()
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


@router_places.callback_query(StateFilter(None), F.data.startswith("placesqueue_"))
async def callbacks_places_queue(callback: CallbackQuery):
    place_queue_id = callback.data.split('_')[1]

    place, execute_at = db.get_places_from_queue_by_id(place_queue_id)

    text = f"{place}.\n\nЗапланировано на: {execute_at.strftime('%d-%m-%Y %H:%M')}"

    buttons = [
        [InlineKeyboardButton(text="Удалить место из очереди", callback_data=f"deleteplacefromq_{place_queue_id}")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


# Удаление места из очереди на добавление
@router_places.callback_query(F.data.startswith("deleteplacefromq_"))
async def delete_place_from_queue(callback: CallbackQuery, state: FSMContext):
    place_queue_id = callback.data.split('_')[1]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await callback.message.answer("Подтвердите удаление. Для отмены /cancel.", reply_markup=keyboard)
    await state.update_data(place_queue_id=place_queue_id)
    await state.set_state(GetPlace.delete_from_queue)

    await callback.answer()


# Было введено что-то, а не выбрано подтверждение удаления
@router_places.message(GetPlace.delete_from_queue, F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice',
                                                                        'document', 'location', 'contact'}), F.text[0] != "/")
async def incorrect_deletion_place_from_queue(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await message.answer("Вы сделали не правильный выбор. Для удаления нажмите кнопку ниже."
                                  " Для отмены /cancel.", reply_markup=keyboard)


@router_places.callback_query(GetPlace.delete_from_queue, F.data.startswith("confirm_delete"))
async def confirm_deletion_place_from_queue(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    place_queue_id = int(data['place_queue_id'])

    db.remove_place_from_queue(place_queue_id)

    await callback.message.answer("Место было удалено из очереди. Посмотреть очередь запланированных для добавления мест - /placesqueue")
    await state.clear()

    await callback.answer()
