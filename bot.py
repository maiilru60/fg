import os
import logging
import asyncio
from telegram import InputFile, Bot
from telegram.error import TelegramError
from aiohttp import web
import aiohttp_cors
from io import BytesIO

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8465873812:AAGvjy0WzCEzFx2g8S_xbVS9NaA6tupF_lM"  # Убрали лишнюю скобку
GROUP_ID = -1001234567890  # ID вашей группы Telegram
UPLOAD_ROUTE = "/upload"  # путь для POST-запросов

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def send_photo_to_group(photo_content: bytes, guest_name: str, bot: Bot):
    """Отправляет одну фотографию в группу."""
    try:
        caption = f"📸 Новая фотография от гостя: {guest_name}"
        photo_file = InputFile(BytesIO(photo_content), filename=f"{guest_name}.jpg")
        await bot.send_photo(chat_id=GROUP_ID, photo=photo_file, caption=caption)
        logger.info(f"Фотография от '{guest_name}' успешно отправлена в группу {GROUP_ID}.")
    except TelegramError as e:
        logger.error(f"Ошибка отправки фото в Telegram от {guest_name}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при отправке фото от {guest_name}: {e}", exc_info=True)

async def handle_upload(request: web.Request):
    """Обрабатывает POST-запрос с файлом от сайта."""
    try:
        data = await request.post()
        photo_field = data.get('photo')
        user_name_field = data.get('userName')

        if not photo_field or not user_name_field:
            logger.warning("Запрос без поля 'photo' или 'userName'.")
            return web.json_response({'status': 'error', 'message': 'Missing "photo" or "userName" field'}, status=400)

        photo_content = photo_field.file.read()
        guest_name = str(user_name_field)
        logger.info(f"Получен файл от '{guest_name}', размер: {len(photo_content)} байт.")

        bot: Bot = request.app['bot']
        asyncio.create_task(send_photo_to_group(photo_content, guest_name, bot))

        return web.json_response({'status': 'ok', 'message': 'File received and is being processed.'})
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}", exc_info=True)
        return web.json_response({'status': 'error', 'message': 'Internal server error'}, status=500)

async def main():
    """Инициализирует бота и запускает веб-сервер."""
    bot = Bot(token=BOT_TOKEN)
    app = web.Application()
    app['bot'] = bot

    # Настройка маршрута и CORS
    upload_route = app.router.add_post(UPLOAD_ROUTE, handle_upload)
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(allow_credentials=True, expose_headers="*", allow_headers="*")
    })
    cors.add(upload_route)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    logger.info(f"Запуск веб-сервера на http://0.0.0.0:{port}")
    await site.start()

    logger.info("Сервер-бот запущен и готов принимать файлы.")
    await asyncio.Event().wait()  # Бесконечное ожидание

if __name__ == "__main__":
    asyncio.run(main())
