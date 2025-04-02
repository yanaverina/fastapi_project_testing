import pytest
from datetime import datetime, timedelta
from fastapi import status
import uuid

@pytest.mark.asyncio
async def test_create_short_link(async_client, test_user):
    """Тест создания короткой ссылки"""
    response = await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com",
            "custom_alias": "testalias"
        },
        cookies=test_user["cookies"]
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "short_url" in data
    assert "short_code" in data
    assert data["short_code"] == "testalias"

@pytest.mark.asyncio
async def test_redirect_link(async_client, test_user):
    """Тест редиректа по короткой ссылке"""
    # 1. Создаем ссылку
    create_res = await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com",
            "custom_alias": "testredirect"
        },
        cookies=test_user["cookies"]
    )
    assert create_res.status_code == status.HTTP_200_OK
    short_code = create_res.json()["short_code"]

    # 2. Проверяем редирект для браузера
    browser_res = await async_client.get(
        f"/{short_code}",
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=False  # Важно для проверки редиректов
    )
    
    # Ваш API должен возвращать:
    # - Для браузеров: HTMLResponse с кодом 200
    # - Для других клиентов: RedirectResponse с кодом 307
    
    # Проверяем User-Agent в запросе
    user_agent = browser_res.request.headers.get("user-agent", "").lower()
    is_browser = any(browser in user_agent for browser in [
        'chrome', 'firefox', 'safari', 'edge', 'opera', 'msie'
    ])

    if is_browser:
        # Для браузеров ожидаем HTML-страницу с редиректом
        assert browser_res.status_code == status.HTTP_200_OK
        assert "text/html" in browser_res.headers["content-type"]
        assert "https://example.com" in browser_res.text
    else:
        # Для других клиентов ожидаем 307 редирект
        assert browser_res.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert browser_res.headers["location"] == "https://example.com"

    # 3. Дополнительная проверка для API клиентов
    api_res = await async_client.get(
        f"/{short_code}",
        headers={"User-Agent": "python-httpx"},
        follow_redirects=False
    )
    assert api_res.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert api_res.headers["location"] == "https://example.com"

@pytest.mark.asyncio
async def test_link_stats(async_client, test_user):
    """Тест статистики переходов по ссылке"""
    # Создаем ссылку
    create_res = await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com",
            "custom_alias": "teststats"
        },
        cookies=test_user["cookies"]
    )
    short_code = create_res.json()["short_code"]
    
    # Проверяем начальную статистику
    stats_res = await async_client.get(
        f"/links/{short_code}/stats",
        cookies=test_user["cookies"]
    )
    assert stats_res.status_code == status.HTTP_200_OK
    assert stats_res.json()["clicks"] == 0
    
    # Делаем переход
    await async_client.get(
        f"/{short_code}",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    
    # Проверяем обновленную статистику
    stats_res = await async_client.get(
        f"/links/{short_code}/stats",
        cookies=test_user["cookies"]
    )
    assert stats_res.status_code == status.HTTP_200_OK
    assert stats_res.json()["clicks"] == 1

@pytest.mark.asyncio
async def test_expired_link(async_client, test_user):
    """Тест истекшей ссылки"""
    # Создаем истекшую ссылку
    expired_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
    response = await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://expired.example.com",
            "custom_alias": "expiredlink",
            "expires_at": expired_time
        },
        cookies=test_user["cookies"]
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Проверяем ответ для истекшей ссылки
    redirect_res = await async_client.get("/expiredlink")
    assert redirect_res.status_code == status.HTTP_410_GONE
    assert "expired" in redirect_res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_nonexistent_link(async_client):
    """Тест несуществующей ссылки"""
    response = await async_client.get("/nonexistent")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_get_expired_links(async_client, test_user):
    """Тест получения списка истекших ссылок"""
    # Создаем истекшую ссылку
    expired_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
    await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://expired.example.com",
            "expires_at": expired_time
        },
        cookies=test_user["cookies"]
    )
    
    # Получаем список истекших ссылок
    response = await async_client.get("/links/expired")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0
    assert "expires_at" in response.json()[0]
