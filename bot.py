import os
import zipfile
import logging
import shutil
import asyncio
from telegram import InputMediaPhoto, Bot
from aiohttp import web
import aiohttp_cors

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8465873812:AAGvjy0WzCEzFx2g8S_xbVS9NaA6tupF_lM" 
GROUP_ID = -1003068558796
# -----------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def process_and_send_zip(zip_content: bytes, guest_name: str, bot: Bot):
    """Распаковывает архив и отправляет фото в группу."""
    temp_dir = f"temp_{guest_name}_{int(asyncio.get_event_loop().time())}"
    
    try:
        os.makedirs(temp_dir, exist_ok=True)
        zip_path = os.path.join(temp_dir, "photos.zip")

        with open(zip_path, 'wb') as f:
            f.write(zip_content)
        logger.info(f"Архив от '{guest_name}' сохранен.")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        logger.info(f"Архив распакован в папку '{temp_dir}'.")

        photo_paths = [os.path.join(root, filename) for root, _, files in os.walk(temp_dir) for filename in files if filename.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        if not photo_paths:
            logger.warning(f"В архиве от {guest_name} не найдено фотографий.")
            return

        caption = f"📸 Новые фотографии от гостя: {guest_name}"
        
        media_group_full = [InputMediaPhoto(open(photo_path, 'rb'), caption=caption if i == 0 else None) for i, photo_path in enumerate(photo_paths)]

        for i in range(0, len(media_group_full), 10):
            chunk = media_group_full[i:i + 10]
            await bot.send_media_group(chat_id=GROUP_ID, media=chunk)
        
        logger.info(f"Фотографии от '{guest_name}' отправлены в группу {GROUP_ID}.")

    except Exception as e:
        logger.error(f"Ошибка при обработке архива от {guest_name}: {e}", exc_info=True)
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        logger.info(f"Временные файлы для '{guest_name}' удалены.")

async def handle_upload(request: web.Request):
    """Обрабатывает POST-запрос с файлом от сайта."""
    try:
        data = await request.post()
        zip_file_field = data.get('photo')
        user_name_field = data.get('userName')

        if not zip_file_field or not user_name_field:
            return web.json_response({'status': 'error', 'message': 'Missing "photo" or "userName" field'}, status=400)

        zip_content = zip_file_field.file.read()
        guest_name = str(user_name_field)
        logger.info(f"Получен файл от '{guest_name}', размер: {len(zip_content)} байт.")

        bot: Bot = request.app['bot']
        asyncio.create_task(process_and_send_zip(zip_content, guest_name, bot))

        return web.json_response({'status': 'ok', 'message': 'File received and is being processed.'})

    except Exception as e:
        logger.error(f"Ошибка в веб-хендлере /send-photo: {e}", exc_info=True)
        return web.json_response({'status': 'error', 'message': 'Internal server error'}, status=500)

async def main_async():
    """Инициализирует бота и запускает веб-сервер."""
    bot = Bot(token=BOT_TOKEN)
    
    app = web.Application()
    app['bot'] = bot

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*",
        )
    })
    
    upload_route = app.router.add_post('/send-photo', handle_upload)
    cors.add(upload_route)

    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render предоставит порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    logger.info(f"Запуск веб-сервера на http://0.0.0.0:{port}")
    await site.start()
    
    logger.info("Сервер-бот запущен и готов принимать файлы.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Сервер остановлен.")
