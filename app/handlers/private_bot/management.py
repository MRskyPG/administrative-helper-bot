import aiogram
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter

import app.database.crypt_db as db
import app.smiles as smiles

router_manage = Router()

# Глобальная переменная для бота
bot_1: aiogram.Bot


def set_private_bot(bot):
    global bot_1
    bot_1 = bot


class DoRegister(StatesGroup):
    waiting_for_tg_id = State()
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_role = State()


class ManageUser(StatesGroup):
    confirm_deletion_user = State()


async def get_users_list(role: str, your_tg_id: int):
    list_of_users = []
    is_empty = False

    if role == "owner":
        list_of_users = db.get_owners()

    elif role == "admin":
        list_of_users = db.get_admins()

    buttons = []
    if len(list_of_users) != 0:

        i = 1

        for user in list_of_users:
            created_at = user[2]

            try:
                user_acc: types.User = await bot_1.get_chat(user[1])
            except TelegramBadRequest as e:
                if "chat not found" in str(e):
                    await bot_1.send_message(your_tg_id, "Ошибка: пользователь не найден в Telegram. Проверьте корректность данных.")
                    buttons.append(
                        [InlineKeyboardButton(text=f"Зарегистрировать {smiles.pencil}", callback_data="register_user")])
                    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                    is_empty = True

                    return keyboard, buttons, is_empty

            user_fullname = user_acc.full_name

            if user[1] != your_tg_id:
                button = [
                    InlineKeyboardButton(text=f"{i}. {user_fullname}. Tg_id: {user[1]}. Создан: {created_at.strftime('%d-%m-%Y %H:%M')}",
                                         callback_data=f"{role}_{user[0]}")]
            else:
                button = [InlineKeyboardButton(text=f"{i}. {smiles.check_mark} (Это Вы). Tg_id: {user[1]}. Создан: {created_at.strftime('%d-%m-%Y %H:%M')}", callback_data=f"{role}_{user[0]}")]

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


# Хэндлер на команду /manage
@router_manage.message(Command("manage"))
async def cmd_manage(message: Message):
    # Проверяем, является ли отправитель владельцем
    user = db.get_user_by_tg_id(message.from_user.id)

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
@router_manage.callback_query(F.data.startswith("list_owners"))
async def callbacks_owners_list(callback: CallbackQuery):
    owners_list_keyboard, _, is_empty = await get_users_list("owner", callback.from_user.id)
    if is_empty:
        await callback.message.answer("Список владельцев пуст.", reply_markup=owners_list_keyboard)
    else:
        await callback.message.answer("Список владельцев:", reply_markup=owners_list_keyboard)
    await callback.answer()


# Посмотреть список пользователей-админов
@router_manage.callback_query(F.data.startswith("list_admins"))
async def callbacks_admins_list(callback: CallbackQuery):
    admins_list_keyboard, _, is_empty = await get_users_list("admin", callback.from_user.id)
    if is_empty:
        await callback.message.answer("Список админов пуст.", reply_markup=admins_list_keyboard)
    else:
        await callback.message.answer("Список админов:", reply_markup=admins_list_keyboard)
    await callback.answer()


# Зарегистрировать пользователя
@router_manage.callback_query(F.data.startswith("register_user"))
async def callbacks_register(callback: CallbackQuery, state: FSMContext):
    # Проверяем, является ли отправитель владельцем
    user = db.get_user_by_tg_id(callback.from_user.id)

    if user is None or user[4] != 'owner':
        await callback.message.reply("У вас нет прав для управления пользователями.")
        return

    await callback.message.answer("Введите Telegram ID пользователя (Через TestAttach Bot). Для отмены - /cancel")
    await state.set_state(DoRegister.waiting_for_tg_id)


