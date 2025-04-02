import pytest
from datetime import datetime, timedelta
from fastapi import status

@pytest.mark.asyncio
async def test_get_expired_links(test_user, db_connection):
    async_client = test_user["async_client"]
    cookies = test_user["cookies"]
    
    # 1. Создаем истекшую ссылку
    expired_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
    response = await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://expired.test",
            "expires_at": expired_time,
            "custom_alias": "expiredtest"  # Используем правильное имя поля
        },
        cookies=cookies
    )
    assert response.status_code == status.HTTP_200_OK
    
    # 2. Проверяем ответ для истекшей ссылки
    redirect_response = await async_client.get("/expiredtest")
    
    # Допустимые варианты:
    # - 410 Gone (если ссылка существует, но истекла)
    # - 404 Not Found (если ссылка автоматически удаляется после истечения)
    assert redirect_response.status_code in (status.HTTP_410_GONE, status.HTTP_404_NOT_FOUND)

@pytest.mark.asyncio
async def test_me_endpoint(test_user):
    async_client = test_user["async_client"]
    cookies = test_user["cookies"]
    
    # Проверяем endpoint /me
    response = await async_client.get("/me", cookies=cookies)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == test_user["email"]

@pytest.mark.asyncio
async def test_browser_redirect(test_user):
    async_client = test_user["async_client"]
    cookies = test_user["cookies"]
    
    # 1. Создаем ссылку
    response = await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://browser.test",
            "custom_alias": "browsertest"  # Используем правильное имя поля
        },
        cookies=cookies
    )
    assert response.status_code == status.HTTP_200_OK
    
    # 2. Проверяем редирект
    redirect_response = await async_client.get(
        "/browsertest",
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=False  # Важно для проверки редиректов
    )
    
    # Допустимые варианты:
    # - 200 OK с HTML-страницей редиректа
    # - 307/302 Temporary Redirect
    # - 404 если ссылка не найдена (но это не должно происходить)
    assert redirect_response.status_code in (
        status.HTTP_200_OK,
        status.HTTP_307_TEMPORARY_REDIRECT,
        status.HTTP_302_FOUND
    )
    
    if redirect_response.status_code == status.HTTP_200_OK:
        assert "text/html" in redirect_response.headers["content-type"]
        assert "https://browser.test" in redirect_response.text
    else:
        assert redirect_response.headers["location"] == "https://browser.test"
