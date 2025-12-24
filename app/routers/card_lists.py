from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.utils import generate_uuid
from app.models.card import Card
from app.models.card_list import CardList
from app.schemas.card_list import FileUploadResponse, CardListResponse
from app.services.extract_text import extract_text_from_pdf, extract_text_from_txt
from app.services.model import generate_cards

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


@router.post("/upload_text", response_model=FileUploadResponse)
async def upload_text(
        text: str,
        title: str,
        cards_num: int,
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    card_list_id = generate_uuid()

    new_card_list = CardList(
        id=card_list_id,
        title=title,
        user_id=current_user.id,
    )

    db.add(new_card_list)
    await db.flush()

    cards = await generate_cards(text, cards_num)
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
        "title": title,
        "message": "File processed successfully",
    }


@router.post("/upload_txt", response_model=FileUploadResponse)
async def upload_txt_file(
        title: str,
        cards_num: int,
        file: UploadFile = File(...),
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    card_list_id = generate_uuid()

    new_card_list = CardList(
        id=card_list_id,
        title=title,
        user_id=current_user.id,
    )

    db.add(new_card_list)
    await db.flush()

    content = await file.read()
    text = extract_text_from_txt(content)

    cards = await generate_cards(text, cards_num)
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
        "title": title,
        "message": "File processed successfully",
    }


@router.post("/upload_pdf", response_model=FileUploadResponse)
async def upload_pdf_file(
        title: str,
        cards_num: int,
        file: UploadFile = File(...),
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    card_list_id = generate_uuid()

    new_card_list = CardList(
        id=card_list_id,
        title = title,
        user_id=current_user.id,
    )

    db.add(new_card_list)
    await db.flush()

    content = await file.read()
    text = extract_text_from_pdf(content)

    cards = await generate_cards(text, cards_num)
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
        "title": title,
        "message": "File processed successfully",
    }