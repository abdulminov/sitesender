import os
import re
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from vkbottle.bot import Bot, Message
from vkbottle import VideoUploader, DocMessagesUploader
from yt_dlp import YoutubeDL
from playwright.async_api import async_playwright

load_dotenv()
# --- НАСТРОЙКИ ---
# Вставьте ваш токен из настроек сообщества
token = os.getenv("BOT_TOKEN")
bot = Bot(token)

# Если переменная не задана в системе, качаем в текущую папку ./downloads
raw_path = os.getenv("DOWNLOAD_PATH", "./temp_downloads")
DOWNLOAD_PATH=Path(raw_path).resolve()
# Создаем папку, если её нет (важно для первого запуска)
DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
print(f"Файлы будут сохраняться в: {DOWNLOAD_PATH}")

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


YDL_OPTIONS = {
    # Принудительно ищем видео в h264 (avc1) и аудио в m4a
    'format': 'bestvideo[vcodec^=avc1][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': f'{DOWNLOAD_PATH}/video_%(id)s.%(ext)s',
    'noplaylist': True,
    'cookiefile': 'cookies.txt',
    # Добавляем совместимость для mp4
    'merge_output_format': 'mp4',
}




@bot.on.message()
async def main_handler(message: Message):
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
        await handle_video(message, full_url)
    else:
        # Сюда попадут обычные сайты и страницы поиска YouTube (напр. youtube.com?...)
        await handle_pdf(message, full_url)


async def handle_video(message: Message, url: str):
    await message.answer("🎞 Обнаружено видео. Начинаю скачивание...")
    filename = ""
    try:
        # Скачивание видео через yt-dlp во внешнем потоке, чтобы не вешать бота
        with YoutubeDL(YDL_OPTIONS) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get('title', 'YouTube Video')

        # 1. Указываем ID группы вручную (БЕЗ запросов к API, чтобы не было ошибок)

        await message.answer("✅ Видео скачано. Отправляю файл...")

        # Загружаем видео как ДОКУМЕНТ в личные сообщения
        # Это работает с токеном группы без ограничений
        uploader = DocMessagesUploader(bot.api)

        doc = await uploader.upload(
            file_source=filename,
            peer_id=message.peer_id,
            title=f"{title}.mp4"
        )

        await message.answer(f"🎬 Вот ваше видео: {title}", attachment=doc)




    except Exception as e:
        await message.answer(f"❌ Ошибка видео: {str(e)}")
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)


async def handle_pdf(message: Message, url: str):
    await message.answer(f"📄 Делаю PDF страницы...")
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

    except Exception as e:
        await message.answer(f"❌ Ошибка PDF: {str(e)}")
    finally:
        # ЗАКРЫВАЕМ БРАУЗЕР ЗДЕСЬ (Всегда)
        if browser:
            await browser.close()
        # Удаление файла
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    print("Бот запущен...")
    bot.run_forever()
