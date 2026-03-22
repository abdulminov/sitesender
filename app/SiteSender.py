import os
import django
import time
import re
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from vkbottle.bot import Bot, Message
from vkbottle import VideoUploader, DocMessagesUploader
from yt_dlp import YoutubeDL
from playwright.async_api import async_playwright


# 0 - Настройка Django: говорим скрипту, где лежат настройки проекта
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Теперь можно импортировать модель (строго после django.setup())

from asgiref.sync import sync_to_async
from logs.models import RequestLog

save_log_to_db = sync_to_async(RequestLog.objects.create)



load_dotenv()
# --- НАСТРОЙКИ ---
# Вставьте ваш токен из настроек сообщества
token = os.getenv("BOT_TOKEN")
bot = Bot(token)

# Если переменная не задана в системе, качаем в текущую папку ./downloads
#raw_path = os.getenv("DOWNLOAD_PATH", "./temp_downloads")
raw_path='/tmp'
DOWNLOAD_PATH='/tmp'
#DOWNLOAD_PATH=Path(raw_path).resolve()
# Создаем папку, если её нет (важно для первого запуска)
#DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
#print(f"Файлы будут сохраняться в: {DOWNLOAD_PATH}")

# 3. Проверяем тип файловой системы
try:
    # Используем findmnt для проверки конкретной точки
    result = subprocess.run(
        ['findmnt', '-n', '-o', 'FSTYPE', '-T', str(DOWNLOAD_PATH)],
        capture_output=True,
        text=True,
        check=True
    )
    fs_type = result.stdout.strip()
except Exception:
    fs_type = "unknown"

# 4. Логика уведомления
if fs_type == "tmpfs":
    print(f"🚀 Успех: Используется быстрая память (tmpfs) по пути {raw_path}")
else:
    print(f"⚠️ ВНИМАНИЕ: Папка {raw_path} находится на обычном диске ({fs_type}).")
    print("Ресурс ПЗУ (eMMC/SD) под угрозой при частых загрузках!")


def get_ydl_options(height: int):
    return {
        'format': "bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        'outtmpl': f'{DOWNLOAD_PATH}/video_%(id)s.%(ext)s',
        'noplaylist': True,

        'cookiefile': 'cookies.txt',
        'merge_output_format': 'mp4',

    }



@bot.on.message()
async def main_handler(message: Message):
    start_time = time.perf_counter() # засекаем таймер

    text = message.text.strip()

    # 1. Поиск ссылки в тексте
    url_match = re.search(r'(https?://\S+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\S*)', text)
    if not url_match:
        return  # Если ссылок нет, игнорируем сообщение

    raw_url = url_match.group(1)
    full_url = raw_url if raw_url.startswith("http") else "https://" + raw_url

    # 2. Определение режима: Видео (конкретный ролик) или PDF (все остальное, включая поиск)
    # Проверяем, что это YouTube И что в ссылке есть маркеры конкретного видео
    is_youtube_video = (("youtube.com" in full_url) or ("youtu.be/" in full_url)) and not ("search" in full_url)

    if is_youtube_video:
        success, error_msg = await handle_video(message, full_url)
    else:
        # Сюда попадут обычные сайты и страницы поиска YouTube (напр. youtube.com?...)
        success, error_msg = await handle_pdf(message, full_url)
    status = 200 if success else 500


    execution_time = time.perf_counter() - start_time
    await save_log_to_db(
        user_id=str(message.from_id),
        url=full_url,
        request_type=('PDF', 'Video')[is_youtube_video],
        status_code=status,
        execution_time=round(execution_time, 2),
        error_message=error_msg  # Теперь ошибка попадет в базу!

    )

async def handle_video(message: Message, url: str, retry: bool = False):
    success = False
    error_msg = "Unknown error"
    filename = ""
    current_height = 480 if retry else 720

    # Если это ретрай, уведомляем пользователя
    if retry:
        await message.answer("🔄 SONY Файл слишком большой. Пробую скачать в меньшем качестве (480p)...")
    else:
        await message.answer("🎞 SONY Обнаружено видео. Начинаю скачивание...")

    try:
        # Скачивание видео через yt-dlp во внешнем потоке, чтобы не вешать бота
        options = get_ydl_options(current_height)
        with YoutubeDL(options) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get('title', 'YouTube Video')

        await message.answer("SONY ✅ Видео скачано. Отправляю файл...")

        # Загружаем видео как ДОКУМЕНТ в личные сообщения
        # Это работает с токеном группы без ограничений

        uploader = DocMessagesUploader(bot.api)

        doc = await uploader.upload(
            file_source=filename,
            peer_id=message.peer_id,
            title=f"{title}.mp4"
        )
        success = True
        error_msg = None

        await message.answer(f"SONY 🎬 Вот ваше видео: {title}", attachment=doc)


    except Exception as e:
        error_msg = str(e)
        if not retry:
            if filename and os.path.exists(filename):
                os.remove(filename)
            # Пробуем еще раз с качеством 480p
            return await handle_video(message, url, retry=True)
        else:
            await message.answer(f"SONY ❌ Не удалось отправить даже в 480p: {str(e)}")

    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)

    return success, error_msg

async def handle_pdf(message: Message, url: str):
    await message.answer(f"SONY 📄 Делаю PDF страницы...")
    file_path = f"{DOWNLOAD_PATH}/page_{message.from_id}.pdf"

    # Инициализируем переменную браузера заранее
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()

            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(3)

            # ... ваш код прокрутки и ожидания селектора ...

            await page.pdf(path=file_path, format="A4", print_background=True)
            # await browser.close() <- ОТСЮДА УДАЛЯЕМ

        # Отправка файла в ВК
        uploader = DocMessagesUploader(bot.api)
        doc = await uploader.upload(
            file_source=file_path,
            peer_id=message.peer_id,
            title="Снимок_страницы.pdf"
        )
        await message.answer(attachment=doc)
        success, error_msg = (True, None)

    except Exception as e:
        await message.answer(f"SONY ❌ Ошибка PDF: {str(e)}")
        success, error_msg = (False, str(e))

    finally:
        # ЗАКРЫВАЕМ БРАУЗЕР ЗДЕСЬ (Всегда)
        if browser:
            await browser.close()
        # Удаление файла
        if os.path.exists(file_path):
            os.remove(file_path)
        return (success, error_msg)

if __name__ == "__main__":
    print("Бот запущен...")
    bot.run_forever()
