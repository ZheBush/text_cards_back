from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.config import settings
from app.core.s3 import upload_file_to_s3, generate_presigned_url
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.utils import generate_uuid
from app.models.card import Card
from app.models.card_list import CardList
from app.models.group import Group, user_group
from app.models.user import User, UserRole
from app.models.cardlistfile import CardListFile
from app.schemas.card_list import FileUploadResponse, CardListResponse, GroupFileUploadResponse, PaginatedCardListResponse
from app.services.extract_text import extract_text_from_pdf, extract_text_from_txt
from app.services.model import generate_cards

router = APIRouter()


class CardListFilter(BaseModel):
    search: Optional[str] = None
    group_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sort_by: str = "created_at"
    order: str = "desc"
    page: int = 1
    per_page: int = 10


@router.get("/", response_model=PaginatedCardListResponse)
async def get_user_card_lists(
    search: Optional[str] = Query(None),
    group_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    sort_by: str = Query("created_at", regex="^(title|created_at)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(CardList).where(CardList.user_id == current_user.id)

    if search:
        query = query.where(CardList.title.ilike(f"%{search}%"))
    if group_id:
        query = query.where(CardList.group_id == group_id)
    if date_from:
        query = query.where(CardList.created_at >= date_from)
    if date_to:
        query = query.where(CardList.created_at <= date_to)

    if sort_by == "title":
        order_col = CardList.title
    else:
        order_col = CardList.created_at
    if order == "desc":
        query = query.order_by(order_col.desc())
    else:
        query = query.order_by(order_col.asc())

    total = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total.scalar()
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "pages": (total_count + per_page - 1) // per_page,
    }


@router.post("/upload_text", response_model=GroupFileUploadResponse)
async def upload_text(
        text: str = Form(...),
        title: str = Form(...),
        cards_num: int = Form(...),
        group_id: Optional[str] = Form(None),
        current_user: Optional[User] = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    if group_id:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required for group uploads")
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
    else:
        cards = await generate_cards(text, cards_num)
        card_list_id = generate_uuid()
        new_card_list = CardList(
            id=card_list_id,
            title=title,
            user_id=current_user.id if current_user else None,
            group_id=None
        )
        db.add(new_card_list)
        await db.flush()

        all_created_cards = []
        for card_data in cards:
            card = Card(
                id=generate_uuid(),
                question=card_data["question"],
                answer=card_data["answer"],
                user_id=current_user.id if current_user else None,
                card_list_id=card_list_id,
            )
            db.add(card)
            all_created_cards.append(card)

        await db.commit()

        return {
            "card_list_id": card_list_id,
            "title": title,
            "message": "Cards generated successfully",
            "cards_count": len(cards)
        }


@router.post("/upload_txt", response_model=GroupFileUploadResponse)
async def upload_txt_file(
    title: str = Form(...),
    cards_num: int = Form(...),
    file: UploadFile = File(...),
    group_id: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    content = await file.read()
    text = extract_text_from_txt(content)

    if group_id:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required for group uploads")

        stmt = select(user_group).where(
            user_group.c.user_id == current_user.id,
            user_group.c.group_id == group_id,
            user_group.c.role_in_group == "manager"
        )
        result = await db.execute(stmt)

        if not result.first() and current_user.role != "manager":
            raise HTTPException(status_code=403, detail="You are not a manager of this group")

        members_result = await db.execute(
            select(user_group.c.user_id).where(user_group.c.group_id == group_id)
        )
        member_ids = [row[0] for row in members_result.all()]

        if not member_ids:
            raise HTTPException(status_code=400, detail="Group has no members")

        cards = await generate_cards(text, cards_num)

        for member_id in member_ids:

            file_key = f"groups/{group_id}/card_lists/{generate_uuid()}/{file.filename}"
            upload_file_to_s3(content, settings.S3_BUCKET, file_key, file.content_type)

            card_list_id = generate_uuid()

            new_card_list = CardList(
                id=card_list_id,
                title=title,
                user_id=member_id,
                group_id=group_id
            )
            db.add(new_card_list)
            await db.flush()

            db_file = CardListFile(
                filename=file.filename,
                file_key=file_key,
                mime_type=file.content_type,
                size=len(content),
                card_list_id=card_list_id,
                user_id=member_id,
            )
            db.add(db_file)

            for card_data in cards:
                card = Card(
                    id=generate_uuid(),
                    question=card_data["question"],
                    answer=card_data["answer"],
                    user_id=member_id,
                    card_list_id=card_list_id,
                )
                db.add(card)

        await db.commit()

        return {
            "group_id": group_id,
            "title": title,
            "message": f"Cards generated successfully for {len(member_ids)} members",
            "cards_count": len(cards),
            "member_count": len(member_ids)
        }

    else:
        cards = await generate_cards(text, cards_num)

        card_list_id = generate_uuid()
        new_card_list = CardList(
            id=card_list_id,
            title=title,
            user_id=current_user.id if current_user else None,
            group_id=None
        )
        db.add(new_card_list)
        await db.flush()

        for card_data in cards:
            card = Card(
                id=generate_uuid(),
                question=card_data["question"],
                answer=card_data["answer"],
                user_id=current_user.id if current_user else None,
                card_list_id=card_list_id,
            )
            db.add(card)

        await db.commit()

        return {
            "card_list_id": card_list_id,
            "title": title,
            "message": "Cards generated successfully",
            "cards_count": len(cards)
        }


@router.post("/upload_pdf", response_model=GroupFileUploadResponse)
async def upload_pdf_file(
    title: str = Form(...),
    cards_num: int = Form(...),
    file: UploadFile = File(...),
    group_id: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    content = await file.read()
    text = extract_text_from_pdf(content)

    file_key = f"groups/{group_id}/card_lists/{generate_uuid()}/{file.filename}"
    upload_file_to_s3(content, settings.S3_BUCKET, file_key, file.content_type)

    if group_id:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required for group uploads")

        stmt = select(user_group).where(
            user_group.c.user_id == current_user.id,
            user_group.c.group_id == group_id,
            user_group.c.role_in_group == "manager"
        )
        result = await db.execute(stmt)

        if not result.first() and current_user.role != "manager":
            raise HTTPException(status_code=403, detail="You are not a manager of this group")

        members_result = await db.execute(
            select(user_group.c.user_id).where(user_group.c.group_id == group_id)
        )
        member_ids = [row[0] for row in members_result.all()]

        if not member_ids:
            raise HTTPException(status_code=400, detail="Group has no members")

        cards = await generate_cards(text, cards_num)

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

        await db.commit()

        return {
            "group_id": group_id,
            "title": title,
            "message": f"Cards generated successfully for {len(member_ids)} members",
            "cards_count": len(cards),
            "member_count": len(member_ids)
        }

    else:
        cards = await generate_cards(text, cards_num)

        card_list_id = generate_uuid()
        new_card_list = CardList(
            id=card_list_id,
            title=title,
            user_id=current_user.id if current_user else None,
            group_id=None
        )
        db.add(new_card_list)
        await db.flush()

        for card_data in cards:
            card = Card(
                id=generate_uuid(),
                question=card_data["question"],
                answer=card_data["answer"],
                user_id=current_user.id if current_user else None,
                card_list_id=card_list_id,
            )
            db.add(card)

        await db.commit()

        return {
            "card_list_id": card_list_id,
            "title": title,
            "message": "Cards generated successfully",
            "cards_count": len(cards)
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

    if current_user.role != UserRole.manager:
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