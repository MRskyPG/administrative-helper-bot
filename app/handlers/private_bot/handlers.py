import aiogram
import time
from aiogram import F, Router
from aiogram.filters.command import Command
from aiogram.types import Message, BotCommand,\
    ReplyKeyboardRemove, FSInputFile
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext


# Мои библиотеки
from app.database.crypt_db import get_user_by_tg_id, get_auth_status
import app.smiles as smiles


router = Router()


text_about_commands = "Выберите, что вас интересует:" \
                      "\n/setplace - Задать место, где вы находитесь" \
                      "\n/placesqueue - Очередь запланированных мест для добавления" \
        "\n/placeslist - Список использованных ранее мест" \
        "\n/getplace - Получить сведения о заданном ранее месте" \
        "\n/ask - Список общих вопросов/ответов" \
        "\n/staffquestions - Посмотреть вопросы сотрудников" \
        "\n/manage - Управлять пользователями"


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
        BotCommand(command="/manage", description="Управление пользователями (только для owner)"),
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
                 f'\n\t- Редактировать общие ответы и вопросы {smiles.save_emoji}' \
                 f'\n\t- Управлять пользователями данного бота! {smiles.pencil}' \
                 f'\n\nСотрудники будут взаимодействовать с вами через другого бота, ' \
                 f'по которому смогут перейти по QR-коду.\n\n'
    final_text = start_text + text_about_commands

    await message.answer_photo(FSInputFile(path="app/images/start_message_private_bot.jpg"))

    time.sleep(0.5)

    await message.answer(final_text, reply_markup=ReplyKeyboardRemove())


@router.message(StateFilter(None), Command("cancel"))
async def cmd_cancel_no_state(message: Message, state: FSMContext):
    await state.set_data({})

    await message.answer(
        text="Нечего отменять",
        reply_markup=ReplyKeyboardRemove()
    )

    await message.answer_photo(FSInputFile(path="app/images/thinking_man.jpg"))
    time.sleep(1)
    await message.answer(text=text_about_commands)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        text="Действие отменено",
        reply_markup=ReplyKeyboardRemove()
    )

    await message.answer_photo(FSInputFile(path="app/images/thinking_man.jpg"))
    time.sleep(1)
    await message.answer(text=text_about_commands)


@router.message(F.content_type.in_({'text', 'sticker', 'photo', 'video', 'audio', 'voice', 'document', 'location', 'contact'}))
async def any_message(message: Message, state: FSMContext):
    await message.answer("Неизвестная команда. Попробуйте /start")
