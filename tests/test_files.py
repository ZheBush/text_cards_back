import pytest
from io import BytesIO
from httpx import AsyncClient
from app.core import s3
from app.models.cardlistfile import CardListFile
from app.models.card_list import CardList
from app.models.user import UserRole


async def register_and_login(client: AsyncClient, email: str, password: str):
    await client.post("/auth/register", json={"email": email, "password": password, "role": "user"})
    login_response = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    return login_response


@pytest.mark.asyncio
async def test_upload_file_rejects_invalid_type(client: AsyncClient, monkeypatch):
    login_response = await register_and_login(client, "fileuser@example.com", "secret123")
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    upload_response = await client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.gif", b"GIF89a", "image/gif")},
    )
    assert upload_response.status_code == 400
    assert "Unsupported file type" in upload_response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_and_get_file_info(client: AsyncClient, db_session, monkeypatch):
    login_response = await register_and_login(client, "owner@example.com", "secret987")
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    monkeypatch.setattr(s3.s3_client, "put_object", lambda **kwargs: None)
    monkeypatch.setattr("app.routers.files.generate_presigned_url", 
                        lambda bucket, key, expires_in=3600: f"https://s3.fake/{key}")

    file_content = b"hello world"
    upload_response = await client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.txt", file_content, "text/plain")},
    )

    assert upload_response.status_code == 200
    file_id = upload_response.json()["id"]

    info_response = await client.get(
        f"/files/{file_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert info_response.status_code == 200
    info_data = info_response.json()
    assert info_data["filename"] == "test.txt"
    assert info_data["url"].startswith("https://s3.fake/")


@pytest.mark.asyncio
async def test_delete_file_forbidden_for_non_owner(client: AsyncClient, monkeypatch):
    owner_login = await register_and_login(client, "owner2@example.com", "secret123")
    assert owner_login.status_code == 200
    owner_token = owner_login.json()["access_token"]

    monkeypatch.setattr(s3.s3_client, "put_object", lambda **kwargs: None)
    monkeypatch.setattr("app.routers.files.generate_presigned_url", 
        lambda bucket, key, expires_in=3600: f"https://s3.fake/{key}"
    )
    
    upload_response = await client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("secret.txt", b"secret data", "text/plain")},
    )
    assert upload_response.status_code == 200
    file_id = upload_response.json()["id"]

    stranger_login = await register_and_login(client, "stranger2@example.com", "secret123")
    assert stranger_login.status_code == 200
    stranger_token = stranger_login.json()["access_token"]

    delete_response = await client.delete(
        f"/files/{file_id}",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "CardListFile not found"


@pytest.mark.asyncio
async def test_upload_pdf_file(client: AsyncClient, monkeypatch):
    """Test uploading PDF file"""
    login_response = await register_and_login(client, "pdf@example.com", "secret123")
    token = login_response.json()["access_token"]
    
    monkeypatch.setattr(s3.s3_client, "put_object", lambda **kwargs: None)
    monkeypatch.setattr("app.routers.files.generate_presigned_url", 
                        lambda bucket, key, expires_in=3600: f"https://s3.fake/{key}")
    
    response = await client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("document.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "document.pdf"


@pytest.mark.asyncio
async def test_upload_png_file(client: AsyncClient, monkeypatch):
    """Test uploading PNG image file"""
    login_response = await register_and_login(client, "png@example.com", "secret123")
    token = login_response.json()["access_token"]
    
    monkeypatch.setattr(s3.s3_client, "put_object", lambda **kwargs: None)
    monkeypatch.setattr("app.routers.files.generate_presigned_url", 
                        lambda bucket, key, expires_in=3600: f"https://s3.fake/{key}")
    
    response = await client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("image.png", b"\\x89PNG\\r\\n", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "image.png"

