import os
import asyncio
import logging
from threading import Thread
from fastapi import FastAPI
import uvicorn
import httpx
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand, ReplyKeyboardMarkup, KeyboardButton
from google import genai

# --- Логирование ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# --- Настройки ---
API_TOKEN = os.environ.get("API_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")

if not API_TOKEN:
    raise RuntimeError("Переменная окружения API_TOKEN не задана!")
if not GEMINI_API_KEY:
    raise RuntimeError("Переменная окружения GEMINI_API_KEY не задана!")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Настройка Gemini ---
client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"

# --- Логика калькулятора ---
def calc_total(price: float):
    customs = price * 0.15      # таможня 15%
    logistics = 1000.0          # логистика фиксированная, USD
    commission = price * 0.05   # комиссия 5%
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

# --- Keep-alive пинг чтобы Render не усыплял сервис ---
async def keep_alive():
    async with httpx.AsyncClient() as http:
        while True:
            await asyncio.sleep(600)  # каждые 10 минут
            try:
                await http.get(f"{RENDER_EXTERNAL_URL}/")
                logger.info("Keep-alive ping отправлен")
            except Exception as e:
                logger.warning(f"Keep-alive ошибка: {e}")

# --- Хэндлеры ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Вас приветствует Бот калькулятор!\n\n"
        "Введите модель и цену через пробел.\n"
        "Например: Audi A5 3000",
        reply_markup=main_kb
    )

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "Доступные команды:\n"
        "/start — начать работу\n"
        "/help — справка\n"
        "/calc — рассчитать стоимость",
        reply_markup=main_kb
    )

@dp.message(Command("calc"))
async def calc_cmd(message: types.Message):
    await message.answer(
        "Введите модель и цену через пробел.\n"
        "Например: Audi A5 3000",
        reply_markup=main_kb
    )

@dp.message()
async def calc(message: types.Message):
    try:
        text = message.text.strip()
        parts = text.split()

        if len(parts) < 2:
            await message.answer(
                "Введите модель и цену через пробел.\nНапример: Audi A5 3000",
                reply_markup=main_kb
            )
            return

        price_str = parts[-1]
        model_name = " ".join(parts[:-1])

        try:
            price = float(price_str)
        except ValueError:
            await message.answer(
                f"Цена должна быть числом, получено: «{price_str}»\nНапример: Audi A5 3000",
                reply_markup=main_kb
            )
            return

        if price <= 0:
            await message.answer(
                "Цена должна быть положительным числом.",
                reply_markup=main_kb
            )
            return

        customs, logistics, commission, total = calc_total(price)
        logger.info(f"Запрос: {model_name} | цена={price}")

        prompt = (
            f"Пользователь хочет купить автомобиль: {model_name}, цена {price:.2f} USD.\n\n"
            f"Расчёт итоговой стоимости:\n"
            f"- Цена авто: {price:.2f} USD\n"
            f"- Таможня (15%): {customs:.2f} USD\n"
            f"- Логистика: {logistics:.2f} USD\n"
            f"- Комиссия (5%): {commission:.2f} USD\n"
            f"- Итого: {total:.2f} USD\n\n"
            f"Напиши дружелюбный ответ на русском языке с эмодзи. "
            f"ОБЯЗАТЕЛЬНО включи все 5 строк расчёта в ответ в том же порядке: "
            f"цена авто, таможня, логистика, комиссия, итого. "
            f"Не сокращай и не объединяй строки расчёта."
        )

        # --- Gemini с retry ---
        MAX_RETRIES = 3
        response_text = None

        for attempt in range(MAX_RETRIES):
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[{"role": "user", "parts": [{"text": prompt}]}]
                )
                response_text = response.text
                break

            except Exception as e:
                error_str = str(e)
                is_503 = "503" in error_str or "UNAVAILABLE" in error_str
                is_429 = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str

                if (is_503 or is_429) and attempt < MAX_RETRIES - 1:
                    wait = (attempt + 1) * 5  # 5s, 10s, 15s
                    logger.warning(f"Gemini {type(e).__name__} (попытка {attempt+1}), жду {wait}с...")
                    await asyncio.sleep(wait)
                    continue

                logger.warning(f"Gemini недоступен после {attempt+1} попыток: {e}")
                response_text = None
                break

        # --- Fallback если Gemini не ответил ---
        if response_text is None:
            response_text = (
                f"🚗 <b>{model_name}</b>\n\n"
                f"💰 Цена авто: {price:.2f} USD\n"
                f"🛃 Таможня (15%): {customs:.2f} USD\n"
                f"🚚 Логистика: {logistics:.2f} USD\n"
                f"💼 Комиссия (5%): {commission:.2f} USD\n"
                f"━━━━━━━━━━━━━━\n"
                f"✅ <b>Итого: {total:.2f} USD</b>"
            )
            await message.answer(response_text, parse_mode="HTML", reply_markup=main_kb)
        else:
            await message.answer(response_text, reply_markup=main_kb)

    except Exception as e:
        logger.error(f"Ошибка в calc(): {type(e).__name__}: {e}", exc_info=True)
        await message.answer(
            f"Произошла ошибка: {type(e).__name__}: {e}",
            reply_markup=main_kb
        )

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
    if price <= 0:
        return {"error": "Цена должна быть положительной"}
    customs, logistics, commission, total = calc_total(price)
    return {
        "customs": round(customs, 2),
        "logistics": round(logistics, 2),
        "commission": round(commission, 2),
        "total": round(total, 2)
    }

def run_api():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

# --- Запуск бота ---
async def run_bot():
    await set_commands(bot)
    asyncio.create_task(keep_alive())
    dp.shutdown.register(lambda: bot.session.close())
    await dp.start_polling(bot, drop_pending_updates=True)

def main():
    Thread(target=run_api, daemon=True).start()
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()