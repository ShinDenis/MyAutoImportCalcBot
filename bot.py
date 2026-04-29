from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio

API_TOKEN = "8733076478:AAGKAfOeYP2F9wKgoATefGF23sI6DNHcMh0"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

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

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())