import pytest
import uuid
from fastapi import status

def test_register(client):
    """Тест регистрации нового пользователя"""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"  # Генерация уникального email
    response = client.post("/register", json={
        "email": email,
        "password": "valid_password123"
    })
    assert response.status_code == status.HTTP_200_OK, f"Registration failed: {response.text}"
    assert "message" in response.json()

def test_register_existing_email(client, test_user):
    """Тест регистрации с существующим email"""
    response = client.post("/register", json={
        "email": test_user["email"],
        "password": "another_password"
    })
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in response.json()["detail"]

def test_login_logout(client, test_user):
    """Тест входа и выхода"""
    # Логин (должен быть успешным, так как пользователь создан в фикстуре test_user)
    login_response = client.post("/login", json={
        "email": test_user["email"],
        "password": "testpassword123"  # Пароль из фикстуры test_user
    })
    assert login_response.status_code == status.HTTP_200_OK
    assert "session_id" in login_response.cookies
    
    cookies = {"session_id": login_response.cookies["session_id"]}
    
    # Проверка доступа
    me_response = client.get("/me", cookies=cookies)
    assert me_response.status_code == status.HTTP_200_OK
    
    # Выход
    logout_response = client.post("/logout", cookies=cookies)
    assert logout_response.status_code == status.HTTP_200_OK
    
    # Проверка после выхода
    me_response_after = client.get("/me")
    assert me_response_after.status_code == status.HTTP_401_UNAUTHORIZED
