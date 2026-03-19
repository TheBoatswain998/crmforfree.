# Telegram + Yandex GPT (yandexgpt-lite) bot using aiogram (async)
# Dependencies:
#   pip install aiogram==3.12 aiohttp python-dotenv
# .env variables required:
#   TELEGRAM_BOT_TOKEN=...
#   YANDEX_API_KEY=...
#   YANDEX_CATALOG_ID=...    # used as modelUri: gpt://{YANDEX_CATALOG_ID}/yandexgpt-lite
# Run: python main.py

import os
import logging
import asyncio
from typing import Optional

from dotenv import load_dotenv
import aiohttp
from aiohttp import ClientTimeout, ClientError
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# --- load config ---
load_dotenv()
# Load required secrets from environment / .env (for security, no hardcoded fallbacks)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_CATALOG_ID = os.getenv("YANDEX_CATALOG_ID")

if not TELEGRAM_BOT_TOKEN or not YANDEX_API_KEY or not YANDEX_CATALOG_ID:
    raise SystemExit("Missing one of required env vars: TELEGRAM_BOT_TOKEN, YANDEX_API_KEY, YANDEX_CATALOG_ID")

# --- logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- aiogram dispatcher ---
dp = Dispatcher()
_http_session: Optional[aiohttp.ClientSession] = None
YANDEX_ENDPOINT = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

# Reply keyboard (persistent) — кнопка 'Помощь'
help_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Помощь")]], resize_keyboard=True)

@dp.message(F.chat.type == "private", F.text == "/start")
async def cmd_start(message: Message) -> None:
    await message.reply("Привет! Я дружелюбный ассистент на базе Yandex GPT. Отправь свой вопрос.", reply_markup=help_kb)

@dp.message(F.chat.type == "private", F.text == "Помощь")
async def help_handler(message: Message) -> None:
    help_text = (
        "Я отправляю ваш запрос в Yandex GPT и возвращаю краткий ответ на русском.\n"
        "Просто отправьте любой текст — я отвечу."
    )
    await message.reply(help_text, reply_markup=help_kb)


@dp.message(F.chat.type == "private", F.text)
async def handle_private_text(message: Message) -> None:
    """Handle user text messages in private chats only and forward to Yandex GPT."""
    global _http_session
    user_text = (message.text or "").strip()
    if not user_text:
        return

    logger.info("Message from %s: %s", message.from_user.id, user_text[:200])

    payload = {
        "modelUri": f"gpt://{YANDEX_CATALOG_ID}/yandexgpt-lite",
        "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": 1500},
        "messages": [
            {"role": "system", "text": "Ты дружелюбный ассистент. Отвечай кратко, по делу, без воды. На русском языке."},
            {"role": "user", "text": user_text},
        ],
    }

    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json",
    }

    if _http_session is None:
        logger.error("HTTP session is not initialized")
        await message.reply("Ошибка 😔 Попробуй позже", reply_markup=help_kb)
        return

    try:
        async with _http_session.post(YANDEX_ENDPOINT, json=payload, headers=headers) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.error("Yandex API error: status=%s body=%s", resp.status, body)
                await message.reply("Ошибка 😔 Попробуй позже", reply_markup=help_kb)
                return

            try:
                resp_json = await resp.json()
            except Exception as e:
                body = await resp.text()
                logger.exception("Failed to parse JSON from Yandex API: %s", e)
                logger.debug("Response body: %s", body)
                await message.reply("Ошибка 😔 Попробуй позже", reply_markup=help_kb)
                return

            try:
                reply_text = resp_json['result']['alternatives'][0]['message']['text']
            except Exception as e:
                logger.exception("Unexpected response structure: %s", e)
                logger.debug("Full response JSON: %s", resp_json)
                await message.reply("Ошибка 😔 Попробуй позже", reply_markup=help_kb)
                return

            if not reply_text:
                logger.warning("Empty reply from Yandex: %s", resp_json)
                await message.reply("Ошибка 😔 Попробуй позже", reply_markup=help_kb)
                return

            await message.reply(reply_text, reply_markup=help_kb)

    except (ClientError, asyncio.TimeoutError) as e:
        logger.exception("Network / API request failed: %s", e)
        await message.reply("Ошибка 😔 Попробуй позже", reply_markup=help_kb)
    except Exception as e:
        logger.exception("Unexpected error while handling message: %s", e)
        await message.reply("Ошибка 😔 Попробуй позже", reply_markup=help_kb)


async def main() -> None:
    global _http_session

    # create aiohttp session with a 25s timeout
    _http_session = aiohttp.ClientSession(timeout=ClientTimeout(total=25))

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        logger.info("Starting bot...")
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down: closing http session and bot session")
        if _http_session and not _http_session.closed:
            await _http_session.close()
        # close aiogram/bot session
        try:
            await bot.session.close()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
