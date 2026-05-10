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


@pytest.mark.asyncio
async def test_authenticated_user_upload_text(client: AsyncClient, monkeypatch):
    """Test authenticated user can upload text and generate cards"""
    login_response = await register_and_login(client, "textupload@example.com", "secret123")
    token = login_response.json()["access_token"]
    
    # Mock generate_cards
    async def mock_generate_cards(text, num):
        return [
            {"question": "Q1", "answer": "A1"},
            {"question": "Q2", "answer": "A2"},
        ]
    
    monkeypatch.setattr("app.routers.card_lists.generate_cards", mock_generate_cards)
    
    response = await client.post(
        "/card_lists/upload_text",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "text": "Test text for cards",
            "title": "Test Deck",
            "cards_num": 2
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Deck"
    assert data["cards_count"] == 2
    assert "card_list_id" in data


@pytest.mark.asyncio
async def test_get_card_list_nonexistent_returns_404(client: AsyncClient):
    """Test retrieving non-existent card list returns 404"""
    login_response = await register_and_login(client, "notfound@example.com", "secret123")
    token = login_response.json()["access_token"]
    
    response = await client.get(
        "/card_lists/nonexistent-id",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_card_lists_sort_by_title_ascending(client: AsyncClient, db_session):
    """Test sorting card lists by title in ascending order"""
    login_response = await register_and_login(client, "sortuser@example.com", "secret123")
    user_id = login_response.json()["user_id"]
    token = login_response.json()["access_token"]
    
    lists = [
        CardList(id="list-z", title="Zebra", user_id=user_id),
        CardList(id="list-a", title="Apple", user_id=user_id),
        CardList(id="list-m", title="Mango", user_id=user_id),
    ]
    db_session.add_all(lists)
    await db_session.commit()
    
    response = await client.get(
        "/card_lists/?sort_by=title&order=asc",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["items"][0]["title"] == "Apple"
    assert data["items"][1]["title"] == "Mango"
    assert data["items"][2]["title"] == "Zebra"


@pytest.mark.asyncio
async def test_list_card_lists_pagination_second_page(client: AsyncClient, db_session):
    """Test pagination second page"""
    login_response = await register_and_login(client, "paginationuser@example.com", "secret123")
    user_id = login_response.json()["user_id"]
    token = login_response.json()["access_token"]
    
    for i in range(5):
        card_list = CardList(id=f"list-{i}", title=f"List {i}", user_id=user_id)
        db_session.add(card_list)
    await db_session.commit()
    
    # Get second page with 2 items per page
    response = await client.get(
        "/card_lists/?per_page=2&page=2",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["pages"] == 3


@pytest.mark.asyncio
async def test_guest_upload_txt_file(client: AsyncClient, monkeypatch):
    """Test guest user can upload TXT file"""
    async def mock_extract_text(content):
        return "Question? Answer"
    
    async def mock_generate_cards(text, num):
        return [{"question": "Question?", "answer": "Answer"}]
    
    monkeypatch.setattr("app.routers.card_lists.extract_text_from_txt", mock_extract_text)
    monkeypatch.setattr("app.routers.card_lists.generate_cards", mock_generate_cards)
    
    response = await client.post(
        "/card_lists/guest/upload_txt",
        data={"cards_num": 1},
        files={"file": ("test.txt", b"Test content", "text/plain")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.txt"
    assert "guest mode" in data["message"]


@pytest.mark.asyncio
async def test_guest_upload_pdf_file(client: AsyncClient, monkeypatch):
    """Test guest user can upload PDF file"""
    async def mock_extract_text(content):
        return "PDF Question? PDF Answer"
    
    async def mock_generate_cards(text, num):
        return [{"question": "PDF Question?", "answer": "PDF Answer"}]
    
    monkeypatch.setattr("app.routers.card_lists.extract_text_from_pdf", mock_extract_text)
    monkeypatch.setattr("app.routers.card_lists.generate_cards", mock_generate_cards)
    
    response = await client.post(
        "/card_lists/guest/upload_pdf",
        data={"cards_num": 1},
        files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert "guest mode" in data["message"]


@pytest.mark.asyncio
async def test_authenticated_user_upload_txt_file(client: AsyncClient, monkeypatch, db_session):
    """Test authenticated user can upload TXT file"""
    login_response = await register_and_login(client, "txtupload@example.com", "secret123")
    user_id = login_response.json()["user_id"]
    token = login_response.json()["access_token"]
    
    async def mock_extract_text(content):
        return "Q: Test? A: Answer"
    
    async def mock_generate_cards(text, num):
        return [{"question": "Test?", "answer": "Answer"}]
    
    monkeypatch.setattr("app.routers.card_lists.extract_text_from_txt", mock_extract_text)
    monkeypatch.setattr("app.routers.card_lists.generate_cards", mock_generate_cards)
    monkeypatch.setattr("app.routers.card_lists.upload_file_to_s3", lambda *args, **kwargs: None)
    
    response = await client.post(
        "/card_lists/upload_txt",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "TXT Cards",
            "cards_num": 1
        },
        files={"file": ("document.txt", b"Test content", "text/plain")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "TXT Cards"


@pytest.mark.asyncio
async def test_authenticated_user_upload_pdf_file(client: AsyncClient, monkeypatch, db_session):
    """Test authenticated user can upload PDF file"""
    login_response = await register_and_login(client, "pdfupload@example.com", "secret123")
    user_id = login_response.json()["user_id"]
    token = login_response.json()["access_token"]
    
    async def mock_extract_text(content):
        return "PDF: Question? Answer"
    
    async def mock_generate_cards(text, num):
        return [{"question": "PDF Question?", "answer": "PDF Answer"}]
    
    monkeypatch.setattr("app.routers.card_lists.extract_text_from_pdf", mock_extract_text)
    monkeypatch.setattr("app.routers.card_lists.generate_cards", mock_generate_cards)
    monkeypatch.setattr("app.routers.card_lists.upload_file_to_s3", lambda *args, **kwargs: None)
    
    response = await client.post(
        "/card_lists/upload_pdf",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "title": "PDF Cards",
            "cards_num": 1
        },
        files={"file": ("document.pdf", b"%PDF-1.4", "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "PDF Cards"
