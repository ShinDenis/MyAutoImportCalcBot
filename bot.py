import os
import asyncio
from threading import Thread
from fastapi import FastAPI
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand, ReplyKeyboardMarkup, KeyboardButton

# Токен берём из переменной окружения
API_TOKEN = os.environ.get("API_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Логика калькулятора ---
def calc_total(price: float):
    customs = price * 0.15
    logistics = 1000
    commission = price * 0.05
    total = price + customs + logistics + commission
    return customs, logistics, commission, total

# --- Клавиатура ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/calc")],
        [KeyboardButton(text="/help")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Вас приветствует Бот калькулятор! Выберите команду из меню или введите модель и цену через пробел: \n Например: AUDI 5000",
        reply_markup=main_kb
    )

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "Доступные команды:\n/start — начать работу\n/help — справка\n/calc — рассчитать стоимость",
        reply_markup=main_kb
    )

@dp.message(Command("calc"))
async def calc_cmd(message: types.Message):
    await message.answer("Введите модель и цену через пробел, например: Audi 25000", reply_markup=main_kb)

@dp.message()
async def calc(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            raise ValueError("Недостаточно аргументов")

        # всё кроме последнего слова — модель
        model = " ".join(parts[:-1])
        price = float(parts[-1])

        customs, logistics, commission, total = calc_total(price)

        await message.answer(
            f"🚗 Модель: {model}\n"
            f"• Базовая цена: ${price:,.0f}\n"
            f"• Таможня: ${customs:,.0f}\n"
            f"• Логистика: ${logistics:,.0f}\n"
            f"• Комиссия: ${commission:,.0f}\n"
            f"--------------------\n"
            f"✅ Итого: ${total:,.0f}"
        )
    except Exception:
        await message.answer("Ошибка ввода. Используй формат: Модель Цена\nНапример: Audi A5 3000")

# --- Установка меню команд ---
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="calc", description="Рассчитать стоимость авто"),
    ]
    await bot.set_my_commands(commands)

# --- REST API ---
app = FastAPI()

@app.get("/")
def home():
    return {"status": "Bot is running"}

@app.get("/calc/{price}")
def api_calc(price: float):
    customs, logistics, commission, total = calc_total(price)
    return {
        "customs": customs,
        "logistics": logistics,
        "commission": commission,
        "total": total
    }

def run_api():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# --- Запуск бота ---
async def run_bot():
    await set_commands(bot)  # меню команд
    await dp.start_polling(bot)

def main():
    Thread(target=run_api).start()
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()


"""
import os
import asyncio
from threading import Thread
from fastapi import FastAPI
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

API_TOKEN = os.environ.get("API_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Логика калькулятора ---
def calc_total(price: float):
    customs = price * 0.15
    logistics = 1000
    commission = price * 0.05
    total = price + customs + logistics + commission
    return customs, logistics, commission, total

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Введи модель и стоимость авто через пробел.\nНапример: BMW 20000")

@dp.message()
async def calc(message: types.Message):
    try:
        model, price = message.text.split()
        price = float(price)
        customs, logistics, commission, total = calc_total(price)
        await message.answer(
            f"🚗 Модель: {model}\n"
            f"• Базовая цена: ${price:,.0f}\n"
            f"• Таможня: ${customs:,.0f}\n"
            f"• Логистика: ${logistics:,.0f}\n"
            f"• Комиссия: ${commission:,.0f}\n"
            f"--------------------\n"
            f"✅ Итого: ${total:,.0f}"
        )
    except:
        await message.answer("Ошибка ввода. Используй формат: Модель Цена")

# --- REST API ---
app = FastAPI()

@app.get("/")
def home():
    return {"status": "Bot is running"}

@app.get("/calc/{price}")
def api_calc(price: float):
    customs, logistics, commission, total = calc_total(price)
    return {
        "customs": customs,
        "logistics": logistics,
        "commission": commission,
        "total": total
    }

def run_api():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# --- Запуск бота ---
async def run_bot():
    await dp.start_polling(bot)

def main():
    Thread(target=run_api).start()
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
"""