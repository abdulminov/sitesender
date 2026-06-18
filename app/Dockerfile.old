# ---- Этап 1: сбора builder
FROM python:3.11-slim AS builder


WORKDIR /build


RUN sed -i 's/deb.debian.org/mirror.yandex.ru/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
# устанавливаем библиотеку в отдельную папку:
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Этап 2: финальный образ Final
 
FROM python:3.11-slim
# копируем только готовые скомпилированные библиотеки из этапа 1
COPY --from=builder /install /usr/local

WORKDIR /code

# устанавливаем только системные зависимости для работы (Runtime)
RUN sed -i 's/deb.debian.org/mirror.yandex.ru/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y \
    libpq5 \
    ffmpeg \
    nodejs \
    && pip install --no-cache-dir playwright \
    && playwright install-deps chromium \
    && rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browser
RUN mkdir -p $PLAYWRIGHT_BROWSERS_PATH

RUN playwright install chromium


RUN groupadd -g 10001 appgroup && \
    useradd -r -u 10001 -g appgroup -s /sbin/nologin appuser 

COPY --chown=appuser:appgroup config/ /code/config/
COPY --chown=appuser:appgroup logs/ /code/logs/
COPY --chown=appuser:appgroup SiteSender.py manage.py cookies.txt /code/
RUN chown -R appuser:appgroup /code $PLAYWRIGHT_BROWSERS_PATH
USER 10001
