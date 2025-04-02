# tests/functional/test_redirects.py
import pytest
from datetime import datetime, timedelta
from fastapi import status

@pytest.mark.asyncio
async def test_expired_redirect(test_user, db_connection):
    """Тест редиректа для истекшей ссылки"""
    async_client = test_user["async_client"]
    
    # 1. Проверяем структуру БД
    columns = await db_connection.fetch(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'links'"
    )
    assert any(c['column_name'] == 'custom_alias' for c in columns), "Column custom_alias missing in database"
    
    # 2. Создаем истекшую ссылку
    expired_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
    response = await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://expired.test",
            "expires_at": expired_time,
            "custom_alias": "expiredtest"
        },
        cookies=test_user["cookies"]
    )
    assert response.status_code == status.HTTP_200_OK
    
    # 3. Проверяем ответ для истекшей ссылки
    redirect_response = await async_client.get("/expiredtest")
    assert redirect_response.status_code == status.HTTP_410_GONE

@pytest.mark.asyncio
async def test_browser_redirect(test_user, db_connection):
    """Тест редиректа для браузера"""
    async_client = test_user["async_client"]
    
    # 1. Создаем ссылку
    response = await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://browser.test",
            "custom_alias": "browsertest"
        },
        cookies=test_user["cookies"]
    )
    assert response.status_code == status.HTTP_200_OK
    
    # 2. Проверяем редирект
    redirect_response = await async_client.get(
        "/browsertest",
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=False  # Отключаем автоматическое следование редиректу
    )
    
    # Проверяем что это редирект (307 или 302)
    assert redirect_response.status_code in (status.HTTP_307_TEMPORARY_REDIRECT, status.HTTP_302_FOUND)
    
    # Проверяем что Location header содержит правильный URL
    assert redirect_response.headers["location"] == "https://browser.test"
