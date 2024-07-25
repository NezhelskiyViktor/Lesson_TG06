import asyncio
import random
import sqlite3
import logging
import requests
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from env import TOKEN
from datetime import datetime

bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

button_tips = KeyboardButton(text="Советы по экономике")
button_exchange_rates = KeyboardButton(text="Курс валют")
button_registr = KeyboardButton(text="Записать расходы")
button_finances = KeyboardButton(text="Мои расходы за месяц")

keyboards = ReplyKeyboardMarkup(keyboard=[
    [button_tips, button_exchange_rates],
    [button_registr, button_finances]
], resize_keyboard=True)

conn = sqlite3.connect('user.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   telegram_id INTEGER, 
   name TEXT,
   date DATE,
   purchase TEXT,
   expense REAL
   )
''')
conn.commit()


class FinancesForm(StatesGroup):
    purchase = State()  # Название расхода
    expense = State()  # Сумма расхода


@dp.message(Command('start'))
async def send_start(message: Message):
    await message.answer(f"Привет, {message.from_user.full_name}! \n"
                         f"Я ваш личный финансовый помощник. \n"
                         f"Выберите одну из опций в меню:",
                         reply_markup=keyboards)


@dp.message(F.text == "Советы по экономике")
async def send_tips(message: Message):
    tips = [
        "Составьте бюджет и придерживайтесь его.",
        "Откладывайте часть дохода на сбережения.",
        "Инвестируйте в долгосрочные финансовые инструменты.",
        "Контролируйте свои расходы и избегайте импульсивных покупок.",
        "Используйте кредитные карты с умом и вовремя погашайте задолженность.",
        "Изучайте финансовые продукты и услуги, чтобы выбрать наиболее выгодные предложения.",
        "Планируйте крупные покупки заранее и старайтесь избегать долгов.",
        "Обучайтесь основам финансовой грамотности.",
        "Создайте чрезвычайный фонд для непредвиденных расходов.",
        "Регулярно пересматривайте и корректируйте свой финансовый план."
    ]
    tip = random.choice(tips)
    await message.answer(tip)


@dp.message(F.text == "Курс валют")
async def exchange_rates(message: Message):
    url = "https://v6.exchangerate-api.com/v6/f4f7120087d555750a35e126/latest/CNY"
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200:
            await message.answer("Не удалось получить данные о курсе валют!")
            return
        cny_to_rub = data['conversion_rates']['RUB']  # Курс юани в RUB
        inr_to_cny = data['conversion_rates']['INR']  # Курс рупии в CNY
        inr_to_rub =  cny_to_rub / inr_to_cny
        await message.answer(f"1 юань - {cny_to_rub:.2f} руб\n"
                             f"1 рупия - {inr_to_rub:.2f} руб")
    except:
        await message.answer("Произошла ошибка")


@dp.message(F.text == "Записать расходы")
async def registration(message: Message, state: FSMContext):
    await state.set_state(FinancesForm.purchase)
    await message.reply("Введите название расхода:")


@dp.message(FinancesForm.purchase)
async def finances(message: Message, state: FSMContext):
    await state.update_data(purchase=message.text)
    await state.set_state(FinancesForm.expense)
    await message.reply("Введите расход в рубях:")


@dp.message(FinancesForm.expense)
async def finances(message: Message, state: FSMContext):
    data = await state.get_data()
    telegram_id = message.from_user.id
    name = message.from_user.full_name
    current_date = datetime.now().strftime('%d-%m-%Y')
    cursor.execute(
        '''INSERT INTO users (telegram_id, name, date, purchase, expense) VALUES (?, ?, ?, ?, ?)''',
        (telegram_id, name, current_date, data['purchase'], float(message.text.strip().replace(',', '.'))))
    conn.commit()
    await state.clear()
    await message.answer(f'Расход "{data['purchase']}" записан.')


@dp.message(F.text == "Мои расходы за месяц")
async def finances(message: Message):
    telegram_id = message.from_user.id
    current_date = datetime.now().strftime('%d-%m-%Y')
    like_date = '%' + current_date[3:]

    conn = sqlite3.connect('user.db')
    cursor = conn.cursor()
    # Выполняем запрос с условиями
    cursor.execute('''
        SELECT SUM(expense) FROM users
        WHERE telegram_id = ? AND date LIKE ?
    ''', (telegram_id, like_date))
    # Получаем результат
    result = cursor.fetchone()[0]
    # Проверяем, если результат None (если нет соответствующих записей)
    if result is None:
        result = 0  # Расходы равны нулю
    conn.close()

    postscript = "расходов нет." if result == 0 else f"вы потратили: {result} руб."
    await message.answer("В этом месяце " + postscript)


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
