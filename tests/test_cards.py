import pytest
from httpx import AsyncClient
from app.models.card_list import CardList
from app.models.card import Card


async def register_and_login(client: AsyncClient, email: str, password: str):
    await client.post("/auth/register", json={"email": email, "password": password, "role": "user"})
    login_response = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    return login_response


@pytest.mark.asyncio
async def test_create_and_read_personal_card_list(client: AsyncClient, db_session):
    login_response = await register_and_login(client, "cardowner@example.com", "secret123")
    token = login_response.json()["access_token"]

    card_list = CardList(id="list-1", title="Test list", user_id=login_response.json()["user_id"])
    db_session.add(card_list)
    await db_session.commit()

    create_response = await client.post(
        "/cards/?card_list_id=list-1",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Q1", "answer": "A1"},
    )
    assert create_response.status_code == 200
    created_card = create_response.json()
    assert created_card["question"] == "Q1"

    list_response = await client.get(
        "/cards/card_list/list-1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    cards = list_response.json()
    assert len(cards) == 1
    assert cards[0]["answer"] == "A1"

    delete_response = await client.delete(
        f"/cards/{created_card['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Card deleted"


@pytest.mark.asyncio
async def test_delete_card_forbidden_for_non_owner(client: AsyncClient, db_session):
    owner_login = await register_and_login(client, "owner2@example.com", "secret123")
    owner_id = owner_login.json()["user_id"]
    token = owner_login.json()["access_token"]

    card_list = CardList(id="list-2", title="List 2", user_id=owner_id)
    db_session.add(card_list)
    await db_session.flush()

    card = Card(id="card-2", question="Q2", answer="A2", user_id=owner_id, card_list_id="list-2")
    db_session.add(card)
    await db_session.commit()

    stranger_login = await register_and_login(client, "stranger@example.com", "secret123")
    stranger_token = stranger_login.json()["access_token"]

    forbidden = await client.delete(
        "/cards/card-2",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "Access denied"
