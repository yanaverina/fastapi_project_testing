# tests/functional/test_database.py
import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_delete_link(async_client, test_user):
    """Тест удаления ссылки"""
    # Создаем ссылку
    await async_client.post(
        "/links/shorten",
        json={
            "original_url": "https://example.com",
            "custom_alias": "todelete"
        },
        cookies=test_user["cookies"]
    )
    
    # Удаляем ссылку
    delete_res = await async_client.delete(
        "/links/todelete",
        cookies=test_user["cookies"]
    )
    assert delete_res.status_code == status.HTTP_200_OK
    
    # Проверяем что ссылка удалена
    stats_res = await async_client.get("/links/todelete/stats", cookies=test_user["cookies"])
    assert stats_res.status_code == status.HTTP_404_NOT_FOUND