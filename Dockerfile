# Базовый образ для всех стадий
FROM python:3.9-slim as base

# Установка системных зависимостей
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Общие зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Стадия для разработки
FROM base as dev
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Стадия для тестов
FROM base as test
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt
COPY . .
CMD ["pytest", "tests/", "-v"]