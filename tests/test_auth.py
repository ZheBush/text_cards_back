import pytest
from httpx import AsyncClient

from app.models.user import UserRole
from .conftest import client


async def register_user(client: AsyncClient, email: str, password: str, role: str = "user"):
    response = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    return response


async def login_user(client: AsyncClient, email: str, password: str):
    response = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    return response


@pytest.mark.asyncio
async def test_register_login_refresh_and_logout(client: AsyncClient):
    register_response = await register_user(client, "test1@example.com", "secret123")
    assert register_response.status_code == 200
    assert register_response.json()["email"] == "test1@example.com"

    login_response = await login_user(client, "test1@example.com", "secret123")
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["token_type"] == "bearer"
    assert login_data["role"] == UserRole.user.value
    assert "access_token" in login_data

    client.cookies.update(login_response.cookies) 
    refresh_response = await client.post("/auth/refresh")
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert refresh_data["token_type"] == "bearer"
    assert refresh_data["role"] == UserRole.user.value

    client.cookies.update(refresh_response.cookies) 
    logout_response = await client.post("/auth/logout")
    assert logout_response.status_code == 200
    assert logout_response.json()["detail"] == "Logged out"

    post_logout_refresh = await client.post("/auth/refresh")
    assert post_logout_refresh.status_code == 401


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(client: AsyncClient):
    login_response = await login_user(client, "missing@example.com", "wrongpass")
    assert login_response.status_code == 401
    assert login_response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_refresh_requires_cookie(client: AsyncClient):
    response = await client.post("/auth/refresh")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing refresh token"


@pytest.mark.asyncio
async def test_register_duplicate_user_returns_400(client: AsyncClient):
    first = await register_user(client, "duplicate@example.com", "pass123")
    assert first.status_code == 200

    second = await register_user(client, "duplicate@example.com", "pass123")
    assert second.status_code == 400
    assert "User already exists" in second.json()["detail"]


@pytest.mark.asyncio
async def test_user_search_requires_manager_role(client: AsyncClient):
    await register_user(client, "member@example.com", "pass123")
    user_login = await login_user(client, "member@example.com", "pass123")
    assert user_login.status_code == 200
    token = user_login.json()["access_token"]

    user_search = await client.get(
        "/auth/users/search?email=member",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert user_search.status_code == 403

    await register_user(client, "boss@example.com", "managerpass", role=UserRole.manager.value)
    manager_login = await login_user(client, "boss@example.com", "managerpass")
    manager_token = manager_login.json()["access_token"]

    manager_search = await client.get(
        "/auth/users/search?email=member",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert manager_search.status_code == 200
    response_body = manager_search.json()
    assert isinstance(response_body, list)
    assert response_body[0]["email"] == "member@example.com"


@pytest.mark.asyncio
async def test_login_preserves_user_role(client: AsyncClient):
    """Test that login response contains user role"""
    await register_user(client, "roletest@example.com", "pass123", role=UserRole.user.value)
    login_response = await login_user(client, "roletest@example.com", "pass123")
    assert login_response.status_code == 200
    data = login_response.json()
    assert data["role"] == UserRole.user.value
    assert "user_id" in data
