import aiogram
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import Command
from aiogram.types import Message, ReplyKeyboardRemove, FSInputFile
from aiogram.fsm.state import StatesGroup, State
import time

from app.handlers.private_bot.handlers import text_about_commands
import app.database.crypt_db as db
import app.smiles as smiles


router_auth = Router()

bot_1: aiogram.Bot


def set_bot(bot):
    global bot_1
    bot_1 = bot


class DoAuth(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()


# Хэндлер на команду /auth
@router_auth.message(Command("auth"))
async def cmd_auth(message: Message, state: FSMContext):
    if db.get_auth_status(message.from_user.id):
        await message.answer("Вы уже авторизованы!")
        return

    user = db.get_user_by_tg_id(message.from_user.id)
    if user is None:
        await message.answer(
            "Вы не зарегистрированы в системе. Обратитесь к владельцу для регистрации.")
        return

    await message.answer("Введите ваш никнейм (логин). Для отмены - /cancel")
    await state.set_state(DoAuth.waiting_for_login)


@router_auth.message(DoAuth.waiting_for_login, F.content_type.in_({'text'}), F.text[0] != "/")
async def enter_login(message: Message, state: FSMContext):
    login = message.text
    message_login_id = message.message_id
    await state.update_data(login=login)
    await state.update_data(message_login_id=message_login_id)
    await message.answer("Теперь введите пароль:")
    await state.set_state(DoAuth.waiting_for_password)


# При ошибочном типе сообщения логина
@router_auth.message(DoAuth.waiting_for_login,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_enter_login(message: Message):
    await message.answer("Напишите текстом!")


@router_auth.message(DoAuth.waiting_for_password, F.content_type.in_({'text'}), F.text[0] != "/")
async def enter_password(message: Message, state: FSMContext):
    password = message.text
    message_password_id = message.message_id

    data = await state.get_data()
    login = data['login']
    message_login_id = data['message_login_id']

    user = db.get_user_by_tg_id(message.from_user.id)

    if user[2] == login and db.verify_password(user[3], password):
        db.set_auth_status(message.from_user.id, True)

        # Очистим для безопасности введенные логин и пароль ранее (для безопасности)
        await bot_1.delete_messages(message.from_user.id, [message_login_id, message_password_id])
        await message.answer("Авторизация прошла успешно!")



        start_text = f'Привет, {message.from_user.full_name}! Данный бот поможет Вам удобно взаимодействовать с сотрудниками. ' \
                     f'\n\nЗдесь Вы можете:' \
                     f'\n\t- Задать ваше текущее место сейчас или запланировать его позже {smiles.clock}' \
                     f'\n\t- Редактировать список запланированных и использованных ранее мест {smiles.pencil}' \
                     f'\n\t- Отвечать на вопросы сотрудников {smiles.letter}' \
                     f'\n\t- Редактировать общие ответы и вопросы! {smiles.save_emoji}' \
                     f'\n\nСотрудники будут взаимодействовать с вами через другого бота, ' \
                     f'по которому смогут перейти по QR-коду.\n\n'

        final_text = start_text + text_about_commands
        await state.clear()

        await message.answer_photo(FSInputFile(path="app/images/start_message_private_bot.jpg"))
        time.sleep(1)
        await message.answer(final_text, reply_markup=ReplyKeyboardRemove())

    else:
        await message.reply("Неверные данные авторизации.")
        await state.clear()


# При ошибочном типе сообщения пароля
@router_auth.message(DoAuth.waiting_for_password,
                F.content_type.in_({'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def incorrect_enter_password(message: Message):
    await message.answer("Напишите текстом!")


@router_auth.message(Command("logout"))
async def cmd_logout(message: Message):
    user = db.get_user_by_tg_id(message.from_user.id)
    if user is None:
        await message.answer(
            "Вы не зарегистрированы в системе. Пожалуйста, обратитесь к владельцу для регистрации.")
        return

    if not db.get_auth_status(message.from_user.id):
        await message.answer("Вы еще не в системе. Пройдите авторизацию командой /auth <username> <password>.")
        return

    db.set_auth_status(message.from_user.id, False)
    await message.reply("Вы вышли из системы.")
