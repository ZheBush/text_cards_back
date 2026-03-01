from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.utils import generate_uuid
from app.models.card import Card
from app.models.card_list import CardList
from app.models.group import Group, user_group
from app.models.user import User, UserRole
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
        text: str = Form(...),
        title: str = Form(...),
        cards_num: int = Form(...),
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
        title: str = Form(...),
        cards_num: int = Form(...),
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
        title: str = Form(...),
        cards_num: int = Form(...),
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


async def are_users_in_same_group(db: AsyncSession, user1_id: str, user2_id: str) -> bool:
    subq = select(user_group.c.group_id).where(user_group.c.user_id == user1_id).subquery()
    result = await db.execute(
        select(user_group).where(
            user_group.c.user_id == user2_id,
            user_group.c.group_id.in_(subq)
        )
    )
    return result.first() is not None


async def check_manager_permission(
    current_user: User,
    target_user_id: Optional[str],
    db: AsyncSession
) -> Optional[str]:
    if target_user_id is None:
        return current_user.id

    if current_user.role != UserRole.MANAGER:
        raise HTTPException(
            status_code=403,
            detail="Only managers can create cards for other users"
        )

    target_user = await db.get(User, target_user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    if not await are_users_in_same_group(db, current_user.id, target_user_id):
        raise HTTPException(
            status_code=403,
            detail="Target user is not in any of your groups"
        )

    return target_user_id


@router.get("/", response_model=List[CardListResponse])
async def get_user_card_lists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(CardList).where(CardList.user_id == current_user.id)
    result = await db.execute(query)
    card_lists = result.scalars().all()
    return card_lists


@router.post("/guest/upload_text")
async def guest_upload_text(
        text: str = Form(...),
        cards_num: int = Form(...)
):
    cards_data = await generate_cards(text, cards_num)

    return {
        "cards": cards_data,
        "message": "Cards generated successfully (guest mode)",
    }


@router.post("/guest/upload_txt")
async def guest_upload_txt_file(
        cards_num: int = Form(...),
        file: UploadFile = File(...)
):
    content = await file.read()
    text = extract_text_from_txt(content)

    cards_data = await generate_cards(text, cards_num)

    return {
        "cards": cards_data,
        "filename": file.filename,
        "message": "Cards generated successfully from TXT (guest mode)",
    }


@router.post("/guest/upload_pdf")
async def guest_upload_pdf_file(
        cards_num: int = Form(...),
        file: UploadFile = File(...)
):
    content = await file.read()
    text = extract_text_from_pdf(content)

    cards_data = await generate_cards(text, cards_num)

    return {
        "cards": cards_data,
        "filename": file.filename,
        "message": "Cards generated successfully from PDF (guest mode)",
    }


@router.post("/upload_text", response_model=FileUploadResponse)
async def upload_text(
    text: str = Form(...),
    title: str = Form(...),
    cards_num: int = Form(...),
    target_user_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id_for_cards = await check_manager_permission(current_user, target_user_id, db)

    card_list_id = generate_uuid()
    new_card_list = CardList(
        id=card_list_id,
        title=title,
        user_id=user_id_for_cards,
    )
    db.add(new_card_list)
    await db.flush()

    cards_data = await generate_cards(text, cards_num)
    created_cards = []

    for card in cards_data:
        card = Card(
            id=generate_uuid(),
            question=card["question"],
            answer=card["answer"],
            user_id=user_id_for_cards,
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
        "message": "Text processed successfully",
    }


@router.post("/upload_txt", response_model=FileUploadResponse)
async def upload_txt_file(
    title: str = Form(...),
    cards_num: int = Form(...),
    file: UploadFile = File(...),
    target_user_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id_for_cards = await check_manager_permission(current_user, target_user_id, db)

    content = await file.read()
    text = extract_text_from_txt(content)

    card_list_id = generate_uuid()
    new_card_list = CardList(
        id=card_list_id,
        title=title,
        user_id=user_id_for_cards,
    )
    db.add(new_card_list)
    await db.flush()

    cards_data = await generate_cards(text, cards_num)
    created_cards = []

    for card in cards_data:
        card = Card(
            id=generate_uuid(),
            question=card["question"],
            answer=card["answer"],
            user_id=user_id_for_cards,
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
        "message": "TXT file processed successfully",
    }


@router.post("/upload_pdf", response_model=FileUploadResponse)
async def upload_pdf_file(
    title: str = Form(...),
    cards_num: int = Form(...),
    file: UploadFile = File(...),
    target_user_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_id_for_cards = await check_manager_permission(current_user, target_user_id, db)

    content = await file.read()
    text = extract_text_from_pdf(content)

    card_list_id = generate_uuid()
    new_card_list = CardList(
        id=card_list_id,
        title=title,
        user_id=user_id_for_cards,
    )
    db.add(new_card_list)
    await db.flush()

    cards_data = await generate_cards(text, cards_num)
    created_cards = []

    for card in cards_data:
        card = Card(
            id=generate_uuid(),
            question=card["question"],
            answer=card["answer"],
            user_id=user_id_for_cards,
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
        "message": "PDF file processed successfully",
    }