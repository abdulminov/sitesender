# Используем официальный образ Python 2025 года
FROM python:3.11-slim


# Устанавливаем системные зависимости: ffmpeg и nodejs
RUN apt-get update && apt-get install -y --no-install-recommends\
	ffmpeg \
	nodejs \
	curl \
	&& rm -rf /var/lib/apt/lists/*

#Устанавливаем рабочую директорию
WORKDIR /app

#Копируем список зависимостей
COPY requirements.txt .

#Устанавливаем библиотеки Python
RUN pip install --no-cache-dir -r requirements.txt

#Устанавливаем Playwright и браузер Chromium
RUN pip install playwright && \
	playwright install chromium && \
	playwright install-deps chromium

COPY SiteSender.py .

#Запускаем бота
CMD ["python", "SiteSender.py"]

