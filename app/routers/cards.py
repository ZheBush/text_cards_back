from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.utils import generate_uuid
from app.models.card import Card
from app.models.card_list import CardList
from app.models.group import user_group
from app.models.user import UserRole, User
from app.schemas.card import CardCreate, CardResponse

router = APIRouter()


@router.get("/card_list/{card_list_id}", response_model = List[CardResponse])
async def get_cards_from_list(
        card_list_id: str,
        current_user: Optional[User] = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    card_list = await db.get(CardList, card_list_id)
    if not card_list:
        raise HTTPException(status_code=404, detail="Card list not found")

    if card_list.user_id is None:
        # Guest card list
        query = select(Card).where(Card.card_list_id == card_list_id)
    else:
        if not current_user or card_list.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        query = select(Card).where(Card.card_list_id == card_list_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=CardResponse)
async def create_card(
        card_list_id: str,
        new_card: CardCreate,
        current_user: Optional[User] = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    card_list = await db.get(CardList, card_list_id)
    if not card_list:
        raise HTTPException(status_code=404, detail="Card list not found")

    if card_list.user_id is not None:
        if not current_user or card_list.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    card = Card(
        id=generate_uuid(),
        question=new_card.question,
        answer=new_card.answer,
        user_id=current_user.id if current_user else None,
        card_list_id=card_list_id,
    )

    db.add(card)
    await db.commit()
    await db.refresh(card)

    return card


@router.delete("/{card_id}")
async def delete_card(
        card_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    card = await db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    card_list = await db.get(CardList, card.card_list_id)
    if not card_list:
        raise HTTPException(status_code=404, detail="Card list not found")

    if card_list.group_id:
        # Group card
        stmt = select(user_group).where(
            user_group.c.user_id == current_user.id,
            user_group.c.group_id == card_list.group_id,
            user_group.c.role_in_group == 'manager'
        )
        result = await db.execute(stmt)
        if not result.first() and current_user.role != UserRole.manager:
            raise HTTPException(status_code=403, detail="Only managers can delete group cards")
    else:
        # Personal card
        if card.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    await db.delete(card)
    await db.commit()

    return {"message": "Card deleted"}
