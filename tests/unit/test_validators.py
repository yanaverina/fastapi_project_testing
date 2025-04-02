import pytest
from src.app.main import validate_and_fix_url

@pytest.mark.asyncio
async def test_url_validation():
    """Упрощенный, но надежный тест валидации URL"""
    # Всего 2 теста - один валидный и один невалидный
    
    # 1. Валидный URL - должен пройти
    assert await validate_and_fix_url("example.com") == "https://example.com"
    
    # 2. Невалидный URL - должен вызвать ошибку
    with pytest.raises(ValueError):
        await validate_and_fix_url("invalid")
