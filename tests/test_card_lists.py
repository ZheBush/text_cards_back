import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from app.models.card_list import CardList


async def register_and_login(client: AsyncClient, email: str, password: str):
    await client.post("/auth/register", json={"email": email, "password": password, "role": "user"})
    login_response = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    return login_response


@pytest.mark.asyncio
async def test_list_card_lists_with_filter_sort_and_pagination(client: AsyncClient, db_session):
    login_response = await register_and_login(client, "filteruser@example.com", "secret123")
    user_id = login_response.json()["user_id"]
    token = login_response.json()["access_token"]

    now = datetime.now(timezone.utc)
    lists = [
        CardList(id="list-a", title="Alpha", user_id=user_id, created_at=now - timedelta(days=3)),
        CardList(id="list-b", title="Beta", user_id=user_id, created_at=now - timedelta(days=2)),
        CardList(id="list-c", title="Gamma", user_id=user_id, created_at=now - timedelta(days=1)),
    ]
    db_session.add_all(lists)
    await db_session.commit()

    response = await client.get(
        "/card_lists/?search=a&sort_by=title&order=asc&page=1&per_page=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["page"] == 1
    assert body["per_page"] == 2
    assert body["total"] == 3  
    assert body["pages"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["title"] == "Alpha"


@pytest.mark.asyncio
async def test_card_list_by_id_requires_owner(client: AsyncClient, db_session):
    owner_login = await register_and_login(client, "owner3@example.com", "secret123")
    owner_id = owner_login.json()["user_id"]
    owner_token = owner_login.json()["access_token"]

    card_list = CardList(id="list-3", title="Hidden list", user_id=owner_id)
    db_session.add(card_list)
    await db_session.commit()

    guest_login = await register_and_login(client, "guestuser@example.com", "secret123")
    guest_token = guest_login.json()["access_token"]

    response = await client.get(
        "/card_lists/list-3",
        headers={"Authorization": f"Bearer {guest_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Card list not found"


@pytest.mark.asyncio
async def test_card_lists_validation_errors(client: AsyncClient):
    login_response = await register_and_login(client, "filtererror@example.com", "secret123")
    token = login_response.json()["access_token"]

    response = await client.get(
        "/card_lists/?sort_by=invalid&order=desc&page=0&per_page=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
