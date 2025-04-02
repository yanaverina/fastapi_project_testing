import pytest
import uuid
from fastapi import status
from datetime import datetime, timedelta
from src.app.database import get_connection as original_get_connection

@pytest.mark.asyncio
async def test_full_flow(async_client, db_connection):
    """Тест полного цикла работы с API (регистрация, логин, создание ссылки и т.д.)"""
    # 1. Регистрация
    email = f"test_{uuid.uuid4().hex}@example.com"
    register_response = await async_client.post("/register", json={
        "email": email,
        "password": "testpass"
    })
    assert register_response.status_code == status.HTTP_200_OK

    # 2. Логин
    login_response = await async_client.post("/login", json={
        "email": email,
        "password": "testpass"
    })
    assert login_response.status_code == status.HTTP_200_OK
    
    # Получаем cookies для аутентификации
    session_id = login_response.cookies.get("session_id")
    cookies = {"session_id": session_id}

    # 3. Проверка текущего пользователя
    me_response = await async_client.get("/me", cookies=cookies)
    assert me_response.status_code == status.HTTP_200_OK
    user_id = me_response.json()["id"]

    # 4. Создание короткой ссылки
    custom_alias = f"alias_{uuid.uuid4().hex[:6]}"
    link_response = await async_client.post("/links/shorten", json={
        "original_url": "https://example.com",
        "custom_alias": custom_alias
    }, cookies=cookies)
    
    assert link_response.status_code == status.HTTP_200_OK
    assert link_response.json()["short_code"] == custom_alias

    # 5. Проверка что ссылка сохранилась в БД
    link = await db_connection.fetchrow(
        "SELECT * FROM links WHERE short_code = $1", 
        custom_alias
    )
    assert link is not None
    assert link["custom_alias"] == custom_alias
    assert link["user_id"] == user_id

    # 6. Проверка редиректа (ИСПРАВЛЕННЫЙ ПАРАМЕТР)
    redirect_response = await async_client.get(
        f"/{custom_alias}", 
        follow_redirects=False  # Вот правильное имя параметра
    )
    assert redirect_response.status_code in (status.HTTP_302_FOUND, status.HTTP_307_TEMPORARY_REDIRECT)
    assert redirect_response.headers["location"] == "https://example.com"

    # 7. Проверка статистики
    stats_response = await async_client.get(
        f"/links/{custom_alias}/stats",
        cookies=cookies
    )
    assert stats_response.status_code == status.HTTP_200_OK
    assert stats_response.json()["clicks"] == 1

    # 8. Выход
    logout_response = await async_client.post("/logout", cookies=cookies)
    assert logout_response.status_code == status.HTTP_200_OK

    # 9. Проверка, что после выхода доступ запрещен
    me_response_after = await async_client.get("/me", cookies=cookies)
    assert me_response_after.status_code == status.HTTP_401_UNAUTHORIZED
