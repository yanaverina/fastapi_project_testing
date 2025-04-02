# 🧪 Тестирование приложения fastapi_project

---

## ⚙️ Предварительные требования

- Python 3.8+
- PostgreSQL для тестовой БД
- Установленные зависимости:

```bash
pip install -r requirements.txt
```

# 🛠️ Настройка окружения
Создайте файл .env.test в корне проекта:

```ini
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/test_db
```

Примените миграции к тестовой БД:

```bash
alembic upgrade head
```

# Запуск тестов
```bash
# Все тесты
pytest tests/

# С подробным выводом
pytest -v tests/

# Конкретный тестовый файл
pytest tests/functional/test_links.py

# Один конкретный тест
pytest tests/functional/test_links.py::test_create_short_link

# Остановка после первой ошибки
pytest -x tests/

# Только последние упавшие тесты
pytest --lf tests/
```

# Анализ покрытия кода
```bash
# Запуск с измерением покрытия
coverage run -m pytest tests/

# Просмотр отчета
coverage report -m

# Генерация HTML-отчета
coverage html
```

# 🚀 Запуск основного приложения

1. Соберите и запустите контейнеры:
```bash
docker-compose up -d --build
```

2. Запустите тесты:

```bash
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```


# 🖥 Ручной запуск тестов
Запустите тестовую БД:

```bash
docker run --name test-db -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test_db -p 5433:5432 -d postgres:13
```

Установите зависимости и запустите тесты:

```bash
python -m pip install -r requirements.txt
TEST_DATABASE_URL=postgresql://test:test@localhost:5433/test_db pytest -v tests/
```

# 🛑 Остановка контейнеров
Остановите тестовые контейнеры:

```bash
docker-compose -f docker-compose.test.yml down
```

Удалите тестовую БД:

```bash
docker stop test-db && docker rm test-db
```

Очистите систему:

```bash
docker system prune -f
```


# 📊 Анализ результатов

91% итоговое покрытие тестами

![Screenshot from 2025-04-03 00-42-34](https://github.com/user-attachments/assets/1e3229fe-59e7-4f19-949b-dd377080e507)