@router_manage.message(DoRegister.waiting_for_tg_id, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_tg_id(message: Message, state: FSMContext):
    tg_id = message.text

    try:
        new_tg_id = int(tg_id)
    except ValueError:
        await message.reply("telegram id должен быть числом. Попробуйте еще раз.")
        return

    try:
        user_acc: types.User = await bot_1.get_chat(new_tg_id)
    except TelegramBadRequest as e:
        if "chat not found" in str(e):
            await message.reply("Ошибка: Чат с пользователем для регистрации не найден. Попросите его "
                                "написать любое сообщение этому боту.")
            return

    await state.update_data(tg_id=new_tg_id)
    await message.answer("Теперь введите username пользователя:")
    await state.set_state(DoRegister.waiting_for_login)


# При ошибочном типе сообщения tg_id
@router_manage.message(DoRegister.waiting_for_tg_id,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_tg_id(message: Message):
    await message.answer("Напишите числовое значение!")


@router_manage.message(DoRegister.waiting_for_login, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_login(message: Message, state: FSMContext):
    login = message.text
    if len(login) < 5:
        await message.answer("Логин слишком короткий. Попробуйте еще раз.")
        return

    await state.update_data(login=login)
    await message.answer("Теперь введите пароль пользователя:")
    await state.set_state(DoRegister.waiting_for_password)


# При ошибочном типе сообщения login
@router_manage.message(DoRegister.waiting_for_login,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_login(message: Message):
    await message.answer("Напишите текстом!")


@router_manage.message(DoRegister.waiting_for_password, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_password(message: Message, state: FSMContext):
    password = message.text
    if len(password) < 5:
        await message.answer("Пароль слишком короткий. Попробуйте еще раз.")
        return


    await state.update_data(password=password)
    await message.answer("Теперь введите роль пользователя (owner или admin):")
    await state.set_state(DoRegister.waiting_for_role)


# При ошибочном типе сообщения password
@router_manage.message(DoRegister.waiting_for_password,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_password(message: Message):
    await message.answer("Напишите текстом!")


@router_manage.message(DoRegister.waiting_for_role, F.content_type.in_({'text'}), F.text[0] != "/")
async def add_role(message: Message, state: FSMContext):
    role = message.text

    if role not in ('owner', 'admin'):
        await message.reply("Роль должна быть 'owner' или 'admin'.")
        return

    data = await state.get_data()
    tg_id = int(data['tg_id'])
    login = data['login']
    password = data['password']

    # Проверяем, существует ли уже пользователь с таким telegram_id и ролью owner
    existing_user = db.get_user_by_tg_id(tg_id)
    if existing_user:
        if existing_user[4] == 'owner' and role == 'admin':
            await message.reply(f"Пользователь с Telegram ID {tg_id} уже зарегистрирован как владелец (owner). "
                                f"Невозможно зарегистрировать его как админа.")
            await state.clear()
            return
        else:
            await message.reply(f"Пользователь с Telegram ID {tg_id} уже зарегистрирован с ролью {existing_user[4]}.")
            await state.clear()
            return

    if db.register_user(tg_id, login, password, role):
        await message.reply(f"Пользователь с Telegram ID {tg_id} зарегистрирован с ролью {role}.")
    else:
        await message.reply(f"Произошла ошибка при регистрации пользователя с Telegram ID {tg_id}. Попробуйте снова.")

    await state.clear()



# При ошибочном типе сообщения role
@router_manage.message(DoRegister.waiting_for_role,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_add_role(message: Message):
    await message.answer("Напишите текстом!")


# Действия над пользователем-админом
@router_manage.callback_query(StateFilter(None), F.data.startswith("admin_"))
async def callbacks_admin_options(callback: CallbackQuery):
    admin_id = callback.data.split('_')[1]

    user = db.get_user_by_id(admin_id)

    text = f"Tg_id: {user[1]}. Создан: {user[5].strftime('%d-%m-%Y %H:%M')}. Роль: {user[4]}."

    buttons = [
        [InlineKeyboardButton(text="Удалить пользователя", callback_data=f"deleteuser_{user[1]}")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


# Действия над пользователем-владельцем
@router_manage.callback_query(StateFilter(None), F.data.startswith("owner_"))
async def callbacks_owner_options(callback: CallbackQuery):
    owner_id = callback.data.split('_')[1]

    user = db.get_user_by_id(owner_id)

    text = f"Tg_id: {user[1]}. Создан: {user[5].strftime('%d-%m-%Y %H:%M')}. Роль: {user[4]}."

    buttons = [
        [InlineKeyboardButton(text="Удалить пользователя", callback_data=f"deleteuser_{user[1]}")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router_manage.callback_query(F.data.startswith("deleteuser_"))
async def delete_user(callback: CallbackQuery, state: FSMContext):
    user_tg_id = callback.data.split('_')[1]

    check_user_id = db.get_user_by_tg_id(callback.from_user.id)

    if check_user_id[1] == int(user_tg_id):
        await callback.message.answer("Вы не можете удалить себя!")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete_user")]])

    await callback.message.answer("Подтвердите удаление. Для отмены /cancel.", reply_markup=keyboard)
    await state.update_data(user_tg_id=user_tg_id)
    await state.set_state(ManageUser.confirm_deletion_user)

    await callback.answer()


# Было введено что-то, а не выбрано подтверждение удаления
@router_manage.message(ManageUser.confirm_deletion_user, F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice',
                                                                        'document', 'location', 'contact'}), F.text[0] != "/")
async def incorrect_delete_user(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Удалить", callback_data="confirm_delete")]])

    await message.answer("Вы сделали не правильный выбор. Для удаления нажмите кнопку ниже."
                                  " Для отмены /cancel.", reply_markup=keyboard)


@router_manage.callback_query(ManageUser.confirm_deletion_user, F.data.startswith("confirm_delete_user"))
async def confirm_delete_user(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_tg_id = int(data['user_tg_id'])

    db.delete_user_by_tg_id(user_tg_id)

    await callback.message.answer("Пользователь был удален из списка.\nУправлять пользователями - /manage\nНачальное меню - /start")
    await state.clear()

    await callback.answer()
