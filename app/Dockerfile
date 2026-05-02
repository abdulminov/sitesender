FROM python:3.11-slim


# 1. Устанавливаем системные зависимости для Postgres и Playwright в одном слое
RUN sed -i 's/deb.debian.org/mirror.yandex.ru/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    ffmpeg \
    nodejs \
    curl \
    && pip install --no-cache-dir playwright \
    && playwright install-deps chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# 3. Скачиваем сам браузер (это самый тяжелый слой, выносим в конец)
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browser
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH

RUN playwright install chromium


RUN groupadd -g 10001 appgroup && \
    useradd -r -u 10001 -g appgroup -s /sbin/nologin appuser 

COPY --chown=appuser:appgroup requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt && \
    chown -R appuser:appgroup /code $PLAYWRIGHT_BROWSERS_PATH

COPY --chown=appuser:appgroup config/ /code/config/
COPY --chown=appuser:appgroup logs/ /code/logs/
COPY --chown=appuser:appgroup SiteSender.py manage.py cookies.txt /code/
#раскомментировать после отработки!
USER 10001

