from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.utils import generate_uuid
from app.models.card import Card
from app.models.card_list import CardList
from app.schemas.card import CardCreate, CardResponse
from app.schemas.card_list import CardListResponse

router = APIRouter()


@router.get("/card_list/{card_list_id}", response_model = List[CardResponse])
async def get_cards_from_list(
        card_list_id: str,
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    query = select(Card).where(Card.card_list_id == card_list_id, Card.user_id == current_user.id)
    result = await db.execute(query)

    return result.scalars().all()


@router.post("/", response_model=CardResponse)
async def create_card(
        card_list_id: str,
        new_card: CardCreate,
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    query = select(CardList).where(CardList.id == card_list_id, CardList.user_id == current_user.id)
    res = await db.execute(query)
    card_list = res.scalars().first()

    if not card_list:
        raise HTTPException(
            status_code = 404,
            detail = "Cards not found"
        )

    card = Card(
        id=generate_uuid(),
        question=new_card.question,
        answer=new_card.answer,
        user_id=current_user.id,
        card_list_id=card_list_id,
    )

    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


# @router.delete("/{card_list_id}")
# async def delete_card(
#     card_list_id: str,
#     current_user = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     query = select(Card).where(Card.id == card_list_id)
#     res = await db.execute(query)
#     card = res.scalars().first()
#
#     if not card or card.user_id != current_user.id:
#         raise HTTPException(
#             status_code=404,
#             detail="Card not found"
#         )
#
#     await db.execute(delete(Card).where(Card.id == card_list_id))
#     await db.commit()
#     return {"detail": "Card deleted"}


# @router.put("/{card_list_id}", response_model=CardResponse)
# async def update_card(
#     card_list_id: str,
#     updated_data: CardUpdate,
#     current_user = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     query = select(Card).where(Card.id == card_list_id)
#     res = await db.execute(query)
#     card = res.scalars().first()
#
#     if not card or card.user_id != current_user.id:
#         raise HTTPException(
#             status_code=404,
#             detail="Card not found"
#         )
#
#     if updated_data.question is not None:
#         card.question = updated_data.question
#     if updated_data.answer is not None:
#         card.answer = updated_data.answer
#
#     db.add(card)
#     await db.commit()
#     await db.refresh(card)
#     return card
