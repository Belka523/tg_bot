from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.command import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, \
    ReplyKeyboardMarkup
from aiogram.types.input_file import FSInputFile
from aiogram.enums import ContentType
import sqlite3
import asyncio
import sys
import zipfile
import re
import os
sys.path.insert(0, './')
from create_test import ydarenia, paronimi, prepri

class UserManager:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                rating INTEGER DEFAULT 0
            );
        ''')
        self.conn.commit()

    def reg(self, user_id, username=''):
        try:
            self.cursor.execute("INSERT OR REPLACE INTO users(telegram_id, username) VALUES (?, ?)",
                                (user_id, username))
            self.conn.commit()
        except Exception as e:
            print(f"Ошибка при регистрации пользователя: {e}")

    def updaterating(self, user_id, change):

        self.cursor.execute("SELECT rating FROM users WHERE telegram_id=?", (user_id,))
        result = self.cursor.fetchone()
        if result is None:
            self.reg(user_id)
            new_rating = max(int(change), 0)
        else:
            old_rating = result[0]
            new_rating = max(old_rating + int(change), 0)
        self.cursor.execute("UPDATE users SET rating=? WHERE telegram_id=?", (new_rating, user_id))
        self.conn.commit()
        return new_rating

    def getrating(self, user_id):
        self.cursor.execute("SELECT rating FROM users WHERE telegram_id=?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def fetch_top_users(self, limit=10):
        self.cursor.execute("SELECT username, rating FROM users WHERE username <> '' ORDER BY rating DESC LIMIT ?",
                            (limit,))
        return self.cursor.fetchall()

class TaskGenerator:
    @staticmethod
    def generate_test(task_type):
        if task_type == "ydarenia":
            return ydarenia()
        elif task_type == "paronimi":
            return paronimi()
        elif task_type == "prepri":
            return prepri()
        else:
            return None, None

class TheorySection:
    def __init__(self, archive_path):
        self.archive_path = archive_path
        self.materials = {}

    def archiv(self):
        output_dir = "Teoriya"
        os.makedirs(output_dir, exist_ok=True)

        with zipfile.ZipFile(self.archive_path, 'r') as zf:
            zf.extractall(output_dir)
            for file in zf.namelist():
                match = re.search(r'(\d+)\.pdf$', file)
                if match:
                    task_number = match.group(1)
                    extracted_file_path = os.path.join(output_dir, file)
                    self.materials[task_number] = extracted_file_path

    def returnn_teoriya(self, task_number):
        material = self.materials.get(task_number)
        if material:
            return material
        return None

class BotHandler:
    def __init__(self, token, storage):
        self.bot = Bot(token=token)
        self.dp = Dispatcher(storage=storage)
        self.user_manager = UserManager('users.db')
        self.router = Router()
        self.theory_section = TheorySection('teoriya.zip')
        self.obrabotchiki()
        self.theory_section.archiv()

    def obrabotchiki(self):
        router = self.router

        @router.message(CommandStart())
        async def command_start(message: types.Message, state: FSMContext):
            self.user_manager.reg(message.from_user.id, message.from_user.username)
            await message.answer(
                f"Привет! Это ваш персональный помощник для подготовки к ЕГЭ по русскому языку.\nВыберите действие:",
                reply_markup=self.first_menu()
            )

        @router.message(F.text.contains("📝"))
        async def choose_task_type(message: types.Message, state: FSMContext):
            await state.set_state(TaskSolver.CHOOSING_TYPE)
            await message.answer("Выберите задание, которое хотите прорешать:", reply_markup=self.create_test())
            self.deleted_menu()

        @router.callback_query(F.data.in_({"ydarenia", "paronimi", "prepri"}))
        async def confirm_quantity(callback_query: types.CallbackQuery, state: FSMContext):
            a = callback_query.data
            await state.update_data(task_function=a)
            await state.set_state(TaskSolver.CONFIRMING_QUANTITY)
            await callback_query.message.answer(f"Введите количество заданий (от 1 до 100):\nДля остановки нарешивания напишите 'стоп'", reply_markup=self.deleted_menu())

        @router.message(TaskSolver.CONFIRMING_QUANTITY, lambda m: m.text.isdigit() and 1 <= int(m.text) <= 100)
        async def start_solving_tasks(message: types.Message, state: FSMContext):
            count = int(message.text)
            task_function = (await state.get_data())["task_function"]
            await state.update_data(remaining_attempts=count)
            await state.set_state(TaskSolver.SOLVING_TASKS)
            task_question, correct_answer = TaskGenerator.generate_test(task_function)
            await state.update_data(correct_answer=correct_answer)
            await message.answer(task_question)

        @router.message(TaskSolver.SOLVING_TASKS)
        async def check_answer(message: types.Message, state: FSMContext):
            data = await state.get_data()
            correct_answer = data["correct_answer"]
            remaining_attempts = data["remaining_attempts"] - 1

            if message.text.lower() == "стоп":
                await message.answer("Вы остановили нарешивание заданий. Выберите следующее действие:",
                                     reply_markup=self.first_menu())
                await state.clear()
            else:
                if message.text.lower() == correct_answer:
                    updated_rating = self.user_manager.updaterating(message.from_user.id, "+100")
                    await message.answer(f"Правильно! Ваш текущий рейтинг: {updated_rating}")
                else:
                    updated_rating = self.user_manager.updaterating(message.from_user.id, "-20")
                    await message.answer(f"Неправильно. Ваш текущий рейтинг: {updated_rating}, правильный ответ: {correct_answer}")

                if remaining_attempts > 0:
                    task_function = data["task_function"]
                    task_question, correct_answer = TaskGenerator.generate_test(task_function)
                    await state.update_data(correct_answer=correct_answer, remaining_attempts=remaining_attempts)
                    await message.answer(task_question)
                else:
                    await state.clear()
                    await message.answer("Вы завершили нарешивание заданий. Выберите следующий шаг:",
                                         reply_markup=self.first_menu())

        @router.message(F.text.contains("🏆"))
        async def show_leaderboard(message: types.Message, state: FSMContext):
            top_users = self.user_manager.fetch_top_users()
            leaderboard_text = "\n".join([f"{i + 1}. {user[0]} — {user[1]}" for i, user in enumerate(top_users)])
            await message.reply(f"🏆 Лидерборд:\n\n{leaderboard_text}")

        @router.message(F.text.contains("📚"))
        async def study_theory(message: types.Message, state: FSMContext):
            await state.set_state(TaskSolver.STUDY_THEORY)
            await message.answer("Выберите номер задания:", reply_markup=self.but_teoriya())

        @router.callback_query(lambda cq: cq.data.isdigit() and 1 <= int(cq.data) <= 23)
        async def send_theory_material(callback_query: types.CallbackQuery, state: FSMContext):
            a = callback_query.data
            theory_file = self.theory_section.returnn_teoriya(a)
            if theory_file:
                file_input = FSInputFile(path=theory_file)
                await callback_query.message.answer_document(file_input, caption=f"Теория по заданию №{a}")
            else:
                await callback_query.message.answer("Материал по данному заданию не найден.")
            await state.clear()

        @router.callback_query(F.data == "back_theory")
        async def back_from_theory(callback_query: types.CallbackQuery, state: FSMContext):
            await state.clear()
            await callback_query.message.answer("Вы вернулись в главное меню.", reply_markup=self.first_menu())

        @router.message(F.text.contains("✉️"))
        async def contact_developer(message: types.Message, state: FSMContext):
            await state.set_state(TaskSolver.CONTACT_DEV)
            await message.answer("Напишите ваше обращение разработчику: \n\nДля загрузки файлов приложите ссылку на какое либо облачное хранилище", reply_markup=self.deleted_menu())

        # Обработчик для обращений к разработчику
        @router.message(TaskSolver.CONTACT_DEV)
        async def forward_message_to_developers(message: types.Message, state: FSMContext):
            if message.content_type == ContentType.TEXT:
                if message.content_type == ContentType.TEXT:
                    username = message.from_user.username if message.from_user.username else f"(ID: {message.from_user.id})"
                    text_with_username = f"Обращение от пользователя (@{username})\n\n{message.text}"
                    await self.bot.send_message(DEVELOPER_CHAT_ID, text_with_username, disable_notification=True)

                await message.answer("Спасибо за ваше сообщение. Оно отправлено разработчику.",
                                     reply_markup=self.first_menu())
            else:
                await message.answer(
                    "Вы отправили фото или файл. Пожалуйста, напишите повторно ваше обращение исключительно текстом. \n\nДля загрузки файлов приложите ссылку на какое либо облачное хранилище",
                    reply_markup=self.first_menu())
            await state.clear()

    def run_bot(self):
        self.dp.include_router(self.router)
        asyncio.run(self.dp.start_polling(self.bot))

    def first_menu(self):
        a = [
            [KeyboardButton(text="📝 Решение заданий"),
             KeyboardButton(text="📚 Теория по заданиям 1 - 23")],
            [KeyboardButton(text="🏆 Лидерборд"),
             KeyboardButton(text="✉️ Связь с разработчиком")]
        ]
        return ReplyKeyboardMarkup(keyboard=a, resize_keyboard=True)

    def create_test(self):
        a = [
            [InlineKeyboardButton(text="Задание №4", callback_data="ydarenia")],
            [InlineKeyboardButton(text="Задание №7", callback_data="paronimi")],
            [InlineKeyboardButton(text="Задание №10", callback_data="prepri")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=a)

    def but_teoriya(self):
        a = [[InlineKeyboardButton(text=str(i), callback_data=str(i)) for i in range(j*5+1, min(j*5+6, 24))]
                   for j in range(5)]
        return InlineKeyboardMarkup(inline_keyboard=a)

    def deleted_menu(self):
        return ReplyKeyboardRemove()


# Группа состояний
class TaskSolver(StatesGroup):
    CHOOSING_TYPE = State()
    CONFIRMING_QUANTITY = State()
    SOLVING_TASKS = State()
    STUDY_THEORY = State()
    CONTACT_DEV = State()

if __name__ == "__main__":
    TOKEN = "7328815218:AAE_gwNlaKZKa5flMRJXCBo6diFwwG8mEec"
    DEVELOPER_CHAT_ID = "-1002673236181"
    storage = MemoryStorage()
    bot_handler = BotHandler(TOKEN, storage)
    bot_handler.run_bot()