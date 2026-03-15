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
from app.schemas.card_list import FileUploadResponse, CardListResponse, GroupFileUploadResponse
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


@router.post("/upload_text", response_model=GroupFileUploadResponse)
async def upload_text(
        text: str = Form(...),
        title: str = Form(...),
        cards_num: int = Form(...),
        group_id: str = Form(...),
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    stmt = select(user_group).where(
        user_group.c.user_id == current_user.id,
        user_group.c.group_id == group_id,
        user_group.c.role_in_group == 'manager'
    )
    result = await db.execute(stmt)

    if not result.first() and not current_user.role == "manager":
        raise HTTPException(status_code=403, detail="You are not a manager of this group")

    members_result = await db.execute(
        select(user_group.c.user_id).where(user_group.c.group_id == group_id)
    )
    member_ids = [row[0] for row in members_result.all()]

    if not member_ids:
        raise HTTPException(status_code=400, detail="Group has no members")

    await db.flush()

    cards = await generate_cards(text, cards_num)
    all_created_cards = []

    for member_id in member_ids:
        card_list_id = generate_uuid()
        new_card_list = CardList(
            id=card_list_id,
            title=title,
            user_id=member_id,
            group_id=group_id
        )
        db.add(new_card_list)
        await db.flush()

        for card_data in cards:
            card = Card(
                id=generate_uuid(),
                question=card_data["question"],
                answer=card_data["answer"],
                user_id=member_id,
                card_list_id=card_list_id,
            )
            db.add(card)
            all_created_cards.append(card)

    await db.commit()

    return {
        "group_id": group_id,
        "title": title,
        "message": f"Cards generated successfully for {len(member_ids)} members",
        "cards_count": len(cards),
        "member_count": len(member_ids)
    }


@router.post("/upload_txt", response_model=GroupFileUploadResponse)
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