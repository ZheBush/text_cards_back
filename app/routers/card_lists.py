from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.utils import generate_uuid
from app.models.card import Card
from app.models.card_list import CardList
from app.schemas.card_list import FileUploadResponse, CardListResponse
from app.services.model import generate_cards
from app.services.pdf import extract_text_from_pdf

router = APIRouter()


@router.get("/", response_model=List[CardListResponse])
async def get_user_card_lists(
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    query = select(CardList).where(CardList.user_id == current_user.id)
    result = await db.execute(query)
    card_lists = result.scalars().all()

    return card_lists


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
        file: UploadFile = File(...),
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    card_list_id = generate_uuid()

    new_card_list = CardList(
        id=card_list_id,
        filename=file.filename,
        user_id=current_user.id,
    )

    db.add(new_card_list)
    await db.flush()

    content = await file.read()
    text = extract_text_from_pdf(content)

    cards = await generate_cards(text)
    created_cards = []

    for card in cards:
        card = Card(
                id=generate_uuid(),
                question=card["question"],
                answer=card["answer"],
                user_id=current_user.id,
                card_list_id=card_list_id,
            )
        db.add(card)
        created_cards.append(card)

    await db.commit()
    await db.refresh(new_card_list)

    for card in created_cards:
        await db.refresh(card)

    return {
        "card_list_id": card_list_id,
        "filename": file.filename,
        "message": "File processed successfully",
    }
#
#
# @router.delete("/{card_list_id}")
# async def delete_card_list(
#     card_list_id: str,
#     current_user = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     query = select(CardList).where(CardList.id == card_list_id)
#     res = await db.execute(query)
#     group = res.scalars().first()
#
#     if not group or group.user_id != current_user.id:
#         raise HTTPException(
#             status_code=404,
#             detail="CardList not found"
#         )
#
#     await db.execute(delete(Card).where(Card.card_list_id == card_list_id))
#     await db.execute(delete(CardList).where(CardList.id == card_list_id))
#     await db.commit()
#
#     return {"detail": "CardList deleted"}
