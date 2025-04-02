# tests/functional/test_database.py
import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_redis_fallback(async_client, test_user, monkeypatch):
    """Тест работы fallback при недоступности Redis"""
    # Эмулируем недоступность Redis
    monkeypatch.setattr("src.app.main.redis_client", None)
    
    # Проверяем работу аутентификации
    response = await async_client.get("/me", cookies=test_user["cookies"])
    assert response.status_code == status.HTTP_200_OK

