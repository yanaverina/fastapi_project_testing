# tests/conftest.py
import pytest
import uuid
import asyncio
import logging
from httpx import AsyncClient
from fastapi.testclient import TestClient
from src.app.main import app
import asyncpg
from passlib.context import CryptContext

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@pytest.fixture(scope="session")
def event_loop():
    """Фикстура для создания цикла событий"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_pool():
    """Фикстура пула соединений с тестовой БД"""
    pool = await asyncpg.create_pool(
        user="test_user",
        password="test_password",
        database="test_db",
        host="localhost",
        min_size=1,
        max_size=10
    )
    
    # Инициализация тестовой БД
    async with pool.acquire() as conn:
        await conn.execute("""
            DROP TABLE IF EXISTS links, users CASCADE;
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE links (
                id SERIAL PRIMARY KEY,
                original_url TEXT NOT NULL,
                short_code TEXT UNIQUE NOT NULL,
                custom_alias TEXT,
                expires_at TIMESTAMP,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                clicks INTEGER DEFAULT 0
            );
        """)
    
    yield pool
    
    # Очистка
    await pool.close()

@pytest.fixture
async def db_connection(db_pool):
    """Фикстура отдельного соединения с БД"""
    async with db_pool.acquire() as conn:
        yield conn

@pytest.fixture
def client():
    """Синхронный тестовый клиент"""
    with TestClient(app) as client:
        yield client

@pytest.fixture
async def async_client():
    """Асинхронный тестовый клиент"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def test_user(async_client, db_pool):
    """Фикстура тестового пользователя с аутентификацией"""
    test_uid = uuid.uuid4().hex[:8]
    email = f"test_{test_uid}@example.com"
    password = "testpassword123"
    
    # Создаем пользователя напрямую в БД (быстрее чем через API)
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval(
            "INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id",
            email,
            pwd_context.hash(password)
        )
    
    # Логинимся через API для получения cookies
    login_res = await async_client.post(
        "/login",
        json={"email": email, "password": password}
    )
    assert login_res.status_code == 200
    assert "session_id" in login_res.cookies
    
    yield {
        "id": user_id,
        "email": email,
        "async_client": async_client,
        "cookies": {"session_id": login_res.cookies["session_id"]},
        "test_uid": test_uid
    }
    
    # Очистка (необязательно, так как БД пересоздается для каждого теста)
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)

@pytest.fixture(autouse=True)
async def cleanup_db(db_pool):
    """Автоматическая очистка тестовых данных после каждого теста"""
    yield
    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE links, users RESTART IDENTITY CASCADE")
