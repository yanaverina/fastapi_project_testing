# tests/functional/test_error_handling.py
import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_invalid_url_shortening(async_client, test_user):
    """Тест создания ссылки с невалидным URL"""
    response = await async_client.post(
        "/links/shorten",
        json={
            "original_url": "invalid url",
            "custom_alias": "badurl"
        },
        cookies=test_user["cookies"]
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid URL" in response.json()["detail"]

@pytest.mark.asyncio
async def test_duplicate_alias(async_client, test_user):
    """Тест создания ссылки с дублирующимся алиасом"""
    # Создаем первую ссылку
    await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com",
            "custom_alias": "duplicate"
        },
        cookies=test_user["cookies"]
    )
    
    # Пытаемся создать дубликат
    response = await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.org",
            "custom_alias": "duplicate"
        },
        cookies=test_user["cookies"]
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"]
