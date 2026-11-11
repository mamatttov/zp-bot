# Образ с Python. slim — облегчённая версия без лишних пакетов.
FROM python:3.12-slim

# Логи сразу попадают в вывод контейнера, .pyc-файлы не создаются.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Сначала только зависимости: этот слой Docker берёт из кэша,
# пока requirements.txt не изменился.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем код проекта.
COPY schema.sql .
COPY zp_bot ./zp_bot
COPY sample ./sample

# Бот работает не от root, а от обычного пользователя.
RUN useradd --create-home bot && mkdir /app/data && chown bot /app/data
USER bot

CMD ["python", "-m", "zp_bot"]