from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile
from sqlalchemy import select

from app.core.s3 import s3_client, generate_presigned_url
from app.core.config import settings
from app.models.cardlistfile import CardListFile
from app.models.card_list import CardList
from app.models.card import Card
from app.core.security import get_current_user
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

router = APIRouter(prefix="/files", tags=["Files"])

ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "application/pdf", "text/plain"]
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/upload")
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    card_list_id: str = None,
    card_id: str = None,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if card_list_id:
        card_list = await db.get(CardList, card_list_id)
        if not card_list or card_list.user_id != current_user.id:
            raise HTTPException(403, "Not owner of card list")
    if card_id:
        card = await db.get(Card, card_id)
        if not card or card.user_id != current_user.id:
            raise HTTPException(403, "Not owner of card")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(400, "CardListFile too large")

    ext = file.filename.split(".")[-1]
    file_key = f"users/{current_user.id}/{uuid.uuid4()}.{ext}"

    content = await file.read()
    s3_client.put_object(Bucket=settings.S3_BUCKET, Key=file_key, Body=content, ContentType=file.content_type)

    db_file = CardListFile(
        filename=file.filename,
        file_key=file_key,
        mime_type=file.content_type,
        size=file.size,
        card_list_id=card_list_id,
        card_id=card_id,
        user_id=current_user.id,
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    return {"id": db_file.id, "filename": db_file.filename}


@router.get("/{file_id}")
async def get_file_info(file_id: str, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    file = await db.get(CardListFile, file_id)

    if not file or file.user_id != current_user.id:
        raise HTTPException(404, "CardListFile not found")

    url = generate_presigned_url(settings.S3_BUCKET, file.file_key)
    return {"id": file.id, "filename": file.filename, "url": url, "mime_type": file.mime_type, "size": file.size}


@router.delete("/{file_id}")
async def delete_file(file_id: str, current_user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    file = await db.get(CardListFile, file_id)

    if not file or file.user_id != current_user.id:
        raise HTTPException(404, "CardListFile not found")

    s3_client.delete_object(Bucket=settings.S3_BUCKET, Key=file.file_key)
    await db.delete(file)
    await db.commit()
    return {"message": "deleted"}


@router.get("/{card_list_id}/files")
async def get_files_for_card_list(
    card_list_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    card_list = await db.get(CardList, card_list_id)
    if not card_list or card_list.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    result = await db.execute(
        select(CardListFile).where(CardListFile.card_list_id == card_list_id)
    )
    files = result.scalars().all()

    response = []
    for f in files:
        url = generate_presigned_url(settings.S3_BUCKET, f.file_key)
        response.append({
            "id": f.id,
            "filename": f.filename,
            "url": url,
            "size": f.size,
            "mime_type": f.mime_type,
        })
    return response